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
		if self.messages_sent == 3:
			res = {
				"type": "update",
				"start": { # labor consectetur elit
					"id": "61631a905c62c1f3e9a38df2",
					"pos": [51.72437634851853, 14.33875342899223]
				},
				"waypoints": [
					[51.728097937217655, 14.326288556332123],
					[51.72754244532547, 14.326364667641977],
					[51.725679793339324, 14.33909214535663]
				],
				"goal": { # praxis dolor amet
					"id": "6162c26c089535c20545116e",
					"pos": [51.72802399574362, 14.325621128053765]
				}
			}
		else:
			res = {
				"type": "none"
			}
		logging.info(f'res {res}')
		self.handle_response(res)
		return True
