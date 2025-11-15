from datetime import datetime
from urllib.request import urlopen
import io, os
import asyncio
from PIL import Image
from utils import makejson
from stores._store import Store
import gc


class Main(Store):
    '''
    Epic store 
    '''
    def __init__(self):
        self.online_data = []
        self.page = 'https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions'
        self.dlcUrl = 'https://store.epicgames.com/en-US/free-games'
        self.giveawayUrl = 'https://store.epicgames.com/en-US/free-games'
        super().__init__(
            name = 'epic',
            id = '1',
            discord_emoji = os.getenv('DISCORD_EPIC_EMOJI'),
            twitter_notification = True,
            bsky_notification = True,
            service_name = 'Epic Games',
            url = 'https://www.epicgames.com/store/us-US/product/'
        )

    #MARK: process_data
    async def process_data(self, pages):
        """
        Main epic scraper
        """
        if not pages:
            return False

        json_data = []
        game_list = pages['data']['Catalog']['searchStore']['elements']
        for game in game_list:

            if game['promotions'] is not None:
                game_name = game['title']

                if (game['catalogNs']['mappings'] is not None) and (len(game['catalogNs']['mappings'])):
                    product_url = game['catalogNs']['mappings'][0]['pageSlug']
                    game_url = self.url + product_url
                elif game['productSlug'] and game['productSlug'] != "[]":
                    # When gift is opened (Xmas, etc) productSlug is []
                    product_url = game['productSlug']
                    game_url = self.url + product_url
                else:
                    game_url = 'https://store.epicgames.com/en-US/free-games'

                # Get the game image
                try:
                    tall_image_url = None
                    wide_image_url = None

                    # Loop through the key images
                    for j, image in enumerate(game['keyImages']):
                        image_type = image['type']

                        if wide_image_url and tall_image_url:
                            break

                        if "Tall" in image_type:
                            tall_image_url = image['url']
                        elif "Wide" in image_type:
                            wide_image_url = image['url']

                except Exception as e:
                    tall_image_url = wide_image_url = game['keyImages'][0]['url']

                # Current deal
                if game['promotions']['promotionalOffers']:
                    if game['price']['totalPrice']['fmtPrice']['discountPrice'] == "0":
                        offer = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]
                        startDate = datetime.strptime(offer['startDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                        endDate = datetime.strptime(offer['endDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                        json_data = makejson.data(json_data,
                                                    game_name,
                                                    1,
                                                    game_url,
                                                    tall_image_url,
                                                    startDate,
                                                    endDate,
                                                    wide_image_url)

                # Upcoming deal
                if game['promotions']['upcomingPromotionalOffers']:
                    for offer in game['promotions']['upcomingPromotionalOffers'][0]['promotionalOffers']:
                        if offer['discountSetting']['discountPercentage'] == 0:
                            offer =  game['promotions']['upcomingPromotionalOffers'][0]['promotionalOffers'][0]
                            startDate = datetime.strptime(offer['startDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                            endDate = datetime.strptime(offer['endDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                            json_data = makejson.data(json_data,
                                                        game_name,
                                                        0,
                                                        game_url,
                                                        tall_image_url,
                                                        startDate,
                                                        endDate,
                                                        wide_image_url)
        del game_list
        return await self.compare(json_data)


    #MARK: combined GIF
    async def create_combined_gif(self):
        """
        Generates a gif from the given list of images
        """
        arr = io.BytesIO()
        curr_images, next_images, combined_images = [], [], []

        image_active = [
            self.fetch_image(game['image']) for game in self.data if game['activeDeal'] == 1
        ]
        image_future = [
            self.fetch_image(game['image']) for game in self.data if game['activeDeal'] == 0
        ]        
        
        active_images, future_images = await asyncio.gather(
            asyncio.gather(*image_active),
            asyncio.gather(*image_future)
        )

        curr_images = [img for img in active_images if img]
        next_images = [img for img in future_images if img]

        if len(curr_images) >= len(next_images):
            for index, image in enumerate(curr_images):
                if index < len(next_images):
                    new_image = Image.new('RGB', (image.size[0] + next_images[index].size[0], image.size[1]), 0)
                    new_image.paste(image, (0, 0))
                    new_image.paste(next_images[index], (image.size[0], 0))
                    combined_images.append(new_image)
                else:
                    new_image = Image.new('RGB', (image.size[0] + next_images[len(next_images) - 1].size[0], image.size[1]), 0)
                    new_image.paste(image, (0, 0))
                    new_image.paste(next_images[len(next_images) - 1], (image.size[0], 0))
                    combined_images.append(new_image)
        else:
            for index, image in enumerate(next_images):
                if index < len(curr_images):
                    new_image = Image.new('RGB', (curr_images[index].size[0] + next_images[index].size[0], image.size[1]), 0)
                    new_image.paste(curr_images[index], (0, 0))
                    new_image.paste(image, (curr_images[index].size[0], 0))
                    combined_images.append(new_image)
                else:
                    new_image = Image.new('RGB', (curr_images[len(curr_images) - 1].size[0] + image.size[0], image.size[1]), 0)
                    new_image.paste(curr_images[len(curr_images) - 1], (0, 0))
                    new_image.paste(image, (curr_images[len(curr_images) - 1].size[0], 0))
                    combined_images.append(new_image)

        combined_images[0].save(arr, format='GIF', append_images=combined_images[1:], save_all=True, duration=2000, loop=0)
        arr.seek(0)
        
        for img in curr_images + next_images + combined_images:
            try:
                img.close()
            except Exception:
                pass
        
        del curr_images, next_images, combined_images
        gc.collect()

        return arr

    #MARK: Scheduler
    async def scheduler(self):
        while True:
            if self.data:
                date = self.data[0]['endDate']

                # From all the deals saved find the one that ends first
                for time in self.data:
                    temp = time['endDate']
                    if temp < date:
                        date = temp

                delta = date - datetime.now()
                # if the time has come, Get the deals 5 minutes after they go live
                if delta.total_seconds() <= 0:
                    print("EPIC -> End date of deal is today i'll wait 10 minutes and get new games")
                    await asyncio.sleep(600)
                    return self
                # if deal ends in the next 24-hours just wait for it.
                elif delta.total_seconds() <= 86400:
                    self.logger.info(f"EPIC -> Waiting for {delta.total_seconds()}", extra={
                        '_game_time': date,
                        '_datetime.now': datetime.now()
                    })

                    await asyncio.sleep(delta.total_seconds())
                # if deal doesn't end in the next 24 hours check if the games changed every 30-minutes
                else:
                    await asyncio.sleep(self.scheduler_time)
                    return self
            else:
                print("self.data was empty")
                await asyncio.sleep(60)

    async def set_images(self):
        self.image = await self.create_combined_gif()
        # self.image_mobile = await self.make_gif_image()
        self.image_twitter = await self.make_gif_image(True, size=2)

    #MARK: get
    async def get(self):
        """
        Runs epic data check, fetch and compile

        returns 0 if nothing changed 
        returns 1 if new data was found
        """
        if await self.process_data(await self.request_data(self.page)):
            return 1
        return 0


if __name__ == "__main__":
    # run with python -m stores.epic
    from utils import environment
    from utils.database import Database
    Database.connect(environment.DB)

    store = Main()
    asyncio.run(store.get())
    print(store.data)
    print(store.image_twitter)
    # asyncio.run(store.scheduler())


    # import clients.twitter.bot as twitter
    # x = twitter.MyClient()
    # x.tweet(store)
