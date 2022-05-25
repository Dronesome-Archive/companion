import ssl
import aiohttp
import asyncio
import logging
from time import time

from connection_base import ConnectionBase

class Connection(ConnectionBase):
	HEARTBEAT_DURATION = 5
	URL = 'https://droneso.me/drone_api/'
	DRONE_CERT = './.ssl/dronesome.crt.pem' # whole chain from drone cert to root cert
	DRONE_PRIVATE_KEY = './.ssl/dronesome.key.pem'
	SERVER_CERT = './.ssl/droneso.me/inter1inter2root1.pem' # chain from intermediate cert to root cert (do not include the server certificate itself)
	TIMEOUT = 10

	def __init__(self, companion):
		super().__init__(companion, Connection.HEARTBEAT_DURATION)

	# see ConnectionBase
	async def send(self, dict):
		# https://docs.aiohttp.org/en/stable/client_quickstart.html
		# https://stackoverflow.com/q/41701791
		logging.info(f'sending {dict}')
		tls = ssl.create_default_context()
		#tls = ssl.create_default_context(cafile=Connection.SERVER_CERT)
		tls.load_cert_chain(Connection.DRONE_CERT, Connection.DRONE_PRIVATE_KEY)
		connector = aiohttp.TCPConnector(ssl_context=tls)
		timeout = aiohttp.ClientTimeout(total=Connection.TIMEOUT)
		async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
			try:
				async with session.request('POST', Connection.URL, json=dict) as r:
					if r.ok:
						json_body = await r.json()
						logging.info(f'received reply {json_body}')
						self.handle_response(json_body)
					else:
						logging.warning(f'received bad reply: {r.status}')
			except aiohttp.ClientConnectionError as e:
				logging.warning(f'connection error {e}')
				return False
			except asyncio.exceptions.TimeoutError as e:
				logging.warning(f'timeout error {e}')
				return False
		return True
