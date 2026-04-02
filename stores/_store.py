import asyncio
import io
import imageio
import aiohttp
import numpy as np
from lxml import html
from urllib.request import urlopen
from playwright.async_api import async_playwright
from typing import List, IO, Self, overload, Literal
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
                data: List | None = None,
                image: IO | None = None,
                image_cdn: str | None = None,
                image_twitter: list[IO[bytes] | None] | None = None,
                video: IO | None = None,
                image_type: str = 'GIF',
                scheduler_time: int = 1800,
                scheduler_retry_time: int = 300,
                new_deal_delay: int = 300,
                discord_emoji: str | None = None,
                twitter_notification: bool = False,
                bsky_notification: bool = False,
                require_all_deals_new: bool = False
                ) -> None:
        self.name = name
        self.logger = environment.logging.getLogger(f'store.{self.name}')
        self.id = id
        self.service_name = service_name
        self.url = url
        self.data = data
        self.image = image
        self.image_cdn = image_cdn
        self.image_twitter = image_twitter
        self.video = video
        self.image_type = image_type
        self.discord_emoji = discord_emoji
        self.scheduler_time = scheduler_time
        self.new_deal_delay = new_deal_delay
        self.scheduler_retry_time = scheduler_retry_time
        self.default_scheduler_time = scheduler_time
        self.twitter_notification = twitter_notification
        self.bsky_notification = bsky_notification
        self.require_all_deals_new = require_all_deals_new
        self._session: aiohttp.ClientSession | None = None

    # MARK Scheduler timer change
    def schedule_retry(self) -> None:
        """
        Sets the scheduler time to retry soon
        """
        self.logger.info("Scheduler change: %s from %s -> %s sec", self.name, self.scheduler_time, self.scheduler_retry_time)
        self.scheduler_time = self.scheduler_retry_time

    def reset_scheduler(self) -> None:
        """
        Resets the scheduler time to default
        """
        if self.scheduler_time != self.default_scheduler_time:
            self.logger.info("Scheduler reset: %s from  %s -> %s sec", self.name, self.scheduler_time, self.default_scheduler_time)
            self.scheduler_time = self.default_scheduler_time

    #MARK: request_data
    @overload
    async def request_data(
        self,
        url: str
    ) -> dict | None: ...

    @overload
    async def request_data(self,
        url: str,
        mode: Literal['json'],
        method: str = 'GET',
        headers: dict | None = None,
        cookies: dict | None = None,
        body: dict | None = None
    ) -> dict | None: ...


    @overload
    async def request_data(self,
        url: str,
        mode: Literal['text'],
        method: str = 'GET',
        headers: dict | None = None,
        cookies: dict | None = None,
        body: dict | None = None
    ) -> str | None: ...


    @overload
    async def request_data(self,
        url: str,
        mode: Literal['html'],
        method: str = 'GET',
        headers: dict | None = None,
        cookies: dict | None = None,
        body: dict | None = None
    ) -> html.HtmlElement | None: ...

    async def request_data(
        self,
        url: str,
        mode: Literal['json', 'text', 'html'] = 'json',
        method: str = 'GET',
        headers: dict | None = None,
        cookies: dict | None = None,
        body: dict | None = None
    ) -> dict | str | html.HtmlElement | None:
        """
        Make an HTTP request and return the response in the requested format.

        Parameters
        ----------
        url : str
            The URL to send the request to.
        mode : Literal['json', 'text', 'html'], default 'json'
            Determines the expected response type:
            - 'json' → returns a dict (parsed JSON)
            - 'text' → returns the raw text
            - 'html' → returns an lxml HtmlElement parsed from the response
        method : str, default 'GET'
            HTTP method to use.
        headers : dict, optional
            Additional HTTP headers to include in the request.
        cookies : dict, optional
            Cookies to include in the request.
        body : dict, optional
            JSON body to send with the request (for POST/PUT).

        Returns
        -------
        dict | str | html.HtmlElement | None
            - `dict` if mode='json'
            - `str` if mode='text'
            - `HtmlElement` if mode='html'
            - `None` if the request fails or an exception occurs
        """

        default_headers = {}
        if headers:
            default_headers.update(headers)

        try:
            await self.create_session()
            assert self._session is not None
            async with self._session.request(method, url, headers=default_headers, json=body, cookies=cookies) as response:
                response.raise_for_status()
                if mode == 'json':
                    return await response.json(content_type=None)
                elif mode == 'text':
                    return await response.text()
                elif mode == 'html':
                    return html.fromstring(await response.read())
                else:
                    raise ValueError(f"Unsupported mode: {mode}")
        except:
            self.logger.warning("Request to %s failed", self.service_name)
            return None


    async def close_session(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def clear_session(self) -> None:
        if self._session and not self._session.closed:
            self._session.cookie_jar.clear()


    async def create_session(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))


    #MARK: playwrite
    async def request_data_playwright(self, url, headers_to_get: list[str] | None = None, return_response: bool=False):
        """
        Launch a temporary Playwright Chromium browser to retrieve request headers
        and cookies from a target page.
        
        Args:
            url (str): The URL to navigate to.
            headers_to_get (List[str]): A list of header names that must be present
                in a request before headers are captured.

        Returns:
            dict: A dictionary with the following structure:
                {
                    "headers": dict,  # Captured request headers (may be empty)
                    "cookies": dict   # Cookies as {name: value}
                }
        """
        result = {"headers": {}, "cookies": {}, "response": None}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True
            )
            page = await context.new_page()
    
            def capture(request) -> None:
                if all (h in request.headers for h in (headers_to_get or [])):
                    result["headers"] = request.headers
                    context.remove_listener("request", capture)

            context.on("request", capture)
            
            await page.goto(url)
            await page.wait_for_load_state('domcontentloaded') 

            cookies = []
            for c in await context.cookies():
                name = c.get('name')
                value = c.get('value')
                if name and value:
                    cookies.append((name, value))

            result["cookies"] = dict(cookies)

            if return_response:
                response = await page.content()
                result["response"] = response

            await browser.close()
        return result


    def make_image(self)-> Image.Image | None:
        '''
        Creates an image with game images appended side by side
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
        
    
    def parse_date(self, date_str, date_formats) -> datetime | None:
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


    async def fetch_image(self, url:str, max_height: int = 300) -> Image.Image | None:
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
    async def make_gif_image(self, wide: bool = False, status: bool | None = None, size: int = 1) -> IO[bytes] | None:
        """Creates a GIF and MP4 asynchronously."""
        if status is None : status = True

        if not self.data:
            return None

        images_key = 'wideImage' if wide else 'image'

        image_futures = [
            self.fetch_image(game[images_key], 500) for game in self.data if game['activeDeal'] is status
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

    def process_images(self, image_list, size) -> tuple[IO[bytes], IO[bytes]]:
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
    def get_date(self, data, status='start', returnAsRelative=False) -> str | None:
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

    async def set_images(self) -> None:
        self.image = self.image_twitter = await self.make_gif_image()


    def _normilize_title(self, data) -> set:
        return set(
            game['title'].encode('ascii', 'ignore').decode('ascii')
            for game in data if game.get('activeDeal')
        )

    # MARK: verify_new_notification
    def verify_new_notification(self, potential_deal) -> bool:
        """
        Verify whether a notification should be sent for the current deals.

        This method checks the incoming deals (`potential_deal`) against the deals
        stored in the database. It uses the db deals as the last deals that a 
        notification was sent for. If the new deals are different from the db deals, 
        it means there's a new deal and a notification should be sent.

        Parameters
        ----------
        potential_deal : list[dict]
            The latest deals retrieved from the store API or scraper.

        Returns
        -------
        bool
            True if a new deal exists that has not been recorded in the database
            (a notification should be sent), otherwise False.
        """
        database_data = database.Database.find(self.name)

        db_data = self._normilize_title(database_data)
        potential_deal = self._normilize_title(potential_deal)

        match = potential_deal.issubset(db_data)

        return False if match else True

    #MARK: compare
    async def compare(self, json_data) -> bool:
        """
        Compare local deals with current deals online
        """
        has_active = json_data and any(game.get('activeDeal') for game in json_data)

        # Theres local data and data online
        if has_active and self.data:

            online_titles = self._normilize_title(json_data)
            local_titles = self._normilize_title(self.data)

            should_update = False
            if self.require_all_deals_new:
                # Only update if all online deals are new (no overlap with local)
                should_update = online_titles and online_titles.isdisjoint(local_titles)
            else:
                # Update if any difference
                should_update = local_titles != online_titles

            if should_update:

                self.logger.info("Store Compare: %s", self.name, extra={
                    '_Online'   : online_titles,
                    '_Local'    : local_titles
                })
                state_backup = (self.data, self.checkout_url, self.image, self.image_cdn, self.image_twitter)
                
                try:
                    self.data = json_data
                    await self.create_checkout_url()
                    await self.set_images()
                except:
                    self.data, self.checkout_url, self.image, self.image_cdn, self.image_twitter = state_backup
                    raise

                return self.verify_new_notification(json_data)
            return False

        # Theres no data online
        elif not json_data:
            self.data = None
            self.image = self.image_twitter = None
            return False
        elif has_active and not self.data:
            self.data = json_data
            await self.create_checkout_url()
            await self.set_images()
            return False
        return False
    
    # MARK: create_checkout_url
    async def create_checkout_url(self) -> None:

        template = getattr(self, 'checkout_url_template', None)

        if not template or not self.data:
            self.checkout_url = None
            return

        offer_links = [
            game["checkout_slug"]
            for game in self.data if game.get("activeDeal")
        ]

        self.checkout_url = template.format(
            slugs = "&".join(offer_links)
        )

    #MARK: scheduler
    async def scheduler(self) -> Self:
        """
        Default scheduler
        """
        # Get update every 30 minutes
        await asyncio.sleep(self.scheduler_time)
        #print(f'{self.service_name}={self.data}')
        return self

    #Mark: get
    async def get(self) -> bool:
        """
        Get method to be implemented by each store
        """
        raise NotImplementedError("The get method must be implemented by the store subclass.")
