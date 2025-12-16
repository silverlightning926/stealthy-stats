from enum import Enum


class SyncType(Enum):
    FULL = "full"  # inactive events, all years
    LIVE = "live"  # active events, current year
    YEAR = "year"  # inactive events, current year
