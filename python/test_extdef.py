"""C6T - C version 6 by Troy - External Definition Parsing"""

import unittest

import util
from c6tstate import ParseState
from extdef import declmods, extdef
from type6 import Type, TypeElem


class FuncTest(unittest.TestCase):
    """Test function definitions."""

    def test_params_locals(self):
        """Test a function definition with parameters and locals."""
        source = ["foobar(foo, bar)", "int *foo;", "{", "return (foo[bar]);", "}"]
        response = [
            "_foobar:.export _foobar",
            "useregs 0",
            "auto 10",
            "load",
            "auto 12",
            "load",
            "con 2",
            "mult",
            "add",
            "load",
            "ret",
            "retnull",
        ]
        self.cmpsrc(source, response)

    def test_func_with_locals(self):
        """Test a function definition with locals, making sure they're at the
        correct positions. Also tests backend output and expressions.
        """
        source = [
            "foo()",
            "{",
            "char bar[10][20];",
            "register i;",
            "static j;",
            "return (bar[i][j]);",
            "}",
        ]
        response = [
            "_foo:.export _foo",
            ".bss",
            "L1:.ds 2",
            ".text",
            "useregs 1",
            "dropstk 200",
            f"auto {util.word(-200)}",
            "reg 0",
            "load",
            "con 20",
            "mult",
            "add",
            "name L1",
            "load",
            "add",
            "cload",
            "ret",
            "retnull",
        ]
        self.cmpsrc(source, response)

    def cmpsrc(self, source: list[str], response: list[str]):
        """Compare the source code to the given response, with each line a
        different element in the list.
        """
        state = ParseState("\n".join(source))
        extdef(state)
        self.assertEqual(state.out_ir.splitlines(keepends=False), response)
        self.assertEqual(state.errcount, 0)


class DataTest(unittest.TestCase):
    """Test data definitions."""

    def test_noinit(self):
        """Test uninitialized data statements."""
        state = ParseState("char foo, bar; char *foobar;")
        extdef(state)
        self.assertEqual(
            state.out_ir.splitlines(keepends=False),
            [".bss", ".common _foo,1", ".common _bar,1", ".common _foobar,2"],
        )
        self.assertEqual(state.errcount, 0)


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
            self.assertEqual(state.errcount, 0)
