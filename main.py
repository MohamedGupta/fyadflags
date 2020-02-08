#!/usr/bin/env python
import twitter, twitter_config
import requests
#cred = next(acct for acct in twitter_config.accounts if acct['username'] == 'FYADFlags')
cred = twitter_config.accounts['FYADFlags']


def handler(event, context):
    try:
        api = twitter.Api(consumer_key=cred['consumer_key'], consumer_secret=cred['consumer_secret'],
                           access_token_key=cred['access_token_key'], access_token_secret=cred['access_token_secret'])
    except:
        print('Failed to authenticate.')
    tweet_flag(api)


def tweet_flag(api):
    flag = requests.get('http://forums.somethingawful.com/flag.php?forumid=26').json()
    while flag['username'] in twitter_config.blacklist_flags or flag['path'] in twitter_config.blacklist_flagpaths:
        flag = requests.get('http://forums.somethingawful.com/flag.php?forumid=26').json()
    #flag = json.loads(req.content)
    flagpath = "http://fi.somethingawful.com/flags" + flag['path']
    tweet = "#FYADflag " + flagpath + " by " + flag['username'] + " " + flag['created']
    mediatweet = "#FYADflag by " + flag['username'] + " " + flag['created'] # + " " + flagpath
    if flag['path'] != 'error.png':
        try:
            r = api.PostUpdate(mediatweet, media=flagpath)
            print('Posted flag ' + flagpath)
        except:
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

