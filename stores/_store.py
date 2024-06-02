import json
import asyncio
import io
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import List, Optional
from PIL import Image
from utils import environment

logger = environment.logging.getLogger("bot")


class Store:
    """
    Init store
    """
    def __init__(self,
                name: str,
                service_name: str,
                url: str,
                data: Optional[List] = None,
                image=None,
                mobile_image=None,
                image_type: str = 'GIF',
                alert_flag: bool = True
                ):
        self.name = name
        self.service_name = service_name
        self.url = url
        self.data = data
        self.image = image
        self.mobile_image = mobile_image
        self.image_type = image_type
        self.alert_flag = alert_flag


    def request_data(self, url=None):
        """
        Simple json getter
        """
        try:
            data = urlopen(Request(url, headers={'User-Agent': 'Mozilla'}))
            data = json.loads(data.read().decode())
            return data
        except (URLError, HTTPError) as e:
            logger.debug("Request to %s failed %s", self.service_name, e)
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
            return new_image

    def make_gif_image(self):
        '''
        Creates a gif off of a list of urls containing images
        '''

        if not self.data:
            return 0

        arr = io.BytesIO()
        img, *imgs = [
            Image.open(urlopen(game['image']))
            for game in self.data
            if game['activeDeal'] == 1
        ]

        img.thumbnail((img.size[0], img.size[1]))

        for im in imgs:
            im.thumbnail((im.size[0], im.size[1]))

        img.save(fp=arr, format='GIF', append_images=imgs, save_all=True, duration=2000, loop=0)
        return arr



    def compare(self, json_data):
        """
        Compare local deals with current deals online
        """
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


            logger.debug('Online Data: %s: %s', self.name, game_titles)
            logger.debug('Local Data: %s: %s', self.name, temp_names)

            # Check if db deals has all the newest games
            check = all(item in temp_names for item in game_titles)

            if check is True:
                logger.info('%s - SAME', self.service_name)
                if len(temp_names) > len(json_data):
                    self.data = json_data.copy()
                return 0
        self.data = json_data
        return 1


    async def scheduler(self):
        """
        Default
        """
        # Get update every 30 minutes
        await asyncio.sleep(1800)
        print(f'{self.service_name}={self.data}')
        return self
