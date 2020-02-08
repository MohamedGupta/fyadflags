#!/usr/bin/env python
import twitter, twitter_config
import requests
import boto3
import hashlib
from collections import defaultdict

cred = twitter_config.accounts['FYADFlags']
s3 = boto3.resource("s3")
FLAG_URL = 'http://forums.somethingawful.com/flag.php?forumid=26'
BUCKET = "theBucket"
STATE = s3.Object(BUCKET, "fyadflags/index.json")
twitter_api = twitter.Api(consumer_key=cred['consumer_key'], consumer_secret=cred['consumer_secret'],
                            access_token_key=cred['access_token_key'], access_token_secret=cred['access_token_secret'])


def get_state():
    try:
        return json.loads(STATE.get()['Body'])
    except Exception as e:
        print('Failed to load state: {e}')
        return defaultdict(dict)


def handler(event, context):
    tweet_flag()


def flag_already_saved(flag_content):
    state = get_state()
    checksum = hashlib.md5(flag_content).hexdigest()
    return checksum in (state.get('flags') or [])


def record_flag(flag, flag_content):
    state = get_state()
    checksum = hashlib.md5(flag_content).hexdigest()
    state['flags']['checksum'] = flag


def get_flag_key(flag_description, flag_content):
    return f"fyadflags/{flag_description.replace(' ', '_')}_{hashlib.md5(flag_content).hexdigest()}"


def archive_handler(event, context):
    tweet_flag(True)


def tweet_flag():
    flag = requests.get(FLAG_URL).json()
    while flag['username'] in twitter_config.blacklist_flags or flag['path'] in twitter_config.blacklist_flagpaths:
        flag = requests.get(FLAG_URL).json()

    flagpath = "http://fi.somethingawful.com/flags" + flag['path']
    flag_description = f"#FYADflag by {flag['username']} {flag['created']}"
    print(f'Posting flag: {flag_description}')
    if flag['path'] != 'error.png':
        try:
            if not archive_only:
                r = twitter_api.PostUpdate(flag_description, media=flagpath)
                print('Posted flag ' + flagpath)
            flag_content = requests.get(flagpath).content
            flag['flag_key'] = get_flag_key(flag_description, flag_content)
            if not flag_already_saved(flag_content):
               s3flag = s3.Object(BUCKET, get_flag_key(flag_description, flag_content))
               s3flag.put(Body=flag_content)
               record_flag(flag_content, flag)

        except:
            raise
            print('Flag post failed ' + flagpath)
    else:
        print('SA PHP error {0}'.format(flag))


if __name__ == '__main__':
    try:
        api = twitter.Api(consumer_key=cred['consumer_key'], consumer_secret=cred['consumer_secret'],
                          access_token_key=cred['access_token_key'], access_token_secret=cred['access_token_secret'])
    except:
        print('Failed to authenticate.')
        exit()

    tweet_flag(api)


