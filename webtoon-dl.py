#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Webtoon-dl is a comic downloader for webtoons.com. It can save individual
comic episodes or entire galleries as folders of numbered images or CBZ
comicbook archive files.
"""
__title__ = 'webtoon-dl.py'
__author__ = 'Goopypanther'
__license__ = 'GPL'
__copyright__ = 'Copyright 2019 Goopypanther'
__version__ = '0.2'


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


def get_episodes_from_list(list_url: str) -> list[str]:
    """Get episode URLs from a episode list URL

    Args:
        list_url (str): URL to webtoons episode list

    Returns:
        list[str]: Episode URLs
    """

    # Has to be this ugly as webtoon doesn't 404 when overpaginating... (._.)
    # Could be so nice with a simple iterator.

    list_pages = set()  # to ensure unique pages
    episode_urls = set()

    # Remove any unneccesary url parameters to ensure being on first page
    major_page_url = list_url.split("&")[0]

    # Circle through all major list pages (only 10 pages/paginator)
    while major_page_url:
        major_page = SESSION.get(major_page_url, cookies=AGE_COOKIE)
        if major_page:
            # Add current page
            list_pages.add(major_page)
            # Extract all list pages from paginator
            for page in major_page.html.find('.paginate', first=True).absolute_links:
                list_pages.add(SESSION.get(page, cookies=AGE_COOKIE))

            # Look for following major page
            paginator_next = major_page.html.find('.pg_next', first=True)
            major_page_url = paginator_next.absolute_links.pop() if (paginator_next) \
                else False

        else:
            return

    # Extract list of episodes on every list page
    for page in list_pages:
        episode_urls.update(
            page.html.find('#_listUl', first=True).absolute_links)

    return list(episode_urls)


def get_episodes(urls: list[str]) -> list[dict]:
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
            urls.extend(get_episodes_from_list(url))
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
parser = argparse.ArgumentParser(description="Webtoons.com comic downloader\nSaves comics as CBZ archives or folders of images.\nAutomatically saves episodes as seperate comics.",
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

# Search episodes
print("🔍 Looking for comics...")
episodes = get_episodes(args.webtoon_url)
print(f"✔️ Found {len(episodes)} episodes!\n")

# Save each comic
episodes.sort(key=lambda episode: (episode['title'], episode['no']))
for episode in episodes:
    # Check if episode should not be downloaded and skip
    if (args.start is not None and episode['no'] < args.start) \
            or (args.end is not None and episode['no'] > args.end):
        print(f"ℹ️ Skipping {episode['title']} #{episode['no']}: "
              f"{episode['name']}.\n")
        continue

    episode_images = get_episode_images(episode)
    print(f"💾 Saving episode...\n")

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
