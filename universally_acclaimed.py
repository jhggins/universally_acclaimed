# universally_acclaimed.py
# Generate simple line charts of the number of Metacritic "universally acclaimed"
# albums, for several major genres, per release year from 2000 to `current year`-1.

# Any single album can belong to more than one genre, and compound genres are
# split into their component genres (For example, a "Pop/Rock" album is a Pop
# album and a Rock album).

# Requires bs4, matplotlib, pandas, and numpy packages, all of which are
# available in the Anaconda Distribution of Python3.

import requests
import re
from itertools import count
from collections import defaultdict
from time import sleep
from datetime import datetime as dt
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import pandas as pd
import numpy as np
from functools import reduce

metacritic = 'https://www.metacritic.com'
# generic browser-spoofing headers to enable web scraping from Metacritic
user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
headers={'User-Agent':user_agent}

def sleepy_soup(url):
    # to prevent rate-limiting error
    sleep(1)
    html = requests.get(url, headers=headers).text
    return BeautifulSoup(html, features="lxml")

def get_universally_acclaimed(url, colname, maxs):
    global scoresdf
    for page in count(0):
        print("page:", page)
        url_page = url.format(page)
        soup = sleepy_soup(url_page)
        u_a_albums = soup.findAll(class_=re.compile("^product release_product"))
        for a in u_a_albums:
            album_link = metacritic + a.find('a')['href']
            
            score = a.find(class_=re.compile("metascore_w")).contents[0]
            if float(score) < float(maxs): break
            scoresdf.loc[album_link, colname] = score #float score ???
            
            date = a.find(class_="stat release_date full_release_date").contents[3].string
            scoresdf.loc[album_link, 'date'] = date
        else: continue
        break

def get_user_picks():
    users_url = metacritic + '/browse/albums/score/userscore/all/filtered?page={}'
    print('getting universally acclaimed albums according to users:')
    get_universally_acclaimed(users_url, 'user', '8.1')

def get_critic_picks():
    critics_url = metacritic + '/browse/albums/score/metascore/all/filtered?page={}'
    print('getting universally acclaimed albums according to critics:')
    get_universally_acclaimed(critics_url, 'meta', '81')

def populate_scores(refresh=False):
    filename = 'scores.csv'
    global scoresdf
    if refresh:
        scoresdf = pd.DataFrame(columns=['date', 'user', 'meta'])
        get_user_picks()
        get_critic_picks()
        scoresdf.to_csv(filename)
    else:
        scoresdf = pd.read_csv(filename, index_col=0)

def populate_genres():
    '''Populates a dataframe with a boolean mask for each album link (rows) indicating
    which genres (columns) each album encompasses. I assume genres are not subject to change
    over time like user scores and metascores are.'''
    filename = 'genres.csv'
    global genresdf
    try:
        genresdf = pd.read_csv(filename, index_col=0)
    except:
        genresdf = pd.DataFrame()
    any_new = False
    for album_link in scoresdf.index:
        if album_link in genresdf.index: continue
        any_new = True
        print('getting genres for', album_link)
        album_soup = sleepy_soup(album_link)
        genres = [x.string for x in album_soup.findAll(itemprop="genre")]
        if len(genresdf.columns) > 0:
            genresdf.loc[album_link] = [False]*len(genresdf.columns)
        for g in genres:
            if g not in genresdf: genresdf[g] = False
            genresdf.loc[album_link, g] = True
        if len(genresdf)%100 == 0: genresdf.to_csv(filename)
    genresdf = genresdf.filter(items=scoresdf.index, axis=0)
    if any_new: genresdf.to_csv(filename)

populate_scores()
populate_genres()

mgenresdf = pd.DataFrame(False, columns=genresdf.columns, index=genresdf.index)
subsets = defaultdict(set)
subgenres = dict()
words = lambda g: re.findall('\w+&?\w*', g)
for genre in mgenresdf.columns:
    for word in words(genre):
        subsets[word].add(genre)
for genre in mgenresdf.columns:
    subgenres[genre] = set.intersection(*map(subsets.get, words(genre)))
    mgenresdf[genre] = reduce(np.logical_or, map(genresdf.get, subgenres[genre]), False)

supergenres = defaultdict(set)
for genre, subs in subgenres.items():
    for sub in subs:
        supergenres[sub].add(genre)

albums_per_genre = mgenresdf.sum(axis=0)

ag = 'All'
mgenresdf[ag] = True

scoresdf['year'] = scoresdf['date'].str.split(expand=True)[2].astype(int)
pertinent_years = range(2000, dt.now().year)
genres_years_usernua = pd.DataFrame(0, columns=mgenresdf.columns, index=pertinent_years)
genres_years_metanua = pd.DataFrame(0, columns=mgenresdf.columns, index=pertinent_years)
for link in scoresdf.index:
    year = scoresdf['year'][link]
    if not year in pertinent_years: continue
    if not pd.isnull(scoresdf.loc[link, 'user']):
        genres_years_usernua.loc[year] += mgenresdf.loc[link]
    if not pd.isnull(scoresdf.loc[link, 'meta']):
        genres_years_metanua.loc[year] += mgenresdf.loc[link]

fig = plt.figure(figsize=(14, 75))
displayed_genres = 28
gs = GridSpec((displayed_genres+1)//2*3 + 4, 6)

def current_plot():
    yield fig.add_subplot(gs[:4,1:5])
    for i in range(displayed_genres):
        yield fig.add_subplot(gs[4+i//2*3:7+i//2*3, (i%2)*3:(i%2+1)*3])
plots = current_plot()

def graph(plot, genre):
    plot.title.set_text(genre + ' albums')
    plot.locator_params(integer=True)
    plot.set_xticks(range(pertinent_years[0], pertinent_years[-1]+1, 4))
    plot.plot(genres_years_usernua[genre])
    plot.plot(genres_years_metanua[genre])

plot = next(plots)
graph(plot, ag)
plot.legend(["According to users", "According to critics"], loc="upper right", fontsize=16)
plot.title.set_fontsize(16)

supers_already_graphed = set()
for genre, number in sorted(albums_per_genre.items(), key=lambda x: x[-1], reverse=True):
    if genre in supers_already_graphed: continue
    if albums_per_genre[genre] < max(albums_per_genre[sup] for sup in supergenres[genre]): continue
    try: plot = next(plots)
    except StopIteration: break
    graph(plot, genre)
    supers_already_graphed.update(supergenres[genre])

fig.suptitle('Metacritic: number of "universally acclaimed"\n albums per release year', fontsize=20, y=.9)
fig.subplots_adjust(wspace=1, hspace=1)
fig.savefig('universally_acclaimed_{}'.format(dt.now().year), bbox_inches='tight')
