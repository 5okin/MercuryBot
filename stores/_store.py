from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
from PIL import Image
import environment
import makejson
import json
import asyncio
import io


logger = environment.logging.getLogger("bot")


class Store:
    def __init__(self, 
                 name, 
                 service_name, 
                 url, 
                 data=[],
                 image=None, 
                 image_type='GIF', 
                 alert_flag=True
                 ):
        self.name = name
        self.service_name = service_name
        self.url = url
        self.data = data
        self.image = image
        self.image_type = image_type
        self.alert_flag = alert_flag


    def request_data(self, url=None):
        if url is None : url = self.page
        try:
            data = urlopen(Request(url, headers={'User-Agent': 'Mozilla'}))
            data = json.loads(data.read().decode())
            return data
        except (URLError, HTTPError) as e:
            print(f"Request to {self.service_name} failed")
            return False

    
    def make_image(self):
        '''
        Creates an image with game images appended side by side

        :return: Nothing, saves the result to store image variable
        '''
        images = []
        new_img_size = 0

        if self.data:
            for game in self.data:
                images.append(Image.open(urlopen(game['image'])))

            for image in images:
                new_img_size += image.size[0]
            new_image = Image.new('RGB', (new_img_size, images[0].size[1]), (47, 49, 54, 0))

            size = 0
            for image in images:
                new_image.paste(image, (size, 0))
                size += image.size[0]

            new_image.thumbnail((new_image.size[0] // 2, new_image.size[1] // 2))
            self.image = new_image
 
    def make_gif_image(self):
        '''
        Creates a gif off of a list of urls containing images
        '''

        if not self.data:
            return 0

        arr = io.BytesIO()
        img, *imgs = [Image.open(urlopen(game['image'])) for game in self.data]

        img.thumbnail((img.size[0], img.size[1]))

        for im in imgs:
            im.thumbnail((im.size[0], im.size[1]))

        img.save(fp=arr, format='GIF', append_images=imgs, save_all=True, duration=1000, loop=0)
        self.image = arr

     

    def compare(self, json_data):
        if self.data:

            # Online data
            game_titles = []
            for game in json_data:
                if game['activeDeal']:
                    game_titles.append(game['title'].encode('ascii', 'ignore').decode('ascii'))

            # Local data
            temp_names = []
            for data_game_name in self.data:
                if data_game_name['activeDeal']:
                    temp_names.append(data_game_name['title'])


            logger.debug(f'{self.name=}: {game_titles=}')
            logger.debug(f'{self.name=}: {temp_names=}')

            # Check if db deals has all the newest games
            check = all(item in temp_names for item in game_titles)

            if check is True:
                logger.info(f'{self.service_name} - SAME')
                if len(temp_names) > len(json_data):
                    self.data = json_data.copy()
                return 0
        self.data = json_data
        return 1


    """
    get(self)
    
    check if we have new deals
    process the data
    return 1 if theres new data
    return 0 if there isnt new data
    """



    async def scheduler(self):
        # Get update every 6 hours
        await asyncio.sleep(1800)
        print(f'{self.service_name}={self.data}')
        return self
    
