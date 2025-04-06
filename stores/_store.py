import json
import asyncio
import io
import imageio
import aiohttp
import numpy as np
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import List, Optional, IO
from PIL import Image
from utils import environment
from datetime import datetime, timedelta


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
                video: IO = None,
                image_type: str = 'GIF',
                scheduler_time: int = 1800,
                twitter_notification: bool = False,
                bsky_notification: bool = False
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
        self.video = video
        self.image_type = image_type
        self.scheduler_time = scheduler_time
        self.twitter_notification = twitter_notification
        self.bsky_notification = bsky_notification


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
        
    
    def parse_date(self, date_str, date_formats):
        '''
        Returns a date object according to given formats

        Parameters:
        - date_str: The date string to convert.
        - date_formats: List of formats to try for converting.
        
        Returns:
        - A datetime object.
        """
        '''

        if isinstance(date_str, str):
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            self.logger.warning(f"Date format not recognized: {date_str}")
        return None


    async def fetch_image(self, session, url):
        """Fetch an image asynchronously and return a BytesIO object."""
        async with session.get(url) as response:
            if response.status == 200:
                return io.BytesIO(await response.read())
            return None


    # MARK: make_gif_image
    async def make_gif_image(self, wide=False, status=1, size=1):
        """Creates a GIF and MP4 asynchronously."""

        if not self.data:
            return None

        images_key = 'wideImage' if wide else 'image'

        async with aiohttp.ClientSession() as session:
            image_futures = [
                self.fetch_image(session, game[images_key]) for game in self.data if game['activeDeal'] == status
            ]
            image_bytes_list = await asyncio.gather(*image_futures)

        image_bytes_list = [img_bytes for img_bytes in image_bytes_list if img_bytes]

        if not image_bytes_list:
            return None

        # Run image processing in a separate thread (non-blocking)
        arr, arr_mp4 = await asyncio.to_thread(self.process_images, image_bytes_list, size)

        self.video = arr_mp4  # Store the MP4 buffer
        return arr

    def process_images(self, image_bytes_list, size):
        
        arr = io.BytesIO()
        arr_mp4 = io.BytesIO()

        # Open images with PIL
        img, *imgs = [Image.open(img_bytes).convert("RGB") for img_bytes in image_bytes_list]

        img.thumbnail((img.size[0]//size, img.size[1]//size))
        for im in imgs:
            im.thumbnail((im.size[0]//size, im.size[1]//size))

        img.save(fp=arr, format='GIF', append_images=imgs, save_all=True, duration=2000, loop=0)

        # Create MP4
        writer = imageio.get_writer(arr_mp4, fps=5, format='mp4')
        frame_duration = 3

        for img_bytes in image_bytes_list:
            image = Image.open(img_bytes).convert("RGB")
            image.thumbnail((image.size[0]//size, image.size[1]//size))
            width, height = image.size
            new_width = ((width + 16 - 1) // 16) * 16
            new_height = ((height + 16 - 1) // 16) * 16
            image = image.resize((new_width, new_height))
            image_np = np.array(image)

            # 3 seconds for each frame
            for _ in range(frame_duration * 5):
                writer.append_data(image_np)

        writer.close()
        arr_mp4.seek(0)

        return arr, arr_mp4


    #MARK: get_date
    def get_date(self, data, status='start', returnAsRelative=False):
        """
        Returns the start or end date of a deal based on the status parameter.
        
        Parameters:
        - deal: The dictionary containing deal details.
        - status: A string indicating which date to return ('start' or 'end').
        - returnAsRelative: A boolean indicating the format True for False for data string and True 'Tomorrow !!')
        
        Returns:
        - A formatted date string or "Tomorrow !!" returnAsRelative value.
        """
        if status == 'start':
            status = 'startDate'
        elif status == 'end':
            status = 'endDate'
        else:
            raise ValueError("Invalid date_type. Choose 'start' or 'end'.")
        
        if data.get(status):
            date_value = data[status]
            tomorrow = datetime.now().date() + timedelta(days=1)

            if returnAsRelative and date_value.date() == tomorrow:
                return "Tomorrow !!"
            month = date_value.strftime("%b")
            day = date_value.day
            return f"{month} {day}"
        return None

    async def set_images(self):
        self.image = self.image_twitter = await self.make_gif_image()


    #MARK: compare
    async def compare(self, json_data):
        """
        Compare local deals with current deals online
        """
        # Theres local data and data online
        if json_data and self.data:

            # Online data
            online_titles = [
                game['title'].encode('ascii', 'ignore').decode('ascii')
                for game in json_data if game['activeDeal']
            ]

            # Local data
            local_titles = [
                game['title']
                for game in self.data if game['activeDeal']
            ]

            self.logger.info("Store Compare: %s", self.name, extra={
                '_Online' : online_titles,
                '_Local': local_titles
            })
            # Check if online deals exist in local
            match = all(title in local_titles for title in online_titles)

            if match is True:
                if len(local_titles) > len(online_titles):
                    self.data = json_data.copy()
                    await self.set_images()
                return 0
            else:
                self.data = json_data
                await self.set_images()
                return 1

        # Data is empty but theres data online (1st run)
        elif json_data and not self.data:
            self.data = json_data
            await self.set_images()
            return 1

        # Theres no data online
        elif not json_data:
            self.data = None
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
