import asyncio

import mavsdk
from haversine import haversine

import mission
from mav_value import MavValue
from message_type import ToServer, ToDrone
import log


class Drone:
    # constants
    HEARTBEAT_DELAY = 2
    MAX_START_DIST_KM = 0.05
    MIN_BATTERY_CHARGE = 0.2
    BATTERY_DRAIN_MULTIPLIER = 1.1

    def __init__(self, mav, server):

        # connections
        self.mav = mav
        self.server = server

        # connection tasks
        self.heartbeat = asyncio.create_task(self.send_heartbeat())
        self.server_consumer = asyncio.create_task(self.server_consume())
        self.position = MavValue(self.mav.telemetry.position)
        self.battery = MavValue(self.mav.telemetry.battery)

        # state
        self.state = None
        self.current_mission = None
        self.new_mission = None
        self.task = None
        self.latest_facility = None

    # return True if drone successfully landed on the pad; return False if landing failed (e.g. pad not found)
    async def try_landing(self):
        # TODO: Alex, hier integrieren
        # si si si 
        pass

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
        await self.mav.action.disarm()

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
        mission_plan = mavsdk.mission.MissionPlan(self.current_mission.get_items())
        await self.mav.mission.set_return_to_launch_after_mission(False)
        await self.mav.mission.upload_mission(mission_plan)
        await self.mav.action.arm()
        await self.mav.mission.start_mission()
        async for progress in self.mav.mission.mission_progress():
            if progress.current == progress.total:
                self.set_state(self.state_landing)

    # attempt first landing and handle failure
    async def state_landing(self):
        if await self.try_landing():
            log.info('landed on', self.current_mission.goal.id)
            self.latest_facility = self.current_mission.goal
            self.set_state(self.state_idle)
        else:
            log.warn('landing failed, returning')
            self.set_state(self.state_emergency_returning)

    # attempt second landing and handle failure
    async def state_return_landing(self):
        if await self.try_landing():
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
            mission_plan = mavsdk.mission.MissionPlan(self.current_mission.get_items(True, self.position))
            await self.mav.current_mission.clear_mission()
            await self.mav.current_mission.set_return_to_launch_after_mission(False)
            await self.mav.current_mission.upload_mission(mission_plan)
            await self.mav.current_mission.start_mission()
            async for progress in self.mav.mission.mission_progress():
                if progress.current == progress.total:
                    self.set_state(self.state_return_landing)

    # fuck it, we landing
    async def state_emergency_landing(self):
        await self.mav.land()
        self.set_state(self.state_crashed)

    # when emergency landing is completed, notify server and keep calm
    async def state_crashed(self):
        log.warn('crashed')
        await self.mav.action.disarm()
