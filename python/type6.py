"""C6T - C version 6 by Troy - Type System"""

import dataclasses
import enum
import functools
import typing

from typing_extensions import Self


class Type(enum.Enum):
    """A single type string element."""

    INT = enum.auto()
    CHAR = enum.auto()
    FLOAT = enum.auto()
    DOUBLE = enum.auto()
    STRUCT = enum.auto()
    POINT = enum.auto()
    ARRAY = enum.auto()
    FUNC = enum.auto()


SIZED = (Type.STRUCT, Type.ARRAY)
INTEGRAL = (Type.INT, Type.CHAR)
POINTER = (Type.POINT, Type.ARRAY)
FLOATING = (Type.FLOAT, Type.DOUBLE)
SIZES = {
    Type.INT: 2,
    Type.CHAR: 1,
    Type.FLOAT: 4,
    Type.DOUBLE: 8,
    Type.POINT: 2,
    Type.FUNC: 0,
}
BASE = (Type.INT, Type.CHAR, Type.FLOAT, Type.DOUBLE, Type.STRUCT)
MOD = (Type.POINT, Type.ARRAY, Type.FUNC)


@dataclasses.dataclass(frozen=True)
class TypeElem:
    """A single type string element."""

    label: Type
    size: int

    def __init__(self, label: Type, size: int | None = None) -> None:
        object.__setattr__(self, "label", label)
        if self.label in SIZED:
            if size is None:
                raise ValueError("must supply size on sized type")
        else:
            if size is not None and size != SIZES[label]:
                raise ValueError("bad size supplied for non-sized type")
            size = SIZES[label]
        object.__setattr__(self, "size", size)


class TypeString(typing.Sequence[TypeElem]):
    """A string describing a C6T type."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({','.join((repr(elem) for elem in self))})"

    def __init__(self, *elems: TypeElem | Type) -> None:
        self._elems: list[TypeElem] = []
        for elem in elems:
            if isinstance(elem, Type):
                elem = TypeElem(elem)
            self._elems.append(elem)
        if len(self._elems) < 1:
            raise ValueError("must contain at least one TypeElem")
        if self._elems[-1].label not in BASE:
            raise ValueError("last element in TypeString must be base type")
        if any((elem.label not in MOD for elem in self._elems[:-1])):
            raise ValueError("all elements preceeding base type must be mod types")

    def __len__(self) -> int:
        return len(self._elems)

    @typing.overload
    def __getitem__(self, i: slice) -> Self:
        ...

    @typing.overload
    def __getitem__(self, i: typing.SupportsIndex) -> TypeElem:
        ...

    def __getitem__(self, i: slice | typing.SupportsIndex):
        if isinstance(i, slice):
            return self.__class__(*self._elems[i])
        return self._elems[i]

    @functools.cached_property
    def popped(self) -> Self:
        """A copy of the type string with the first element removed."""
        return self[1:]

    @functools.cached_property
    def size(self) -> int:
        """Return the size in bytes of the type string."""
        if self[0].label == Type.ARRAY:
            return self.sizenext * self[0].size
        return self[0].size

    @functools.cached_property
    def sizenext(self) -> int:
        """Return the size in bytes in all elements after the first."""
        return self.popped.size

    @functools.cached_property
    def integral(self) -> bool:
        """Flag for if this is an integral type."""
        return self[0].label in INTEGRAL

    @functools.cached_property
    def floating(self) -> bool:
        """Flag for if this is a floating type."""
        return self[0].label in FLOATING

    @functools.cached_property
    def pointer(self) -> bool:
        """Flag for if this is a pointer type."""
        return self[0].label in POINTER
