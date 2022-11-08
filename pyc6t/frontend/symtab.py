"""C6T - C version 6 by Troy - Symbol Table"""

from __future__ import annotations

import dataclasses
import enum

from . import type6


class Storage(enum.Enum):
    """Storage class for a given symbol."""

    AUTO = enum.auto()  # Ironic, ain't it?
    EXTERN = enum.auto()
    STATIC = enum.auto()
    REGISTER = enum.auto()
    MEMBER = enum.auto()
    STRUCT = enum.auto()


@dataclasses.dataclass
class Symbol:
    """A C6T symbol table entry."""

    storage: Storage
    offset: int | str
    typestr: type6.TypeString
    local: bool = dataclasses.field(default=False, kw_only=True)
    undef: bool = dataclasses.field(default=False, kw_only=True)


@dataclasses.dataclass(frozen=True)
class FrozenSym:
    """An immutable symbol."""

    storage: Storage
    offset: int | str
    typestr: type6.TypeString
    local: bool
    undef: bool

    @classmethod
    def fromsym(cls, sym: Symbol) -> FrozenSym:
        """Construct a FrozenSym from an existing symbol."""
        return FrozenSym(sym.storage, sym.offset, sym.typestr, sym.local, sym.undef)


SymTypeTuple = (Symbol, FrozenSym)
SymType = Symbol | FrozenSym
