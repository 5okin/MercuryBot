from typing import Self
from atproto import Client, client_utils
from utils import environment

logger = environment.logging.getLogger("bot.blueSky")

class MyClient():

    def __new__(cls) -> None | Self:
        '''
        Check if running in dev mode
        '''
        if environment.DEVELOPMENT:
            logger.debug("Bluesky doesn't run in development")
            return None
        return super(MyClient, cls).__new__(cls)

    def __init__(self) -> None:
        self.name = 'bluesky'
        self.client = Client()
        self.user = environment.BSKY_USER
        self.client.login(environment.BSKY_USER, environment.BSKY_PASSWORD)


    def get_follower_count(self) -> dict:
        """Returns the number of followers of the Bluesky account."""
        try:
            if self.user:
                profile = self.client.get_profile(self.user)
                return {"name": self.name, "followers_count": profile.followers_count}
            else: 
                return {}
        except Exception:
            logger.error("Bluesky failed to retrieve follower count")
            return {}

    #MARK: format post
    def format_post(self, store) -> str:
        txt = client_utils.TextBuilder()
        txt.text("🕹️ ").tag('Free now', 'freegames')
        txt.text(" on ").tag(store.name, store.name).text(" 🕹️\n\n")

        end_date = store.get_date(store.data[0], 'end', True)
        txt.text(f'Free now until: {str(end_date)}\n\n')

        for data in store.data:
            title = data['title']
            link = data['url']
            if data['activeDeal']:
                txt.text("• ").link(title, link)
                txt.text("\n\n")
        return str(txt)

    #MARK: Post
    def post(self, store) -> str:
        try:
            txt_string = self.format_post(store)
            post = self.client.send_video(text=txt_string, video=store.video, video_alt='game photos')
            
            bskyUrl = f"https://bsky.app/profile/{environment.BSKY_USER}/post/{post.uri.split('/')[-1]}"
            logger.info("blueSky: /%s", bskyUrl)
            
            return  (bskyUrl)

        except Exception as e:
            logger.error("Failed to create Bluesky post %s", str(e))
            return "Failed"


if __name__ == "__main__":
    from utils import environment
    
    bsky = MyClient()

    number = bsky.get_follower_count()
    print(number)
