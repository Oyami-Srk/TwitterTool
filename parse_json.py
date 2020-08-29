#!/usr/bin/env python3
import json

default_json_dir = "./json"


def get_json_dict(id, json_dir=default_json_dir) -> dict:
    id = str(id)
    with open(json_dir + "/" + id + ".json", "r") as f:
        json_dict = json.load(f)
    return json_dict


def get_threads(id, obj: dict, quiet=False) -> list:
    is_thread = False
    tweets = obj['globalObjects']['tweets']
    main_tweet = tweets[str(id)]
    user_id = main_tweet['user_id_str']

    """
    current_user_tweets = [
        tweet_id for tweet_id in tweets
        if tweets[tweet_id]['user_id_str'] == user_id
        and tweets[tweet_id]['in_reply_to_user_id_str'] == user_id
        and 'extended_entities' in tweets[tweet_id].keys()
    ]
    """
    current_user_tweets = [str(id)]
    for tweet_id in tweets:
        if tweets[tweet_id]['user_id_str'] == user_id and 'extended_entities' in tweets[tweet_id].keys():
            if 'in_reply_to_user_id_str' in tweets[tweet_id].keys() and tweets[tweet_id]['in_reply_to_user_id_str'] == user_id:
                current_user_tweets.append(tweet_id)

    if "in_reply_to_status_id" in main_tweet.keys() and main_tweet['in_reply_to_status_id'] != None:
        is_thread = True
    elif "in_reply_to_status_id_str" in main_tweet.keys() and main_tweet['in_reply_to_status_id_str'] != None:
        is_thread = True
    elif len(current_user_tweets) > 1:
        is_thread = True

    threads = []

    if is_thread:
        current_tweet = main_tweet
        while True:
            threads.append(current_tweet)
            if "in_reply_to_status_id" not in current_tweet.keys():
                break
            if current_tweet['in_reply_to_status_id_str'] == None:
                break
            next_id = current_tweet['in_reply_to_status_id_str']
            if next_id not in tweets.keys():
                if not quiet:
                    print(f"[INFO] {id} Thread too lang")
                return [main_tweet]
            else:
                current_tweet = tweets[next_id]

    threads_ids = [i['id_str'] for i in threads]

    rest = [x for x in current_user_tweets if x not in threads_ids]

    for i in rest:
        threads.append(tweets[i])

    threads.sort(key=lambda x: int(x["id_str"]))
    return threads


def get_tweet_content_info(tweet_obj: dict) -> dict:
    if 'extended_entities' in tweet_obj.keys():
        raw_media_entities = tweet_obj['extended_entities']["media"]
    else:
        raw_media_entities = []
    medias = []
    id = 0

    for m in raw_media_entities:
        media_url = m['media_url_https']
        if m['type'] == "animated_gif" or m['type'] == "video":
            video_info = m['video_info']
            vs = video_info['variants']
            max_vs = max(vs, key=lambda x: x.get('bitrate', 0))
            media_url = max_vs['url']
            medias.append({
                "id": id,
                "media_id": m['id_str'],
                "url": media_url,
                "size": {
                    "width": m['original_info']['width'],
                    "height": m['original_info']['height']
                },
                "type": m['type'],
                "video_info": video_info
            })
        else:
            medias.append({
                "id": id,
                "media_id": m['id_str'],
                "url": media_url,
                "size": {
                    "width": m['original_info']['width'],
                    "height": m['original_info']['height']
                },
                "type": m['type']
            })
        id += 1

    return {
        "id": tweet_obj['id_str'],
        "id_str": tweet_obj['id_str'],
        "full_text": tweet_obj['full_text'],
        "medias": medias,
        "created_at": tweet_obj['created_at']
    }


def get_tweet_user(id, obj: dict) -> dict:
    id = str(id)
    users = obj["globalObjects"]["users"]
    # return users[id]  # mainly "screen_name", "name", "id"
    return {
        "id": users[id]["id_str"],
        "name": users[id]["name"],
        "screen_name": users[id]["screen_name"],
    }


def get_tweet(id, json_dir=default_json_dir, quiet=False) -> list:
    obj = get_json_dict(id, json_dir)
    threads = get_threads(id, obj, quiet=quiet)
    result = []
    for t in threads:
        twinfo = get_tweet_content_info(t)
        twuser = get_tweet_user(t['user_id_str'], obj)
        twinfo['user'] = twuser
        result.append(twinfo)
    return result


if __name__ == "__main__":
    import sys
    json_path = sys.argv[1]
    path = '/'.join(json_path.split('/')[:-1])
    id = int(json_path.split('/')[-1].split('.')[0])
    print(json.dumps(
        get_tweet(id, path), ensure_ascii=False, indent=4))
