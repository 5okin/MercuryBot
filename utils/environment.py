from dotenv import load_dotenv
from logging.config import dictConfig
import json
import logging, traceback
import os
import sys


load_dotenv(override=True)
DEBUG = (os.getenv('DEBUG', 'True').lower() == 'true')

# DISCORD_DEV_GUILD = os.getenv('DISCORD_DEV_GUILD')
DISCORD_DEV_GUILD = os.getenv('DISCORD_DEV_GUILD') # if os.getenv('DISCORD_DEV_GUILD') is not None else '0'
DISCORD_ADMIN_ACC = int(os.getenv('DISCORD_ADMIN_ACC')) if os.getenv('DISCORD_ADMIN_ACC') is not None else None

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

    COLORS = {
        logging.DEBUG: "\033[32m",      # Dark green
        logging.INFO: "\x1b[38;21m",    # grey
        logging.WARNING: "\033[33m",    # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[41m",   # Red background
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, self.RESET)

        log_record = {
            "message": record.getMessage(),
            "level": record.levelname,
            "time": self.formatTime(record, datefmt='%Y-%m-%d %H:%M:%S'),
            "name": record.name
        }

        # Automatically add traceback for errors or critical logs
        if record.levelno >= logging.WARNING: 
            log_record['file'] = f'{record.pathname} :{record.lineno}'
            log_record["traceback"] = traceback.format_exc()

            if record.exc_info and sys.exc_info()[0] is not None:
                log_record["exception_type"] = str(sys.exc_info()[0])
                log_record["exception_message"] = str(sys.exc_info()[1]) 
            
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key.startswith("_"):
                log_record[key[1:]] = value

        json_log = json.dumps(log_record)
        return f"{log_color}{json_log}{self.RESET}" if DEBUG else json_log


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
