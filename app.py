import asyncio
from os import environ
import log

from mock_drone import Drone
from socketio_connection import SocketIOConnection

# Paths
LOG = './drone.log'
SERVER_URL = 'https://dronesem.studio'
SERVER_NAMESPACE = '/drone'


# Create drone
async def create_drone():
    log.setup()

    # connection to server
    server = SocketIOConnection(SERVER_NAMESPACE)

    # connection to mav
    # system = mavsdk.System()
    # await system.connect(system_address="udp://:14540")
    # await system.param.set_param_int('COM_RC_IN_MODE', 2)
    system = None
    
    drone = Drone(system, server)

    await server.sio.connect(SERVER_URL, auth=environ['SUPER_SECRET_DRONE_KEY'], namespaces=SERVER_NAMESPACE)
    await drone.heartbeat


asyncio.run(create_drone())
