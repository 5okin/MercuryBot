import json


def data(json_data, game_name, active_deal, game_url, game_image, offer_from=None, offer_until=None) -> dict:
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
    """

    if offer_from and "T" in offer_from:
        offer_from = date_from_str(offer_from)

    if offer_until and "T" in offer_until:
        offer_until = date_from_str(offer_until)

    json_data.append({
        'title': game_name.encode('ascii', 'ignore').decode('ascii'),
        'activeDeal': active_deal,
        'url': game_url,
        'startDate': offer_from,
        'endDate': offer_until,
        'image': game_image,
    })
    return json_data


def date_from_str(date):
    date = date.split("T")
    date[1] = date[1][:-5]
    date[0] = date[0][2:]
    date = date[0] + ' ' + date[1]
    return date


def save_to_file(filename, json_data):
    with open(filename, 'w', encoding="utf-8") as outfile:
        json.dump(json_data, outfile, ensure_ascii=False, indent=4, sort_keys=False)
