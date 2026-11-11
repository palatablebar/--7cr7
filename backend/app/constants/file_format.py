"""Table file format + compaction strategy enumerations."""
from enum import Enum


class FileFormat(str, Enum):
    PARQUET = "parquet"
    ORC = "orc"


class PlanStrategy(str, Enum):
    FFD_256 = "ffd_256"          # first-fit-decreasing, target size from the table
    FFD_TARGET = "ffd_target"    # same packing, explicit target override


class TableStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
