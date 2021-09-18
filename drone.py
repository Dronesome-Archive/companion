import asyncio

import mavsdk
from haversine import haversine

import mission
from mav_value import MavValue
import message_type
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

        # status
        self.status = None
        self.current_mission = None
        self.new_mission = None
        self.task = None

    # return True if drone successfully landed on the pad; return False if landing failed (e.g. pad not found)
    async def try_landing(self):
        # TODO: Alex, hier integrieren
        pass

    # set self.task to new task if status change is valid
    def set_status(self, new):

        # check if change is valid
        if self.status == new:
            log.warn(new.__name__, 'same as old status')
            return False
        if (
            (new == self.status_idle and self.status not in [self.status_landing, self.status_updating]) or
            (new == self.status_updating and self.status not in [self.status_idle]) or
            (new == self.status_en_route and self.status not in [self.status_updating]) or
            (new == self.status_landing and self.status not in [self.status_en_route, self.status_returning]) or
            (new == self.status_returning and self.status not in [self.status_en_route, self.status_landing]) or
            (new == self.status_emergency_landing and self.status not in [self.status_en_route, self.status_landing, self.status_returning]) or
            (new == self.status_crashed and self.status not in [self.status_emergency_landing])
        ):
            log.warn('status change from', self.status.__name__, 'to', new.__name__, 'rejected')
            return False

        # change status
        log.info('status change from', self.status.__name__, 'to', new.__name__)
        self.status = new
        if self.task is not None:
            self.task.cancel()
        self.task = asyncio.create_task(new)
        self.server.queue_message(message_type.Outbound.STATUS_UPDATE, new.__name__)
        return True

    ####################################################################################################################
    # SERVER CONNECTION
    ####################################################################################################################

    # continuously send position and battery values
    async def send_heartbeat(self):
        while True:
            if self.position.val and self.battery.val:
                self.server.queue_message(message_type.Outbound.HEARTBEAT, {
                    'pos': [self.position.val.latitude_deg, self.position.val.longitude_deg],
                    'battery': self.battery.val.remaining_percent
                })
            await asyncio.sleep(Drone.HEARTBEAT_DELAY)

    # handle messages incoming from the server
    async def server_consume(self):
        while True:  # async for don't work w/ asyncio.Queue :(
            msg = await self.server.inbox.get()
            if msg['type'] == message_type.Inbound.EMERGENCY_LAND.value:
                self.set_status(self.status_emergency_landing)
            elif msg['type'] == message_type.Inbound.RETURN.value:
                self.set_status(self.status_returning)
            elif msg['type'] == message_type.Inbound.UPDATE.value:
                self.new_mission = mission.Mission(msg['body'], self.battery.val.remaining_percent)
                if not self.set_status(self.status_updating):
                    self.server.queue_message(message_type.Outbound.MISSION_UPDATE, {
                        'action': 'rejected',
                        'mission_id': self.new_mission.id,
                        'port_id': 0
                    })

    ####################################################################################################################
    # STATUS TASKS
    ####################################################################################################################

    # disarm and wait
    async def status_idle(self):
        await self.mav.action.disarm()

    # accept or reject self.new_mission
    async def status_updating(self):
        current_pos = [self.position.val.latitude_deg, self.position.val.longitude_deg]
        start_dist_km = haversine(current_pos, self.new_mission.start.pos)
        if start_dist_km > Drone.MAX_START_DIST_KM or self.battery.val < Drone.MIN_BATTERY_CHARGE:
            log.warn('new mission rejected', self.new_mission.id)
            self.server.queue_message(message_type.Outbound.MISSION_UPDATE, {
                'action': 'rejected',
                'mission_id': self.new_mission.id,
                'port_id': 0
            })
            self.set_status(self.status_returning)
        else:
            log.info('new mission', self.new_mission.id)
            self.current_mission = self.new_mission
            self.server.queue_message(message_type.Outbound.MISSION_UPDATE, {
                'action': 'accepted',
                'mission_id': self.current_mission.id,
                'port_id': 0
            })
            self.set_status(self.status_en_route)

    # fly self.current_mission and try landing when finished
    async def status_en_route(self):
        mission_plan = mavsdk.mission.MissionPlan(self.current_mission.get_items())
        await self.mav.mission.set_return_to_launch_after_mission(False)
        await self.mav.mission.upload_mission(mission_plan)
        await self.mav.action.arm()
        await self.mav.mission.start_mission()
        async for progress in self.mav.mission.mission_progress():
            if progress.current == progress.total:
                self.set_status(self.status_landing)

    # attempt to land and handle failure
    async def status_landing(self):
        if await self.try_landing():
            self.server.queue_message(message_type.Outbound.MISSION_UPDATE, {
                'action': 'landed',
                'mission_id': self.current_mission.id,
                'port_id': self.current_mission.goal.id
            })
            self.set_status(self.status_idle)
        elif not self.current_mission.cancelled:
            log.warn('landing failed, returning')
            self.set_status(self.status_returning)
        else:
            log.warn('landing failed, performing emergency landing')
            self.set_status(self.status_emergency_landing)

    # reverse self.current_mission, fly and land
    async def status_returning(self):
        if (self.current_mission.batteryStart - self.battery.val) * Drone.BATTERY_DRAIN_MULTIPLIER > self.battery.val:
            # abort if battery charge will be insufficient
            log.warn('not enough battery charge, performing emergency landing')
            self.set_status(self.status_emergency_landing)
        else:
            # reverse mission
            self.current_mission.cancelled = True
            self.current_mission.start, self.current_mission.goal = self.current_mission.goal, self.current_mission.start
            self.current_mission.waypoints.reverse()

            # start at closest waypoint
            distances = [haversine(self.position, (i.latitude_deg, i.longitude_deg)) for i in self.current_mission.getItems()]
            index_closest = distances.index(min(distances))
            mission_plan = mavsdk.mission.MissionPlan(self.current_mission.getItems()[index_closest:])
            await self.mav.current_mission.clear_mission()
            await self.mav.current_mission.set_return_to_launch_after_mission(False)
            await self.mav.current_mission.upload_mission(mission_plan)
            await self.mav.current_mission.start_mission()
            async for progress in self.mav.mission.mission_progress():
                if progress.current == progress.total:
                    self.set_status(self.status_landing)

    # fuck it, we landing
    async def status_emergency_landing(self):
        await self.mav.land()
        self.set_status(self.status_crashed)

    # when emergency landing is completed, notify server and keep calm
    async def status_crashed(self):
        log.warn('crashed')
        self.server.queue_message(message_type.Outbound.MISSION_UPDATE, {
            'action': 'crashed',
            'mission_id': 0,
            'port_id': 0
        })
