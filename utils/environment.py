from dotenv import load_dotenv
from logging.config import dictConfig
import logging
import os


load_dotenv(override=True)
DEBUG = (os.getenv('DEBUG', 'True').lower() == 'true')


config = {
    'version':1,
    'disable_existing_loggers':False,
    'formatters': {
        'standard':{
            'format': '%(levelname)-10s - %(asctime)s - %(module)-7s : %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        },
        'console2': {
            'level': 'WARNING',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        },
    },
    'loggers': {
        "bot": {
            'handlers': ['console'],
            'level':'DEBUG',
            'propagate' : False
        },
        "discord": {
            'handlers': ['console2'],
            'level':'INFO',
            'propagate' : False
        }
    }
}

dictConfig(config)

if DEBUG:
    print("---::-DEBUG-::---")
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_TOKEN_TEST')
    DEVELOPMENT = True
    DB = '_dev'

else:
    print("---::-PRODUCTION-::---")
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_TOKEN_LIVE')
    DEVELOPMENT = False
    DB = ''
    X_API_KEY =  os.getenv('X_API_KEY')
    X_API_SECRET =  os.getenv('X_API_SECRET')
    X_ACCESS_TOKEN =  os.getenv('X_ACCESS_TOKEN')
    X_ACCESS_TOKEN_SECRET =  os.getenv('X_ACCESS_TOKEN_SECRET')
