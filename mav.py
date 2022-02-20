import asyncio
import mavsdk

from mav_base import MavBase

class Mav(MavBase):
	def __init__(self):
		self.__mav = mavsdk.System()
		self.battery = 1.0 # 0.0 - 1.0
		self.pos = [0.0, 0.0] # lat, lon
	
	async def __get_battery(self):
		async for val in self.__mav.telemetry.battery:
			self.battery = val.remaining_percent

	async def __get_pos(self):
		async for val in self.__mav.telemetry.pos:
			self.pos = [val.latitude_deg, val.longitude_deg]

	async def keep_connected(self):
		await self.__mav.connect(system_address='udp://:14540')
		await self.__mav.param.set_param_int('COM_RC_IN_MODE', 2)
		await asyncio.gather(self.__get_battery, self.__get_pos)

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
