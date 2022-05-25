import asyncio
import logging
import sys

from drone import Drone
from mav import Mav
from mav_mock import Mav as MavMock
from connection import Connection
from connection_mock import Connection as ConnectionMock


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
	logging.info("configured logging")

	if '--mockmav' in sys.argv[1:]:
		mav = MavMock()
		logging.info('mocking mav')
	else:
		mav = Mav()
	await mav.init_connection()

	drone = Drone(mav)

	if '--mockconn' in sys.argv[1:]:
		server_connection = ConnectionMock(drone)
		logging.info('mocking connection')
	else:
		server_connection = Connection(drone)

	await asyncio.gather(server_connection.produce(), mav.gather_telemetry())


asyncio.run(main())
