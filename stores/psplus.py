import json
from PIL import Image
import makejson
from bs4 import BeautifulSoup
import asyncio
import io
from urllib.request import urlopen, Request
from stores._store import Store


class Main(Store):

    def __init__(self):
        self.id = '4'
        self.base_url = 'https://www.playstation.com'
        super().__init__(
            name = 'psplus',
            service_name = 'PlayStation Plus',
            url = 'https://www.playstation.com/en-gr/ps-plus/whats-new/'
        )

    
    def scrape(self):
        data = urlopen(Request(self.url))
        soup = BeautifulSoup(data, 'html.parser')
        games = soup.find("div", {"class": "cmp-experiencefragment cmp-experiencefragment--your-latest-monthly-games"})
        games = games.findAll("div", {"class": "box"})

        json_data = []

        for game in games:
            title = game.find("h3", {"class":"txt-style-medium-title txt-block-paragraph__title"}).text.strip()
            game_url = self.base_url + game.find("a", {"role":"button"})['href']
            game_image = game.findAll("source")[2]['srcset']
           
            json_data = makejson.data(json_data, title, 1, game_url, game_image)
        
        return self.compare(json_data)
    

    async def get(self):
        if self.scrape():
            self.make_gif_image()
            return 1
        return 0


if __name__ == "__main__":
    a = Main()
    asyncio.run(a.get())
    print(a.data)
