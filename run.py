import asyncio
import logging

from mav import Mav
from connection_mock import Connection
from drone import Drone


LOG = './drone.log'
SERVER_URL = 'https://dronesem.studio'
SERVER_NAMESPACE = '/drone'

def configure_logging():
	formatter = logging.Formatter('[{levelname:4.4} {asctime} {module}:{funcName}] {message}', style='{', datefmt='%H:%M:%S')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.getLogger().addHandler(handler)
	logging.getLogger().setLevel(logging.INFO)

async def main():
	configure_logging()
	mav = Mav()
	drone = Drone(mav)
	server_connection = Connection(drone)
	await asyncio.gather(server_connection.produce(), mav.keep_connected())


asyncio.run(main())
