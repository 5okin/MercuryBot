import asyncio
import json
import os
from datetime import datetime
from urllib.error import URLError, HTTPError
from urllib.request import urlopen, Request

import aiohttp
from bs4 import BeautifulSoup

from utils import environment, makejson
from stores._store import Store


class Main(Store):
    """
    Gog store
    """
    def __init__(self):
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
            service_name = 'gog',
            url = 'https://www.gog.com/games/ajax/filtered?mediaType=game&page=1&price=discounted'
        )

    #MARK: giveaway
    async def giveaway(self, json_data):
        '''
        Search gog front page for giveaways
        '''
        html_content = await self.request_data(self.base_url, 'text')

        giveaway = None
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            game_url = None
            game_id = None
            giveaway = soup.find(id="giveaway")
            soup.decompose()
            del soup

        if giveaway:
            self.logger.debug('Theres a giveaway')
            game_url = self.base_url + giveaway['ng-href'] if giveaway.get('ng-href') is not None else None
            giveaway = giveaway.find("a", {"class": "giveaway__overlay-link"})
            
            if giveaway:
                game_url = giveaway['href'] if giveaway.get('href') is not None else None

            if game_url:
                game_page = BeautifulSoup(urlopen(game_url),'html.parser')
                game_id = game_page.find("div",{"card-product" : True}).attrs["card-product"]
                offer_until = game_page.find("span",class_="product-actions__time").text.rsplit(' ', 1)[0]
                offer_until = self.parse_date(offer_until, ["%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M"])
        
            games = await self.request_data(f"https://api.gog.com/v2/games/{game_id}")
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

    async def client_session(self):
        '''
        Create urls and connect to them using async
        '''
        tasks = []

        async with aiohttp.ClientSession() as session:
            try:
                for url in self.urls:
                    tasks.append(self.request_data(session, url))

                return await asyncio.gather(*tasks)

            except (URLError, HTTPError) as e:
                self.logger.debug('Request to: %s failed: %s', self.service_name, e)
                return False

    async def process_data(self):
        '''
        Parse the retrieved data
        '''

        json_data = []
        data = []

        # Retry the urls that returned Error: 429
        # while self.urls:
        #     response = await self.client_session()
        #     data.extend(response)

        # # Search for games on 100% discount
        # for page in data:
        #     if page is not None:
        #         for game in page['products']:
        #             if game['price']['discountPercentage'] == 100:
        #                 game_name = (game['title']).encode('ascii', 'ignore').decode('ascii')
        #                 if ['type'] != 1:
        #                     game_name += " DLC"
        #                 game_url = 'https://www.gog.com' + game['url']
        #                 offer_from = None
        #                 offer_until = None
        #                 game_image = 'https:' + game['image'] + '.jpg'
        #                 json_data = makejson.data(json_data, game_name, 1, game_url,
        #                                         game_image, offer_from, offer_until)

        await self.giveaway(json_data)
        return await self.compare(json_data)

    #MARK: get
    async def get(self):
        '''
        Gog get method
        '''
        if await self.process_data():
            return 1
        return 0


if __name__ == "__main__":
    a = Main()
    asyncio.run(a.get())
    print(a.data)

