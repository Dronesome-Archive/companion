import logging

class MavBase:

	def __init__(self, battery=1.0, pos=[0.0, 0.0]):
		self.battery = battery # 0.0 - 1.0
		self.pos = pos # lat, lon

	async def keep_connected(self):
		logging.error("called abstract function")

	async def execute_mission(self, mission_items):
		logging.error("called abstract function")

	async def land(self):
		logging.error("called abstract function")

	async def disarm(self):
		logging.error("called abstract function")
