import asyncio
from urllib.request import urlopen, Request, HTTPCookieProcessor, build_opener
from bs4 import BeautifulSoup
from stores._store import Store
from utils import makejson
import http.cookiejar
from datetime import datetime


class Main(Store):
    """
    Steam store
    """
    def __init__(self):
        self.gamesInfoApi = 'https://store.steampowered.com/api/appdetails?appids'
        self.dlcUrl = 'https://store.steampowered.com/search/?maxprice=free&category1=21&specials=1'
        super().__init__(
            name = 'steam',
            id = '3',
            twitter_notification=True,
            service_name = 'Steam',
            scheduler_time=7200,
            url = ('https://store.steampowered.com/search/results/?'
                    'query=&start=0&count=50&dynamic_data=&sort_by=_ASC&'
                    'maxprice=free&snr=1_7_7_2300_7&specials=1&infinite=1')
        )


    #MARK: process_data 
    async def process_data(self, games_num):
        """
        Steam process data
        """
        i = 0
        json_data = []
        # print(games_num)
        if games_num:
            for i in range(0, games_num, 15):

                url = ("https://store.steampowered.com/search/results/?query=&start=" + str(i
                        ) + "&count=50&dynamic_data=&sort_by=_ASC&maxprice=free&snr=1_7_7_2300_7"
                        "&specials=1&infinite=1")

                data = self.request_data(url)
                soup = BeautifulSoup(data['results_html'], 'html.parser')
                games = soup.findAll("a", {"class": "search_result_row ds_collapse_flag"})

                # Get new deals
                for game in games:
                    end_date_object = None
                    game_name = game.find("span", {"class": "title"}).text
                    game_url = game['href']
                    appId = game['data-ds-appid']
                    productType = self.request_data(f'{self.gamesInfoApi}={appId}')[appId]['data']['type']
                    data = urlopen(Request(game_url))
                    soup = BeautifulSoup(data, 'html.parser')
                    end_date = soup.find("p", {"class":"game_purchase_discount_quantity"})

                    try:
                        end_date = (end_date.text.split('before')[1]).split('@')[0].strip()
                        date_formats = ["%b %d", "%d %b", "%d %b, %Y", "%b %d, %Y"]
                        end_date_object = self.parse_date(end_date, date_formats).replace(year=datetime.now().year)
                    except:
                        self.logger.warning("Date could not be handled")
                    offer_from  = datetime.now()
                    game_image = soup.find("meta", property="og:image").get("content")
                    json_data = makejson.data(json_data, game_name, 1, game_url, game_image, offer_from, end_date_object, productType=productType)

        return await self.compare(json_data)

    #MARK: get
    async def get(self):
        '''
        Steam get
        '''
        if await self.process_data(self.request_data(self.url)['total_count']):
            # self.image = self.image_twitter = self.make_gif_image()
            return 1
        return 0

if __name__ == "__main__":
    store = Main()
    asyncio.run(store.get())
    print(store.data)
