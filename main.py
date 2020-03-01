#!/usr/bin/env python
import twitter, twitter_config
import requests
import sys
import json
import hashlib
from collections import defaultdict
from multiprocessing import Pool
from requests_oauthlib import OAuth1Session

cred = twitter_config.accounts["FYADFlags"]
FLAG_URL = "http://forums.somethingawful.com/flag.php?forumid=26"
BUCKET = "fucktardidiot"
LOCALSTATE = "fyadflags.json"
twitter_api = twitter.Api(
    consumer_key=cred["consumer_key"],
    consumer_secret=cred["consumer_secret"],
    access_token_key=cred["access_token_key"],
    access_token_secret=cred["access_token_secret"],
)


def load_state():
    try:
        return json.load(open(LOCALSTATE, "r"))
    except Exception:
        return defaultdict(dict)


def save_state(state):
    with open(LOCALSTATE, "w") as statefile:
        statefile.write(json.dumps(state, indent=2))


def put_state(key, value):
    state = load_state()
    state[key] = value
    save_state(state)


def get_state(key, default=None):
    state = load_state()
    return state.get(key, default)


def post_flag_from_dm():
    last_dm_timestamp = get_state("last_dm_timestamp", "0")
    dms = get_dms(cred, since_timestamp=last_dm_timestamp)
    if dms:
        oldest_dm = dms[-1]
        dm_timestamp = oldest_dm['created_timestamp']
        put_state("last_dm_timestamp", dm_timestamp)
        if flag_dm_is_valid(oldest_dm):
            media, extension = get_media_content_from_dm(oldest_dm)
            if media and extension:
                print(f'Posted new dm from {dm_timestamp}')
                filename = f"dm_media/{oldest_dm['message_create']['sender_id']}_{dm_timestamp}.{extension}"
                send_tweet_with_media(media, extension, "", filename)
            else:
                print("No content")
    else:
        print("No new dms")


def refresh_follows():
    follows = twitter_api.GetFriends(cred['id'])
    follows = [{"name": f.screen_name, "id": f.id} for f in follows]
    put_state('follows', follows)
    return follows


def flag_dm_is_valid(dm):
    follows = get_state("follows")
    if not follows:
        follows = refresh_follows()
    follow_ids = [f['id'] for f in follows]
    if int(dm['message_create']['sender_id']) in follow_ids:
        try:
            dimensions = dm['message_create']['message_data']['attachment']['media']['sizes']['large']
            ratio = round(dimensions['w']/dimensions['h'], 1)
            if ratio == 2.5:
                return True
            else:
                print(f"Ignored dm because dimensions were wrong")
        except KeyError as e:
            print(f'Encountered exception trying to check dimensions: {e}')
            return False
    else:
        print(f'Ignored dm from {dm["created_timestamp"]} someone i dont follow')
    return False


def get_oauth1_session(cred):
    return OAuth1Session(
        cred["consumer_key"],
        client_secret=cred["consumer_secret"],
        resource_owner_key=cred["access_token_key"],
        resource_owner_secret=cred["access_token_secret"],
    )


def get_dms(cred, since_timestamp=None, cursor=None):
    url = "https://api.twitter.com/1.1/direct_messages/events/list.json"
    if cursor:
        url = f"{url}?cursor={cursor}"
    session = get_oauth1_session(cred)
    response = session.get(url).json()
    try:
        if since_timestamp:
            return [
                dm
                for dm in response["events"]
                if dm.get("created_timestamp") > since_timestamp
            ]
        return response["events"]
    except KeyError:
        raise Exception(response.get('errors'))


def get_media_content_from_dm(dm):
    session = get_oauth1_session(cred)
    try:
        media_path = dm['message_create']['message_data']['attachment']['media']['media_url']
    except KeyError:
        return b"", ""
    return session.get(media_path).content, media_path[media_path.rfind('.')+1:]


def handler(event, context):
    tweet_flag()


def flag_already_saved(flag, flag_content):
    state = load_state()
    saved_paths = state.get('saved_paths', [])
    if flag["flagpath"] in saved_paths:
        return True
    state = load_state()
    checksum = hashlib.md5(flag_content).hexdigest()
    return checksum in (state.get("flags") or [])


def record_flag(flag, flag_content):
    state = load_state()
    checksum = hashlib.md5(flag_content).hexdigest()
    state["flags"][checksum] = flag
    saved_paths = state.get('saved_paths', [])
    saved_paths.append(flag["flagpath"])
    state['saved_paths'] = saved_paths
    save_state(state)


def save_and_record_flag(flag, flag_content):
    if not flag_already_saved(flag, flag_content):
        with open(f"{get_flag_key(flag['description'], flag_content)}.jpg", "wb") as f:
            f.write(flag_content)
        record_flag(flag, flag_content)
        #print(f"Found a new flag: {flag['description']}")


def get_flag_key(flag_description, flag_content):
    return f"fyadflags/{flag_description.replace(' ', '_').replace('/', '_').replace('#', '')}_{hashlib.md5(flag_content).hexdigest()}"


def send_tweet_with_media(media_content, extension, message, filename=None):
    if not filename:
        filename = f"_media.{extension}"
    open(filename, "wb").write(media_content)
    twitter_api.PostUpdate(message, media=filename)


def archive_flag():
    flag = requests.get(FLAG_URL).json()
    flag["flagpath"] = "http://fi.somethingawful.com/flags" + flag["path"]
    flag["description"] = f"#FYADflag by {flag['username']} {flag['created']}"
    flag_content = requests.get(flag["flagpath"]).content
    flag["flag_key"] = get_flag_key(flag["description"], flag_content)
    save_and_record_flag(flag, flag_content)


def tweet_flag():
    flag = requests.get(FLAG_URL).json()
    while (
        flag["username"] in twitter_config.blacklist_flags
        or flag["path"] in twitter_config.blacklist_flagpaths
    ):
        flag = requests.get(FLAG_URL).json()

    flag["flagpath"] = "http://fi.somethingawful.com/flags" + flag["path"]
    flag["description"] = f"#FYADflag by {flag['username']} {flag['created']}"
    if flag["path"] != "error.png":
        print(f'Posting flag: {flag["description"]}')
        r = twitter_api.PostUpdate(flag["description"], media=flag["flagpath"])

    else:
        print("SA PHP error {0}".format(flag))


if __name__ == "__main__":
    mode = sys.argv[1]
    try:
        api = twitter.Api(
            consumer_key=cred["consumer_key"],
            consumer_secret=cred["consumer_secret"],
            access_token_key=cred["access_token_key"],
            access_token_secret=cred["access_token_secret"],
        )
    except:
        print("Failed to authenticate.")
        exit()
    state = load_state()
    saved_paths = [f["flagpath"] for f in state.get("flags", {}).values()]
    starting_count = len(saved_paths)
    if mode == "post":
        tweet_flag()
    elif mode == "archive":
        with Pool(50) as pool:
            for x in range(10000):
                pool.apply(archive_flag)
        final_count = len(get_state('flags'))
        print(f'Archived {final_count-starting_count} new flags')
    elif mode == "dm":
        refresh_follows()
        post_flag_from_dm()
