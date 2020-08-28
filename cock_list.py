#!/usr/bin/python3
import os
import sys
from parse_json import get_tweet
import argparse
import json
import traceback

parser = argparse.ArgumentParser(
    description=
    "Convert folder contains tweet json files info a simple single json file for downloader."
)
parser.add_argument("-o",
                    "--output",
                    dest="output",
                    required=False,
                    metavar="OUTPUT_DIR",
                    default="download.json",
                    type=str,
                    help="Output json filename")

parser.add_argument("folder",
                    type=str,
                    metavar="JSON_DIR",
                    help="Tweet json files source directory")

parser.add_argument("-q",
                    "--quiet",
                    dest="quiet",
                    help="do not display info",
                    action="store_true")

parser.add_argument("-n",
                    "--extract-nomedia",
                    dest="nomedia",
                    help="only output nomedia tweets content",
                    action="store_true")

if __name__ == "__main__":
    tweets = []
    args = parser.parse_args()

    for fn in os.listdir(args.folder):
        if os.path.isfile(args.folder + "/" + fn):
            id = fn.split('.')[0]
            if id.isdigit() is False or fn.split('.')[1] != 'json':
                continue
            try:
                tweet = get_tweet(id, args.folder, quiet=args.quiet)
            except KeyboardInterrupt:
                print("User Interrupt, exiting.")
                exit()
            except:
                print("Error with parsing id " + id)
                traceback.print_exc()
                continue
            if not args.nomedia:
                if not args.quiet and len(tweet) > 1:
                    print(f"[INFO] {id} is a thread, has {len(tweet)} tweets")
                tweets.extend(tweet)
            else:
                for t in tweet:
                    if id == t['id_str']:
                        if t['medias'] == []:
                            print("id: " + id)
                            print(t)
    if args.nomedia:
        exit()
    uniq_list = []
    seen = set()
    for t in tweets:
        if t['id'] not in seen:
            seen.add(t['id'])
            uniq_list.append(t)

    uniq_list.sort(key=lambda x: int(x["id"]))
    uniq_list.sort(key=lambda x: x["user"]["screen_name"])
    # filter no media
    for u in uniq_list:
        if u['medias'] == []:
            uniq_list.remove(u)

    with open(args.output, "w") as f:
        json.dump(uniq_list, f, ensure_ascii=False)
    if not args.quiet:
        print(f"[OUPUT] {args.output} wrote.")
