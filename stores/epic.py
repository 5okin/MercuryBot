from datetime import datetime
from urllib.request import urlopen
import io
import asyncio
from PIL import Image
from utils import makejson
from stores._store import Store


class Main(Store):
    '''
    Epic store 
    '''
    def __init__(self):
        self.online_data = []
        self.page = 'https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions'
        super().__init__(
            name = 'epic',
            id = '1',
            twitter_notification=True,
            service_name = 'Epic Games',
            url = 'https://www.epicgames.com/store/us-US/product/',
        )

    #MARK: process_data
    def process_data(self, pages):
        """
        Main epic scraper
        """
        if not pages:
            return False

        json_data = []

        i = 0
        game_list = pages['data']['Catalog']['searchStore']['elements']
        #while i < len(game_list):
        for game in game_list:

            if game['promotions'] is not None:
                game_name = game['title']

                if (game['catalogNs']['mappings'] is not None) and (len(game['catalogNs']['mappings'])):
                    product_url = game['catalogNs']['mappings'][0]['pageSlug']
                    game_url = self.url + product_url
                elif game['productSlug'] != "[]":
                    # When gift is opened (Xmas, etc) productSlug is []
                    product_url = game['productSlug']
                    game_url = self.url + product_url
                else:
                    game_url = 'https://store.epicgames.com/en-US/free-games'

                # Get the game image

                try:
                    tall_image_url: str = None
                    wide_image_url: str = None

                    # Loop through the key images
                    for j, image in enumerate(game['keyImages']):
                        image_type = image['type']
                        
                        # Check for the wide image for Twitter
                        if image_type == 'OfferImageWide':
                            wide_image_url = image['url']

                        priority_types = ['VaultOpened', 'DieselStoreFrontTall', 'Thumbnail', 'VaultClosed']
                        while priority_types:
                            current_priority = priority_types.pop(0)
                            
                            if image_type == current_priority:
                                if image_type == 'VaultClosed' and j + 2 < len(game['keyImages']):
                                    tall_image_url = game['keyImages'][j + 2]['url']
                                else:
                                    tall_image_url = image['url']
                                break
                        
                        if wide_image_url and tall_image_url:
                            break

                except Exception as e:
                    tall_image_url = wide_image_url = game['keyImages'][0]['url']

                tall_image_url = tall_image_url.replace(" ", "%20")

                # If Current deal
                if game['promotions']['promotionalOffers']:
                    if game['price']['totalPrice']['fmtPrice']['discountPrice'] == "0":
                        offer = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]
                        json_data = makejson.data(json_data,
                                                    game_name,
                                                    1,
                                                    game_url,
                                                    tall_image_url,
                                                    offer['startDate'],
                                                    offer['endDate'],
                                                    wide_image_url)

                # If upcoming upcoming deal
                if game['promotions']['upcomingPromotionalOffers']:
                    for offer in game['promotions']['upcomingPromotionalOffers'][0]['promotionalOffers']:
                        if offer['discountSetting']['discountPercentage'] == 0:
                            offer =  game['promotions']['upcomingPromotionalOffers'][0]['promotionalOffers'][0]
                            json_data = makejson.data(json_data,
                                                        game_name,
                                                        0,
                                                        game_url,
                                                        tall_image_url,
                                                        offer['startDate'],
                                                        offer['endDate'],
                                                        wide_image_url)
            i += 1
        return self.compare(json_data)

    #MARK: resize images
    @staticmethod
    def resize_images(images):
        '''
        Image resize
        '''

        for index, image in enumerate(images):
            fixed_height = 300
            height_percent = fixed_height / float(image.size[1])
            width_size = int((float(image.size[0]) * float(height_percent)))
            images[index] = image.resize((width_size, fixed_height))
        return images

    #MARK: combined GIF
    def create_combined_gif(self):
        """
        Generates a gif from the given list of images
        """

        arr = io.BytesIO()
        curr_images = []
        next_images = []
        combined_images = []

        # Separate images to 2 list according to if it's free now or in the future
        for game in self.data:
            if game['activeDeal']:
                curr_images.append(Image.open(urlopen(game['image'])))
            else:
                next_images.append(Image.open(urlopen(game['image'])))

        curr_images = self.resize_images(curr_images)
        next_images = self.resize_images(next_images)

        if len(curr_images) >= len(next_images):
            for index, image in enumerate(curr_images):
                if index < len(next_images):
                    new_image = Image.new('RGB',
                                        (image.size[0] + next_images[index].size[0],
                                        image.size[1]),(47, 49, 54, 0))
                    new_image.paste(image, (0, 0))
                    new_image.paste(next_images[index], (image.size[0], 0))
                    combined_images.append(new_image)
                else:
                    new_image = Image.new('RGB',
                                        (image.size[0] + next_images[len(next_images) - 1].size[0],
                                        image.size[1]),(47, 49, 54, 0))
                    new_image.paste(image, (0, 0))
                    new_image.paste(next_images[len(next_images) - 1], (image.size[0], 0))
                    combined_images.append(new_image)

        if len(curr_images) < len(next_images):
            for index, image in enumerate(next_images):
                if index < len(curr_images):
                    new_image = Image.new('RGB',
                                        (curr_images[index].size[0] + next_images[index].size[0],
                                        image.size[1]),(47, 49, 54, 0))
                    new_image.paste(curr_images[index], (0, 0))
                    new_image.paste(image, (curr_images[index].size[0], 0))
                    combined_images.append(new_image)
                else:
                    new_image = Image.new('RGB',
                                        (curr_images[len(curr_images) - 1].size[0] + next_images[len(next_images) - 1].size[0],
                                        image.size[1]), (47, 49, 54, 0))
                    new_image.paste(curr_images[len(curr_images) - 1], (0, 0))
                    new_image.paste(image, (curr_images[len(curr_images) - 1].size[0], 0))
                    combined_images.append(new_image)

        combined_images[0].save(arr, format='GIF', append_images=combined_images[1:], save_all=True, duration=2000,
                                loop=0)
        return arr

    #MARK: Scheduler
    async def scheduler(self):
        while True:
            if self.data:
                date = datetime.strptime(self.data[0]['endDate'], '%y-%m-%d %H:%M:%S')

                # From all the deals saved find the one that ends first
                for time in self.data:
                    temp = datetime.strptime(time['endDate'], '%y-%m-%d %H:%M:%S')
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
                    print(f'game time: {date}')
                    print(f'datetime.now: {datetime.now()}')
                    print(f'EPIC -> Waiting for {delta.total_seconds()} before trying to loop again')
                    await asyncio.sleep(delta.total_seconds())
                # if deal doesn't end in the next 24 hours check if the games changed every 30-minutes
                else:
                    await asyncio.sleep(1800)
                    return self
            else:
                print("self.data was empty")
                await asyncio.sleep(60)

    #MARK: get
    async def get(self):
        """
        Runs epic data check, fetch and compile
        """
        if self.process_data(self.request_data(self.page)):
            self.image = self.create_combined_gif()
            self.image_mobile = self.make_gif_image()
            self.image_twitter = self.make_gif_image(True, size=2)
            #self.image_twitter[1] = self.make_gif_image(True, 0)
            return 1
        return 0


if __name__ == "__main__":
    # run with python -m stores.epic
    a = Main()
    asyncio.run(a.get())
    print(a.data)
    print(a.image_twitter)
    #asyncio.run(a.scheduler())


    import clients.twitter.bot as twitter
    x = twitter.MyClient()
    x.tweet(a)
