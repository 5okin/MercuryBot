import io
import os
from pymongo import MongoClient
from dotenv import load_dotenv


class Database(object):

    store_list = []
    load_dotenv(override=True)
    CONNECTION_STRING = os.getenv('DB_CONNECTION_STRING')
    #print(f'{CONNECTION_STRING=}')
    deals = None
    images = None

    def __init__(self, modules):
        for store in modules:
            self.store_list.append(store.name)


    @staticmethod
    def connect(dev):
        '''
        Connect to mongoDB and setup collections
        '''
        client = MongoClient(Database.CONNECTION_STRING)
        Database.servers = client['servers'+dev]
        Database.deals = client['deals'+dev]
        Database.feedback = client['feedback'+dev]
        Database.images = Database.deals.images


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
    def remove_server(guild):
        '''
        Removes the server from the database when the bot is kicked.
        Important so it doesnt try to send messages to a server its no longer connected to.
        '''
        result = Database.servers['discord'].delete_one({'server': guild.id})

        # Check if the document was deleted successfully
        if result.deleted_count == 1:
            print(f"Document deleted successfully.")
        else:
            print(f"No server found.")


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
            if not Database.collections_exists(collection):
                print(f'Creating {collection}')
                Database.deals[collection].insert_many(data)
            else:
                print(f'delete {collection} and write')
                Database.deals[collection].insert_many(data)
        else:
            print(f'Module {collection} has no data to upload')

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
                'data': image.getvalue()
            }
            Database.images.insert_one(thumbnail)
        else:
            print(f'Module {store.name} has no image to upload')

    @staticmethod
    def get_image(name):
        '''
        Return image of a given store
        '''
        if Database.image_exists(name):
            img = Database.images.find_one({"_id": name})
            pil_img = io.BytesIO(img['data'])
            return pil_img
        else:
            print('image not found')
