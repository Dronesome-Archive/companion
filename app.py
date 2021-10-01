import asyncio

import mavsdk

from drone import Drone
from socketio_connection import SocketIOConnection
import log

# Paths
LOG = './drone.log'
SUPER_SECRET_DRONE_KEY_FILE = './drone.key'
SERVER_URL = 'ws://localhost:8000'
SERVER_NAMESPACE = '/drone'


# Create drone
async def create_drone():
    log.setup()

    # connection to server
    with open(SUPER_SECRET_DRONE_KEY_FILE) as f:
        key = f.read()
    server = SocketIOConnection(SERVER_NAMESPACE, SERVER_URL, key)

    # connection to mav
    system = mavsdk.System()
    await system.connect(system_address="udp://:14540")
    drone = Drone(system, server)

    await drone.heartbeat


asyncio.run(create_drone())
