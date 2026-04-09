import asyncio, os
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from stores._store import Store
from utils.makejson import GameDeal, append_game_deal


class Main(Store):
    """
    Steam store
    """
    def __init__(self) -> None:
        self.gamesInfoApi = 'https://store.steampowered.com/api/appdetails?appids'
        self.dlcUrl = 'https://store.steampowered.com/search/?maxprice=free&category1=21&specials=1'
        self.giveawayUrl = 'https://store.steampowered.com/search/?maxprice=free&specials=1&ndl=1'
        super().__init__(
            name='steam',
            id='3',
            discord_emoji=os.getenv('DISCORD_STEAM_EMOJI'),
            twitter_notification=True,
            bsky_notification=True,
            service_name='Steam',
            scheduler_time=7200,
            url=('https://store.steampowered.com/search/results/?'
                 'query=&start=0&count=50&dynamic_data=&sort_by=_ASC&'
                 'maxprice=free&snr=1_7_7_2300_7&specials=1&infinite=1')
        )

    async def _parse_end_date(self, soup: BeautifulSoup) -> datetime | None:
        end_date = soup.select_one("p.game_purchase_discount_quantity")

        if not end_date: return None

        end_date_text = (end_date.text.split('before')[1]).split('@')[0].strip()
        date_formats = ["%b %d", "%d %b", "%d %b, %Y", "%b %d, %Y"]
        parsed_date = self.parse_date(end_date_text, date_formats)

        if parsed_date:
            return parsed_date.replace(year=datetime.now().year)
        else:
            self.logger.warning("Could not parse date: %s", end_date_text)
            return None

    #MARK: process_data 
    async def process_data(self) -> bool:
        """
        Steam process data
        """
        json_data = []
        data = await self.request_data(self.url, mode='json')
        if not data or data.get('total_count', 0) == 0:
            return False
        
        soup = BeautifulSoup(data['results_html'], 'html.parser')
        games = soup.find_all("a", class_="search_result_row ds_collapse_flag")

        # Get new deals
        for game in games:
            
            if not isinstance(game, Tag):
                continue

            title_tag = game.select_one("span.title")
            game_name = title_tag.text.strip() if title_tag else None
            game_url = str(game['href'])
            img = game.select_one(".search_capsule img")
            game_image = str(img.get("src")) if img else None
            app_id = game['data-ds-appid']
            details = await self.request_data(f'{self.gamesInfoApi}={app_id}') or {}
            product_type = details.get(app_id, {}).get('data', {}).get('type')

            if not game_name or (not game_url) or (not game_image):
                continue

            game_details = await self.request_data(game_url, mode='text')
            end_date_object = None
            if game_details:
                soup = BeautifulSoup(game_details, 'html.parser')
                end_date_object = await self._parse_end_date(soup)
                meta = soup.find("meta", property="og:image")
                game_image = str(meta.get("content")) if isinstance(meta, Tag) else game_image

            game_data = GameDeal(
                name=game_name,
                url=game_url,
                active_deal=True,
                image=str(game_image),
                wide_image=str(game_image),
                offer_until=end_date_object,
                product_type=product_type
            )
            json_data = append_game_deal(json_data, game_data)
            
        return await self.compare(json_data)

    #MARK: get
    async def get(self) -> bool:
        '''
        Steam get
        '''
        return await self.process_data()


if __name__ == "__main__":
    from utils import environment
    from utils.database import Database
    Database.connect(environment.DB)

    store = Main()
    asyncio.run(store.get())
    print(store.data)
