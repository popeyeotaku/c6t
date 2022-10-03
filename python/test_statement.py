"""C6T - C version 6 by Troy - Statement Unit Tests"""

import unittest

import statement
from c6tstate import ParseState


class StateTest(unittest.TestCase):
    """Test cases for statements."""

    def test_goto(self):
        """Test goto statements."""
        state = ParseState("{\ngoto foo;\nfoo:\nbar:\ngoto bar;\n\n}")
        state.localscope = True
        statement.statement(state)
        self.assertTrue(state.eof())
        self.assertEqual(
            state.out_ir.splitlines(keepends=False),
            ["name L1", "goto", "L1:L2:name L2", "goto"],
        )
        self.assertEqual(state.errcount, 0)

    def test_retnull(self):
        """Test null returns."""
        state = ParseState("return;\n")
        state.localscope = True
        statement.statement(state)
        self.assertTrue(state.eof())
        self.assertEqual(state.out_ir, "retnull\n")
        self.assertEqual(state.errcount, 0)
