Webtoon-dl.py
=============

Comic downloader/scraper for http://www.webtoons.com. Download individual episodes or entire comics.
Output as CBZ archives or as sets of folders containing numbered images.

Requirements
------------

 * `>=Python3.6`
 * [requests_html](https://github.com/kennethreitz/requests-html) (`pip3 install requests_html`)

Usage
-----

```
usage: webtoon-dl.py [-h] [-r] [-o OUTPUT] [-n] [-s START] [-e END] webtoon_url [webtoon_url ...]

Webtoons.com comic downloader
Saves comics as CBZ archives or folders of images.
Automatically saves galleries as seperate comics.

positional arguments:
  webtoon_url           Url to webtoons comic or creator page.
                        Multiple URLs may be entered.

options:
  -h, --help            show this help message and exit
  -r, --raw             Save image files to folder instead of CBZ output.
  -o OUTPUT, --output OUTPUT
                        Path to output directory. Defaults to current directory.
  -n, --number          Add episode numbers to file names. Useful when episode names do not contain numbering.
  -s START, --start START
                        Specify episode number from which download should start.
  -e END, --end END     Specify episode number which should be downloaded last.
```
