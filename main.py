#!/usr/bin/env python
import twitter, twitter_config
import requests
import boto3
import json
import hashlib
from collections import defaultdict
from multiprocessing import Pool

cred = twitter_config.accounts['FYADFlags']
s3 = boto3.resource("s3")
FLAG_URL = 'http://forums.somethingawful.com/flag.php?forumid=26'
BUCKET = "fucktardidiot"
STATE = s3.Object(BUCKET, "fyadflags/index.json")
LOCALSTATE = "fyadflags.json"
twitter_api = twitter.Api(consumer_key=cred['consumer_key'], consumer_secret=cred['consumer_secret'],
                            access_token_key=cred['access_token_key'], access_token_secret=cred['access_token_secret'])
global saved_paths

def get_state():
    try:
        return json.load(open(LOCALSTATE, "r"))
    except Exception:
        return defaultdict(dict)
    # try:
    #     return json.loads(STATE.get()['Body'])
    # except Exception as e:
    #     print('Failed to load state: {e}')
    #     return defaultdict(dict)

def save_state(state):
    with open(LOCALSTATE, "w") as statefile:
        statefile.write(json.dumps(state))


def handler(event, context):
    tweet_flag()


def flag_already_saved(flag, flag_content):
    if flag['flagpath'] in saved_paths:
        return True
    state = get_state()
    checksum = hashlib.md5(flag_content).hexdigest()
    return checksum in (state.get('flags') or [])


def record_flag(flag, flag_content):
    state = get_state()
    checksum = hashlib.md5(flag_content).hexdigest()
    state['flags'][checksum] = flag
    saved_paths.append(flag['flagpath'])
    save_state(state)


def save_and_record_flag(flag, flag_content):
    # s3flag = s3.Object(BUCKET, get_flag_key(flag_description, flag_content))
    # s3flag.put(Body=flag_content)
    if not flag_already_saved(flag, flag_content):
        with open(f"{get_flag_key(flag['description'], flag_content)}.jpg", "wb") as f:
            f.write(flag_content)
        record_flag(flag, flag_content)
        print(f"Found a new flag: {flag['description']}")
    else:
        print(f"Flag already archived")


def get_flag_key(flag_description, flag_content):
    return f"fyadflags/{flag_description.replace(' ', '_').replace('/', '_').replace('#', '')}_{hashlib.md5(flag_content).hexdigest()}"


def archive_handler(event, context):
    tweet_flag(True)


def tweet_flag(archive_only=False):
    flag = requests.get(FLAG_URL).json()
    while flag['username'] in twitter_config.blacklist_flags or flag['path'] in twitter_config.blacklist_flagpaths:
        flag = requests.get(FLAG_URL).json()

    flag['flagpath'] = "http://fi.somethingawful.com/flags" + flag['path']
    flag['description'] = f"#FYADflag by {flag['username']} {flag['created']}"
    if flag['path'] != 'error.png':
        try:
            if not archive_only:
                print(f'Posting flag: {flag["description"]}')
                r = twitter_api.PostUpdate(flag['description'], media=flag['flagpath'])
            flag_content = requests.get(flag['flagpath']).content
            flag['flag_key'] = get_flag_key(flag['description'], flag_content)
            save_and_record_flag(flag, flag_content)

        except:
            raise
            print('Flag post failed ' + flag['flagpath'])
    else:
        print('SA PHP error {0}'.format(flag))


if __name__ == '__main__':
    try:
        api = twitter.Api(consumer_key=cred['consumer_key'], consumer_secret=cred['consumer_secret'],
                          access_token_key=cred['access_token_key'], access_token_secret=cred['access_token_secret'])
    except:
        print('Failed to authenticate.')
        exit()
    state = get_state()
    saved_paths = [f['flagpath'] for f in state.get('flags', {}).values()]
    with Pool(50) as pool:
        for x in range(10000):
            pool.apply(tweet_flag, [True])


