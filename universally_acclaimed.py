# universally_acclaimed.py
# generate a simple line chart of the number of Metacritic "universally
# acclaimed" albums per release year, from 2000 to `current year`-1

import requests
import re
from itertools import count
from collections import Counter
from time import sleep
from datetime import datetime as dt
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

# generic browser-spoofing headers to enable web scraping from Metacritic
user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
headers={'User-Agent':user_agent}

def get_universally_acclaimed(years, url, maxs):
    for page in count(0):
        print("page:", page)
        print("scores:", len(years))
        url_page = url.format(page)
        sleep(1) # to prevent rate-limiting error
        html = requests.get(url_page, headers=headers).text
        soup = BeautifulSoup(html, features="lxml")
        albums = soup.findAll(class_=re.compile("^product release_product"))
        for a in albums:
            score = a.find(class_=re.compile("metascore_w")).contents[0]
            if score < maxs: break
            year = int(a.find(class_="stat release_date full_release_date").contents[3].string[-4:])
            years.append(year)
        else: continue
        break

users = []
users_url = 'https://www.metacritic.com/browse/albums/score/userscore/all/filtered?page={}'
get_universally_acclaimed(users, users_url, '8.1')
x1, y1 = zip(*sorted(Counter(users).items()))

critics = []
critics_url = 'https://www.metacritic.com/browse/albums/score/metascore/all/filtered?page={}'
get_universally_acclaimed(critics, critics_url, '81')
x2, y2 = zip(*sorted(Counter(critics).items()))

fig = plt.figure(figsize = (8, 6))
plt.xticks(range(2000, max(x1 + x2), 4))
plt.title('Metacritic: number of "universally acclaimed"\nalbums per release year')
plt.plot(x1[1:-1], y1[1:-1])
plt.plot(x2[1:-1], y2[1:-1])
plt.legend(["According to users", "According to critics"], loc="upper right")
fig.savefig('universally_acclaimed_{}'.format(dt.now().year))