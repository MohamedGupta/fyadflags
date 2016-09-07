import twitter, twitter_config
from os import path
user = 'FYADFlags'

states_file = '/users/pi/git/fyadflags/states.dict'
if path.isfile(states_file):
    states = dict(open(states_file, 'r').read())
else:
    states = {'since_id': 0, 'blacklist_users': [], 'blacklist_paths': []}

def check_tweets(tw):
    try:
        menchies = tw.GetMentions(since_id=states['since_id'])
    except:
        print 'Failed to get menchies for ' + user
        return
    if menchies:
        states['since_id'] = menchies[0].id
        for mench in menchies:
            if 'blacklist' in mench.text.lower():
                try:
                    bad_tweet = tw.GetStatus(mench.in_reply_to_status_id)
                    blacklist_path = bad_tweet.text

                    states['blacklist_paths']
                except twitter.error.TwitterError:
                    next




if __name__ == '__main__':
    cred = twitter_config.accounts[user]
    try:
        tw = twitter.Api(consumer_key=cred['consumer_key'],
                         consumer_secret=cred['consumer_secret'],
                         access_token_key=cred['access_token_key'],
                         access_token_secret=cred['access_token_secret'])
    except Exception, e:
        print e
        print 'Error on init'
        exit()

    check_tweets(tw)

