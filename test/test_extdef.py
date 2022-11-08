"""C6T - C version 6 by Troy - External Definition Parsing"""

import unittest

from pyc6t.frontend import util
from pyc6t.frontend.c6tstate import ParseState
from pyc6t.frontend.extdef import declmods, extdef
from pyc6t.frontend.type6 import Type, TypeElem


class FuncTest(unittest.TestCase):
    """Test function definitions."""

    def test_datainit(self):
        """Test data initializers."""
        source = [
            'char foo[] "foo", bar[] "bar", *foobar[] { foo, bar };',
            "struct foobar { int foo; struct foobar *bar; };",
            "struct foobar foostk[] { 0, foostk, 1, &foostk[1], 2, &foostk[2], -1 };",
            "int foosize sizeof(foostk);",
            "float ffoo 1; int fbar 2.0;",
        ]
        response = [
            ".data",
            "_foo:.export _foo",
            ".db 102,111,111,0",
            "_bar:.export _bar",
            ".db 98,97,114,0",
            "_foobar:.export _foobar",
            ".dw _foo",
            ".dw _bar",
            "_foostk:.export _foostk",
            ".dw 0",
            ".dw _foostk",
            ".dw 1",
            ".dw _foostk+4",
            ".dw 2",
            ".dw _foostk+8",
            ".dw 65535",
            ".ds 2",
            "_foosize:.export _foosize",
            ".dw 16",
            "_ffoo:.export _ffoo",
            ".df 1",
            "_fbar:.export _fbar",
            ".dd 2.0",
        ]
        self.cmpsrc(source, response)

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

    def cmpsrc(self, source: list[str], response: list[str]):
        """Compare the source code to the given response, with each line a
        different element in the list.
        """
        state = ParseState("\n".join(source))
        extdef(state)
        self.assertEqual(state.out_ir.splitlines(keepends=False), response)
        self.assertEqual(state.errcount, 0)

    def test_struct(self):
        """Test struct type definitions."""
        self.cmpsrc(
            [
                "struct foobar { int foo; struct foobar *bar; };",
                "foobar(foo)",
                "struct foobar *foo;",
                "{",
                "static struct foobar bar;",
                "bar.bar = foo;",
                "bar.foo = foo->bar->foo;",
                "return (sizeof(bar));",
                "}",
            ],
            [
                "_foobar:.export _foobar",
                ".bss",
                "L1:.ds 4",
                ".text",
                "useregs 0",
                "name L1",
                "con 2",
                "add",
                "auto 10",
                "load",
                "assign",
                "eval",
                "name L1",
                "auto 10",
                "load",
                "con 2",
                "add",
                "load",
                "load",
                "assign",
                "eval",
                "con 4",
                "ret",
                "retnull",
            ],
        )

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
