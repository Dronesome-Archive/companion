import asyncio
from logging import getLogger
from enum import Enum

import mavsdk
from haversine import haversine

import mission
from mav_value import MavValue
from websocket_connection import MessageType


class Status(Enum):
	IDLE = 0
	EN_ROUTE = 1
	LANDING = 2
	RETURNING = 3
	EMERGENCY_LANDING = 4


class Message(Enum):
	UPDATE = 'update'
	RETURN = 'return'
	EMERGENCY_LAND = 'emergency_land'


class Drone:

	# constants
	HEARTBEAT_DELAY = 2

	def __init__(self, mav, server):

		# connections
		self.mav = mav
		self.server = server

		# connection tasks
		self.heartbeat = asyncio.create_task(self.send_heartbeat())
		self.server_consumer = asyncio.create_task(self.server_consume())
		self.position = MavValue(self.mav.telemetry.position)
		self.battery = MavValue(self.mav.telemetry.battery)

		# status
		self.status = Status.IDLE
		self.mission = None
		self.task = None

	# return false if status change is illegal; else, set self.task to new task
	async def set_status(self, new_status):

		if self.status == new_status:
			# getLogger().warning('Status ' + new_status + ' same as old status')
			return False
		else:
			# status is switched before we can be sure that it is accepted
			old_status = self.status
			self.status = new_status

		# perform specific tasks occurring on status switch
		try:
			if new_status == Status.IDLE and old_status in [Status.LANDING, Status.EMERGENCY_LANDING]:
				if self.task is not None: self.task.cancel()
				self.task = asyncio.create_task(self.mav.action.disarm())
			elif new_status == Status.EN_ROUTE and old_status == Status.IDLE:
				if self.task is not None: self.task.cancel()
				self.task = asyncio.create_task(self.start_new_mission())
			elif new_status == Status.LANDING and old_status in [Status.EN_ROUTE, Status.RETURNING]:
				if self.task is not None: self.task.cancel()
				# TODO: what does cancel_mission_upload do if no mission is being uploaded?
				try:
					await self.mav.cancel_mission_upload()
				except:
					await self.mav.clear_mission()
				self.task = asyncio.create_task(self.try_landing(old_status))
			elif new_status == Status.RETURNING and old_status in [Status.LANDING, Status.EN_ROUTE] and self.mission is not None:
				if self.task is not None: self.task.cancel()
				if old_status == Status.EN_ROUTE:
					try:
						await self.mav.cancel_mission_upload()
					except:
						await self.mav.clear_mission()
				if (self.mission.batteryStart - self.battery.val) * 1.1 > self.battery.val:
					# not enough battery charge to return
					asyncio.create_task(self.set_status(Status.EMERGENCY_LANDING))
					return False
				self.task = asyncio.create_task(self.return_to_start())
			elif new_status == Status.EMERGENCY_LANDING:
				if self.task is not None: self.task.cancel()
				if old_status == Status.EN_ROUTE:
					try:
						await self.mav.cancel_mission_upload()
					except:
						await self.mav.clear_mission()
				self.task = asyncio.create_task(self.mav.land())
			else:
				return False
		except Exception as e:
			# getLogger().warning('Status could not be changed: ', e)
			self.status = old_status
			return False

		self.server.queue_message(MessageType.STATUS_UPDATE, new_status)
		return True

	# attempt to land and handle possible failure
	async def try_landing(self, old_status):
		if old_status == Status.EN_ROUTE:
			if not await self.land():
				await self.set_status(Status.RETURNING)
		elif old_status == Status.RETURNING:
			if not await self.land():
				await self.set_status(Status.EMERGENCY_LANDING)

	# return True if drone successfully landed on the pad; return False if landing failed (e.g. pad not found)
	async def land(self):
		pass

	# GET new mission from server and start the drone
	async def start_new_mission(self):
		self.server.queue_message(MessageType.MISSION_UPDATE, self.mission.id)

		# start new mission
		mission_plan = mavsdk.mission.MissionPlan(self.mission.get_items())
		await self.mav.mission.set_return_to_launch_after_mission(False)
		await self.mav.mission.upload_mission(mission_plan)
		await self.mav.action.arm()
		await self.mav.mission.start_mission()

	# fly back to the current mission's starting point
	async def return_to_start(self):
		# reverse mission
		self.mission.start, self.mission.goal = self.mission.goal, self.mission.start
		self.mission.waypoints.reverse()

		# start at closest waypoint
		distances = [haversine(self.position, (i.latitude_deg, i.longitude_deg)) for i in self.mission.getItems()]
		index_closest = distances.find(min(distances))
		mission_plan = mavsdk.mission.MissionPlan(self.mission.getItems()[index_closest:])
		await self.mav.mission.clear_mission()
		await self.mav.mission.set_return_to_launch_after_mission(False)
		await self.mav.mission.upload_mission(mission_plan)
		await self.mav.mission.start_mission()

	# continuously send position and battery
	async def send_heartbeat(self):
		while True:
			if self.position.val and self.battery.val:
				self.server.queue_message(MessageType.HEARTBEAT, {
					'pos': [self.position.val.latitude_deg, self.position.val.longitude_deg],
					'battery': self.battery.val.remaining_percent
				})
			await asyncio.sleep(Drone.HEARTBEAT_DELAY)

	# handle messages incoming from the server
	async def server_consume(self):
		while True:  # async for don't work w/ asyncio.Queue :(
			msg = await self.server.inbox.get()
			if msg['type'] == Message.EMERGENCY_LAND.value:
				await self.set_status(Status.EMERGENCY_LANDING)
			elif msg['type'] == Message.RETURN.value:
				await self.set_status(Status.RETURNING)
			elif msg['type'] == Message.UPDATE.value:
				self.mission = mission.Mission(msg['body'], self.battery.val.remaining_percent)
				await self.set_status(Status.EN_ROUTE)
