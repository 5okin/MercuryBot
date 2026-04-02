import json
from typing import Any
from utils import environment
from datetime import datetime, timezone

logger = environment.logging.getLogger("bot.makejson")

def append_game_deal(
        json_data: list[dict[str, Any]],
        game_name: str,
        active_deal: bool,
        game_url: str,
        game_image: str | None = None,
        offer_from: datetime | None = None,
        offer_until: datetime | None = None,
        wide_image: str | None = None,
        productType: str | None = 'game',
        checkout_slug: str | None = None
    ) -> list[dict[str, Any]]:

    """
    Append a game deal entry to an existing list of game data.

    This function creates a structured dictionary representing a game deal and appends it to the provided list. 
    Dates are stored as `datetime` objects so that further calculations (like finding the earliest end date)
    can be performed directly. Image URLs are percent-encoded for safety.

    Parameters
    ----------
    json_data : list[dict[str, Any]]
        The list to append the new game data to.
    game_name : str
        The name of the game. Non-ASCII characters are stripped.
    active_deal : bool
        Indicates whether the deal is currently active.
    game_url : str
        The URL to the game's store or offer page.
    game_image : str
        URL of the main image for the game.
    offer_from : datetime | None, optional
        The start date of the offer. If None, defaults to the current UTC datetime.
    offer_until : datetime | None, optional
        The end date of the offer. If None, no end date is set.
    wide_image : str | None, optional
        URL of a wide/banner image for the game.
    productType : str | None, optional
        The type of product (default is 'game').
    checkout_slug : str | None, optional
        Identifier used for checkout url.

    Returns
    -------
    list[dict[str, Any]]
        The updated list with the new game entry appended.

    Notes
    -----
    - Non-ASCII characters in `game_name` are removed.
    - Image URLs are percent-encoded using `urllib.parse.quote`.
    - For JSON serialization, use `json.dump(..., default=str)` to handle `datetime` objects.
    - If `game_name`, `game_image`, or `game_url` are missing or empty, the function logs a warning and does **not** append an entry to `json_data`.

    Example
    -------
    >>> json_data = []
    >>> data(
    ...     json_data,
    ...     game_name="Example Game",
    ...     active_deal=True,
    ...     game_url="https://example.com",
    ...     game_image="https://example.com/image.jpg"
    ... )
    [{'title': 'Example Game', 'activeDeal': True, ...}]
    """

    # Enforce presence of required fields
    if not game_name or not(game_image or wide_image) or (not game_url):
        logger.warning(f"Not all required data passed for '{game_name = }', '{game_image = }', '{wide_image = }', '{game_url = }'")
        return json_data

    # Ensure offer_from and offer_until are datetime objects
    if offer_from is None or not isinstance(offer_from, datetime):
        offer_from = datetime.now(timezone.utc)
    if offer_until is not None and not isinstance(offer_until, datetime):
        offer_until = None
        logger.warning("Dates of passed for %s arent datetime objects", game_name)


    json_data.append({
        'title': game_name.encode('ascii', 'ignore').decode('ascii'),
        'activeDeal': active_deal,
        'url': game_url,
        'startDate': offer_from,
        'endDate': offer_until,
        'image': game_image.replace(" ", "%20") if game_image else None,
        'wideImage': wide_image.replace(" ", "%20") if wide_image else None,
        'type': productType,
        'checkout_slug': checkout_slug
    })
    return json_data


def save_to_file(filename: str, json_data: list[dict[str, Any]]) -> None:
    with open(filename, 'w', encoding="utf-8") as outfile:
        json.dump(json_data, outfile, ensure_ascii=False, indent=4, default=str, sort_keys=False)
