import time
import sys
import datetime

import tweepy
import pytz

DJT_USER_ID = '25073877'
WH_USER_ID = '822215673812119553'

class TweetStream():
    # Should take from_id in constructor
    def __init__(self, start_date, api_key, api_secret):
        self.callback = None
        self.start_date = start_date
        self.auth = None
        self.api = None
        self.api_key = api_key
        self.api_secret = api_secret

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
        self.auth = tweepy.AppAuthHandler(self.api_key, self.api_secret)
        self.api = tweepy.API(self.auth)

        previous_tweets = self.get_tweets_until_date()
        count = len(previous_tweets)
        print(count)
        last_id = previous_tweets[0].id
        print(previous_tweets[0].text)
        print(previous_tweets[0].created_at)
        #initial_tweet = api.user_timeline(id=DJT_USER_ID, count=1)[0]
        #current_id = initial_tweet.id
        while True:
            try:
                for tweet in tweepy.Cursor(self.api.user_timeline, id=DJT_USER_ID, since_id=last_id).items():
                    last_id = tweet.id
                    count += 1
                    if self.callback:
                        self.callback(tweet, count)
                        sys.exit(0)
                
                # This is a significant bottleneck?
                time.sleep(1)
            except tweepy.TweepError as e:
                print(f'Waiting 30 seconds: {e.response.text}')
                time.sleep(30)


    # callback is a function that takes a tweet object as an argument
    def set_callback(self, callback):
        self.callback = callback

# Return a list of tweets up to a unix timestamp (Make sure it's in UTC!)
# Utilize the last item to obtain the current tweet id for tweet stream
    def get_tweets_until_date(self):
        if not self.auth:
            self.auth = tweepy.AppAuthHandler(self.api_key, self.api_secret)
        if not self.api:
            self.api = tweepy.API(self.auth)
        #auth = tweepy.AppAuthHandler(API_KEY, API_SECRET)
        #api = tweepy.API(auth)
        tweets = []
        for page in tweepy.Cursor(self.api.user_timeline, count=200, id=DJT_USER_ID).pages():
            # No idea why I can't get the datetime library to work the way I want to do direct comparisons..
            for tweet in page:
                tweet_date = tweet.created_at.astimezone(datetime.timezone.utc)
                #tweet_date = tweet.created_at.astimezone(datetime.timezone.utc)
                #tweet_date = tweet.created_at.timestamp() - 60*60*5
                #tweet_date = pytz.timezone('US/Eastern').localize(tweet.created_at)
                if tweet_date.timestamp() < self.start_date.timestamp():
                    #print(f'hit boundary tweet: {tweet.created_at}, {tweet.text}')
                    return tweets
                tweets.append(tweet)

        return tweets

def callback(tweet, count):
    #print(f'{count}, {pytz.timezone("US/Eastern").localize(tweet.created_at)}')
    print(f'{count},{tweet.created_at}')

def load_keys(filename):
    with open(filename, 'r') as f:
        data = f.read().strip('\n')
        return data.split('\n')

if __name__ == '__main__':
    # How can we input the time in eastern, convert to utc, and then compare to the utc dates
    # from tweet timestamps?
    t = datetime.datetime.strptime('Aug 28 2019 16:00', '%b %d %Y %H:%M').astimezone(datetime.timezone.utc)
    ts = TweetStream(t, *load_keys('../etc/api.txt'))
    count = 1
    tweets = ts.get_tweets_until_date()
    tweets.reverse()
    for tweet in tweets:
        #print(f'{count} {datetime.datetime.fromtimestamp(tweet.created_at.timestamp() - 60*60*5)}')
        callback(tweet, count)
        count += 1
    #ts.set_callback(callback)
    #ts.run()
