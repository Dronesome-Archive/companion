import logging
import ssl

import mavsdk
import asyncio

from drone import Drone
from websocket_connection import WebsocketConnection

# Paths
LOG = './drone.log'
CLIENT_CERT_CHAIN = './_ssl/drone.pem'
CLIENT_CERT_KEY = './_ssl/drone.key'
SERVER_URL = 'ws://localhost:8000'

# Set up logging
# logging.basicConfig(
#     filename=LOG,
#     level=logging.DEBUG,
#     format='%(levelname)s %(asctime)s - %(message)s'
# )
# logging.getLogger().addHandler(logging.StreamHandler())  # without this errors only go to log, not stderr
# logger = logging.getLogger()


# Create drone
async def create_drone():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_default_certs()
    ssl_context.load_cert_chain(CLIENT_CERT_CHAIN, CLIENT_CERT_KEY)
    ssl_context.verify_mode = ssl.VerifyMode.CERT_REQUIRED
    ssl_context.check_hostname = True
    connection = WebsocketConnection(SERVER_URL, ssl_context)
    system = mavsdk.System()
    await system.connect(system_address="udp://:14540")
    drone = Drone(system, connection)
    await drone.heartbeat


asyncio.run(create_drone())
