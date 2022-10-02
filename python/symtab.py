"""C6T - C version 6 by Troy - Symbol Table"""

import dataclasses
import enum
import type6


class Storage(enum.Enum):
    """Storage class for a given symbol."""

    AUTO = enum.auto()  # Ironic, ain't it?
    EXTERN = enum.auto()
    STATIC = enum.auto()
    REGISTER = enum.auto()


@dataclasses.dataclass(frozen=True)
class Symbol:
    """A C6T symbol table entry."""

    storage: Storage
    offset: int | str
    type: type6.TypeString
