# discogs is pretty slow, be patient!

import json
import os.path
from pathlib import Path

from bs4 import BeautifulSoup
import requests

session = requests.session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}

session.get(
    'https://www.discogs.com/artist/144998-Black-Sabbath?sort=year%2Casc&limit=100&layout=sm&page_size=50&subtype=Albums&filter_anv=0&type=Releases&page=1'
)

base_url = 'https://www.discogs.com'

result = dict()

basedir = Path(__file__).parent


def download_album_art(artist, title, url):
    title = title.replace('/', '__')
    directory = basedir.joinpath('examples/static/album_art') / artist
    directory.mkdir(parents=True, exist_ok=True)
    extension = Path(url).suffix
    target_file = directory / f'{title}{extension}'
    if target_file.exists():
        print('   ', title, 'already exists')
        return
    with open(target_file, 'wb') as f:
        f.write(session.get(url, headers=headers).content)
    print('   ', title, 'downloaded')


def scrape_album(artist, album_title, tracks, url):
    soup = BeautifulSoup(session.get(base_url + url, headers=headers).content, "html.parser")
    images = soup.select('picture img')
    result[artist][album_title]['thumbnails'] = [x.attrs['src'] for x in images]

    for row in soup.select('.tracklist_track'):
        title = row.find(class_='tracklist_track_title')
        duration = row.find(class_='tracklist_track_duration')
        if not title:
            continue
        duration = duration.text if duration else ''
        title = title.text.strip()
        tracks.append((title, duration.strip()))


def scrape_artist(artist, url):
    print(artist)
    soup = BeautifulSoup(session.get(base_url + url, headers=headers).content, "html.parser")
    table = soup.find(id='artist')

    albums = {}
    result[artist] = albums

    for row in table.find_all('tr'):
        foo = row.find(class_='title')
        if not foo:
            continue
        a = foo.find('a')
        album_url = a.attrs['href']
        if '/master/' not in album_url:
            continue
        title = a.text.strip()
        print('    ', title)
        year = row.find(class_='year').text
        tracks = []
        albums[title] = dict(
            year=year,
            tracks=tracks,
        )
        scrape_album(artist, title, tracks, album_url)


def scrape_data():
    if os.path.exists(basedir.joinpath('scraped_data.json')):
        print('### Reusing scraped_data.json')
        with open(basedir.joinpath('scraped_data.json')) as f:
            global result
            result = json.load(f)
    else:
        print('### Scraping artist and album data')
        scrape_artist('Django Reinhardt', '/artist/253481-Django-Reinhardt?filter_anv=0&subtype=Albums&type=Releases')
        scrape_artist(
            'Quintette Du Hot Club De France',
            '/artist/355185-Quintette-Du-Hot-Club-De-France?filter_anv=0&subtype=Albums&type=Releases',
        )
        scrape_artist(
            'Black Sabbath',
            '/artist/144998-Black-Sabbath?sort=year%2Casc&limit=100&filter_anv=0&subtype=Albums&type=Releases&page=1&layout=sm',
        )
        scrape_artist('Dio', '/artist/252122-Dio-2?filter_anv=0&subtype=Albums&type=Releases')
        scrape_artist('Ozzy Osbourne', '/artist/59770-Ozzy-Osbourne?filter_anv=0&subtype=Albums&type=Releases')
        scrape_artist('Tony Iommi', '/artist/253791-Tony-Iommi?filter_anv=0&subtype=Albums&type=Releases')
        scrape_artist('Radiohead', '/artist/3840-Radiohead?filter_anv=0&subtype=Albums&type=Releases')

        with open(basedir.joinpath('scraped_data.json'), 'w') as f:
            json.dump(result, f)

    print('### Downloading images')
    for artist, albums in result.items():
        for title, album in albums.items():
            if album['thumbnails']:
                download_album_art(artist, title, album['thumbnails'][0])


if __name__ == '__main__':
    scrape_data()
