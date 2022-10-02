"""C6T - C version 6 by Troy - Tokenizer."""

import dataclasses
import re
import typing

NAMELEN = 8  # Maximum length of a NAME token (aka an 'identifier')


@dataclasses.dataclass
class Source:
    """Allows advancing through some source text."""

    source: str
    i: int = 0

    @property
    def text(self):
        """The source text from the current position (self.i)."""
        return self.source[self.i :]

    def matchlit(self, *literals: str) -> str | None:
        """Go through each of the given literals. If any literal matches the
        current text, skip past it and return the matched text. Else, skip
        nothing and return None.
        """
        for literal in literals:
            if self.text.startswith(literal):
                self.i += len(literal)
                return literal
        return None

    def matchre(self, pattern: str) -> re.Match[str] | None:
        """Try to match a regular expression pattern. If we do, skip past it
        and return the match object. Else, return None.
        """
        if match := re.match(pattern, self.text):
            self.i += len(match[0])
            return match
        return None

    @property
    def eof(self):
        """A flag for if we're at the end of the text."""
        return self.i >= len(self.source)

    def popchar(self) -> str:
        """Return the character at the top of the text, and skip past it."""
        if self.eof:
            return ""
        char = self.source[self.i]
        self.i += 1
        return char


@dataclasses.dataclass(frozen=True)
class Token:
    """An input lexical token."""

    label: str
    line: int
    value: typing.Any = None


KEYWORDS = {
    "int",
    "char",
    "float",
    "double",
    "struct",
    "auto",
    "extern",
    "register",
    "static",
    "goto",
    "return",
    "sizeof",
    "break",
    "continue",
    "if",
    "else",
    "for",
    "do",
    "while",
    "switch",
    "case",
    "default",
    "entry",
}

OPERATORS = sorted(
    [
        "{",
        "}",
        ";",
        ",",
        "=",
        "=+",
        "=-",
        "=*",
        "=/",
        "=%",
        "=>>",
        "=<<",
        "=&",
        "=^",
        "=|",
        "?",
        ":",
        "||",
        "&&",
        "|",
        "^",
        "&",
        "==",
        "!=",
        "<",
        ">",
        "<=",
        ">=",
        ">>",
        "<<",
        "+",
        "-",
        "*",
        "/",
        "%",
        "!",
        "~",
        "++",
        " --",
        "(",
        ")",
        "[",
        "]",
        ".",
        "->",
    ],
    key=len,
    reverse=True,
)

RE_NAME = r"[a-zA-Z_][a-zA-Z_0-9]*"
RE_FCON = r"([0-9]*\.[0-9]+([eE][+-]?[0-9]+)?)|([0-9]+[eE][+-]?[0-9]+)"
RE_CON = r"[0-9]+"
RE_CHARCON = r"'([^']|(\\'))*'"
RE_STRING = r'"([^"]|(\\"))*"'

# The entry keyword is never used, but was at this time reserved for a
# proposed feature to allow multiple entry points to the same function.


class Tokenizer:
    """Tokenizes some source text."""

    def __init__(self, source: str) -> None:
        self.source = Source(source)
        self.line = 1
        self.countlines = True

    def __iter__(self) -> typing.Iterator[Token]:
        return self

    def _token(self, label: str, value: typing.Any = None) -> Token:
        """Return a token with the current line number set."""
        return Token(label, self.line, value)

    def __next__(self) -> Token:
        self._whitespace()
        if self.source.eof:
            token = self._token("eof")
        elif token := self._name():
            pass
        elif token := self._fcon():
            # Try a float first since otherwise it may be mistaken for a CON.
            pass
        elif token := self._con():
            pass
        elif token := self._operator():
            pass
        elif token := self._charcon():
            pass
        elif token := self._string():
            pass
        else:
            raise ValueError(f"invalid input character {self.source.popchar()}")
        return token

    def _charcon(self) -> Token | None:
        """Try to parse a character constant."""
        raise NotImplementedError

    def _string(self) -> Token | None:
        """Try to parse a string."""
        raise NotImplementedError

    def _name(self) -> Token | None:
        """Try to parse a NAME token."""
        if match := self.source.matchre(RE_NAME):
            name = match[0][:NAMELEN]
            if name in KEYWORDS:
                return self._token(name)
            return self._token("name", name)
        return None

    def _fcon(self) -> Token | None:
        """Try to parse a FCON token."""
        if match := self.source.matchre(RE_FCON):
            return self._token("fcon", float(match[0]))
        return None

    def _con(self) -> Token | None:
        """Try to parse a CON token."""
        if match := self.source.matchre(RE_CON):
            digits = match[0]
            base = 8 if digits[0] == "0" else 10
            num = 0
            for digit in digits:
                num = num * base + int(digit)
            return self._token("con", num)
        return None

    def _operator(self) -> Token | None:
        """Try to parse an operator token."""
        if operator := self.source.matchlit(*OPERATORS):
            return self._token(operator)
        return None

    def _whitespace(self) -> None:
        """Skip leading whitespace."""
        while lit := self.source.matchlit(" ", "\t", "@", "\n", "/*"):
            match lit:
                case "@":
                    # C6T extends the original standard to allow @ as a
                    # character which flips whether we should count source
                    # lines. This is because we do not count line numbers
                    # inside includes.
                    self.countlines = not self.countlines
                case "\n":
                    if self.countlines:
                        self.line += 1
                case "/*":
                    while not self.source.eof and not self.source.matchlit("*/"):
                        char = self.source.popchar()
                        if self.countlines and char == "\n":
                            self.line += 1
                            # Do not count '@' symbols in comments since those
                            # might be used genuinely there.
                            # This also means included files should not end
                            # mid-comment.
                case _:
                    pass
