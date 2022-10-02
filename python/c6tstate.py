"""C6T - C version 6 by Troy - Shared Parser State"""

import lexer


class ParseState:
    """Shared state for the C6T frontend parser."""

    def __init__(self, source: str) -> None:
        self._lexer = lexer.Tokenizer(source)
        self._peeked: list[lexer.Token] = []
        self.out_ir = ""
        self.errcount = 0

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
        line = f"\t{opcode}"
        if operands:
            line += f'\t{",".join(*operands)}'
        self.out_ir += f"{line}\n"

    def deflabel(self, label: str) -> None:
        """Append the label into the IR text so that it is defined at the
        current position.
        """
        self.out_ir += f"{label}:\t"

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
