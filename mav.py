import asyncio
import logging

import mavsdk

from mav_base import MavBase
from landing import do_landing

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

	async def init_connection(self):
		# connect
		await self.__mav.connect(system_address='serial:///dev/ttyAMA0')
		async for state in self.__mav.core.connection_state():
			logging.info(f"connection state: {state}")
			if state.is_connected:
				break
		logging.info("connected")

		# use mavlink instead of rc http://docs.px4.io/master/en/advanced_config/parameter_reference.html
		await self.__mav.param.set_param_int('COM_RC_IN_MODE', 2)
		logging.info("changed COM_RC_IN_MODE to 2")

		# calibrate
		logging.info("starting gyroscope calibration")
		async for progress_data in self.__mav.calibration.calibrate_gyro():
			logging.debug(progress_data)
		logging.info("gyroscope calibration finished")
		logging.info("starting board level horizon calibration")
		async for progress_data in self.__mav.calibration.calibrate_level_horizon():
			logging.info(progress_data)
		logging.info("board level calibration finished")

	async def gather_telemetry(self):
		await asyncio.gather(self.__get_battery(), self.__get_pos())

	async def arm(self):
		logging.info("waiting for global position estimate")
		async for health in self.__mav.telemetry.health():
			logging.debug(health)
			if health.is_global_position_ok:
				logging.info("global position estimate ok")
				break
		await self.__mav.action.arm()

	async def execute_mission(self, mission_items):
		mission_plan = mavsdk.mission.MissionPlan(mission_items)
		await self.__mav.mission.set_return_to_launch_after_mission(False)
		await self.__mav.mission.upload_mission(mission_plan)
		await self.arm()
		await self.__mav.mission.start_mission()
		async for progress in self.__mav.mission.mission_progress():
			if progress.current == progress.total:
				return

	async def land(self):
		# await do_landing(**{"mav": self, "mavsdk_system": self.__mav})
		await self.__mav.action.land()

	async def disarm(self):
		await self.__mav.action.disarm()
