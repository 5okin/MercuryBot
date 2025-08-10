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
        data = await self.request_data(self.url, mode="html")
        monthly_games_sections = data.xpath('//section[@id="monthly-games"]')
        games_section = monthly_games_sections[1]
        games = games_section.xpath('.//div[starts-with(@class, "box")]')
        json_data = []

        if not games: return self.logger.critical('PSplus isn\'t returning any deals!')
        try:
            for game in games:
                title_el = game.xpath('.//h3[contains(@class, "txt-style-medium-title") and contains(@class, "txt-block-paragraph__title")]')
                title = title_el[0].text_content().strip()
                game_button = game.xpath('.//a[@role="button"]')

                if game_button and 'href' in game_button[0].attrib:
                    game_url = self.base_url + game_button[0].attrib['href']
                else:
                    game_url = 'https://store.playstation.com'

                game_image = (game.xpath('.//source'))[2].attrib.get('srcset')
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

    asyncio.run(a.get())
    print(a.data)
