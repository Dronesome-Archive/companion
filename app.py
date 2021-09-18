import ssl

import mavsdk
import asyncio

from drone import Drone
from websocket_connection import WebsocketConnection
import log

# Paths
LOG = './drone.log'
CLIENT_CERT_CHAIN = './_ssl/drone.pem'
CLIENT_CERT_KEY = './_ssl/drone.key'
SERVER_URL = 'ws://localhost:8000'


# Create drone
async def create_drone():
    log.setup()
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
