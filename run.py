import asyncio
from logging import config

from mav_mock import Mav
from server_connection import ServerConnection
from drone import Drone


LOG = './drone.log'
SERVER_URL = 'https://dronesem.studio'
SERVER_NAMESPACE = '/drone'

def configure_logging():
    config.dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '[%(asctime)s %(levelname)s %(funcName)s]: %(message)s',
                'datefmt': '%H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default'
            },
            'file': {
                'class': 'logging.FileHandler',
                'filename': 'log',
                'formatter': 'default'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    })

async def main():
    configure_logging()
    mav = Mav()
    drone = Drone(mav)
    server_connection = ServerConnection(drone)
    await asyncio.gather(server_connection.produce(), mav.keep_connected())


asyncio.run(main())
