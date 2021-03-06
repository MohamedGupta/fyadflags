#!/usr/bin/env python
import twitter, twitter_config
import requests
from os import path

cred = twitter_config.accounts['FYADFlags']
blacklist_file = '/users/pi/git/fyadflags/blacklist.dict'

if path.isfile(blacklist_file):
    blacklist = dict(open(blacklist_file, 'r').read())
else:
    blacklist = {'users': [], 'paths': []}

def tweet_flag(api):
    flag = requests.get('http://forums.somethingawful.com/flag.php?forumid=26').json()
    while flag['username'] in blacklist['users'] or flag['path'] in blacklist['paths']:
        flag = requests.get('http://forums.somethingawful.com/flag.php?forumid=26').json()

    flagpath = "http://fi.somethingawful.com/flags" + flag['path']
    tweet = "#FYADflag " + flagpath + " by " + flag['username'] + " " + flag['created']
    mediatweet = "#FYADflag by " + flag['username'] + " " + flag['created'] + " " + flagpath
    if flag['path'] != 'error.png':
        try:
            r = api.PostUpdate(mediatweet, media=flagpath)
            print 'Posted flag ' + flagpath
        except:
            print 'Flag post failed ' + flagpath
    else:
        print 'SA PHP error {0}'.format(flag)
if __name__ == '__main__':
    try:
        api = twitter.Api(consumer_key=cred['consumer_key'], consumer_secret=cred['consumer_secret'],
                          access_token_key=cred['access_token_key'], access_token_secret=cred['access_token_secret'])
    except:
        print 'Failed to authenticate.'
        exit()

    tweet_flag(api)

