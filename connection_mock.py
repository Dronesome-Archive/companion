import logging

from connection_base import ConnectionBase

class Connection(ConnectionBase):
	HEARTBEAT_DURATION = 5

	def __init__(self, companion):
		self.messages_sent = 0
		super().__init__(companion, Connection.HEARTBEAT_DURATION)

	# see ConnectionBase
	async def send(self, dict):
		logging.info(f'sending {dict}')
		self.messages_sent += 1
		if False and self.messages_sent == 3:
			res = {
				"type": "update",
				"start": { # sportplatz, earth route bei alex
					"id": "61631a905c62c1f3e9a38df2",
					"pos": [51.766174004755186, 14.32315204684322]
				},
				"waypoints": [
					[51.766198073946384, 14.32296496276771],
					[51.76611051182717, 14.322954233931839]
				],
				"goal": {
					"id": "6162c26c089535c20545116e",
					"pos": [51.76608685757625, 14.32303604130536]
				}
			}
		else:
			res = {
				"type": "none"
			}
		logging.info(f'res {res}')
		self.handle_response(res)
		return True
