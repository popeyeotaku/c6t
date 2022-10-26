"""C6T - C version 6 by Troy - Backend Shared Code"""

from __future__ import annotations

import re
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Type, TypeVar

T = TypeVar("T")

NODES: dict[str, int | Type[Any] | None] = {
    "auto": int,
    "con": int,
    "predec": 2,
    "name": str,
    "preinc": 2,
    "load": 1,
    "call": 2,
    "reg": int,
    "assign": 2,
    "postinc": 2,
    "cload": 1,
    "arg": 2,
    "null": None,
    "sub": 2,
    "logor": 2,
    "ugequ": 2,
    "add": 2,
    "equ": 2,
    "cassign": 2,
    "asnadd": 2,
    "and": 2,
    "rshift": 2,
    "nequ": 2,
    "less": 2,
    "gequ": 2,
    "logand": 2,
    "ucall": 1,
    "lognot": 1,
    'ugreat': 2,
    'mult': 2,
    'casnor': 2,
    'ulequ': 2,
    'div': 2,
    'uless': 2,
    'asnand': 2,
    'or': 2,
    'asnor': 2,
    'asnrshift': 2,
    'lshift': 2,
    'great': 2,
    'lequ': 2,
    'asnmult': 2,
    'neg': 1,
    'asnsub': 2,
}
COMMANDS: dict[str, Type[Any] | None | tuple[Type[Any], ...]] = {
    ".export": str,
    "useregs": int,
    "brz": str,
    "eval": None,
    "jmp": str,
    "retnull": None,
    "ret": None,
    ".text": None,
    ".data": None,
    ".dw": (str, int),
    '.db': (str, int),
    ".bss": None,
    "doswitch": None,
    ".common": (str, int),
    'dropstk': int,
    '.string': None,
    'goto': None,
}

RE_NAME = r"[a-zA-Z_.][.a-zA-Z_0-9]*"
RE_LABEL = r"(" + RE_NAME + r"):"
RE_CON = r"[0-9]+"
RE_MATH = r"[.a-zA-Z_0-9+-]+"


@dataclass(frozen=True)
class Label:
    """C6T backend labels."""

    name: str


@dataclass
class Node:
    """C6T backend nodes."""

    label: str
    children: list[Node] = field(default_factory=list)
    value: Any = None

    def __getitem__(self, index: int) -> Node:
        return self.children[index]


@dataclass
class Command:
    """C6T backend command."""

    label: str
    args: list[Any]


class BackendABC(ABC, Generic[T]):
    """Abstract base class for C6T backends."""

    def __init__(self, source: str) -> None:
        super().__init__()
        self._source = source
        self._i = 0
        self.nodestk: list[Node] = []

    @property
    def source(self) -> str:
        """The IR source for the backend."""
        return self._source

    @property
    def index(self) -> int:
        """The current index into the source."""
        return self._i

    @property
    def text(self) -> str:
        """The IR source from the current index."""
        return self.source[self.index :]

    @property
    def curline(self) -> str:
        """The current text to the end of the current line."""
        try:
            return self.text[: self.text.index("\n")]
        except ValueError:
            return self.text

    def seek(self, i: int, *, relative: bool = True) -> None:
        """Reposition the text index."""
        if relative:
            i += self.index
        self._i = i

    def matchlit(self, *literals, skipws: bool = True) -> str | None:
        """If any of the literals match the current text, seek past it and
        return the first matching literal. Else, don't seek, and reutnr None.

        Skipws will skeep leading whitespace, but not newlines.
        """
        if skipws:
            self._skipws()
        for literal in literals:
            if self.text.startswith(literal):
                self.seek(len(literal))
                return literal
        return None

    def _skipws(self, *, include_newlines=False) -> None:
        """Skip leading whitespace."""
        whitespace = string.whitespace
        if not include_newlines:
            whitespace = whitespace.replace("\n", "")
        while self.text and self.text[0] in whitespace:
            self.seek(1)

    def matchre(self, pattern: str, skipws: bool = True) -> re.Match | None:
        """If we match the regular expression at teh start of our text, skip
        past it and return the match object. Else, return None and don't seek.

        skipws skips leading whitespace, but not newlines.
        """
        if skipws:
            self._skipws()
        if match := re.match(pattern, self.text):
            self.seek(len(match[0]))
            return match
        return None

    def atnl(self, skipws: bool = True) -> bool:
        """Return a flag for if we're at a newline or EOF, without seeking
        past it.

        skipws skips leading whitespace but not newlines.
        """
        if skipws:
            self._skipws()
        if not self.text:
            return True
        return self.text[0] == "\n"

    def grabargs(self) -> list[Any]:
        """Consume arguments from a command line."""
        args = []
        while not self.atnl():
            args.append(self.grabarg())
            if not self.atnl():
                if not self.matchlit(","):
                    raise ValueError(f"missing comma {repr(self.curline)}")
        return args

    def grabarg(self) -> Any:
        """Grab a single argument."""
        if match := self.matchre(RE_CON):
            return int(match[0])
        if match := self.matchre(RE_NAME):
            return str(match[0])
        if match := self.matchre(RE_MATH):
            return str(match[0])
        raise ValueError(f"bad arg {repr(self.curline)}")

    def atom(self) -> Command | Node | Label:
        """Return the next starting element from the source."""
        line = self.curline
        if match := self.matchre(RE_LABEL):
            return Label(match[1])
        if match := self.matchre(RE_NAME):
            label = match[0]
            args = self.grabargs()
            if label in COMMANDS:
                return self.buildcmd(label, args, line)
            if label in NODES:
                return self.buildnode(label, args, line)
        raise ValueError(f"unknown IR {repr(line)}")

    def buildcmd(self, label: str, args: list[Any], line: str) -> Command:
        """Build a command."""
        assert label in COMMANDS
        argtype = COMMANDS[label]
        if argtype is None:
            if args:
                raise ValueError(f"no args supported for command {label}")
        else:
            if any((not isinstance(arg, argtype) for arg in args)):
                raise TypeError(f"arg of bad type {repr(line)}")
        return Command(label, args)

    def buildnode(self, label: str, args: list[Any], line: str) -> Node:
        """Build a node."""
        assert label in NODES
        argtype = NODES[label]
        children: list[Node] = []
        if len(args) > 1:
            raise ValueError(f"too many values for node {label}")
        if args:
            value = args[0]
        else:
            value = None
        if isinstance(argtype, int):
            if value is not None:
                raise ValueError(f"no value for node {label}")
            for _ in range(argtype):
                children.insert(0, self.nodestk.pop())
        elif argtype is None:
            if value is not None:
                raise ValueError(f"no value for node {label}")
        else:
            if not isinstance(value, argtype):
                raise TypeError(f"value of bad type {repr(line)}")
        return Node(label, children, value)

    def process_line(self):
        """Process a single input line."""
        self._skipws(include_newlines=True)
        atom = self.atom()
        if isinstance(atom, Label):
            self.deflab(atom.name)
        elif isinstance(atom, Node):
            self.nodestk.append(atom)
        elif isinstance(atom, Command):
            self.docmd(atom.label, *atom.args)
        if not isinstance(atom, Label):
            if not self.matchlit("\n"):
                raise ValueError("missing expected newline")

    @abstractmethod
    def deflab(self, label: str) -> None:
        """Define a new label."""
        raise NotImplementedError

    @abstractmethod
    def docmd(self, cmd: str, *args: Any) -> None:
        """Process a single command."""
        raise NotImplementedError

    def codegen(self) -> T:
        """Handle all codegen. Raises ValueError if any errors."""
        errors = 0
        self.seek(0, relative=False)
        while self.text:
            try:
                self.process_line()
            except ValueError as exc:
                print("ERROR:", exc)
                errors += 1
            except TypeError as exc:
                print("ERROR:", exc)
                errors += 1
        if self.nodestk:
            print("ERROR:", f"{len(self.nodestk)} nodes left on node stack")
            errors += 1
        if errors:
            raise ValueError(f"codegen errors: {errors}")
        return self.wrapup()

    @abstractmethod
    def wrapup(self) -> T:
        """Return the final return value of the codegen."""
        raise NotImplementedError
