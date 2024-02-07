from urllib.request import urlopen
from PIL import Image
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
from stores._store import Store
import environment
import json
import makejson
import asyncio
import aiohttp
import re
import datetime
import io


logger = environment.logging.getLogger("bot")


class Main(Store):

    def __init__(self):
        self.id = '2'
        self.base_url = 'https://www.gog.com'
        self.urls = []
        super().__init__(
            name = 'gog',
            service_name = 'GoG',
            url = 'https://www.gog.com/games/ajax/filtered?mediaType=game&page=1&price=discounted'
        )

    def create_urls(self):
        print("creating urls for gog")
        total_number_of_pages = json.loads(urlopen(self.url).read().decode())['totalPages']
        for i in range(1, total_number_of_pages + 1):
            url = f'https://www.gog.com/games/ajax/filtered?mediaType=game&page={i}&price=discounted'
            self.urls.append(url)
        print("GoG scraped", total_number_of_pages, "pages")

    async def request_data(self, session, url):
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                else:
                    self.urls.remove(url)
                    json_response = await response.json()
                    return json.loads(json.dumps(json_response))
        except Exception as e:
            print(str(e))

    async def client_session(self):
        tasks = []

        async with aiohttp.ClientSession() as session:
            try:
                for url in self.urls:
                    tasks.append(self.request_data(session, url))

                return await asyncio.gather(*tasks)

            except (URLError, HTTPError) as e:
                print(f"Request to {self.service_name} failed:\n{e}")
                return False

    async def process_data(self):

        json_data = []
        data = []

        # Retry the urls that returned Error: 429 
        while self.urls:
            response = await self.client_session()
            data.extend(response)

        # Search for games on 100% discount
        for page in data:
            if page is not None:
                for game in page['products']:
                    if game['price']['discountPercentage'] == 100:
                        game_name = (game['title']).encode('ascii', 'ignore').decode('ascii')
                        if ['type'] != 1:
                            game_name += " DLC"
                        game_url = 'https://www.gog.com' + game['url']
                        offer_from = None
                        offer_until = None
                        game_image = 'https:' + game['image'] + '.jpg'
                        json_data = makejson.data(json_data, game_name, 1, game_url,
                                                  game_image, offer_from, offer_until)

        # Search front page for Giveaways
        html_content = urlopen(self.base_url)
        soup = BeautifulSoup(html_content, 'html.parser')

        try:
            games = soup.find("a", {"class": re.compile("giveaway")})
            offer_until = int(
                games.find("gog-countdown-timer", {"class": "giveaway-banner__countdown-timer"}).attrs["end-date"])
            game_url = self.base_url + games['ng-href']

            # Go to store page and get game ID
            game_id = BeautifulSoup(urlopen(game_url), 'html.parser').find("div", {"class": "layout"}).attrs[
                "card-product"]
            print(game_id)

            # Go to the giveaway page on gog instead of the store page
            # might be a problem if there is a giveaway and free games
            game_url = 'https://www.gog.com/#giveaway'
            '''
            identifier = (game_url.split('/game/'))[1]
            api_url = quote(identifier)
            api_search = urlopen(
                f"https://catalog.gog.com/v1/catalog?limit=48&query=like:{api_url}&order=desc:score&productType=in:game,pack&page=1")
            games = json.loads(api_search.read().decode())
            game_image = games['products'][0]['coverHorizontal']
            game_title = games['products'][0]['title']
            '''

            api_search = urlopen(f"https://api.gog.com/v2/games/{game_id}")
            games = json.loads(api_search.read().decode())
            game_title = games['_embedded']['product']['title']
            game_image = games['_links']['boxArtImage']['href']

            offer_until = datetime.datetime.fromtimestamp(offer_until / 1000).strftime('%b %d')
            offer_from = None

            json_data = makejson.data(json_data, game_title, 1, game_url, game_image, offer_from, offer_until)
            # self.data = json_data

        except Exception as e:
            print(f"No giveaway found. {e}")

        return self.compare(json_data)
    
    def old_request_data(self):
        json_data = []

        try:
            total_number_of_pages = json.loads(urlopen(self.url).read().decode())['totalPages']
            i = 1
            while i <= total_number_of_pages:
                page = urlopen(f'https://www.gog.com/games/ajax/filtered?mediaType=game&page={i}&price=discounted')
                games = json.loads(page.read().decode())
                j = 0
                while True:
                    try:
                        if games['products'][j]['price']['discountPercentage'] == 100:
                            game_name = (games['products'][j]['title']).encode('ascii', 'ignore').decode('ascii')
                            game_url = 'https://www.gog.com' + games['products'][j]['url']
                            offer_from = None
                            offer_until = None
                            game_image = 'https:' + games['products'][j]['image'] + '.jpg'
                            json_data = makejson.data(json_data, game_name, 1, game_url, offer_from, offer_until,
                                                      game_image)
                    except Exception as e:
                        print(e)
                        break
                    j += 1
                i += 1
                logger.debug(f'Scanned {i-1} GOG pages')
            self.data = json_data
            return json_data

        except (URLError, HTTPError) as e:
            print(f"Request to {self.service_name} failed \n {e}")
            return False

    async def get(self):
        # self.old_request_data()
        self.create_urls()
        if await self.process_data():
            print('waiting to get gog image')
            await asyncio.sleep(50)
            #self.make_image()
            self.make_gif_image()
            return 1
        return 0
        # self.make_gif_image()


# https://stackoverflow.com/questions/52245922/is-it-more-efficient-to-use-create-task-or-gather
# Do it so that epic and gog are downloaded side by side
# Do it so that gog pages are downloaded side by side.

if __name__ == "__main__":
    a = Main()
    asyncio.run(a.get())
    print(a.data)

# a = Main()
# a.get()
# print(a.data)
# https://stackoverflow.com/questions/54088263/runtimewarning-enable-tracemalloc-to-get-the-object-allocation-traceback-with-a
# 40 -> 13, 15 ... 3 times quicker with async
