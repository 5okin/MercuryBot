import asyncio
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from stores._store import Store
from utils import makejson


class Main(Store):
    """
    psplus store
    """
    def __init__(self):
        self.id = '4'
        self.base_url = 'https://www.playstation.com'
        super().__init__(
            name = 'psplus',
            service_name = 'PlayStation Plus',
            url = 'https://www.playstation.com/en-gr/ps-plus/whats-new/'
        )


    def request_data(self, url=None):
        """
        get data for psplus
        """
        data = urlopen(Request(self.url))
        soup = BeautifulSoup(data, 'html.parser')
        games = soup.find("div", {"class": "content-grid layout__3--a"})
        games = games.findAll("div", {"class": "box"})

        json_data = []

        for game in games:
            title = game.find("h3", {"class":"txt-style-medium-title txt-block-paragraph__title"}).text.strip()
            game_button = game.find("a", {"role":"button"})
            if game_button and 'href' in game_button.attrs:
                game_url = self.base_url + game.find("a", {"role":"button"})['href']
            else:
                game_url = 'https://store.playstation.com'
            game_image = game.findAll("source")[2]['srcset']
            json_data = makejson.data(json_data, title, 1, game_url, game_image)

        return self.compare(json_data)


    async def get(self):
        """
        psplus get
        """
        if self.request_data(self.url):
            self.image = self.make_gif_image()
            return 1
        return 0


if __name__ == "__main__":
    a = Main()
    asyncio.run(a.get())
    print(a.data)
