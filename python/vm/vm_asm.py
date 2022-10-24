"""C6T VM assembler.
"""

import math
import re
import string
from dataclasses import dataclass, field
from enum import Enum, auto

from .vm import OPCODES

RE_NAME = r"[.a-zA-Z_][.a-zA-Z_0-9]*"
RE_LABEL = r"(" + RE_NAME + r"):"
RE_CON = r"[0-9]+"


@dataclass(frozen=True)
class Label:
    """An assembler label."""

    name: str


class HiLo(Enum):
    """Hi or Lo byte."""

    BOTH = auto()
    HI = auto()
    LO = auto()


@dataclass(frozen=True)
class Expr:
    """An expression value."""

    name: str | None
    con: int
    hilo: HiLo = HiLo.BOTH

    def tobytes(self, symtab: dict[str, int]) -> bytes:
        """The raw bytes of the Expr, given the current symbol table."""
        i = self.con
        if self.name:
            i += symtab[self.name]
        bytelen = math.ceil(i.bit_length() / 8) + 1
        ibytes = i.to_bytes(bytelen, "little", signed=True) + bytes(2)
        match self.hilo:
            case HiLo.HI:
                ibytes = bytes([ibytes[1], 0])
            case HiLo.LO:
                ibytes = bytes([ibytes[0], 0])
        return ibytes[:2]


@dataclass
class Segment:
    """A single memory segment."""

    asm: bytes = field(default_factory=bytes)
    symtab: dict[str, int] = field(default_factory=dict)
    curloc: int = 0
    start: int = 0
    end: int = 0


SEGNAMES: tuple[str, ...] = (".text", ".data", ".string", ".bss")


class Assembler:
    """C6T VM assembler."""

    def __init__(self, source: str):
        self.source = source
        self.i = 0
        self.segments: dict[str, Segment] = {name: Segment() for name in SEGNAMES}
        self.segname = ".text"
        self.symtab: dict[str, int] = {}

    @property
    def curseg(self) -> Segment:
        """The current segment."""
        return self.segments[self.segname]

    @property
    def text(self) -> str:
        """The source text from the current position."""
        return self.source[self.i :]

    def skipws(self, *, include_newlines: bool = False) -> None:
        """Skip leading whitespace in self.text."""
        whitespace = string.whitespace
        if not include_newlines:
            whitespace = whitespace.replace("\n", "")
        while self.text and self.text[0] in whitespace:
            self.i += 1

    def match_re(self, pattern: str) -> re.Match | None:
        """If we match the RE pattern at the start of our text, skip past it
        and return the match object. Else, don't skip and return None.
        """
        self.skipws()
        if match := re.match(pattern, self.text):
            self.i += len(match[0])
            return match
        return None

    def matchlit(self, *literals: str) -> str | None:
        """If any of the literals match, skip past the first one matched and
        return it. Else, don't skip and return None.
        """
        self.skipws()
        for lit in literals:
            if self.text.startswith(lit):
                self.i += len(lit)
                return lit
        return None

    def atom(self) -> Label | str | int:
        """Return a singular element."""
        if match := self.match_re(RE_LABEL):
            return Label(match[1])
        if match := self.match_re(RE_NAME):
            return match[0]
        if match := self.match_re(RE_CON):
            return int(match[0])
        raise ValueError("no valid atom")

    def expr(self) -> Expr:
        """Parse an expression."""
        match self.matchlit("<", ">"):
            case ">":
                hilo = HiLo.HI
            case "<":
                hilo = HiLo.LO
            case _:
                hilo = HiLo.BOTH
        expr = self._expr1()
        return Expr(expr.name, expr.con, hilo)

    def _expr1(self) -> Expr:
        """First level expression parsing."""
        expr = self._expr2()
        while operator := self.matchlit("+", "-"):
            expr = self._math(operator, expr, self._expr2())
        return expr

    def _expr2(self) -> Expr:
        """Second level expression parsing."""
        i = self.i
        atom = self.atom()
        if isinstance(atom, str):
            return Expr(atom, 0)
        if isinstance(atom, int):
            return Expr(None, atom)
        self.i = i
        raise ValueError("missing expr atom")

    def _math(self, operator: str, left: Expr, right: Expr) -> Expr:
        """Perform a math operation."""
        if operator == "+":
            if right.name:
                left, right = right, left
        if right.name:
            raise ValueError("illegal positioning of name in an expression")
        match operator:
            case "+":
                con = left.con + right.con
            case "-":
                con = left.con - right.con
            case _:
                raise ValueError(f"bad operator {repr(operator)}")
        if left.name:
            name = left.name
        else:
            name = None
        return Expr(name, con)

    def grabargs(self) -> list[Expr]:
        """Grab multiple arguments."""
        args: list[Expr] = []
        while not self.matchlit("\n"):
            args.append(self.expr())
            if self.matchlit("\n"):
                break
            if not self.matchlit(","):
                raise ValueError("missing comma")
        return args

    @property
    def eof(self) -> bool:
        """Flag for if we're at EOF (only whitespace to EOF)."""
        return len(self.text.strip()) == 0

    def pass1(self) -> None:
        """Compute the symbol table."""
        for segname in self.segments:
            self.segments[segname] = Segment()
        self.segname = ".text"
        while not self.eof:
            self.skipws(include_newlines=True)
            i = self.i
            atom = self.atom()
            if isinstance(atom, Label):
                self.curseg.symtab[atom.name] = self.curseg.curloc
            elif isinstance(atom, str):
                args = self.grabargs()
                if atom in SEGNAMES:
                    self.segname = atom
                match atom:
                    case ".export":
                        pass
                    case ".dc":
                        self.curseg.curloc += len(args)
                    case ".dw":
                        self.curseg.curloc += len(args) * 2
                    case _:
                        self.curseg.curloc += 1 + 2 * len(args)
            else:
                self.i = i
                raise ValueError("bad atom", atom)
        self.symtab.clear()
        start = 0
        for segname in SEGNAMES:
            seg = self.segments[segname]
            seg.start = start
            seg.end = seg.curloc + start
            self.symtab.update({name: i + start for name, i in seg.symtab.items()})
            start = seg.end
        self.symtab["_etext"] = self.segments[".text"].end
        self.symtab["_edata"] = self.segments[".string"].end
        self.symtab["_end"] = self.segments[".bss"].end

    def pass2(self) -> None:
        """Given the symbol table, output all segments."""
        self.i = 0
        self.segname = ".text"
        while not self.eof:
            self.skipws(include_newlines=True)
            i = self.i
            atom = self.atom()
            if isinstance(atom, Label):
                if len(self.curseg.asm) + self.curseg.start != self.symtab[atom.name]:
                    raise ValueError("phase error")
            elif isinstance(atom, str):
                args = self.grabargs()
                match atom:
                    case ".export":
                        pass
                    case ".dc":
                        for arg in args:
                            self.curseg.asm += bytes([arg.tobytes(self.symtab)[0]])
                    case ".dw":
                        for arg in args:
                            self.curseg.asm += arg.tobytes(self.symtab)
                    case _:
                        self.curseg.asm += bytes([OPCODES[atom]])
                        for arg in args:
                            self.curseg.asm += arg.tobytes(self.symtab)
            else:
                self.i = i
                raise ValueError("bad atom")

    def assemble(self) -> bytes:
        """Assemble the source code."""
        self.pass1()
        self.pass2()
        asmbytes: bytes = bytes()
        for segname in SEGNAMES:
            if segname == '.bss':
                continue
            asmbytes += self.segments[segname].asm
        return asmbytes
