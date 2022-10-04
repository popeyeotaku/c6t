"""C6T - C version 6 by Troy - Shared Parser State"""

import lexer
import symtab

MAXREGS: int = 3


class C6TCrash(BaseException):
    """The C6T compiler crashed."""


# pylint: disable=too-many-instance-attributes, too-many-public-methods
class ParseState:
    """Shared state for the C6T frontend parser."""

    def __init__(self, source: str) -> None:
        self._lexer = lexer.Tokenizer(source)
        self._peeked: list[lexer.Token] = []
        self.out_ir = ""
        self.errcount = 0
        self.localscope: bool = False
        self.symtab: dict[str, symtab.Symbol] = {}
        self.curstatic = 0
        self.tags: dict[str, symtab.Symbol] = {}
        self.auto_offset: int = 0
        self.usedregs: int = 0
        self.curseg = "text"

    def goseg(self, segment: str) -> str:
        """Go to the given segment, returnig the old one."""
        oldseg = self.curseg
        if segment != oldseg:
            self.pseudo(segment)
            self.curseg = segment
        return oldseg

    def golocal(self) -> None:
        """Enter local state."""
        self.localscope = True
        self.auto_offset = 0
        self.usedregs = 0

    def exitlocal(self) -> None:
        """Exit local state."""
        for table in self.symtab, self.tags:
            for name, symbol in table.copy().items():
                if symbol.undef:
                    assert symbol.local
                    self.error(f"undefined name {name}")
                if symbol.local:
                    del table[name]
        self.localscope = False

    def jmpstatic(self, label: int) -> None:
        """Jump to a static label."""
        assert label > 0
        self.asm("jmp", f"L{label}")

    def brz(self, label: int) -> None:
        """Assemble a brz to a static label."""
        assert label > 0
        self.asm("brz", f"L{label}")

    def defstatic(self, label: int) -> None:
        """Define a static label here."""
        assert label > 0
        self.deflabel(f"L{label}")

    def redef(self, name: str) -> None:
        """Output a redefinition error if the symbol name already exists."""
        if name in self.symtab:
            self.error(f"redefined name {name}")

    def need(self, *labels: str) -> lexer.Token | None:
        """If the next token does not match any label, report an error and
        return None. If it does match a label, return the token.
        """
        if not (match := self.match(*labels)):
            self.error("missing expected token")
            return None
        return match

    def peekmatch(self, *labels: str) -> bool:
        """Return a flag if the next symbol, which is NOT advanced past and IS
        returned to the input stream, matches any of the labels.
        """
        return self.peek().label in labels

    def earlyeof(self) -> None:
        """If we match EOF, crash the compiler."""
        if self.eof():
            self.crash("unexpected end of file")

    def crash(self, msg: str, line: int | None = None) -> None:
        """Issue an error message and crash."""
        self.error(msg, line)
        raise C6TCrash(msg)

    def static(self) -> int:
        """Return the next static label number."""
        self.curstatic += 1
        return self.curstatic

    def error(self, msg: str, line: int | None = None) -> None:
        """Output an error message."""
        if line is None:
            line = self.line()
        print(f"ERROR {self.line()}: {msg}")
        self.errcount += 1

    def line(self) -> int:
        """Return the current line number."""
        return self.peek().line

    def peek(self) -> lexer.Token:
        """Return the next input token, allowing it to be seen again at the
        next self.peek() or next(self) call.
        """
        while not self._peeked:
            self.unsee(next(self))
        return self._peeked[-1]

    def eof(self) -> bool:
        """Return a flag for if we're at end of file or not."""
        return self.peek().label == "eof"

    def __next__(self) -> lexer.Token:
        """Return the next input token."""
        if self._peeked:
            return self._peeked.pop()
        while True:
            try:
                return next(self._lexer)
            except ValueError as error:
                self.error(error.args[0])

    def unsee(self, token: lexer.Token) -> None:
        """Return a token to the input stream."""
        self._peeked.append(token)

    def asm(self, opcode: str, *operands: str) -> None:
        """Append the given IR assembly into the IR text."""
        line = f"{opcode}"
        if operands:
            line += f' {",".join(operands)}'
        self.out_ir += f"{line}\n"

    def deflabel(self, label: str) -> None:
        """Append the label into the IR text so that it is defined at the
        current position.
        """
        self.out_ir += f"{label}:"

    def pseudo(self, opcode: str, *operands: str) -> None:
        """Append the given pseudo-op to the IR text."""
        self.asm(f".{opcode}", *operands)

    def match(self, *labels: str) -> lexer.Token | None:
        """If the next token matches any of the labels, return the matching
        token. Else, return None.
        """
        token = next(self)
        if token.label in labels:
            return token
        self.unsee(token)
        return None
