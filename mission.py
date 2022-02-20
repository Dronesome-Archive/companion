from haversine import haversine

from mavsdk.mission import MissionItem
from facility import Facility


# equivalent to mavsdk.mission: one flight, from takeoff to landed
class Mission:
    RELATIVE_ALTITUDE = 30
    SPEED = 10
    ACCEPTANCE_RADIUS = 10

    # construct Mission instance from an HTTP response
    def __init__(self, raw, battery):
        self.start = Facility(raw['start']['id'], (raw['start']['pos'][0], raw['start']['pos'][1]))
        self.waypoints = [(pos[0], pos[1]) for pos in raw['waypoints']]
        self.goal = Facility(raw['goal']['id'], (raw['goal']['pos'][0], raw['goal']['pos'][1]))
        self.batteryStart = battery

    # create mavsdk.mission.MissionItem with default values
    def mission_item(self, pos, fly_through):
        return MissionItem(
            pos[0],
            pos[1],
            Mission.RELATIVE_ALTITUDE,
            Mission.SPEED if fly_through else 0,
            fly_through,
            float('nan'),
            float('nan'),
            MissionItem.CameraAction.NONE,
            float('nan'),
            float('nan'),
            Mission.ACCEPTANCE_RADIUS,
            float('nan')
        )

    # get list of mavsdk.mission.MissionItem according to self.waypoints
    def get_items(self, reverse=False, start_pos=None):
        if not start_pos:
            start_pos = self.start.pos

        if reverse:
            start = self.goal
            between = reversed(self.waypoints)
            goal = self.start
        else:
            start = self.start
            between = self.waypoints
            goal = self.goal

        items = [self.mission_item(start.pos, True)]
        for pos in between:
            items.append(self.mission_item(pos, True))
        items.append(self.mission_item(goal.pos, False))
        distances = [haversine(start_pos, [item.latitude_deg, item.longitude_deg]) for item in items]
        index_closest = distances.index(min(distances))
        return items[index_closest:]
