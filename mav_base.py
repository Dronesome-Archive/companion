class MavBase:

	def __init__(self):
		self.battery = 1.0
		self.pos = [0.0, 0.0]

	async def keep_connected(self): pass

	async def execute_mission(self, mission_items):	pass

	async def land(self): pass

	async def disarm(self): pass
