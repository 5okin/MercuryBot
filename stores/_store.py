import asyncio
import io,os, copy
import imageio
import aiohttp
import numpy as np
from lxml import html
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import List, Optional, IO
from PIL import Image
from utils import environment, database
from datetime import datetime, timedelta
import psutil, tracemalloc
import objgraph
import gc

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
                image: Optional[IO] = None,
                image_mobile: Optional[IO] = None,
                image_twitter: Optional[list[Optional[IO[bytes]]]] = None,
                video: Optional[IO] = None,
                image_type: str = 'GIF',
                scheduler_time: int = 1800,
                discord_emoji: int = 0,
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
        self.discord_emoji = discord_emoji
        self.scheduler_time = scheduler_time
        self.default_scheduler_time = scheduler_time
        self.twitter_notification = twitter_notification
        self.bsky_notification = bsky_notification
        self._session: Optional[aiohttp.ClientSession] = None

    # MARK 
    def schedule_retry(self, seconds: int = 300):
        """
        Sets the scheduler time to retry soon
        """
        self.logger.info(" %s scheduler changed: %s -> %s", self.name, self.scheduler_time, seconds)
        self.scheduler_time = seconds

    def reset_scheduler(self):
        """
        Resets the scheduler time to default
        """
        if self.scheduler_time != self.default_scheduler_time:
            self.logger.info(" %s Scheduler reset from  %s -> %s", self.name, self.scheduler_time, self.default_scheduler_time)
            self.scheduler_time = self.default_scheduler_time

    async def request_data(self, url: str | None = None, mode='json'):
        """
        Simple json getter
        """
        if url is None:
            raise ValueError("URL must be provided")

        try:
            await self.create_session()
            assert self._session is not None
            async with self._session.get(url, headers={'User-Agent': 'Mozilla'}) as response:
                response.raise_for_status()
                if mode == 'json':
                    return await response.json()
                elif mode == 'text':
                    return await response.text()
                elif mode == 'html':
                    html_bytes = await response.read()
                    tree = html.parse(io.BytesIO(html_bytes))
                    del html_bytes
                    return tree
                else:
                    raise ValueError(f"Unsupported mode: {mode}")
        except:
            self.logger.warning("Request to %s failed", self.service_name)
            return False


    async def close_session(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


    async def create_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))


    def make_image(self):
        '''
        Creates an image with game images appended side by side

        :return: Nothing, saves the result to store image variable
        '''
        images = []
        new_img_size = 0

        if self.data:
            for game in self.data:
                with urlopen(game['image']) as img_stream:
                    with Image.open(img_stream) as img:
                        images.append(img.copy())

            for image in images:
                new_img_size += image.size[0]
            new_image = Image.new('RGB', (new_img_size, images[0].size[1]), color=(47, 49, 54)) # type: ignore

            size = 0
            for image in images:
                new_image.paste(image, (size, 0))
                size += image.size[0]

            new_image.thumbnail((new_image.size[0] // 2, new_image.size[1] // 2))
            return new_image
        
    
    def parse_date(self, date_str, date_formats):
        """
        Returns a date object according to given formats

        Parameters:
        - date_str: The date string to convert.
        - date_formats: List of formats to try for converting.
        
        Returns:
        - A datetime object.
        """

        if isinstance(date_str, str):
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            self.logger.warning(f"Date format not recognized: {date_str}")
        return None


    async def fetch_image(self, url:str, max_height=300) -> Image.Image | None:
        """Fetch an image asynchronously and return a BytesIO object."""
        try:
            await self.create_session()
            assert self._session is not None
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None
                image_data = await response.read()

            buffer = io.BytesIO(image_data)
            with Image.open(buffer) as img:
                img = img.convert("RGB")
                height_percent = (max_height / float(img.size[1]))
                width_size = int((float(img.size[0]) * float(height_percent)))
                img = img.resize((width_size, max_height), Image.Resampling.LANCZOS)
                return img.copy()
        except Exception as e:
            self.logger.warning(f"Failed to fetch image from {url}: {e}")
            return None


    # MARK: make_gif_image
    async def make_gif_image(self, wide=False, status=1, size=1):
        """Creates a GIF and MP4 asynchronously."""

        if not self.data:
            return None

        images_key = 'wideImage' if wide else 'image'

        image_futures = [
            self.fetch_image(game[images_key], 500) for game in self.data if game['activeDeal'] == status
        ]
        image_bytes_list = await asyncio.gather(*image_futures)

        image_bytes_list = [img_bytes for img_bytes in image_bytes_list if img_bytes]

        if not image_bytes_list:
            return None

        # Run image processing in a separate thread (non-blocking)
        arr, arr_mp4 = await asyncio.to_thread(self.process_images, image_bytes_list, size)

        for b in image_bytes_list:
            try:
                b.close()
            except:
                pass

        del image_bytes_list

        self.video = arr_mp4  # Store the MP4 buffer
        return arr

    def process_images(self, image_list, size):
        arr = io.BytesIO()
        arr_mp4 = io.BytesIO()
        resized_imgs = []

        if not image_list:
            return arr, arr_mp4

        def make_divisible_by_16(width, height):
            return (width + 15) // 16 * 16, (height + 15) // 16 * 16

        try:
            target_width = min(img.width for img in image_list) // size
            target_height = min(img.height for img in image_list) // size
            video_width, video_height = make_divisible_by_16(target_width, target_height)
            resized_imgs = [img.resize((video_width, video_height)) for img in image_list]

            resized_imgs[0].save(fp=arr, format='GIF', append_images=resized_imgs[1:], save_all=True, duration=2000, loop=0)
            arr.seek(0)

            # Create MP4
            writer = imageio.get_writer(arr_mp4, fps=5, format='mp4') # type: ignore
            frame_duration = 3
            for img in resized_imgs:
                for _ in range(frame_duration * 5): # 3 seconds @ 5 fps
                    writer.append_data(np.array(img))
            writer.close()
            arr_mp4.seek(0)
        
        finally:
            # Close all image objects
            for img in resized_imgs:
                try:
                    img.close()
                except Exception:
                    pass
            del resized_imgs
        
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
        working_off = 'local'

        if json_data and not self.data:
            # If self.data is None, then maybe the last run it was removed because site was down / missed deal
            # Check with database data to make sure the "new" deal isnt actually the old/prev deal.
            database_data = database.Database.find(self.name)
            self.data = database_data
            working_off = 'database'
            
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

            if match:
                if len(local_titles) > len(online_titles) or working_off == 'database':
                    self.data = copy.deepcopy(json_data)
                    await self.set_images()
                return 0
            else:
                self.data = copy.deepcopy(json_data)
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
