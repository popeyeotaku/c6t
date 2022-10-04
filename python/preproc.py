"""C6T - C version 6 by Troy - Preprocessor
"""

import pathlib
import re
from collections import deque
from typing import Iterable, Iterator

RE_DEFINE = r"^#\s*define\s+([a-zA-Z_][a-zA-Z_0-9]*)\s+(.*?)\s*$"
RE_INCLUDE = r'^#\s*include\s+"(.*?)"\s*$'
RE_COMMENT = r"/\*.*?\*/"
RE_REPLACE = r"([a-zA-Z_][a-zA-Z_0-9]*)|(.)"


class Source(Iterable[str]):
    """Returns lines from the source code, allowing for include insertion."""

    def __init__(self, source: str):
        self._lines = deque(source.splitlines(keepends=False))
        self._include: deque[str] = deque()
        self._line = 0

    def __iter__(self) -> Iterator[str]:
        return self

    @property
    def in_include(self) -> bool:
        """A flag for if we're inside an include or not."""
        return bool(self._include)

    def __next__(self) -> str:
        if self.in_include:
            return self._include.popleft()
        if self._lines:
            self._line += 1
            return self._lines.popleft()
        raise StopIteration

    def include(self, pathstr: str) -> None:
        """Include the file."""
        if self.in_include:
            error("already inside an include", self._line)
            return
        path = pathlib.Path(pathlib.PurePosixPath(pathstr))
        if not path.exists():
            error(f"include {repr(pathstr)} does not exist", self._line)
            return
        text = "@" + path.read_text("ascii") + "\n@"
        self._include = deque(text.splitlines(keepends=False))


def error(msg: str, line: int) -> None:
    """Output an error message."""
    print(f"ERROR {line}: {msg}")


def preproc(source: str) -> str:
    """Perform C6T preprocessing on the source code.

    This will only modify the source if the first character is a '#'.

    Any line starting with a '#' is output as a blank line, and - after
    skipping whitespace past the '#' - if one of two command names is
    indicated, a preprocessor operation takes place.

    Commands:
        # define NAME TEXT - anywhere the NAME is encountered in the text, it
                             is replaced by the corresponding TEXT, after
                             replacing comments in the TEXT with a single
                             space and placing an additional space on either
                             side of it.
        # include "NAME"   - the entire text of the file NAME is placed
                             inline. Macro expansions and defines go on
                             as usual inside it, but includes inside an
                             include are illegal - INCLUDES ARE ONLY ONE LEVEL
                             DEEP!! The '@' character is output on either side
                             of it to keep C6T from counting line numbers
                             inside.
    """
    if source[0] != "#":
        return source

    macros: dict[str, str] = {}

    srciter = Source(source)
    preproced: list[str] = []

    for line in srciter:
        if line.startswith("#"):
            preproced.append("")  # This should probably go AFTER an include
            if match := re.match(RE_DEFINE, line):
                macros[match[1]] = mactext(match[2])
            elif match := re.match(RE_INCLUDE, line):
                srciter.include(match[1])
            else:
                pass
        else:
            preproced.append(macreplace(line, macros))

    return "\n".join(preproced)


def mactext(text: str) -> str:
    """Replace comments with spaces and place a space character on either
    side, returning the modified text.
    """
    return " " + re.sub(RE_COMMENT, " ", text) + " "


def macreplace(line: str, macros: dict[str, str]) -> str:
    """Replace all macros."""
    replaced = ""
    for match in re.finditer(RE_REPLACE, line, re.DOTALL):
        if match[1] is None:
            assert match[2] is not None
            replaced += match[2]
        else:
            if match[1] in macros:
                replaced += macros[match[1]]
            else:
                replaced += match[1]
    return replaced
