import asyncio, json
from stores.epic import Main as epic
from utils import makejson
from datetime import datetime, timezone

class Main(epic):
    """
    epic mobile store
    """
    def __init__(self):
        super().__init__(
            name='epic_mobile',
            id='0',
            service_name='Epic Games Mobile',
            url = 'https://www.epicgames.com/store/us-US/product/',
            scheduler_time = 7200,
            new_deal_delay = 900 # 15 minutes
        )
        
        self.platforms = ['ios', 'android']
        self.api_url = (
            'https://egs-platform-service.store.epicgames.com/api/v2/public/'
            'discover/home?count=10&country=US&locale=en-US'
            '&platform={platform}&start=0&store=EGS'
        )   
        self.cart_url = 'https://store.epicgames.com/purchase?{slugs}#/purchase/payment-methods'
        self.checkout_url = None


    def cleanup_json_response(self, json_text):
        """
        epic mobile cleanup json response
        """
        start = json_text.find("<pre>")
        end = json_text.find("</pre>")
        if start != -1 and end != -1:
            json_text = json_text[start + 5:end]
            return json.loads(json_text)
        else:
            return None


    # MARK: process_data    
    async def process_data(self):
        """
        epic mobile process data
        """
        json_data = []

        for platform in self.platforms:
            url = self.api_url.format(platform=platform)
            response = (await self.request_data_playwright(url, return_response=True))['response']

            data = self.cleanup_json_response(response)
            
            for game in data['data']:
                if game.get('type') == "freeGame":
                    title = game.get('offers')[0].get('content').get('title') + f" for {platform}"
                    image = game.get('offers')[0].get('content').get('media').get('card16x9')['imageSrc']
                    wide_image = game.get('offers')[0].get('content').get('media').get('card3x4')['imageSrc']
                    endDeal = game.get('offers')[0].get('content').get('purchase')[0].get('discount').get('discountEndDate')
                    endDate = datetime.strptime(endDeal, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

                    parts = game.get('offers')[0].get('content').get('purchase')[0].get('purchasePayload')
                    checkout_slug = f'offers=1-{parts.get("sandboxId")}-{parts.get("offerId")}'
                    product_url = game.get('offers')[0].get('content').get('mapping').get('slug')
                    game_url = self.url + product_url
 
                    json_data = makejson.data(json_data, title, 1, game_url, image, None, endDate, wide_image, 'game', checkout_slug)

        return await self.compare(json_data)

    #MARK: get
    async def get(self):
        """
        epic mobile get
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
