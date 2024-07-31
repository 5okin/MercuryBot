import tweepy
import os
from dotenv import load_dotenv
from datetime import datetime
import tweepy.client
from utils import environment, makejson

load_dotenv(override=True)
logger = environment.logging.getLogger("bot")

class MyClient():

    def __new__(cls):
        '''
        Check if running in dev mode
        '''
        if environment.DEVELOPMENT:
            logger.debug('Twitter bot not running in development')
            return 0
        return super(MyClient, cls).__new__(cls)

    def __init__(self):
        self.client_v1 = self.get_x_v1()
        self.client_v2 = self.get_x_v2()


    # MARK: Setup V2
    def get_x_v1(self) -> tweepy.API:
        '''
        Get X connection 1.1
        '''

        auth = tweepy.OAuth1UserHandler(environment.X_API_KEY, environment.X_API_SECRET)
        auth.set_access_token(environment.X_ACCESS_TOKEN, environment.X_ACCESS_TOKEN_SECRET)
        return tweepy.API(auth)

    # MARK: Setup V2
    def get_x_v2(self) -> tweepy.Client:
        """Get X connection 2.0"""

        client = tweepy.Client(
            consumer_key = environment.X_API_KEY,
            consumer_secret = environment.X_API_SECRET,
            access_token = environment.X_ACCESS_TOKEN,
            access_token_secret = environment.X_ACCESS_TOKEN_SECRET,
        )
        return client
    # MARK: twitter txt
    def format_tweet(self, store) -> str:

        txt = f'🕹️ Free now on {store.name} 🕹️\n\n'

        try:
            if(store.data[0]['endDate']):
                month = datetime.strptime(store.data[0]['endDate'], '%y-%m-%d %H:%M:%S').strftime("%b")
                day = datetime.strptime(store.data[0]['endDate'], '%y-%m-%d %H:%M:%S').day
                txt += f'Free now until: {str(month)} {str(day)}\n\n'
        except:
            txt += f'Free now\n\n'

        for data in store.data:
            title = data['title']
            link = data['url']
            if data['activeDeal']:
                txt += "• " + f"{title}\n{link}\n\n"

        return txt.strip()
    
    # MARK: Tweet
    def tweet(self, store) -> None:

        media_id: str = None

        txt_string = self.format_tweet(store)

        if (store.image_twitter):
            print('----------------WITH IMAGE--------------------')
            store.image_twitter.seek(0)

            media = self.client_v1.media_upload(filename='image', file=store.image_twitter)
            media_id = [media.media_id_string]

        tweetNow = self.client_v2.create_tweet(text=txt_string, media_ids=media_id)
        print(f"https://twitter.com/user/status/{tweetNow.data['id']}")





if __name__ == "__main__":
    x = MyClient()

    current_info = "Until: Jun 20, Idle Champions of the Forgotten Realms, Redout 2"
    media_path = "img.gif"

    formatted_string = x.format_tweet(current_info)

    print(formatted_string)
    x.tweet(formatted_string, media_path)