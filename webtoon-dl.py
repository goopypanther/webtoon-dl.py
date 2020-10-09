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


def comics_from_gallery(gallery_url):
    """
    Return a list of comic issue URLs from a gallery URL
    :param gallery_url: str URL to webtoons gallery
    :return: list of URLs to comic issues
    """

    comics_list = []
    pages = []
    
    session = HTMLSession()
    
    # Get first page
    agecookie = {'ageGatePass': 'true'}
    pages.append(session.get(gallery_url, cookies=agecookie))


    
    if pages[0]:
        # Extract list of other pages and download
        for new_page in pages[0].html.find('.paginate', first=True).absolute_links:
            # Get all other pages
            pages.append(session.get(new_page, cookies=agecookie))
        
        # Extract list of every comic on every page
        for page in pages:
            comics_list.extend(page.html.find('#_listUl', first=True).absolute_links)
            # TODO: how does pagination work on webtoons? The div with class "paginate" on a gallery page seems to have equal entities to the number of pages. Is there an upper limit to this? Is it reliable?
           
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
                print("Getting gallery from %s..." % r.group(1))
                
                # Do additional processing that returns new url list
                # Recursivly run this fuction
                # Extend results into expanded_list
                processed_list.extend(process_url_list(comics_from_gallery(url)))
                
            else:
                processed_list.append({'url': url, 'author': r.group(1), 'title': r.group(2)})
                print(r.group(2))

    return (processed_list)


def get_comic_pages(issue_dict):
    """
    Get direct image links to all comic page images from link to issue page
    :param issue_dict: comic issue dict entry
                       {'url': str, 'author': str, 'title': str}
    :return: list of str URLs to comic page images
    """
    
    session = HTMLSession()
    agecookie = {'ageGatePass': 'true'}
    
    r = session.get(issue_dict['url'], cookies=agecookie)
    
    if r:
        pages_list = [page.attrs['data-url'] for page in r.html.find('._images')]
        print("Comic %s: got %i pages" % (issue_dict['title'], len(pages_list)))
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
    
    print("Issue: %s" % issue_dict['title'])
    
    # Download each image in page list and create list of jpg binary data
    for index, page in enumerate(issue_dict['page-urls']):
        print("Downloading page %i/%i" % ((index + 1), len(issue_dict['page-urls'])))
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
                    help="Add episode/issue numbers to file names- useful when episodes/issue names do not contain numbering.",
                    action="store_true")

# Parse arguments
args = parser.parse_args()

print("Finding comics...")
comic_list = process_url_list(args.webtoon_url)
print("Found %i issues." % len(comic_list))

# Save each comic
for comic in comic_list:
    # Add page URLs for each issue in dict list
    comic.update({'page-urls': get_comic_pages(comic)})
    
    # Get images for each issue in dict list
    comic.update({'page-img': get_comic_page_images(comic)})    
    
    # Fetch the chapter/episode/issue number from the end of the URL
    episodeNumber = comic['url'].split('episode_no=')[1]

    print("Saving issue " + episodeNumber + ": %s_%s..." % (comic['author'], comic['title']))

    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Raw mode, save images into folders
    if args.raw:
        if args.number:
            outpath = "%s" % args.output + "/" + episodeNumber + "_%s_%s" % (comic['author'], comic['title'])
        else:
            outpath = "%s/%s_%s" % (args.output, comic['author'], comic['title'])
        os.makedirs(outpath, exist_ok=True)
        
        # Write each image to folder
        for index, image in enumerate(comic['page-img']):
            with open("%s/%s.jpg" % (outpath, index), 'wb') as f:
                f.write(image)

    # CBZ mode
    else:
        outpath = "%s/%s_%s.cbz" % (args.output, comic['author'], comic['title'])
        
        # Write each image into zip file
        with zipfile.ZipFile(outpath, 'w') as zip:
            for index, image in enumerate(comic['page-img']):
                zip.writestr("%i.jpg" % index, image)

print("Done")
