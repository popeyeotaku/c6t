"""C6T - C version 6 by Troy - Statement Unit Tests"""

import unittest

import extdef
from c6tstate import ParseState


class StateTest(unittest.TestCase):
    """Test cases for statements."""

    def dosrc(self, source: list[str], result: list[str]):
        """Given a source and IR output, both in the format of a list of
        strings w/ one line per string, compile the source and assert that
        there were no errors, AND the result matches.
        """
        state = ParseState("\n".join(source))
        extdef.extdef(state)
        self.assertTrue(state.eof())
        self.assertEqual(state.errcount, 0)
        self.assertEqual(state.out_ir.splitlines(keepends=False), result)

    def test_if(self):
        """Test the if statement."""
        source = [
            "foobar(foo, bar)",
            "{",
            "if (foo)",
            "return (bar);",
            "if (bar)",
            "return (foo);",
            "else",
            "return (-1);",
            "}",
        ]
        result = [
            "_foobar:.export _foobar",
            "useregs 0",
            "auto 10",
            "load",
            "brz L1",
            "auto 12",
            "load",
            "ret",
            "L1:auto 12",
            "load",
            "brz L2",
            "auto 10",
            "load",
            "ret",
            "jmp L3",
            "L2:con 65535",
            "ret",
            "L3:retnull",
        ]
        self.dosrc(source, result)
