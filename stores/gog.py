import asyncio
import json
import os
from datetime import datetime
from urllib.error import URLError, HTTPError
from urllib.request import urlopen, Request

import aiohttp
from bs4 import BeautifulSoup

from utils import makejson
from stores._store import Store


class Main(Store):
    """
    Gog store
    """
    def __init__(self) -> None:
        """
        GoG store
        """
        self.base_url = 'https://www.gog.com'
        self.dlcUrl = 'https://www.gog.com/#giveaway'
        self.giveawayUrl = self.dlcUrl
        self.urls = []
        super().__init__(
            name = 'gog',
            id = '2',
            twitter_notification = True,
            discord_emoji = os.getenv('DISCORD_GOG_EMOJI'),
            service_name = 'GOG',
            url = 'https://www.gog.com/games/ajax/filtered?mediaType=game&page=1&price=discounted'
        )

    #MARK: giveaway
    async def giveaway(self, json_data) -> None:
        '''
        Search gog front page for giveaways
        '''
        tree = await self.request_data(self.base_url, mode='html')
        if tree is None: return
        giveaway = tree.find(".//*[@id='giveaway']")

        if giveaway is not None:
            self.logger.debug('Theres a giveaway')
            link = giveaway.find(".//a[@class='giveaway__overlay-link']")

            game_data = await self.request_data(link.get('href'),'html')
            if game_data is None: return 

            root = game_data.getroot()
            game_id = root.find(".//div[@card-product]").get("card-product")
            offer_until = root.find(".//span[@class='product-actions__time']").text.rsplit(' ', 1)[0]
            offer_until = self.parse_date(offer_until, ["%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M"])              

            games = await self.request_data(f"https://api.gog.com/v2/games/{game_id}")
            if games is None: return

            game_title = games['_embedded']['product']['title']
            game_image = games['_links']['boxArtImage']['href']
            game_url = self.giveawayUrl
            offer_from  = datetime.now()

            json_data = makejson.data(json_data, game_title, 1, game_url, game_image, offer_from, offer_until)
        else:
            return


    def create_urls(self):
        '''
        Creates all the urls for data
        '''
        total_number_of_pages = json.loads(urlopen(self.url).read().decode())['totalPages']
        for i in range(1, total_number_of_pages + 1):
            url = f'https://www.gog.com/games/ajax/filtered?mediaType=game&page={i}&price=discounted'
            self.urls.append(url)
        self.logger.debug('GoG scraped: %s pages', total_number_of_pages)


    # async def request_data(self, session, url):
    #     try:
    #         async with session.get(url) as response:
    #             if response.status != 200:
    #                 return None
    #             else:
    #                 self.urls.remove(url)
    #                 json_response = await response.json()
    #                 return json.loads(json.dumps(json_response))
    #     except Exception as e:
    #         self.logger.error('Gog request data broke: %s', str(e))

    async def process_data(self) -> bool:
        '''
        Parse the retrieved data
        '''
        json_data = []
        data = []

        await self.giveaway(json_data)
        return await self.compare(json_data)

    #MARK: get
    async def get(self) -> bool:
        '''
        Gog get method
        '''
        if await self.process_data():
            return True
        return False


if __name__ == "__main__":
    from utils import environment
    from utils.database import Database
    Database.connect(environment.DB)
    
    a = Main()
    asyncio.run(a.get())
    print(a.data)

