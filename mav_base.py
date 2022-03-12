import logging

class MavBase:

	def __init__(self, battery=1.0, pos=[0.0, 0.0]):
		self.battery = battery # 0.0 - 1.0
		self.pos = pos # lat, lon
	
	async def init_connection(self):
		logging.warning("called abstract function")

	async def gather_telemetry(self):
		logging.warning("called abstract function")

	async def execute_mission(self, mission_items):
		logging.warning("called abstract function")

	async def land(self):
		logging.warning("called abstract function")

	async def disarm(self):
		logging.warning("called abstract function")
