#!/usr/bin/env python
import twitter, twitter_config
import requests
import sys
import json
import hashlib
from collections import defaultdict
from multiprocessing import Pool
from requests_oauthlib import OAuth1Session
import time
from json_state import state
import pickle


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


def post_flag_from_dm():
    last_dm_timestamp = state.get("last_dm_timestamp", "0")
    dms = get_dms(cred, since_timestamp=last_dm_timestamp)
    if dms:
        oldest_dm = dms[-1]
        dm_timestamp = oldest_dm["created_timestamp"]
        state.put("last_dm_timestamp", dm_timestamp)
        if flag_dm_is_valid(oldest_dm):
            media, extension = get_media_content_from_dm(oldest_dm)
            if media and extension:
                print(f"Posted new dm from {dm_timestamp}")
                filename = f"dm_media/{oldest_dm['message_create']['sender_id']}_{dm_timestamp}.{extension}"
                send_tweet_with_media(media, extension, "", filename)
            else:
                print("No content")
    else:
        print("No new dms")


def refresh_follows():
    follows = twitter_api.GetFriends(cred["id"])
    follows = [{"name": f.screen_name, "id": f.id} for f in follows]
    state.put("follows", follows)
    return follows


def flag_dm_is_valid(dm):
    follows = state.get("follows")
    if not follows:
        follows = refresh_follows()
    follow_ids = [f["id"] for f in follows]
    if int(dm["message_create"]["sender_id"]) in follow_ids:
        try:
            dimensions = dm["message_create"]["message_data"]["attachment"]["media"][
                "sizes"
            ]["large"]
            ratio = round(dimensions["w"] / dimensions["h"], 1)
            if ratio == 2.5:
                return True
            else:
                print(f"Ignored dm because dimensions were wrong")
        except KeyError as e:
            print(f"Encountered exception trying to check dimensions: {e}")
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
        raise Exception(response.get("errors"))


def get_media_content_from_dm(dm):
    session = get_oauth1_session(cred)
    try:
        media_path = dm["message_create"]["message_data"]["attachment"]["media"][
            "media_url"
        ]
    except KeyError:
        return b"", ""
    return session.get(media_path).content, media_path[media_path.rfind(".") + 1 :]


def handler(event, context):
    tweet_flag()


def flag_already_saved(flag, flag_content):
    saved_paths = state.get("saved_paths", [])
    if flag["flagpath"] in saved_paths:
        return True
    checksum = hashlib.md5(flag_content).hexdigest()
    return checksum in (state.get("flags") or [])


def record_flag(flag, flag_content):
    this_state = state.load()
    checksum = hashlib.md5(flag_content).hexdigest()
    this_state["flags"][checksum] = flag
    saved_paths = this_state.get("saved_paths", [])
    saved_paths.append(flag["flagpath"])
    this_state["saved_paths"] = saved_paths
    state.save(this_state)


def save_and_record_flag(flag, flag_content):
    if not flag_already_saved(flag, flag_content):
        with open(f"{get_flag_key(flag['description'], flag_content)}.jpg", "wb") as f:
            f.write(flag_content)
        record_flag(flag, flag_content)
        # print(f"Found a new flag: {flag['description']}")


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


def get_flag_user(flag_description):
    text = flag_description.replace("#FYADflag by ", "")
    return "".join([t for t in text.split()][:-2])


def get_fyadflags_timeline(max_count=6000):
    tweets = state.pickle_get("fyadflags_timeline", [])
    try:
        latest_id = max([tweet.id for tweet in tweets])
    except ValueError:
        latest_id = None
    try:
        oldest_id = min([tweet.id for tweet in tweets])
    except ValueError:
        oldest_id = None
    tweets = get_user_tweets(cred["id"], since_id=latest_id, max_count=max_count)
    state.pickle_put("fyadflags_timeline", tweets)
    return tweets


def get_flag_metrics():
    # tweets = get_fyadflags_timeline()
    tweets = pickle.load(
        open("/home/phil/code/fyadflags/tests/fyadflags_timeline.p", "rb")
    )
    leaderboard = {}
    for tweet in tweets:
        username = get_flag_user(tweet.text)
        stats = leaderboard.get(username) or {"retweets": 0, "favs": 0, "flag_count": 0}
        stats["retweets"] += tweet.retweet_count
        stats["favs"] += tweet.favorite_count
        stats["flag_count"] += 1
        leaderboard[username] = stats
    leaderboard = [
        dict(username=username, **data) for username, data in leaderboard.items()
    ]
    state.put("fyadflags_leaderboard", leaderboard)
    top_5 = sorted(leaderboard, key=lambda t: (t["retweets"] + t["favs"]))[-5:]
    print('\n'.join([format_flag_summary(s) for s in top_5]))


def format_flag_summary(summary):
    return f"{summary['username']} RTs: {summary['retweets']} favs: {summary['favs']} flag posts: {summary['flag_count']}"


def get_user_tweets(
    user_id,
    since_id=None,
    max_count=6000,
    max_id=None,
    include_rts=False,
    trim_user=True,
    exclude_replies=True,
):
    more_tweets = []
    for tweet in yield_user_tweets(
        user_id,
        since_id=since_id,
        max_id=max_id,
        include_rts=include_rts,
        trim_user=trim_user,
        exclude_replies=exclude_replies,
    ):
        more_tweets.append(tweet)
        if len(more_tweets) >= max_count:
            break
    return more_tweets


def yield_user_tweets(
    user_id,
    max_id=None,
    since_id=None,
    include_rts=False,
    trim_user=True,
    exclude_replies=True,
):
    def _timeline():
        return twitter_api.GetUserTimeline(
            user_id,
            max_id=max_id,
            since_id=since_id,
            count=200,
            include_rts=include_rts,
            trim_user=trim_user,
            exclude_replies=exclude_replies,
        )

    try:
        user_tweets = _timeline()
        while user_tweets:
            max_id = min([t.id for t in user_tweets])
            for tweet in user_tweets:
                yield tweet
            user_tweets = _timeline()
    except Exception as e:
        print(f"Error! {e}")
        pass


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
    saved_paths = [f["flagpath"] for f in state.get("flags", {}).values()]
    starting_count = len(saved_paths)
    if mode == "post":
        tweet_flag()
    elif mode == "archive":
        with Pool(50) as pool:
            for x in range(10000):
                pool.apply(archive_flag)
        final_count = len(state.get("flags"))
        print(f"Archived {final_count-starting_count} new flags")
    elif mode == "dm":
        refresh_follows()
        post_flag_from_dm()
