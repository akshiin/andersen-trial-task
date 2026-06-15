from enum import Enum


class NetworkType(str, Enum):
    IN_NETWORK = "In-Network"
    OUT_OF_NETWORK = "Out-of-Network"
