# coding=utf-8

import itertools
import os
import asyncio
import importlib
import psutil, tracemalloc, gc, ctypes
import threading

from utils.database import Database
from utils import environment

import clients.discord.bot as discord_module
import clients.twitter.bot as twitter
import clients.blueSky.bot as blueSky

logger = environment.logging.getLogger("bot.main")
shutdown_flag_is_set: bool = False
modules = []
web_server_thread = None

#MARK: load modules
def load_modules() -> list:
    """Imports and instances all the modules automagically."""

    stores_dir = os.path.join( os.path.dirname(os.path.abspath(__file__)), "stores")
    for i in sorted(os.listdir(stores_dir)):
        module_name, module_extension = os.path.splitext(i)
        if module_extension == ".py" and not module_name.startswith('_'):
            try:
                imported_module = importlib.import_module(f"stores.{module_name}")
                modules.append(getattr(imported_module, "Main")())
            except:
                logger.error("Error while loading module")
    if not modules:
        logger.error("Program is exiting because no modules were loaded")
        import sys
        sys.exit(1)
    return modules

load_modules()

discord = discord_module.MyClient(modules)
Database.initialize(modules)
Database.connect(environment.DB)
x = twitter.MyClient()
bsky = blueSky.MyClient()


# MARK: Memory logger
def log_memory(tag=""):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 * 1024)
    logger.info(f"[{tag}] RAM Usage: {mem:.2f} MB")


#MARK: Update
async def update(update_store=None) -> None:
    '''
    Update specified store

    Parameters:
        update_store (store object): The store to update
    '''

    try:
        if update_store:
            logger.info("Updating store: %s", update_store.name)
            if await update_store.get():
                Database.overwrite_deals(update_store.name, update_store.data)
                Database.add_image(update_store)
                await send_games_notification(update_store)
            else:
                logger.debug("No new games to for %s", update_store.name)
            await update_store.close_session()
            update_store.reset_scheduler()
    except:
        update_store.schedule_retry()
        logger.error("Failed to update store")

#MARK: Initialize
async def initialize() -> None:
    '''
    --- APP START / RESTART ---
    '''

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
    gc.collect()
    log_memory('Done with notification')

#MARK: Scheduler loop
async def scrape_scheduler() -> None:
    '''
    Schedules the scraping of stores, runs perpetually
    '''
    tasks = {asyncio.create_task(store.scheduler(), name=store.name) for store in modules}
    loop_counter = itertools.count(1)
    LOG_EVERY_N = 5

    while tasks:
        iteration = next(loop_counter)

        if iteration % LOG_EVERY_N == 0:
            log_memory('Before Scrape Loop')
            logger.info("Pending tasks: %s",', '.join(task.get_name() for task in asyncio.all_tasks() if not task.done()))
        
        finished, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in finished:
            tasks.remove(task)
            
            store = task.result()
            await update(store)
            
            tasks.add(asyncio.create_task(store.scheduler(), name=store.name))
            logger.debug("Adding back in %s", task.get_name())

        # gc.collect()
        # try:
        #     libc = ctypes.CDLL("libc.so.6")
        #     libc.malloc_trim(0)
        # except Exception:
        #     logger.warning(f"malloc_trim not available")

        if iteration % LOG_EVERY_N == 0:
            log_memory('After Scrape Loop')

        if shutdown_flag_is_set:
            print("Braking scrape_scheduler()")
            for task in tasks:
                task.cancel()
            break


# MARK: start_web_server
def start_web_server():
    """Start the Flask web server in a separate thread"""
    try:
        from web.app import run_server
        web_port = int(os.getenv('WEB_PORT', 5000))
        web_host = os.getenv('WEB_HOST', '0.0.0.0')
        logger.info(f"Starting web server on {web_host}:{web_port}")
        run_server(discord, host=web_host, port=web_port)
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")


#MARK: main
if __name__ == "__main__":
    log_memory('Start')

    if environment.DISCORD_BOT_TOKEN is None:
        logger.critical("DISCORD_BOT_TOKEN is not set! Exiting.")
        import sys
        sys.exit(1)

    try:
        logger.info('Modules: %s', ', '.join(store.name for store in modules))

        # Start web server in separate thread
        web_server_thread = threading.Thread(target=start_web_server, daemon=True)
        web_server_thread.start()
        logger.info("Web server thread started")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

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
