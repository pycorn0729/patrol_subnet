from enum import Enum


class Constants:
    RESPONSE_TIME_HALF_SCORE: int = 2
    INFLECTION_POINT = 1000
    STEEPNESS = 0.005
    U64_MAX = 2**64 - 1
    LOWER_BLOCK_LIMIT: int = 3014341
    MAX_RESPONSE_TIME: int = 12
    DTAO_RELEASE_BLOCK: int = 4920351

class TaskType(Enum):
    HOTKEY_OWNERSHIP = 'HOTKEY_OWNERSHIP'
    COLDKEY_SEARCH = 'COLDKEY_SEARCH'
    PREDICT_ALPHA_SELL = 'PREDICT_ALPHA_SELL'

from typing import NamedTuple

from bittensor import AxonInfo

class Miner(NamedTuple):
    axon_info: AxonInfo
    uid: int

class ValidationException(Exception):
    pass
