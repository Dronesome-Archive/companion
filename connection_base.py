from time import time
import asyncio
import logging

from message_type import ToServer, ToDrone
from mission import Mission

class ConnectionBase:

	def __init__(self, companion, heartbeat_duration):
		self.connected = True
		self.companion = companion
		self.heartbeat_duration = heartbeat_duration
		self.last_heartbeat = time() - heartbeat_duration
	
	# send message to server, handle_response and return a bool representing whether sending the message worked
	async def send(self):
		logging.warning("called abstract function")

	# every heartbeat_duration seconds, return a heartbeat message
	async def get_heartbeat(self):
		delay = self.last_heartbeat + self.heartbeat_duration - time()
		await asyncio.sleep(delay if delay > 0 else 0)
		self.last_heartbeat = time()
		return { 'type': ToServer.HEARTBEAT.value, 'pos': self.companion.mav.pos, 'battery': self.companion.mav.battery }
	
	# update self_companion depending on the type of response
	def handle_response(self, res):
		if (res['type'] == ToDrone.UPDATE.value):
			logging.info('received UPDATE')
			self.companion.new_mission = Mission(res, self.companion.mav.battery)
			self.companion.set_state(self.companion.state_updating)
		elif (res['type'] == ToDrone.EMERGENCY_LAND.value):
			logging.info('received EMERGENCY_LAND')
			self.companion.set_state(self.companion.state_emergency_landing)
		elif (res['type'] == ToDrone.EMERGENCY_RETURN.value):
			logging.info('receivde EMERGENCY_RETURN')
			self.companion.set_state(self.companion.state_emergency_returning)

	# continually send heartbeats and state updates; if connection is cut off, queue state updates until a heartbeat goes through
	async def produce(self):
		while True:
			if (self.connected):
				heartbeat = self.get_heartbeat()
				state_update = self.companion.outbox.get()
				done_set, pending_set = await asyncio.wait([heartbeat, state_update], return_when=asyncio.FIRST_COMPLETED)
				for task in pending_set:
					task.cancel()
				done = [i for i in done_set][0]
				self.connected = await self.send(done.result())
				if done == state_update and self.companion.outbox.empty() and not self.connected:
					await self.companion.outbox.put(done.result())
			else:
				msg = await self.get_heartbeat()
				self.connected = self.send(msg)
