import tweepy
from dotenv import load_dotenv
import tweepy.client
from utils import environment

load_dotenv(override=True)
logger = environment.logging.getLogger("bot.twitter")

class MyClient():

    def __new__(cls):
        '''
        Check if running in dev mode
        '''
        if environment.DEVELOPMENT:
            logger.debug("Twitter bot doesn't run in development")
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
    def format_tweet(self, store, minify=False) -> str:

        txt = f'🕹️ Free now on {store.name} 🕹️\n\n'

        for data in store.data:
            title = data['title']
            link = data['url']
            end_date = store.get_date(data, 'end')
            active_deal = data.get('activeDeal', False)

            if active_deal and (not minify or data.get('type') == 'game'):
                line = "• " + f"{title}\n"
                if end_date:
                    line += f"Until: {end_date}\n"
                line += f"{link}"
                txt += f"{line}\n\n"

        if (minify):
            dlcCount = sum(1 for obj in store.data if obj.get('type') != "game")
            txt += f"• {dlcCount} free DLC's \n{store.dlcUrl}"
        return txt.strip()
    
    # MARK: Tweet
    def tweet(self, store) -> str:
        try:
            media_id: str = None
            txt_string = self.format_tweet(store)

            if len(txt_string) > 280:
                txt_string = self.format_tweet(store, True)
                if len(txt_string) > 280:
                    logger.error("Tweet content exceeds 280 characters, even in minified form")

            if (store.image_twitter):
                store.image_twitter.seek(0)

                media = self.client_v1.media_upload(filename='image', file=store.image_twitter)
                media_id = [media.media_id_string]

            tweetNow = self.client_v2.create_tweet(text=txt_string, media_ids=media_id)
            tweetUrl = f'https://twitter.com/user/status/{ tweetNow.data["id"] }'
            logger.info("twitter: /%s", tweetUrl)
            
            return (tweetUrl)

        except Exception as e:
            logger.error("Failed to create tweet: %s", str(e))
            return None


if __name__ == "__main__":
    x = MyClient()

    current_info = "Until: Jun 20, Idle Champions of the Forgotten Realms, Redout 2"
    media_path = "img.gif"

    formatted_string = x.format_tweet(current_info)

    print(formatted_string)
    x.tweet(formatted_string, media_path)