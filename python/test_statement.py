"""C6T - C version 6 by Troy - Statement Unit Tests"""

import unittest

from c6tstate import ParseState
import statement


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
            ["\tname L1", "\tgoto", "L1:", "L2:", "\tname L2", "\tgoto"],
        )
