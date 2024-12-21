from atproto import Client, client_utils
from utils import environment

logger = environment.logging.getLogger("bot.blueSky")

class MyClient():

    def __new__(cls):
        '''
        Check if running in dev mode
        '''
        if environment.DEVELOPMENT:
            logger.debug("Bluesky doesn't run in development")
            return 0
        return super(MyClient, cls).__new__(cls)

    def __init__(self):
        self.client = Client()
        self.client.login(environment.BSKY_USER, environment.BSKY_PASSWORD)

    #MARK: format post
    def format_post(self, store) -> str:
        txt = client_utils.TextBuilder()
        txt.text(f'🕹️ Free now on {store.name} 🕹️\n\n')

        end_date = store.get_date(store.data[0], 'end')
        txt.text(f'Free now until: {str(end_date)}\n\n')

        for data in store.data:
            title = data['title']
            link = data['url']
            if data['activeDeal']:
                txt.text("• ").link(title, link)
                txt.text("\n\n")
        return txt

    #MARK: Post
    def post(self, store) -> str:
        txt_string = self.format_post(store)
        post = self.client.send_video(text=txt_string, video=store.video, video_alt='game photos')
        
        bskyUrl = f"https://bsky.app/profile/{environment.BSKY_USER}/post/{post.uri.split('/')[-1]}"
        logger.info("blueSky: /%s", bskyUrl)
        
        return  (bskyUrl)
