import io
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from utils import environment
from datetime import datetime, timezone

logger = environment.logging.getLogger("bot.database")

class Database(object):
    store_list = []
    load_dotenv(override=True)
    CONNECTION_STRING = os.getenv('DB_CONNECTION_STRING')
    _client = None


    @classmethod
    def initialize(cls, modules):
        cls.store_list = [store.name for store in modules]


    @classmethod
    def connect(cls, dev):
        '''
        Connect to mongoDB and setup collections
        '''
        if cls._client is None:
            cls._client = MongoClient(cls.CONNECTION_STRING)
            cls.servers = cls._client['servers'+dev]
            cls.deals = cls._client['deals'+dev]
            cls.feedback = cls._client['feedback'+dev]
            cls.social = cls.servers.social
            cls.images = cls.deals.images


    @staticmethod
    def add_feedback(data):
        '''
        Save feedback to server 
        '''
        Database.feedback['discord'].insert_one(data)


    @staticmethod
    def insert_store_notifications(data):
        '''
        Inserts or updates guild store notification prefrences
        '''
        for server_info in data:
            filter_criteria = {"server":server_info['server']}
            Database.servers['discord'].update_one(filter_criteria, {"$set":server_info}, upsert=True)


    @staticmethod
    def insert_discord_server(data):
        '''
        Inserts or updates the discord server database 
        according to the server id field ['server':'xxxxxxx']
        '''
        for server_info in data:
            filter_criteria = {"server":server_info['server']}
            Database.servers['discord'].update_one(filter_criteria, {"$set":server_info}, upsert=True)


    @staticmethod
    def get_discord_servers():
        '''
        Return list of the discord servers with their corresponding notification role and channel. 
        '''
        data = []
        for document in Database.servers['discord'].find():
            data.append(document)
        return data


    @staticmethod
    def get_discord_server(server_id):
        '''
        Return notification role and channel for a given server id.
        '''
        return Database.servers['discord'].find_one({'server': server_id})


    @staticmethod
    def remove_server(guildId):
        '''
        Removes the server from the database when the bot is kicked.
        Important so it doesnt try to send messages to a server its no longer connected to.
        '''
        server = Database.servers['discord'].find_one({'server': guildId})

        if not server:
            logger.info('Document for server %s was not found', guildId)
            return
        
        joined_date = server.get('joined')
        duration = 0
        if joined_date:
            duration = datetime.now(timezone.utc) - joined_date.replace(tzinfo=timezone.utc)

        result = Database.servers['discord'].delete_one({'server': guildId})

        # Check if the document was deleted successfully
        if result.deleted_count == 1:
            logger.info('Document deleted successfully for %s', guildId,
                        extra={'_Joined for:': duration, '_detailed': server}    
            )
        else:
            logger.info('No server found.')


    @staticmethod
    def collections_exists(collection_name):
        return True if collection_name in Database.deals.list_collection_names() else False

    @staticmethod
    def image_exists(store_name):
        '''
        Return a boolean (True/False) for a given store
        '''
        return True if Database.images.find_one({"_id": store_name}) else False

    @staticmethod
    def overwrite_deals(collection, data):
        Database.deals[collection].drop()
        if data:
            logger.info('Creating collection for %s', collection)
            Database.deals[collection].insert_many(data)
        else:
            logger.debug('Module %s has no data to upload', collection)

    @staticmethod
    def find(collection):
        data = []
        for x in Database.deals[collection].find():
            data.append(x)
        return data

    @staticmethod
    def stores_to_get():
        notfound = []
        for collection in Database.store_list:
            if not Database.collections_exists(collection):
                notfound.append(collection)
        return notfound

    @staticmethod
    def saved_stores():
        found = []
        for collection in Database.store_list:
            if Database.collections_exists(collection):
                found.append(collection)
        return found

    @staticmethod
    def add_image(store):
        if store.image:
            if Database.image_exists(store.name):
                Database.images.delete_many({"_id": store.name})

            if not isinstance(store.image, io.BytesIO):
                image = io.BytesIO()
                store.image.save(image, format=store.image_type)
            else:
                image = store.image

            thumbnail = {
                '_id': store.name,
                'data': image.getvalue(),
                'cdn' : store.image_cdn
            }
            Database.images.insert_one(thumbnail)
        else:
            logger.debug('Module %s has no image to upload', store.name)

    @staticmethod
    def get_image(name, row="data"):
        '''
        Return image of a given store
        row must be either "data" or "cdn"
        '''

        if row not in ("data", "cdn"):
            raise ValueError(f"row must be 'data' or 'cdn', got '{row}'")

        if Database.image_exists(name):
            img = Database.images.find_one({"_id": name})
            pil_img = io.BytesIO(img['data']) if row =="data" else img.get(row)
            return pil_img
        else:
            logger.error("Image not found")

    
    @staticmethod
    def update_social_followers(social):
        '''
        Updates the number of followers on social media
        '''
        if social:
            filter_criteria = {"social":social.get('name')}
            Database.servers['social'].update_one(filter_criteria, {"$set":{"followers":social.get('followers_count')}}, upsert=True)
        else:
            logger.warning("No social data provided, skipping update.")
