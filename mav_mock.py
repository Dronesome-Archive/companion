import asyncio
import logging
from haversine import haversine

from mav_base import MavBase

class Mav(MavBase):
	STARTING_POS = [51.72437634851853, 14.33875342899223]
	SPEED_MS = 40 # m/s

	def __init__(self):
		self.battery = 1.0 # 0.0 - 1.0
		self.pos = Mav.STARTING_POS # lat, lon

	def __flight_step(self, next_item, mission_items):
		pos0 = self.pos
		pos1 = [mission_items[next_item].latitude_deg, mission_items[next_item].longitude_deg]
		d = haversine(pos0, pos1) * 1000
		p = 1.0 if d == 0.0 or Mav.SPEED_MS >= d else Mav.SPEED_MS / d
		logging.info(f"item {next_item:02d}/{len(mission_items):02d} at dist {d:.0f}m")
		self.pos[0] += (pos1[0] - pos0[0]) * p
		self.pos[1] += (pos1[1] - pos0[1]) * p
		return next_item+1 if p == 1.0 else next_item

	async def execute_mission(self, mission_items):
		logging.info('armed')
		i = 0
		logging.info(f"executing { [(item.latitude_deg, item.longitude_deg) for item in mission_items] }")
		while i < len(mission_items):
			await asyncio.sleep(1)
			i = self.__flight_step(i, mission_items)

	async def land(self):
		logging.info('landing')

	async def disarm(self):
		logging.info('disarmed')
