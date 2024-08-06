from dotenv import load_dotenv
from logging.config import dictConfig
import logging
import os


load_dotenv(override=True)
DEBUG = (os.getenv('DEBUG', 'True').lower() == 'true')


if DEBUG:
    print('\x1b[6;30;42m' + "---::-DEBUG-::---" + '\x1b[0m')
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_TOKEN_TEST')
    DEVELOPMENT = True
    DB = '_dev'
    loggerlevel = 'DEBUG'

else:
    print('\x1b[37;41m' + "---::-PRODUCTION-::---" + '\x1b[0m')
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_TOKEN_LIVE')
    DEVELOPMENT = False
    DB = ''
    loggerlevel = 'INFO'
    X_API_KEY =  os.getenv('X_API_KEY')
    X_API_SECRET =  os.getenv('X_API_SECRET')
    X_ACCESS_TOKEN =  os.getenv('X_ACCESS_TOKEN')
    X_ACCESS_TOKEN_SECRET =  os.getenv('X_ACCESS_TOKEN_SECRET')


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    dark_green = "\033[32m"
    yellow = "\033[33m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    #format = " %(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d) "
    format = '%(levelname)-8s - %(asctime)s - %(name)-14s : %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'

    FORMATS = {
        logging.DEBUG: dark_green + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, log):
        log_fmt = self.FORMATS.get(log.levelno)
        formatter = logging.Formatter(log_fmt, datefmt= '%Y-%m-%d %H:%M:%S')
        return formatter.format(log)

config = {
    'version':1,
    'disable_existing_loggers':False,
    'formatters': {
        'custom': {
            '()': CustomFormatter,
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'formatter': 'custom',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        },
        'console2': {
            'level': 'WARNING',
            'formatter': 'custom',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        },
    },
    'loggers': {
        "bot": {
            'handlers': ['console'],
            'level':loggerlevel,
            'propagate' : False
        },
        "discord": {
            'handlers': ['console2'],
            'level':loggerlevel,
            'propagate' : False
        },
        "store": {
            'handlers': ['console'],
            'level':loggerlevel,
            'propagate' : False
        },
    }
}

dictConfig(config)
