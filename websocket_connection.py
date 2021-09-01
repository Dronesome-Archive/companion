from enum import Enum
from logging import getLogger

import asyncio
import websockets
import json


class MessageType(Enum):
    HEARTBEAT = 'heartbeat'
    STATUS_UPDATE = 'status_update'
    MISSION_UPDATE = 'mission_update'


class OutboundMessage:
    def __init__(self, msg_type, number, content):
        self.msg_type = msg_type
        self.number = number
        self.content = content


class WebsocketConnection:

    RETRY_DELAY = 10

    def __init__(self, server_url, ssl_context):
        self.server_url = server_url
        self.ssl_context = ssl_context
        self.outbox = asyncio.LifoQueue()  # most recent messages get sent first
        self.inbox = asyncio.LifoQueue(maxsize=1)  # every message but the most recent gets discarded
        self.most_recent_outbound = {enum.value: 0 for enum in MessageType}
        self.handler = asyncio.create_task(self.handle())

    # keep the connection alive
    async def handle(self):
        while True:
            ws = None
            try:
                # TODO: ws = websockets.connect(self.server_url, ssl_context=self.ssl_context)
                ws = await websockets.connect(self.server_url)
            except:
                # getLogger().warning('Connecting to ' + self.server_url + ' failed!')
                await asyncio.sleep(WebsocketConnection.RETRY_DELAY)
                continue
            consumer = asyncio.create_task(self.consume(ws))
            producer = asyncio.create_task(self.produce(ws))

            # restart loop once sending or receiving fails
            await asyncio.wait([consumer, producer], return_when=asyncio.tasks.FIRST_COMPLETED)
            consumer.cancel()
            producer.cancel()

    # keep putting incoming messages into the inbox
    async def consume(self, ws):
        try:
            async for raw_msg in ws:
                # getLogger().info('RECEIVED', msg)
                while not self.inbox.empty():
                    await self.inbox.get()
                await self.inbox.put(json.loads(raw_msg))
        except Exception as e:
            # getLogger().warning('Error while consuming ws messages', e)
            return

    # keep sending messages from the outbox
    async def produce(self, ws):
        while True:
            msg = await self.outbox.get()
            if msg.number == self.most_recent_outbound[msg.msg_type.value]:
                try:
                    msg_raw = json.dumps({'type': msg.msg_type.value, 'body': msg.content})
                    await ws.send(msg_raw)
                    # getLogger().info('SENT', msg_raw)
                except Exception as e:
                    # getLogger().warning('Error while producing ws messages', e)
                    await self.outbox.put(msg)
                    return

    # put a new message into the outbox
    def queue_message(self, msg_type, content):
        self.most_recent_outbound[msg_type.value] += 1
        self.outbox.put_nowait(OutboundMessage(msg_type, self.most_recent_outbound[msg_type.value], content))

