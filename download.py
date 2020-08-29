#!/usr/bin/python3
from ImgDownloader import Downloader
import os
import sys
import json
import argparse
import logging

parser = argparse.ArgumentParser(
    description="Download tweets media from simplified json file.")

parser.add_argument("json",
                    help="Simplified json file", type=str)
parser.add_argument("-D", "--dump", dest="is_dump",
                    action="store_true", help="Only dump downloaded media path")
parser.add_argument("-o", "--output", dest="output",
                    required=False, default="download", help="Download folder")

if __name__ == "__main__":
    args = parser.parse_args()
    download_json = args.json
    default_download_dir = args.output

    with open(download_json, "r") as f:
        uniq_list = json.load(f)

    if args.is_dump == True:
        # dump list
        for t in uniq_list:
            author_dir = t['user']['screen_name']
            target_dir = os.path.join(default_download_dir, author_dir)
            for m in t['medias']:
                fn = os.path.join(
                    target_dir, os.path.basename(m['url']).split('?')[0])
                print(os.path.abspath(fn))
        exit()

    print("[INFO] Tweets wait for download: " + str(len(uniq_list)))

    total = 0
    for t in uniq_list:
        for m in t['medias']:
            total += 1
    current = 0

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    logging.getLogger('').setLevel(logging.INFO)

    dler = Downloader(base_path=default_download_dir,
                      total=total, logger=logging.getLogger(''))

    for t in uniq_list:
        # Check file exists
        author_dir = t['user']['screen_name']
        target_dir = os.path.join(dler.base_path, author_dir)
        for m in t['medias']:
            fn = os.path.basename(m['url']).split('?')[0]
            if m['type'] == 'photo':
                url = m['url'] + ":orig"
            else:
                url = m['url']
            if os.path.exists(target_dir + "/" + fn):
                print(
                    f"[ERROR] download {url} , {target_dir + '/' + fn} exists. ({current}/{total})")
                current += 1
                continue
            try:
                dler.download(url,
                              path=author_dir,
                              fn=fn,
                              referer=f"https://twitter.com/{author_dir}/status/{t['id']}")
            except:
                print(
                    f"[ERROR] download {url} , Connection fault. ({current}/{total})")
                current += 1
                continue
            print(f"[DONE] downloaded {url} ({current}/{total})")
            current += 1
    print("[INFO] Pool closed, waiting for download complete")
    dler.close()

    print("Finished")
