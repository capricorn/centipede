import time
import sys
import datetime

import tweepy

DJT_USER_ID = '25073877'
WH_USER_ID = '822215673812119553'

class TweetStream():
    # Should take from_id in constructor
    def __init__(self, start_date):
        self.callback = None
        self.start_date = start_date.timestamp()
        self.auth = None
        self.api = None

    def stream(self):
        self.auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
        self.auth.set_access_token(ACCESS_TOKEN_PUB, ACCESS_TOKEN_SECRET)
        self.api = tweepy.API(self.auth)


        class MyStreamListener(tweepy.StreamListener):
            def on_status(self, status):
                if status.user.id_str == DJT_USER_ID:
                    print(status.text)

            def on_error(self, status_code):
                print(status_code)

        # Might have our realtime filter working here

        stream_listener = MyStreamListener()
        stream = tweepy.Stream(auth=self.api.auth, listener=stream_listener)
        stream.filter(follow=['25073877'])
        

    def run(self):
        self.auth = tweepy.AppAuthHandler(API_KEY, API_SECRET)
        self.api = tweepy.API(self.auth)

        previous_tweets = self._get_tweets_until_date()
        count = len(previous_tweets)
        print(count)
        last_id = previous_tweets[0].id
        #initial_tweet = api.user_timeline(id=DJT_USER_ID, count=1)[0]
        #current_id = initial_tweet.id
        while True:
            for tweet in tweepy.Cursor(self.api.user_timeline, id=WH_USER_ID, since_id=last_id).items():
                last_id = tweet.id
                count += 1
                if self.callback:
                    self.callback(tweet, count)
                    sys.exit(0)
            
            # This is a significant bottleneck
            time.sleep(1)

    # callback is a function that takes a tweet object as an argument
    def set_callback(self, callback):
        self.callback = callback

# Return a list of tweets up to a unix timestamp (Make sure it's in UTC!)
# Utilize the last item to obtain the current tweet id for tweet stream
    def _get_tweets_until_date(self):
        #auth = tweepy.AppAuthHandler(API_KEY, API_SECRET)
        #api = tweepy.API(auth)
        tweets = []
        for tweet in tweepy.Cursor(self.api.user_timeline, id=WH_USER_ID).items(200):
            # No idea why I can't get the datetime library to work the way I want to do direct comparisons..
            tweet_date = tweet.created_at.timestamp() - 60*60*5
            if tweet_date < self.start_date:
                break
            tweets.append(tweet)
        return tweets

def callback(tweet, count):
    print(f'{count}, {tweet.created_at}')

if __name__ == '__main__':
    t = datetime.datetime.strptime('Aug 15 2019 12:00', '%b %d %Y %H:%M')
    ts = TweetStream(t)
    ts.set_callback(callback)
    ts.run()
