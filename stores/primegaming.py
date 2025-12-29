import asyncio
import os
from datetime import datetime, timedelta
from stores._store import Store
from utils import makejson


class Main(Store):
    '''
    Amazon Prime Gaming store
    '''
    def __init__(self):
        self.page = 'https://gaming.amazon.com/home'
        super().__init__(
            name='primegaming',
            id='5',
            discord_emoji=os.getenv('DISCORD_PRIMEGAMING_EMOJI'),
            twitter_notification=True,
            bsky_notification=True,
            service_name='Amazon Prime Gaming',
            url='https://gaming.amazon.com/'
        )

    #MARK: process_data
    async def process_data(self, tree):
        """
        Main Prime Gaming scraper
        """
        if not tree:
            return False

        json_data = []

        try:
            # Amazon Prime Gaming uses a React app with data in script tags
            # Try to find the game offers from the HTML structure
            # Note: This is a basic implementation - Amazon's site structure may require
            # more sophisticated parsing or API calls

            # For now, return empty data to avoid errors
            # TODO: Implement actual scraping logic based on Amazon's current page structure
            self.logger.info("Prime Gaming data fetch - implementation pending")

        except Exception as e:
            self.logger.error(f"Error processing Prime Gaming data: {e}")
            return False

        return await self.compare(json_data)

    #MARK: get
    async def get(self):
        """
        Runs Prime Gaming data check, fetch and compile

        returns 0 if nothing changed
        returns 1 if new data was found
        """
        tree = await self.request_data(self.page, mode='html')
        if tree is not None:
            if await self.process_data(tree):
                return 1
        return 0


if __name__ == "__main__":
    # run with python -m stores.primegaming
    from utils import environment
    from utils.database import Database
    Database.connect(environment.DB)

    store = Main()
    asyncio.run(store.get())
    print(store.data)
