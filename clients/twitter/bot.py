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
        self.name = 'twitter'
        self.TWEET_MAX = 280
        self.TCO_URL_LENGTH = 23
        self.client_v1 = self.get_x_v1()
        self.client_v2 = self.get_x_v2()

    def get_follower_count(self) -> dict[str, int | str]:
        """Returns the number of followers of the twitter account."""
        try:
            user = self.client_v2.get_me(user_fields=["public_metrics"])
            return {"name": self.name, "followers_count": user.data.public_metrics["followers_count"]}
        except Exception:
            logger.warning("Twitter failed to retrieve follower count")
            return {}

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
    

    def _format_deal_line(self, data, store, include_link=True):
        """
        Format a single deal line with title, optional end date, and optional link.
    
        Returns:
            Tuple of formatted deal string and calculated tweet length impact.
        """
        title = data['title']
        link = data['url']
        end_date = store.get_date(data, 'end', True)

        line = "• " + f"{title}\n"
        if end_date:
            line += f"Until: {end_date}\n"
            if (include_link):
                line += f"{link}\n\n"

        length = len(line) + self.TCO_URL_LENGTH - (len(link) if include_link else 0)
        return line, length


    def _format_default(self, store):
        """
        Format tweet with all active deals listed individually, including their links and end dates.
        """
        txt = f'🕹️ #FreeGames now on #{store.name} 🕹️\n\n'
        tweet_length = len(txt)

        for data in store.data:
            if not data.get('activeDeal', False):
                continue

            line, length = self._format_deal_line(data, store)
            txt += line
            tweet_length += length
        return txt, tweet_length
    

    def _format_group_dlc(self, store, include_link=True) -> tuple[str, int]:
        """
        Format tweet by listing only games individually, then summarizing DLCs with a single grouped link.
        """
        txt = f'🕹️ #FreeGames on #{store.name} 🕹️\n\n'
        tweet_length = len(txt)

        for data in store.data:
            if not data.get('activeDeal', False) or data.get('type') != 'game':
                continue

            line, length = self._format_deal_line(data, store, include_link)
            txt += line
            tweet_length += length

        dlcCount = sum(1 for obj in store.data if obj.get('type') != "game")
        if dlcCount:
            dlc_line = f"• {dlcCount} free DLC's \n{store.dlcUrl}"
            txt += dlc_line
            tweet_length += len(dlc_line) - len(store.dlcUrl) + self.TCO_URL_LENGTH
        return txt, tweet_length
    

    def _format_group_all(self, store) -> tuple[str, int]:
        """
        Format tweet by displaying only a grouped giveaway link, without listing individual items.
        """
        txt = f'🕹️ #FreeGames on #{store.name} 🕹️\n\n{store.giveawayUrl}'
        tweet_length = len(txt) - len(store.giveawayUrl) + self.TCO_URL_LENGTH
        return txt, tweet_length
        

    def _format_tweet(self, store, group_mode=0) -> tuple[str, int]:
        if group_mode == 1:
            return self._format_group_dlc(store)
        elif group_mode == 2:
            return self._format_group_dlc(store, include_link=False)
        elif group_mode == 3:
            return self._format_group_all(store)
        return self._format_default(store)
    

    def tweet_txt(self, store) -> str:
        for mode in range(3):
            txt, length = self._format_tweet(store, group_mode=mode)
            if length <= 280:
                return txt
        raise Exception("Tweet content exceeds 280 characters for all modes") 

        
    # MARK: Tweet
    def tweet(self, store) -> str:
        try:
            media_id: str = None
            txt = self.tweet_txt(store)

            if (store.image_twitter):
                store.image_twitter.seek(0)

                media = self.client_v1.media_upload(filename='image', file=store.image_twitter)
                media_id = [media.media_id_string]

            tweetNow = self.client_v2.create_tweet(text=txt, media_ids=media_id)
            tweetUrl = f'https://twitter.com/user/status/{ tweetNow.data["id"] }'
            logger.info("twitter: /%s", tweetUrl)
            
            return (tweetUrl)

        except Exception as e:
            logger.error("Failed to create tweet: %s", str(e))
            return "Failed"


if __name__ == "__main__":
    x = MyClient()

    current_info = "Until: Jun 20, Idle Champions of the Forgotten Realms, Redout 2"
    media_path = "img.gif"

    formatted_string = x._format_tweet(current_info)

    print(formatted_string)
    x.tweet(formatted_string, media_path)