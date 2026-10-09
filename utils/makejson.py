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
    title : str
        The game title. Leading/trailing whitespaces are stripped during initialization.
        Non-ASCII characters are removed during initialization.
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
        Type of product e.g. 'game', 'dlc', 'low_quality'. Defaults to 'game'.
    checkout_slug : str | None
        Identifier used for the checkout URL.
    new_deal : bool
        Whether this deal was newly found during the latest comparison.

    Methods
    -------
    is_valid() -> bool
        Returns True if the deal contains the minimum required data
        (title, url, and at least one image).

    to_document() -> dict[str, Any]
        Converts the GameDeal to the existing MongoDB document schema.
    """

    title: str
    url: str
    active_deal: bool = True
    image: str | None = None
    wide_image: str | None = None
    offer_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    offer_until: datetime | None = None
    product_type: str = 'game'
    checkout_slug: str | None = None
    new_deal: bool = False

    def __post_init__(self):
        """
        Post-initialization validation and normalization.
        """
        self.title = self.title.strip() if isinstance(self.title, str) else self.title
        self.title = self.title.encode('ascii', 'ignore').decode('ascii') if isinstance(self.title, str) else self.title
        self.url = self.url.strip() if isinstance(self.url, str) else self.url
        self.image = self.image.replace(" ", "%20") if self.image else None
        self.wide_image = self.wide_image.replace(" ", "%20") if self.wide_image else None

        if not isinstance(self.offer_from, datetime):
            logger.warning("Invalid offer_from date", extra={'_game': self.title, '_date': self.offer_from})
            self.offer_from = datetime.now(timezone.utc)

        if self.offer_until is not None and not isinstance(self.offer_until, datetime):
            logger.warning("Invalid offer_until date", extra={'_game': self.title, '_date': self.offer_until})
            self.offer_until = None

    def is_valid(self) -> bool:
        """
        Check if the GameDeal has all required fields for appending.

        Returns
        -------
        bool
            True if name, url, and at least one image are present; False otherwise.
        """
        return bool(self.title and self.url and (self.image or self.wide_image))

    def to_document(self) -> dict[str, Any]:
        """
        Convert the deal to the MongoDB document schema used by existing data.

        Returns
        -------
        dict[str, Any]
            A MongoDB-compatible representation of the GameDeal.
        """
        return {
            'title': self.title,
            'activeDeal': self.active_deal,
            'url': self.url,
            'startDate': self.offer_from,
            'endDate': self.offer_until,
            'image': self.image,
            'wideImage': self.wide_image,
            'type': self.product_type,
            'checkout_slug': self.checkout_slug,
            'newDeal': self.new_deal,
        }

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "GameDeal":
        """Create a deal from a MongoDB document."""
        return cls(
            title=document.get('title', document.get('name', '')),
            url=document.get('url', ''),
            active_deal=document.get('activeDeal', document.get('active_deal', True)),
            image=document.get('image'),
            wide_image=document.get('wideImage', document.get('wide_image')),
            offer_from=document.get('startDate', document.get('offer_from', datetime.now(timezone.utc))),
            offer_until=document.get('endDate', document.get('offer_until')),
            product_type=document.get('type', document.get('product_type', 'game')),
            checkout_slug=document.get('checkout_slug'),
            new_deal=document.get('newDeal', document.get('new_deal', False)),
        )


def append_game_deal(deals: list[GameDeal], deal: GameDeal) -> list[GameDeal]:
    """
    Append a game deal entry to an existing list of game data.

    Appends a valid GameDeal instance to the provided list. Dates stay as datetime objects
    for calculations such as finding the earliest end date.

    Parameters
    ----------
    deals : list[GameDeal]
        The list to append the new deal to.
    deal : GameDeal
        The game deal to append. See GameDeal for field descriptions.

    Returns
    -------
    list[GameDeal]
        The updated list with the new deal appended.

    Notes
    -----
    - The deal is only appended if `deal.is_valid()` returns True.
    - Invalid deals are logged and skipped.
    - Deals are kept as `GameDeal` instances and converted only at persistence boundaries.

    Example
    -------
    >>> deals = []
    >>> deal = GameDeal(title="Example Game", url="https://example.com", image="https://example.com/image.jpg")
    >>> append_game_deal(deals, deal)
    [GameDeal(title='Example Game', ...)]
    """

    if not deal.is_valid():
        logger.warning(
            "Not all required data passed for game deal", 
            extra={'_game': deal.title, '_image': deal.image, '_wide_image': deal.wide_image, '_url': deal.url}
        )
        return deals

    deals.append(deal)
    return deals
