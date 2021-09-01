from mavsdk.mission import MissionItem
from port import Port


# equivalent to mavsdk.mission: one flight, from takeoff to landed
class Mission:

	RELATIVE_ALTITUDE = 30
	SPEED = 10
	ACCEPTANCE_RADIUS = 10

	# construct Mission instance from an HTTP response
	def __init__(self, raw, battery):
		self.id = raw['id']
		self.start = Port(raw['start']['id'], (raw['start']['pos'][0], raw['start']['pos'][1]))
		self.waypoints = [(pos[0], pos[1]) for pos in raw['waypoints']]
		self.goal = Port(raw['goal']['id'], (raw['goal']['pos'][0], raw['goal']['pos'][1]))
		self.batteryStart = battery

	# get list of mavsdk.mission.MissionItem according to self.waypoints
	def get_items(self):
		items = []

		# TODO: if the drone doesn't rise to the relative altitude right away, add starting waypoint

		# append in-between waypoints
		for pos in self.waypoints:
			items.append(MissionItem(
				pos[0],
				pos[1],
				Mission.RELATIVE_ALTITUDE,
				Mission.SPEED,
				True,
				float('nan'),
				float('nan'),
				MissionItem.CameraAction.NONE,
				float('nan'),
				float('nan'),
				Mission.ACCEPTANCE_RADIUS,
				float('nan')
			))
		
		# append final waypoint
		items.append(MissionItem(
			self.goal.pos[0],
			self.goal.pos[1],
			Mission.RELATIVE_ALTITUDE,
			0,
			False,
			float('nan'),
			float('nan'),
			MissionItem.CameraAction.NONE,
			float('nan'),
			float('nan'),
			Mission.ACCEPTANCE_RADIUS,
			float('nan')
		))

		return items

