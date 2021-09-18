from enum import Enum


class Inbound(Enum):
    UPDATE = 'update'
    RETURN = 'return'
    EMERGENCY_LAND = 'emergency_land'


class Outbound(Enum):
    HEARTBEAT = 'heartbeat'
    STATUS_UPDATE = 'status_update'
    MISSION_UPDATE = 'mission_update'
