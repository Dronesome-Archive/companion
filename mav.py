import asyncio
import logging

import mavsdk

from mav_base import MavBase

class Mav(MavBase):
	def __init__(self):
		self.__mav = mavsdk.System()
		super().__init__()
	
	async def __get_battery(self):
		async for val in self.__mav.telemetry.battery():
			logging.info(f"val: {val}")
			self.battery = val.remaining_percent
			logging.info(f"new battery: {self.battery}")

	async def __get_pos(self):
		async for val in self.__mav.telemetry.position():
			logging.info(f"val: {val}")
			self.pos = [val.latitude_deg, val.longitude_deg]
			logging.info(f"new pos: {self.pos}")

	async def keep_connected(self):
		await self.__mav.connect(system_address='serial:///dev/ttyAMA0')
		async for state in self.__mav.core.connection_state():
			logging.info(f"connection state: {state}")
			if state.is_connected:
				break
		logging.info("connected!")
		await self.__mav.param.set_param_int('COM_RC_IN_MODE', 2)
		await asyncio.gather(self.__get_battery(), self.__get_pos())

	async def execute_mission(self, mission_items):
		mission_plan = mavsdk.mission.MissionPlan(mission_items)
		await self.__mav.mission.set_return_to_launch_after_mission(False)
		await self.__mav.mission.upload_mission(mission_plan)
		await self.__mav.action.arm()
		await self.__mav.mission.start_mission()
		async for progress in self.__mav.mission.mission_progress():
			if progress.current == progress.total:
				return

	async def land(self):
		await self.__mav.land()

	async def disarm(self):
		await self.__mav.action.disarm()
