import asyncio, os
from datetime import datetime

from stores._store import Store
from utils.makejson import GameDeal, append_game_deal


class Main(Store):
    """
    psplus store
    """
    def __init__(self) -> None:
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
        if data is None : return

        monthly_games_section = data.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " cmp-experiencefragment--wn-latest-monthly-games-content ")]')[0]
        games= monthly_games_section.xpath('.//div[starts-with(@class, "box")]')
        json_data = []

        if not games: return self.logger.critical('PSplus isn\'t returning any deals!')

        for i, game in enumerate(games): 
            try:
                title_el = game.xpath('.//h3[contains(@class, "txt-style-medium-title") and contains(@class, "txt-block-paragraph__title")]')
                title = title_el[0].text_content().strip()
                game_button = game.xpath('.//a[@role="button"]')

                if game_button and 'href' in game_button[0].attrib:
                    game_url = self.base_url + game_button[0].attrib['href']
                else:
                    game_url = 'https://store.playstation.com'

                game_image = (game.xpath('.//source'))[2].attrib.get('srcset') if len(game.xpath('.//source')) >= 2 else (games[i-1].xpath('.//source'))[2].attrib.get('srcset') 
                
                game_data = GameDeal(
                    name=title,
                    url=game_url,
                    active_deal=True,
                    image=game_image,
                    wide_image=game_image
                )
                json_data = append_game_deal(json_data, game_data)
            except Exception as e:
                self.logger.debug("Data acquisition failed %s", e)

        return await self.compare(json_data)


    async def get(self) -> bool:
        """
        psplus get
        """
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
