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

    session = HTMLSession()

    # Get first page
    pages.append(session.get(gallery_url, cookies=AGE_COOKIE))

    if pages[0]:
        more_pages.append(pages[0])
        moarpages = pages[0].html.find('.pg_next', first=True)

        # Check if the list of pages is paginated
        while moarpages:
            moarpages_link = session.get(''.join(moarpages.absolute_links),
                                         cookies=AGE_COOKIE)
            more_pages.append(moarpages_link)
            moarpages = moarpages_link.html.find('.pg_next', first=True)

        # Repeat for each pagination page
        for pagegroup in more_pages:

            # Extract list of other pages and download
            for new_page in pagegroup.html.find('.paginate', first=True).absolute_links:
                # Get all other pages
                pages.append(session.get(new_page, cookies=AGE_COOKIE))

        # Extract list of every comic on every page
        for page in pages:
            comics_list.extend(page.html.find(
                '#_listUl', first=True).absolute_links)

    return (comics_list)


def process_url_list(url_list):
    """
    Organize webtoons URLs into dictionary and expand any links to galleries
    :param url_list: list of str URLs to comic issue or gallery pages
    :return: list of dicts containing url, author and title for each comic issue
             [{'url': str, 'author': str, 'title': str}, ...]
    """

    processed_list = []

    for url in url_list:
        # Capture groups: 0 -- Full match, 1 -- Author name, 2 -- Comic title
        r = re.search(r"webtoons\.com\/.+?\/.+?\/(.+?)\/(.+?)(?:\?|\/)", url)

        if r:
            # Check if webtoon_url is gallery
            if r.group(2) == "list":
                print(f"Getting gallery from {r.group(1)}...")

                # Do additional processing that returns new url list
                # Recursivly run this fuction
                # Extend results into expanded_list
                processed_list.extend(
                    process_url_list(comics_from_gallery(url)))

            else:
                processed_list.append({
                    'url': url,
                    'author': r.group(1),
                    'title': r.group(2)
                })
                # print(r.group(2))

    return (processed_list)


def get_comic_pages(issue_dict):
    """
    Get direct image links to all comic page images from link to issue page
    :param issue_dict: comic issue dict entry
                       {'url': str, 'author': str, 'title': str}
    :return: list of str URLs to comic page images
    """

    session = HTMLSession()

    r = session.get(issue_dict['url'], cookies=AGE_COOKIE)

    if r:
        pages_list = [page.attrs['data-url']
                      for page in r.html.find('._images')]
        print(f"Comic {issue_dict['title']}: got {len(pages_list)} pages")
    return (pages_list)


def get_comic_page_images(issue_dict):
    """
    Get image files for each page of comic issue
    :param issue_dict: comic issue dict entry
                       {'url': str, 'author': str, 'title': str}
    :return: list of jpg binary data for each page of comic
    """

    page_images = []

    session = HTMLSession()

    print(f"Issue: {issue_dict['title']}")

    # Download each image in page list and create list of jpg binary data
    for index, page in enumerate(issue_dict['page-urls']):
        print(f"Downloading page {(index + 1)}/{len(issue_dict['page-urls'])}")
        # to download good-quality images
        page = page.replace('?type=q90', '')
        r = session.get(page, headers={'referer': issue_dict['url']})

        if r:
            page_images.append(r.content)

    return (page_images)


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

# Parse arguments
args = parser.parse_args()

print("Finding comics...")
comic_list = process_url_list(args.webtoon_url)
print(f"Found {len(comic_list)} issues.")

# Add page URLs for each issue in dict list
#[comic.update({'page-urls': get_comic_pages(comic)}) for comic in comic_list]

# Get images for each issue in dict list
#[comic.update({'page-img': get_comic_page_images(comic)}) for comic in comic_list]

# Save each comic
for comic in comic_list:
    # Fetch the episode number from the end of the URL
    episode_no = int(comic['url'].split('episode_no=')[1])

    # Check if episode should not be downloaded and skip
    if (args.start is not None and episode_no < args.start) \
            or (args.end is not None and episode_no > args.end):
        print(f"Skipping issue {episode_no}: " \
            f"{comic['author']} / {comic['title']}.")
        continue

    # Add page URLs for each issue in dict list
    comic.update({'page-urls': get_comic_pages(comic)})

    # Get images for each issue in dict list
    comic.update({'page-img': get_comic_page_images(comic)})

    print(f"Saving issue {episode_no}: " \
        f"{comic['author']} / {comic['title']}...")

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Raw mode, save images into folders
    if args.raw:
        if args.number:
            outpath = f"{args.output}/{episode_no}_{comic['author']}_{comic['title']}"
        else:
            outpath = f"{args.output}/{comic['author']}_{comic['title']}"
        os.makedirs(outpath, exist_ok=True)

        # Write each image to folder
        for index, image in enumerate(comic['page-img']):
            with open(f"{outpath}/{index}.jpg", 'wb') as f:
                f.write(image)

    # CBZ mode
    else:
        outpath = f"{args.output}/{comic['author']}_{comic['title']}.cbz"

        # Write each image into zip file
        with zipfile.ZipFile(outpath, 'w') as zip:
            for index, image in enumerate(comic['page-img']):
                zip.writestr(f"{index}.jpg", image)

print("Done")
