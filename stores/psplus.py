import asyncio, os
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from stores._store import Store
from utils import makejson
from datetime import datetime


class Main(Store):
    """
    psplus store
    """
    def __init__(self):
        self.base_url = 'https://www.playstation.com'
        super().__init__(
            name = 'psplus',
            id = '4',
            discord_emoji = os.getenv('DISCORD_PSPLUS_EMOJI'),
            service_name = 'PlayStation Plus',
            url = 'https://www.playstation.com/en-gr/ps-plus/whats-new/'
        )


    async def process_data(self):
        """
        get data for psplus
        """
        data = await self.request_data(self.url, mode="text")
        soup = BeautifulSoup(data, 'html.parser')
        games = soup.findAll("section", {"id": "monthly-games"})[1]
        games = games.select("div[class^='box']")
        json_data = []
        soup.decompose()
        del soup

        if not games: return self.logger.critical('PSplus isn\'t returning any deals!')
        try:
            for game in games:
                title = game.find("h3", {"class":"txt-style-medium-title txt-block-paragraph__title"}).text.strip()
                game_button = game.find("a", {"role":"button"})
                if game_button and 'href' in game_button.attrs:
                    game_url = self.base_url + game.find("a", {"role":"button"})['href']
                else:
                    game_url = 'https://store.playstation.com'
                game_image = game.findAll("source")[2]['srcset']
                offer_from  = datetime.now()
                json_data = makejson.data(json_data, title, 1, game_url, game_image, offer_from)
        except Exception as e:
            self.logger.critical("Data acquisition failed %s", e)

        return await self.compare(json_data)


    async def get(self):
        """
        psplus get
        """
        if await self.process_data():
            return 1
        return 0


if __name__ == "__main__":
    from utils.database import Database
    from utils import environment

    a = Main()
    Database([a])
    Database.connect(environment.DB)

    asyncio.run(a.get())
    print(a.data)
