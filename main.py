# coding=utf-8

import os
import sys
import asyncio
import traceback
import importlib

from utils.database import Database
from utils import environment

import clients.discord.bot as discord

logger = environment.logging.getLogger("bot")

shutdown_flag_is_set = False

# --- Change status --- #
status = ['Still', 'in', 'Development']

modules = []

def load_modules() -> list:
    """Imports and instances all the modules automagically."""

    stores_dir = os.path.join( os.path.dirname(os.path.abspath(__file__)), "stores")
    for i in sorted(os.listdir(stores_dir)):
        module_name = os.path.splitext(i)[0]
        module_extension = os.path.splitext(i)[1]
        if module_extension == ".py" and not module_name.startswith('_'):
            try:
                imported_module = importlib.import_module(f"stores.{module_name}")
                modules.append(getattr(imported_module, "Main")())
            except:
                print(f"Error while loading module {module_name} beacuse of {sys.exc_info()[0]}")
                print(f"{sys.exc_info()[1]}\n")
    logger.info(f"{len(modules)} modules loaded")
    if not modules:
        print("Program is exiting because no modules were loaded")
        exit()
    return modules

load_modules()

discord = discord.setup(modules)

async def update(update_store=None) -> None:
    '''
    Update specified store

    Parameters:
        update_store (store object): The store to update
    '''
    Database(modules)
    Database.connect(environment.DB)

    if update_store:
        logger.info("Updating store: %s", update_store.name)
        if await update_store.get():
            Database.overwrite_deals(update_store.name, update_store.data)
            Database.add_image(update_store)
            if update_store.alert_flag:
                await send_games_notification(update_store)
            else:
                print("Updated but didn't send reminders")
            update_store.alert_flag = True
        else:
            logger.info("No new games games to get for %s", update_store.name)


async def initialize() -> None:
    '''
    --- APP START / RESTART ---
    '''
    # await client.wait_until_ready()

    # Connect to database (deals)
    Database(modules)
    Database.connect(environment.DB)

    for store in modules:
        # If there's data for this store on the db get it
        if store.name in Database.saved_stores():
            logger.debug("Getting Data from DB for %s", store.name)
            store.data = Database.find(store.name)
            store.image = Database.get_image(store.name)

            # Then check if live data is different
            logger.debug("Checking if theres new data")
            await update(store)
        else:
            logger.debug("Scrapping data for %s", store.name)
            try:
                await store.get()
                Database.overwrite_deals(store.name, store.data)
                Database.add_image(store)
            except Exception as error:
                logger.error("Failed to scrape store %s: %s", store.name, str(error))


async def send_games_notification(store):
    '''
    Send games notifications
    '''
    await discord.wait_until_ready()
    servers_data = Database.get_discord_servers()
    for server in servers_data:
        # Check server notification settings
        if str(store.id) in str(server.get('notification_settings')):
            if server.get('channel'):
                #print(f"{server.get('channel')} has role {server.get('role')}")
                await discord.store_messages(store.name, server.get('channel'), server.get('role'))
            else:
                #print(f"2: {server.get('channel')} has role {server.get('role')}")
                await discord.store_messages(store.name, discord.guilds.system_channel, server.get('role'))

    """
    if store:
        for guild in client.guilds:
            if guild.id == 827564503930765312:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        print("trying to send reminder")
                        if x.data:
                            await channel.send(f'<@&1037050135391256576> Here are the new deals on {x.name}')
                            await store_messages(store.name, channel)
                        else:
                            print("The only deal on the store was just taken down")

        channel = client.get_channel(828324732604514344)
        await store_messages(store.name, channel)

    if not store:
        for guild in client.guilds:
            if guild.id == 827564503930765312:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send('Last chance to get the games')
    """



async def scrape_scheduler() -> None:
    '''
    Schedules the scraping of stores, runs perpetually/
    '''
    # await client.wait_until_ready()
    tasks = set()

    for store in modules:
        tasks.add(asyncio.create_task(store.scheduler(), name=store.name))

    finished = set()
    pending = set()

    while tasks:
        logger.debug("finished=%s pending=%s tasks=%s", finished, pending, tasks)
        finished, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # print(f"{finished=}\n{pending=}\n{tasks=}")

        for task in finished:
            store = task.result()

            try:
                await update(store)
            except Exception:
                logger.error("FAILED TASK: %s", task.result)
                logger.error(traceback.format_exc())

            pending.add(asyncio.create_task(store.scheduler(), name=store.name))
            logger.debug("Adding back in %s", task.get_name())

        finished.clear()
        tasks = pending.copy()
        pending.clear()

        if shutdown_flag_is_set:
            print("Braking scrape_scheduler()")
            tasks.cancel()
            break



if __name__ == "__main__":
    #load_dotenv(override=True)

    try:
        logger.info('Modules: %s', ', '.join(['%s' % store.name for store in modules]))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        #loop.create_task(test_commands())
        loop.create_task(discord.start(environment.DISCORD_BOT_TOKEN))
        loop.create_task(initialize())
        loop.create_task(scrape_scheduler())
        loop.run_forever()

    except KeyboardInterrupt as exit:
        logger.info("Caught keyboard interrupt. Canceling tasks...")
        shutdown_flag_is_set = True

    finally:
        logger.info("Exiting program.")
        loop.close()
