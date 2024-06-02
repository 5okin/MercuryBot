import asyncio
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from stores._store import Store
from utils import makejson


class Main(Store):
    """
    Steam store
    """
    def __init__(self):
        self.id = '3'
        super().__init__(
            name = 'steam',
            service_name = 'Steam',
            url = ('https://store.steampowered.com/search/results/?'
                    'query=&start=0&count=50&dynamic_data=&sort_by=_ASC&'
                    'maxprice=free&snr=1_7_7_2300_7&specials=1&infinite=1')
        )

    def process_data(self, games_num):
        """
        Steam process data
        """
        number = 0
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
                print("--- Get new game deals ---")
                for game in games:
                    game_name = game.find("span", {"class": "title"}).text
                    game_url = game['href']
                    # game_image = game.find("img")['src']
                    # Get bigger images
                    data = urlopen(Request(game_url))
                    soup = BeautifulSoup(data, 'html.parser')
                    # game_image = soup.find("link", rel="image_src")['href']
                    game_image = soup.find("meta", property="og:image")
                    game_image = game_image['content'].rsplit('/', 1)[0] + '/header.jpg'
                    number += 1
                    json_data = makejson.data(json_data, game_name, 1, game_url, game_image)

                return self.compare(json_data)
        else:
        # If theres no new deals update
            self.data.clear()
            self.image = None
            return 0

    async def get(self):
        '''
        Steam get
        '''
        if self.process_data(self.request_data(self.url)['total_count']):
            self.image = self.make_gif_image()
            return 1
        return 0

if __name__ == "__main__":
    a = Main()
    asyncio.run(a.get())
    print(a.data)
