from enum import Enum


class ToDrone(Enum):
    UPDATE = 'update'
    RETURN = 'return'
    EMERGENCY_LAND = 'emergency_land'


class ToServer(Enum):
    HEARTBEAT = 'heartbeat'
    STATUS_UPDATE = 'status_update'
