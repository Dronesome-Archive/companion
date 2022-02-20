import ssl
import aiohttp
import asyncio
import logging
from time import time

from message_type import ToServer, ToDrone
from mission import Mission

class ServerConnection:
	URL = 'https://droneso.me/drone_api/'
	DRONE_CERT = './.ssl/dronesome.crt.pem' # whole chain from drone cert to root cert
	DRONE_PRIVATE_KEY = './.ssl/dronesome.key.pem'
	SERVER_CERT = './.ssl/droneso.me/inter1inter2root1.pem' # chain from intermediate cert to root cert (do not include the server certificate itself)
	HEARTBEAT_DURATION = 5
	TIMEOUT = 10

	def __init__(self, companion):
		self.__connected = True
		self.__companion = companion
		self.__last_heartbeat = time() - ServerConnection.HEARTBEAT_DURATION
	
	async def __get_heartbeat(self):
		await asyncio.sleep(self.__last_heartbeat + ServerConnection.HEARTBEAT_DURATION - time())
		self.__last_heartbeat = time()
		return { 'type': ToServer.HEARTBEAT.value, 'pos': self.__companion.mav.pos, 'battery': self.__companion.mav.battery }

	async def __send(self, dict):
		# https://docs.aiohttp.org/en/stable/client_quickstart.html
		# https://stackoverflow.com/q/41701791
		logging.info(f'sending {dict}')
		tls = ssl.create_default_context()
		#tls = ssl.create_default_context(cafile=ServerConnection.SERVER_CERT)
		tls.load_cert_chain(ServerConnection.DRONE_CERT, ServerConnection.DRONE_PRIVATE_KEY)
		connector = aiohttp.TCPConnector(ssl_context=tls)
		timeout = aiohttp.ClientTimeout(total=ServerConnection.TIMEOUT)
		async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
			try:
				async with session.request('POST', ServerConnection.URL, json=dict) as r:
					if r.ok:
						json_body = await r.json()
						logging.info(f'received reply {json_body}')
						self.__handle_response(json_body)
					else:
						logging.warning(f'received bad reply: {r.status}')
			except aiohttp.ClientConnectionError as e:
				logging.warning(f'connection error {e}')
				return False
			except TimeoutError as e:
				logging.warning(f'timeout error {e}')
				return False
		return True
	
	def __handle_response(self, res):
		if (res['type'] == ToDrone.UPDATE.value):
			logging.info('received UPDATE')
			self.__companion.new_mission = Mission(res, self.__companion.mav.battery)
			self.__companion.set_state(self.__companion.state_updating)
		elif (res['type'] == ToDrone.EMERGENCY_LAND.value):
			logging.info('received EMERGENCY_LAND')
			self.__companion.set_state(self.__companion.state_emergency_landing)
		elif (res['type'] == ToDrone.EMERGENCY_RETURN.value):
			logging.info('receivde EMERGENCY_RETURN')
			self.__companion.set_state(self.__companion.state_emergency_returning)

	async def produce(self):
		while True:
			if (self.__connected):
				heartbeat = self.__get_heartbeat()
				state_update = self.__companion.outbox.get()
				done_set, pending_set = await asyncio.wait([heartbeat, state_update], return_when=asyncio.FIRST_COMPLETED)
				for task in pending_set:
					task.cancel()
				done = [i for i in done_set][0]
				self.__connected = await self.__send(done.result())
				if done == state_update and self.__companion.outbox.empty() and not self.__connected:
					await self.__companion.outbox.put(done.result())
			else:
				msg = await self.__get_heartbeat()
				self.__connected = self.__send(msg)
