from enum import Enum
from mavsdk.mission import MissionItem
import port

class Status(Enum):
	STARTING = 0
	FLYING = 1
	LANDING = 2
	FINISHED = 3

# equivalent to mavsdk.mission: One flight, from takeoff to landed
class Mission:

	relativeAltitude = 30
	speed = 10

	# construct Mission instance from an HTTP response
	def __init__(self, raw, battery):
		self.id = raw['id'],
		self.waypoints = [(coords[0], coords[1]) for coords in raw['waypoints']],
		self.goal = Port(raw['port']['id'], (raw['port']['coords'][0], raw['port']['coords'][1])),
		self.batteryStart = battery
		self.status = Status.STARTING

	# get list of mavsdk.mission.MissionItem according to self.waypoints
	def getItems():
		items = []

		# append in-between waypoints
		for coords in self.waypoints:
			items.append(MissionItem(
				coords[0],
				coords[1],
				relativeAltitude,
				speed,
				True,
				float('nan'),
				float('nan'),
				MissionItem.CameraAction.NONE,
				float('nan'),
				float('nan')
			))
		
		# append final waypoint
		items.append(MissionItem(
			self.goal.coords[0],
			self.goal.coords[1],
			relativeAltitude,
			0,
			False,
			float('nan'),
			float('nan'),
			MissionItem.CameraAction.NONE,
			float('nan'),
			float('nan')
		))

		return items

