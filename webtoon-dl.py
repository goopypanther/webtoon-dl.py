#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Webtoon-dl is a comic downloader for webtoons.com. It can save individual
comics or entire galleries as folders of numbered images or CBZ comicbook
archive files.
"""
__title__ = 'webtoon-dl.py'
__author__ = 'Goopypanther'
__license__ = 'GPL'
__copyright__ = 'Copyright 2019 Goopypanther'
__version__ = '0.1'


import argparse
import os
import re
from requests_html import HTMLSession
import zipfile

SESSION = HTMLSession()
# bypass age confirmation page
AGE_COOKIE = {
    'needCCPA': 'false',
    'needCOPPA': 'false',
    'needGDPR': 'false',
}


def comics_from_gallery(gallery_url):
    """
    Return a list of comic issue URLs from a gallery URL
    :param gallery_url: str URL to webtoons gallery
    :return: list of URLs to comic issues
    """

    comics_list = []
    pages = []
    more_pages = []

    # Get first page
    pages.append(SESSION.get(gallery_url, cookies=AGE_COOKIE))

    if pages[0]:
        more_pages.append(pages[0])
        moarpages = pages[0].html.find('.pg_next', first=True)

        # Check if the list of pages is paginated
        while moarpages:
            moarpages_link = SESSION.get(''.join(moarpages.absolute_links),
                                         cookies=AGE_COOKIE)
            more_pages.append(moarpages_link)
            moarpages = moarpages_link.html.find('.pg_next', first=True)

        # Repeat for each pagination page
        for pagegroup in more_pages:

            # Extract list of other pages and download
            for new_page in pagegroup.html.find('.paginate', first=True).absolute_links:
                # Get all other pages
                pages.append(SESSION.get(new_page, cookies=AGE_COOKIE))

        # Extract list of every comic on every page
        for page in pages:
            comics_list.extend(page.html.find(
                '#_listUl', first=True).absolute_links)

    return (comics_list)


def get_episode_list(urls: list[str]) -> list[dict]:
    """Organize webtoons URLs into dictionary and expand any links to episodes

    Args:
        urls (list[str]): URLs to comic title or episode pages

    Returns:
        list[dict]: Comic episodes (url, title and episode no/name)
                    [{'url': str, 'title': str, 'no': int, 'name': str}, ...]
    """

    episodes = []

    for url in urls:
        # Capture groups: 0 -- Full match, 1 -- Title, 2 -- Episode name
        match = re.search(
            r"webtoons\.com\/.+?\/.+?\/(.+?)\/(.+?)(?:\?|\/)", url)

        if match is None:
            print(f"\t ❌ Error: '{url}' could not be parsed.")
            continue

        # Retrieve episode urls if url is title page/episode list
        if match.group(2) == "list":
            print(f"Fetching episodes from {match.group(1)}...")
            urls.extend(comics_from_gallery(url))
            continue

        episodes.append({
            'url': url,
            'title': match.group(1),
            'no': int(url.split('episode_no=')[1]),
            'name': match.group(2)
        })

    return episodes


def get_image_urls(episode: dict) -> list[str]:
    """Get direct image links to all page images of episode

    Args:
        episode (dict): Episode dict object
                        {'url': str, 'title': str, 'no': int, 'name': str}

    Returns:
        list[str]: List of page image URLs
    """

    r = SESSION.get(episode['url'], cookies=AGE_COOKIE)

    if r:
        image_urls = [image.attrs['data-url']
                      for image in r.html.find('._images')]
        print(f"📄 {episode['title']} #{episode['no']}: "
              f"{episode['name']} - Found {len(image_urls)} pages.")

    return (image_urls)


def get_episode_images(episode: dict) -> list[bytes]:
    """Get image files (pages) of an episode

    Args:
        episode (dict): Episode dict object
                        {'url': str, 'title': str, 'no': int, 'name': str}

    Returns:
        list[bytes]: Episode's page images (jpg binary data)
    """

    images = []
    image_urls = get_image_urls(episode)

    total_pages = len(image_urls)
    for index, image_url in enumerate(image_urls):
        print(f"\tDownloading page {index+1}/{total_pages}.")
        # to download good-quality images
        image_url = image_url.replace('?type=q90', '')
        r = SESSION.get(image_url, headers={'referer': episode['url']})

        if r:
            images.append(r.content)

    return (images)


########################################################################
#   MAIN FUNCTION                                                      #
########################################################################
# Set up argument parser
parser = argparse.ArgumentParser(description="Webtoons.com comic downloader\nSaves comics as CBZ archives or folders of images.\nAutomatically saves galleries as seperate comics.",
                                 formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("webtoon_url",
                    help="Url to webtoons comic or creator page.\nMultiple URLs may be entered.",
                    type=str,
                    nargs='+')
parser.add_argument("-r", "--raw",
                    help="Save image files to folder instead of CBZ output.",
                    action="store_true")
parser.add_argument("-o", "--output",
                    default=os.getcwd(),
                    help="Path to output directory. Defaults to current directory.",
                    type=str)
parser.add_argument("-n", "--number",
                    help="Add episode number to file name. Useful when episode names do not contain numbering.",
                    action="store_true")
parser.add_argument("-s", "--start",
                    help="Specify episode number from which download should start.",
                    type=int)
parser.add_argument("-e", "--end",
                    help="Specify episode number which should be downloaded last.",
                    type=int)

args = parser.parse_args()

print("🔍 Finding comics...")
episodes = get_episode_list(args.webtoon_url)
print(f"✔️ Found {len(episodes)} episodes!")

# Save each comic
for episode in episodes:
    # Check if episode should not be downloaded and skip
    if (args.start is not None and episode['no'] < args.start) \
            or (args.end is not None and episode['no'] > args.end):
        print(f"ℹ️ Skipping {episode['title']} #{episode['no']}: "
              f"{episode['name']}.")
        continue

    episode_images = get_episode_images(episode)
    print(f"💾 Saving episode...")

    # Create title output directory
    outpath = f"{args.output}/{episode['title']}"
    os.makedirs(outpath, exist_ok=True)

    # Check for number argument
    numbering = f"#{episode['no']:03}_" if args.number else ""
    outpath += f"/{episode['title']}_{numbering}{episode['name']}"

    # Raw mode, save images into folder
    if args.raw:
        os.makedirs(outpath, exist_ok=True)
        for index, image in enumerate(episode_images):
            with open(f"{outpath}/{index:02}.jpg", 'wb') as f:
                f.write(image)

    # CBZ mode, save images into zip file
    else:
        with zipfile.ZipFile(f"{outpath}.cbz", 'w') as zip:
            for index, image in enumerate(episode_images):
                zip.writestr(f"{index:02}.jpg", image)

print("🎉 DONE! All episodes downloaded.")
