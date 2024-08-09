import json
from utils import environment
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

    # Don't leave date objects as None if no data is passed.
    if offer_from is None: offer_from = datetime(1970, 1, 1)
    if offer_until is None: offer_until = datetime(1970, 1, 1)

    if not isinstance(offer_from, datetime) or not isinstance(offer_until, datetime):
        logger.warning("Dates of passed for %s arent datetime objects", game_name)


    json_data.append({
        'title': game_name.encode('ascii', 'ignore').decode('ascii'),
        'activeDeal': active_deal,
        'url': game_url,
        'startDate': offer_from,
        'endDate': offer_until,
        'image': game_image,
        'wideImage': wide_image
    })
    return json_data


def save_to_file(filename, json_data):
    with open(filename, 'w', encoding="utf-8") as outfile:
        json.dump(json_data, outfile, ensure_ascii=False, indent=4, sort_keys=False)
