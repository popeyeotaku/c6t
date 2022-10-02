"""C6T - C version 6 by Troy - External Definition Parsing"""

import unittest

from c6tstate import ParseState
from extdef import declmods
from type6 import Type, TypeElem


class DeclTest(unittest.TestCase):
    """Tests declarator parsing."""

    def test_fncpoint(self):
        """Test pointer to function and function returning pointer."""
        for testsrc, testname, testmods, testargs in (
            (
                "(*foo)(bar)",
                "foo",
                [TypeElem(Type.POINT), TypeElem(Type.FUNC)],
                ["bar"],
            ),
            ("*foo(bar)", "foo", [TypeElem(Type.FUNC), TypeElem(Type.POINT)], ["bar"]),
        ):
            mods: list[TypeElem] = []
            state = ParseState(testsrc)
            name, args = declmods(state, mods)
            self.assertTrue(state.eof())
            self.assertEqual(name, testname)
            self.assertEqual(args, testargs)
            self.assertEqual(testmods, mods)
