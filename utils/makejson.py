import json
from utils import environment
from urllib.parse import quote
from datetime import datetime

logger = environment.logging.getLogger("bot.makejson")

def data(json_data, game_name, active_deal, game_url, game_image, offer_from=None, offer_until=None, wide_image=None) -> dict:
    """ Creates a json file from the given data
        
        Parameters
        -----------
        json_data
                The variable you want to append the data too

        Returns
        -----------
        A Json file.
        :param json_data:
        :param game_name:
        :param active_deal:
        :param game_url:
        :param offer_from:
        :param offer_until:
        :param game_image:
        :param wide_image:
    """

    # Set offer_from to today if its not provided
    if offer_from is None or not isinstance(offer_from, datetime) : offer_from = datetime.now()
    if offer_until is not None or not isinstance(offer_until, datetime):
        logger.warning("Dates of passed for %s arent datetime objects", game_name)


    json_data.append({
        'title': game_name.encode('ascii', 'ignore').decode('ascii'),
        'activeDeal': active_deal,
        'url': game_url,
        'startDate': offer_from,
        'endDate': offer_until,
        'image': game_image.replace(" ", "%20"),
        'wideImage': wide_image.replace(" ", "%20") if wide_image else None
    })
    return json_data


def save_to_file(filename, json_data):
    with open(filename, 'w', encoding="utf-8") as outfile:
        json.dump(json_data, outfile, ensure_ascii=False, indent=4, sort_keys=False)
