import asyncio
import json
from logging import getLogger

import socketio

from message_type import ToDrone, ToServer


class OutboundMessage:
    def __init__(self, msg_type, number, content):
        self.msg_type = msg_type
        self.number = number
        self.content = content


class InboundMessage:
    def __init__(self, msg_type, content=None):
        self.msg_type = msg_type
        self.content = content


class SocketIOConnection(socketio.AsyncClientNamespace):

    RETRY_DELAY = 10
    MAX_RETRY_DELAY = 40

    def __init__(self, namespace):
        socketio.AsyncClientNamespace.__init__(self, namespace)

        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=0,
            reconnection_delay=SocketIOConnection.RETRY_DELAY,
            reconnection_delay_max=SocketIOConnection.MAX_RETRY_DELAY,
            logger=getLogger()  # TODO: how much gets logged?
        )
        self.sio.register_namespace(self)
        self.outbox = asyncio.LifoQueue()  # most recent messages get sent first
        self.inbox = asyncio.LifoQueue(maxsize=1)  # every message but the most recent one gets discarded
        self.most_recent_outbound = {enum.value: 0 for enum in ToServer}
        self.producer = None

    # put a new message into the outbox
    def queue_message(self, msg_type, content):
        self.most_recent_outbound[msg_type.value] += 1
        self.outbox.put_nowait(OutboundMessage(msg_type, self.most_recent_outbound[msg_type.value], content))

    ####################################################################################################################
    # CONNECTION TO SERVER
    ####################################################################################################################

    # start producing messages from the outbox
    def on_connect(self):
        print('CON')
        self.producer = asyncio.create_task(self.produce())

    # stop producing messages from the outbox
    def on_disconnect(self):
        print('DIS')
        self.producer.cancel()
        self.producer = None

    # empty inbox and put in the return message
    async def on_return(self):
        print('RCV: return')
        while not self.inbox.empty():
            await self.inbox.get()
        await self.inbox.put(InboundMessage(ToDrone.EMERGENCY_RETURN))

    # empty inbox and put in the emergency land message
    async def on_emergency_land(self):
        print('RCV: emergency')
        while not self.inbox.empty():
            await self.inbox.get()
        await self.inbox.put(InboundMessage(ToDrone.EMERGENCY_LAND))

    # empty inbox and put in the update message
    async def on_update(self, raw_msg):
        print('RCV: update')
        print(raw_msg)
        while not self.inbox.empty():
            await self.inbox.get()
        await self.inbox.put(InboundMessage(ToDrone.UPDATE, json.loads(raw_msg)))

    # keep sending messages from the outbox
    async def produce(self):
        while True:
            msg = await self.outbox.get()
            print('SND: ' + msg.msg_type.value)
            print(msg.content)
            if msg.number == self.most_recent_outbound[msg.msg_type.value]:
                await self.sio.emit(msg.msg_type.value, namespace=self.namespace, data=msg.content)
