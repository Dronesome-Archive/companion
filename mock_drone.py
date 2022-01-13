import asyncio
from time import time

from haversine import haversine

import mission
from message_type import ToServer, ToDrone
import log


class MockValue:
    def __init__(self, val):
        self.val = val

class MockBattery:
    def __init__(self, percent):
        self.remaining_percent = percent

class MockPosition:
    def __init__(self, lat, lon):
        self.latitude_deg = lat
        self.longitude_deg = lon


class Drone:
    # constants
    HEARTBEAT_DELAY = 2
    MAX_START_DIST_KM = 0.05
    MIN_BATTERY_CHARGE = 0.2
    BATTERY_DRAIN_MULTIPLIER = 1.1

    # mock
    STARTING_POSITION = MockPosition(51.75548871014251, 14.337482007009129)
    SPEED = 20 # m/s
    LANDING_SUCCESS = True
    RETURN_LANDING_SUCCESS = True

    def __init__(self, mav, server):

        # connections
        self.server = server

        # connection tasks
        self.heartbeat = asyncio.create_task(self.send_heartbeat())
        self.server_consumer = asyncio.create_task(self.server_consume())
        self.position = MockValue(Drone.STARTING_POSITION)
        self.battery = MockValue(MockBattery(1.0))

        # state
        self.state = None
        self.current_mission = None
        self.new_mission = None
        self.task = None
        self.latest_facility = None

    # set self.task to new task if state change is valid
    def set_state(self, new):

        # check if change is valid
        if self.state == new:
            log.warn(new.__name__, 'same as old state')
            return False
        if (
            (new == self.state_idle and self.state not in [self.state_landing, self.state_updating]) or
            (new == self.state_updating and self.state not in [self.state_idle]) or
            (new == self.state_en_route and self.state not in [self.state_updating]) or
            (new == self.state_landing and self.state not in [self.state_en_route]) or
            (new == self.state_return_landing and self.state not in [self.state_emergency_returning]) or
            (new == self.state_emergency_returning and self.state not in [self.state_en_route, self.state_landing]) or
            (new == self.state_emergency_landing and self.state not in [self.state_en_route, self.state_landing, self.state_emergency_returning]) or
            (new == self.state_crashed and self.state not in [self.state_emergency_landing])
        ):
            log.warn('state change from', self.state.__name__, 'to', new.__name__, 'rejected')
            return False

        # change state
        log.info('state change from', self.state.__name__, 'to', new.__name__)
        self.state = new
        if self.task is not None:
            self.task.cancel()
        self.task = asyncio.create_task(new)
        self.server.queue_message(ToServer.STATE_UPDATE, {
            'state': new.__name__[6:],
            'latest_facility_id': self.latest_facility.id if self.latest_facility else 0,
            'goal_facility_id': self.current_mission.goal.id if self.current_mission else 0
        })
        return True

    ####################################################################################################################
    # MOCK
    ####################################################################################################################

    def mock_flight(self, i, start, reverse):
        pos0 = self.current_mission.waypoints[i]
        pos1 = self.current_mission.waypoints[i-1] if reverse else self.current_mission.waypoints[i+1]
        d = haversine(pos0, pos1) * 1000
        t = max(0.1, time() - start)
        p = min(1.0, d / (Drone.SPEED * t))
        self.position.val.latitude_deg = pos0[0] + (pos1[0] - pos0[0]) * p
        self.position.val.longitude_deg = pos0[1] + (pos1[1] - pos0[1]) * p

        if (p == 1.0):
            i += -1 if reverse else 1
            start = time()
        
        return (i, start)

    ####################################################################################################################
    # SERVER CONNECTION
    ####################################################################################################################

    # continuously send position and battery values
    async def send_heartbeat(self):
        while True:
            if self.position.val and self.battery.val:
                self.server.queue_message(ToServer.HEARTBEAT, {
                    'pos': [self.position.val.latitude_deg, self.position.val.longitude_deg],
                    'battery': self.battery.val.remaining_percent
                })
            await asyncio.sleep(Drone.HEARTBEAT_DELAY)

    # we can silently ignore orders from the server if they're stupid
    async def server_consume(self):
        while True:  # async for don't work w/ asyncio.Queue :(
            msg = await self.server.inbox.get()
            if msg.msg_type == ToDrone.EMERGENCY_LAND:
                self.set_state(self.state_emergency_landing)
            elif msg.msg_type == ToDrone.EMERGENCY_RETURN:
                self.set_state(self.state_emergency_returning)
            elif msg.msg_type == ToDrone.UPDATE and self.state == self.state_idle:
                self.new_mission = mission.Mission(msg.content, self.battery.val.remaining_percent)
                self.set_state(self.state_updating)

    ####################################################################################################################
    # STATE TASKS
    ####################################################################################################################

    # disarm and wait
    async def state_idle(self):
        return

    # go en_route on self.new_mission or just stay idle if it's bullshit
    async def state_updating(self):
        current_pos = [self.position.val.latitude_deg, self.position.val.longitude_deg]
        start_dist_km = haversine(current_pos, self.new_mission.start.pos)
        if start_dist_km > Drone.MAX_START_DIST_KM or self.battery.val.remaining_percent < Drone.MIN_BATTERY_CHARGE:
            log.warn('new mission rejected', self.new_mission.id)
            self.set_state(self.state_idle)
        else:
            log.info('new mission', self.new_mission.id)
            self.current_mission = self.new_mission
            self.set_state(self.state_en_route)

    # arm drone, fly self.current_mission and try landing when finished
    async def state_en_route(self):
        i = 0
        start = time()
        while self.mission_item_index < len(self.current_mission.waypoints):
            await asyncio.sleep(1)
            i = self.mock_flight(i, start, False)
        self.set_state(self.state_landing)

    # attempt first landing and handle failure
    async def state_landing(self):
        if Drone.LANDING_SUCCESS:
            log.info('landed on', self.current_mission.goal.id)
            self.latest_facility = self.current_mission.goal
            self.set_state(self.state_idle)
        else:
            log.warn('landing failed, returning')
            self.set_state(self.state_emergency_returning)

    # attempt second landing and handle failure
    async def state_return_landing(self):
        if Drone.RETURN_LANDING_SUCCESS:
            log.info('landed on', self.current_mission.goal.id)
            self.latest_facility = self.current_mission.goal
            self.set_state(self.state_idle)
        else:
            log.warn('landing failed, performing emergency landing')
            self.set_state(self.state_emergency_landing)

    # reverse self.current_mission, fly and land
    async def state_emergency_returning(self):
        if (self.current_mission.batteryStart - self.battery.val.remaining_percent) * Drone.BATTERY_DRAIN_MULTIPLIER > self.battery.val:
            # abort if battery charge will be insufficient
            log.warn('not enough battery charge, performing emergency landing')
            self.set_state(self.state_emergency_landing)
        else:
            i = len(self.current_mission.waypoints) - 1
            start = time()
            while self.mission_item_index > 0:
                await asyncio.sleep(1)
                i, start = self.mock_flight(i, start, True)
            self.set_state(self.state_return_landing)

    # fuck it, we landing
    async def state_emergency_landing(self):
        await asyncio.sleep(10)
        self.set_state(self.state_crashed)

    # when emergency landing is completed, notify server and keep calm
    async def state_crashed(self):
        log.warn('crashed')
