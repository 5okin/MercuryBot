import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from utils import environment

logger = environment.logging.getLogger("bot.makejson")


@dataclass(slots=True)
class GameDeal:
    """
    Represents a single free game deal.

    Attributes
    ----------
    name : str
        The game title. Leading/trailing whitespaces are stripped during initialization.
        Non-ASCII characters are removed when converting to a dictionary.
    url : str
        URL to the game's store or offer page. Stripped of leading/trailing whitespaces.
    active_deal : bool
        Whether the deal is currently active. Defaults to True.
    image : str | None
        URL of the main game image.
    wide_image : str | None
        URL of a wide/banner image.
    offer_from : datetime
        Start of the offer. Defaults to current UTC time. Invalid values are replaced.
    offer_until : datetime | None
        End of the offer, or None if no end date. Invalid values are set to None.
    product_type : str | None
        Type of product e.g. 'game', 'dlc'. Defaults to 'game'.
    checkout_slug : str | None
        Identifier used for the checkout URL.

    Methods
    -------
    is_valid() -> bool
        Returns True if the deal contains the minimum required data
        (name, url, and at least one image).

    to_dict() -> dict[str, Any]
        Converts the GameDeal into a dictionary.
        Handles string normalization, ASCII cleanup, and URL formatting.
    """

    name: str
    url: str
    active_deal: bool = True
    image: str | None = None
    wide_image: str | None = None
    offer_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    offer_until: datetime | None = None
    product_type: str = 'game'
    checkout_slug: str | None = None

    def __post_init__(self):
        """
        Post-initialization validation and normalization.
        """
        self.name = self.name.strip() if isinstance(self.name, str) else self.name
        self.url = self.url.strip() if isinstance(self.url, str) else self.url

        if not isinstance(self.offer_from, datetime):
            logger.warning("Invalid offer_from date", extra={'_game': self.name, '_date': self.offer_from})
            self.offer_from = datetime.now(timezone.utc)

        if self.offer_until is not None and not isinstance(self.offer_until, datetime):
            logger.warning("Invalid offer_until date", extra={'_game': self.name, '_date': self.offer_until})
            self.offer_until = None

    def is_valid(self) -> bool:
        """
        Check if the GameDeal has all required fields for appending.

        Returns
        -------
        bool
            True if name, url, and at least one image are present; False otherwise.
        """
        return bool(self.name and self.url and (self.image or self.wide_image))

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the GameDeal to a dictionary.

        Returns
        -------
        dict[str, Any]
            A dictionary representation of the GameDeal.
        """
        return {
            'title': self.name.encode('ascii', 'ignore').decode('ascii'),
            'activeDeal': self.active_deal,
            'url': self.url,
            'startDate': self.offer_from,
            'endDate': self.offer_until,
            'image': self.image.replace(" ", "%20") if self.image else None,
            'wideImage': self.wide_image.replace(" ", "%20") if self.wide_image else None,
            'type': self.product_type,
            'checkout_slug': self.checkout_slug,
        }


def append_game_deal(json_data: list[dict[str, Any]], deal: GameDeal) -> list[dict[str, Any]]:
    """
    Append a game deal entry to an existing list of game data.

    Creates a structured dictionary from a GameDeal and appends it to the provided list.
    Dates are stored as datetime objects so further calculations (like finding the earliest
    end date) can be performed directly.

    Parameters
    ----------
    json_data : list[dict[str, Any]]
        The list to append the new game data to.
    deal : GameDeal
        The game deal to append. See GameDeal for field descriptions.

    Returns
    -------
    list[dict[str, Any]]
        The updated list with the new game entry appended.

    Notes
    -----
    - The deal is only appended if `deal.is_valid()` returns True.
    - Invalid deals are logged and skipped.
    - Conversion to dictionary is handled by `GameDeal.to_dict()`.

    Example
    -------
    >>> json_data = []
    >>> deal = GameDeal(name="Example Game", url="https://example.com", image="https://example.com/image.jpg")
    >>> append_game_deal(json_data, deal)
    [{'title': 'Example Game', 'activeDeal': True, ...}]
    """

    if not deal.is_valid():
        logger.warning(
            "Not all required data passed for game deal", 
            extra={'_game': deal.name, '_image': deal.image, '_wide_image': deal.wide_image, '_url': deal.url}
        )
        return json_data

    json_data.append(deal.to_dict())
    return json_data


def save_to_file(filename: str, json_data: list[dict[str, Any]]) -> None:
    with open(filename, 'w', encoding="utf-8") as outfile:
        json.dump(json_data, outfile, ensure_ascii=False, indent=4, default=str, sort_keys=False)
