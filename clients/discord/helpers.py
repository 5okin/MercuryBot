import io
import discord
import clients.discord.messages as messages
from utils import environment

logger = environment.logging.getLogger("bot.discord")


def build_deal_payload(store, mobile: bool = False):
    if store.data and any(game.get("activeDeal", False) for game in store.data):
        message_to_show = getattr(messages, store.name, messages.default)
        if isinstance(store.image, io.BytesIO):
            store.image.seek(0)
            file = discord.File(store.image, filename="img." + store.image_type.lower())
            return {
                "embed": message_to_show(store, mobile=mobile),
                "file": file,
                "store": store,
            }
        logger.error("Image isnt BytesIO and image wasn't found on CDN", extra={"_store_data": store.data})
    return None
