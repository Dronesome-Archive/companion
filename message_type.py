from enum import Enum


class ToDrone(Enum):
    UPDATE = 'update'
    EMERGENCY_RETURN = 'emergency_return'
    EMERGENCY_LAND = 'emergency_land'


class ToServer(Enum):
    HEARTBEAT = 'heartbeat'
    STATUS_UPDATE = 'status_update'
