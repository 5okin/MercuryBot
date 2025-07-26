# coding=utf-8

import os
import asyncio
import importlib
import psutil, tracemalloc

from utils.database import Database
from utils import environment

import clients.discord.bot as discord
import clients.twitter.bot as twitter
import clients.blueSky.bot as blueSky

logger = environment.logging.getLogger("bot.main")

shutdown_flag_is_set = False

# --- Change status --- #
status = ['Still', 'in', 'Development']

modules = []

#MARK: load modules
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
                logger.error("Error while loading module")
    if not modules:
        logger.error("Program is exiting because no modules were loaded")
        exit()
    return modules

load_modules()

discord = discord.MyClient(modules)
x = twitter.MyClient()
bsky = blueSky.MyClient()


def log_memory(tag=""):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 * 1024)
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    extra = {f'_{i+1}': top_stats[i] for i in range(min(5, len(top_stats)))}
    logger.info(f"[{tag}] RAM Usage: {mem:.2f} MB", extra = extra)


#MARK: Update
async def update(update_store=None) -> None:
    '''
    Update specified store

    Parameters:
        update_store (store object): The store to update
    '''
    Database(modules)
    Database.connect(environment.DB)

    try:
        if update_store:
            logger.info("Updating store: %s", update_store.name)
            if await update_store.get():
                log_memory('Before store update')
                Database.overwrite_deals(update_store.name, update_store.data)
                Database.add_image(update_store)
                await send_games_notification(update_store)
                log_memory('After store Update')
            else:
                logger.debug("No new games to for %s", update_store.name)
    except:
        logger.error("Failed to update store")

#MARK: Initialize
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

#MARK: Send games notification
async def send_games_notification(store) -> None:
    '''
    Send games notifications
    '''
    log_memory('Before send social notification')

    # tweet about it...
    if store.twitter_notification and x:
        tweet_url = x.tweet(store)
        await discord.dm_logs("Tweet", tweet_url)
        Database.update_social_followers(x.get_follower_count())

    # The other tweet about it...
    if store.bsky_notification and bsky:
        bsky_url = bsky.post(store)
        await discord.dm_logs("Bluesky", bsky_url)
        Database.update_social_followers(bsky.get_follower_count())

    log_memory('Before send discord notification')
    await discord.send_notifications(store)
    log_memory('Done with notification')

#MARK: Scheduler loop
async def scrape_scheduler() -> None:
    '''
    Schedules the scraping of stores, runs perpetually
    '''
    # await client.wait_until_ready()
    tasks = set()

    for store in modules:
        tasks.add(asyncio.create_task(store.scheduler(), name=store.name))

    finished = set()
    pending = set()

    while tasks:
        logger.debug("tasks=%s", [task.get_name() for task in tasks])
        logger.info("Active tasks: %s", [task.get_name() for task in asyncio.all_tasks()])
        log_memory('Scrape Loop')
        
        finished, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # print(f"{finished=}\n{pending=}\n{tasks=}")

        for task in finished:
            store = task.result()

            await update(store)

            pending.add(asyncio.create_task(store.scheduler(), name=store.name))
            logger.debug("Adding back in %s", task.get_name())

        finished.clear()
        tasks = pending.copy()
        pending.clear()

        if shutdown_flag_is_set:
            print("Braking scrape_scheduler()")
            tasks.cancel()
            break


#MARK: main
if __name__ == "__main__":
    #load_dotenv(override=True)
    tracemalloc.start()
    log_memory('Start')

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
