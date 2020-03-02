from main import cred, yield_user_tweets, get_flag_metrics, get_fyadflags_timeline, get_user_tweets
from unittest import TestCase
import pickle


class TestGetUserTweets(TestCase):
    def test_yield_tweets(self):
        tweet_generator = yield_user_tweets(cred['id'])
        unique_tweets = [
        ]
        for tweet in tweet_generator:
            if tweet not in unique_tweets:
                unique_tweets.append(tweet)
            if len(unique_tweets) >= 200:
                return
        print(len(unique_tweets))

    def test_fyadflags_timeline(self):
        tweets = get_fyadflags_timeline(400)
        print(len(tweets))

    def test_metrics(self):
        metrics = get_flag_metrics()
        print(metrics)

    def test_get_tweets(self):
        tweets = get_user_tweets(cred['id'], max_count=400)
        self.assertLessEqual(400, len(tweets))

    def test_refresh_archive(self):
        tweets = get_fyadflags_timeline(6000)
        self.assertLessEqual(6000, len(tweets))