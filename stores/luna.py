import asyncio, os
from datetime import datetime
from stores._store import Store
from utils import makejson


class Main(Store):
    """
    Luna store
    """
    def __init__(self):
        self.headers = None
        self.gamesInfoApi = 'https://luna.amazon.com/graphql'
        self.graphql_body = {
            "operationName":"CarouselData",
            "variables":{"collectionType":"FREE_GAMES"},
            "query": """
                query CarouselData($collectionType: ItemCollectionType, $dateOverride: Time) { 
                    items(collectionType: $collectionType, dateOverride: $dateOverride) {items {...CarouselItem}__typename}
                }
                fragment CarouselItem on Item { isFGWP category
                    assets {title externalClaimLink cardMedia { defaultMedia { src1x src2x type}}}
                    offers {startTime endTime __typename }}
                """
        }

        super().__init__(
            name = 'luna',
            id = '5',
            discord_emoji = os.getenv('DISCORD_LUNA_EMOJI'),
            scheduler_time=7200,
            service_name = 'luna',
            url = 'https://luna.amazon.com/claims/home'
        )


    async def get_cookies_playwright(self):
        await self.clear_session()
        result = await self.request_data_playwright(self.url, ["csrf-token"])

        self.headers = {
            "csrf-token": result["headers"].get("csrf-token"),
            "cookie": "; ".join(f"{k}={v}" for k,v in result["cookies"].items()),
            "content-type": "application/json"
        }


    async def process_data(self):
        """
        Luna process data
        """
        json_data = []
        if not self.headers:
            await self.get_cookies_playwright()
        
        try:
            data = await self.request_data(url=self.gamesInfoApi, mode='json', method='POST', headers=self.headers, body=self.graphql_body)
            
            if data is False:
                self.logger.debug("Auth expired for %s, refreshing cookies", self.service_name)
                await self.get_cookies_playwright()
                data = await self.request_data(url=self.gamesInfoApi, mode='json', method='POST', headers=self.headers, body=self.graphql_body)

            for item in data.get("data").get("items").get("items"):
                title = item.get("assets").get("title")
                link = item.get("assets").get("externalClaimLink")
                image = item.get("assets").get("cardMedia").get("defaultMedia").get("src2x")
                startDate = datetime.strptime(item.get("offers")[0].get("startTime"), "%Y-%m-%dT%H:%M:%SZ")
                endDate = datetime.strptime(item.get("offers")[0].get("endTime"), "%Y-%m-%dT%H:%M:%SZ")
                json_data = makejson.data(json_data, title, 1, link, image, startDate, endDate)
        
            return await self.compare(json_data)

        except Exception:
            self.logger.error("Unexpected error retrieving data for %s", self.service_name)

    async def get(self):
        """
        luna get
        """
        if await self.process_data():
            return 1
        return 0


if __name__ == "__main__":
    from utils import environment
    from utils.database import Database
    Database.connect(environment.DB)

    a = Main()
    asyncio.run(a.get())
    print(a.data)
