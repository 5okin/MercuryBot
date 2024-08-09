import json
import asyncio
import io
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import List, Optional, IO
from PIL import Image
from utils import environment


class Store:
    """
    Init store
    """
    def __init__(self,
                name: str,
                id: str,
                service_name: str,
                url: str,
                data: Optional[List] = None,
                image: IO = None,
                image_mobile: IO = None,
                image_twitter: IO [bytes] = [None, None],
                image_type: str = 'GIF',
                scheduler_time: int = 1800,
                twitter_notification: bool = False
                ):
        self.name = name
        self.logger = environment.logging.getLogger(f'store.{self.name}')
        self.id = id
        self.service_name = service_name
        self.url = url
        self.data = data
        self.image = image
        self.image_mobile = image_mobile
        self.image_twitter = image_twitter
        self.image_type = image_type
        self.scheduler_time = scheduler_time
        self.twitter_notification = twitter_notification


    def request_data(self, url=None):
        """
        Simple json getter
        """
        try:
            data = urlopen(Request(url, headers={'User-Agent': 'Mozilla'}))
            data = json.loads(data.read().decode())
            return data
        except (URLError, HTTPError) as e:
            self.logger.debug("Request to %s failed %s", self.service_name, e)
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


    #MARK: make_gif_image
    def make_gif_image(self, wide=False, status=1, size=1):
        '''
        Creates a gif off of a list of urls containing images

        -----------
        wide
            If not set its defaults to class image
        -----------
        '''

        if not self.data:
            return 0
        
        if(wide):
            images = 'wideImage'
        else:
            images = 'image'

        arr = io.BytesIO()
        img, *imgs = [
            Image.open(urlopen(game[images]))
            for game in self.data
            if game['activeDeal'] == status
        ]

        img.thumbnail((img.size[0]//size, img.size[1]//size))

        for im in imgs:
            im.thumbnail((im.size[0]//size, im.size[1]//size))

        img.save(fp=arr, format='GIF', append_images=imgs, save_all=True, duration=2000, loop=0)
        return arr

    #MARK: get_date
    def get_date(self, data, status='start'):
        """
        Returns the start or end date of a deal based on the status parameter.
        
        Parameters:
        - deal: The dictionary containing deal details.
        - status: A string indicating which date to return ('start' or 'end').
        
        Returns:
        - A formatted date string of the specified type.
        """
        if status == 'start':
            status = 'startDate'
        elif status == 'end':
            status = 'endDate'
        else:
            raise ValueError("Invalid date_type. Choose 'start' or 'end'.")
        
        month = data[status].strftime("%b")
        day = data[status].day
        return str(month) + ' ' + str(day)
    

    def make_images_test(self):
        self.image = self.image_twitter = self.make_gif_image()


    #MARK: compare
    def compare(self, json_data):
        """
        Compare local deals with current deals online
        """
        # Theres local data and data online
        if json_data and self.data:
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

            self.logger.info('Online: %s', game_titles)
            self.logger.info('Local: %s', temp_names)

            # Check if db deals has all the newest games
            check = all(item in temp_names for item in game_titles)

            if check is True:
                self.logger.info('-- SAME --')
                if len(temp_names) > len(json_data):
                    self.data = json_data.copy()
                    self.make_images_test()
                return 0
            else:
                self.data = json_data
                self.make_images_test()
                return 1

        # Data is empty but theres data online (1st run)
        elif json_data and not self.data:
            self.data = json_data
            self.make_images_test()
            return 0

        # Theres no data online
        elif not json_data:
            self.data = json_data
            self.image = self.image_mobile = self.image_twitter = None
            return 0

    #MARK: scheduler
    async def scheduler(self):
        """
        Default scheduler
        """
        # Get update every 30 minutes
        await asyncio.sleep(self.scheduler_time)
        #print(f'{self.service_name}={self.data}')
        return self
