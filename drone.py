import asyncio
import logging

import mavsdk
from haversine import haversine

from message_type import ToServer


class Drone:
    # constants
    MAX_START_DIST_KM = 0.05
    MIN_BATTERY_CHARGE = 0.2
    BATTERY_DRAIN_MULTIPLIER = 1.1

    def __init__(self, mav):
        self.__state = self.state_idle
        self.__current_mission = None
        self.new_mission = None
        self.__task = None
        self.__latest_facility = None
        self.outbox = asyncio.Queue()
        self.mav = mav

    # return True if drone successfully landed on the pad; return False if landing failed (e.g. pad not found)
    async def __try_landing(self):
        return self.mav.land()

    def __handle_task_result(self, task):
        # https://quantlane.com/blog/ensure-asyncio-task-exceptions-get-logged/
        try:
            task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            logging.exception(f'Exception in task {task}:')

    # set self.task to new task if state change is valid
    def set_state(self, new):

        # check if change is valid
        if self.__state == new:
            logging.warning(f'{new.__name__} same as old state')
            return False
        if (
            (new == self.state_idle and self.__state not in [self.state_landing, self.state_updating]) or
            (new == self.state_updating and self.__state not in [self.state_idle]) or
            (new == self.state_en_route and self.__state not in [self.state_updating]) or
            (new == self.state_landing and self.__state not in [self.state_en_route]) or
            (new == self.state_return_landing and self.__state not in [self.state_emergency_returning]) or
            (new == self.state_emergency_returning and self.__state not in [self.state_en_route, self.state_landing]) or
            (new == self.state_emergency_landing and self.__state not in [self.state_en_route, self.state_landing, self.state_emergency_returning]) or
            (new == self.state_crashed and self.__state not in [self.state_emergency_landing])
        ):
            logging.warning(f'state change from {self.__state.__name__} to {new.__name__} rejected')
            return False

        # change state
        logging.info(f'state change from {self.__state.__name__} to {new.__name__}')
        self.__state = new
        if self.__task:
            self.__task.cancel()
        self.__task = asyncio.create_task(self.__state())
        self.__task.add_done_callback(self.__handle_task_result)
        if not self.outbox.empty():
            self.outbox.get_nowait()
        self.outbox.put_nowait({
            'type': ToServer.STATE_UPDATE.value,
            'state': new.__name__[6:],
            'latest_facility_id': self.__latest_facility.id if self.__latest_facility else None,
            'goal_facility_id': self.__current_mission.goal.id if self.__current_mission else None
        })
        return True


    ####################################################################################################################
    # STATE TASKS
    ####################################################################################################################

    # disarm and wait
    async def state_idle(self):
        await self.mav.disarm()

    # go en_route on self.new_mission or just stay idle if it's bullshit
    async def state_updating(self):
        start_dist_km = haversine(self.mav.pos, self.new_mission.start.pos)
        if start_dist_km > Drone.MAX_START_DIST_KM or self.mav.battery < Drone.MIN_BATTERY_CHARGE:
            logging.warning(f'new mission rejected')
            self.set_state(self.state_idle)
        else:
            logging.info(f'new mission')
            self.__current_mission = self.new_mission
            self.set_state(self.state_en_route)

    # arm drone, fly self.current_mission and try landing when finished
    async def state_en_route(self):
        await self.mav.execute_mission(self.__current_mission.get_items())
        self.set_state(self.state_landing)

    # attempt first landing and handle failure
    async def state_landing(self):
        if await self.__try_landing():
            logging.info(f'landed on {self.__current_mission.goal.id}')
            self.__latest_facility = self.__current_mission.goal
            self.set_state(self.state_idle)
        else:
            logging.warning('landing failed, returning')
            self.set_state(self.state_emergency_returning)

    # attempt second landing and handle failure
    async def state_return_landing(self):
        if await self.__try_landing():
            logging.info(f'landed on {self.__current_mission.goal.id}')
            self.__latest_facility = self.__current_mission.goal
            self.set_state(self.state_idle)
        else:
            logging.warning('landing failed, performing emergency landing')
            self.set_state(self.state_emergency_landing)

    # reverse self.current_mission, fly and land
    async def state_emergency_returning(self):
        battery_used = self.__current_mission.batteryStart - self.mav.battery
        if battery_used * Drone.BATTERY_DRAIN_MULTIPLIER > self.mav.battery:
            # abort if battery charge will be insufficient
            logging.warning('not enough battery charge, performing emergency landing')
            self.set_state(self.state_emergency_landing)
        else:
            await self.mav.execute_mission(self.__current_mission.get_items(True, self.mav.pos))
            self.set_state(self.state_return_landing)

    # fuck it, we landing
    async def state_emergency_landing(self):
        await self.mav.land()
        self.set_state(self.state_crashed)

    # when emergency landing is completed, notify server and keep calm
    async def state_crashed(self):
        logging.warning('crashed')
        await self.mav.action.disarm()
