"""C6T - C version 6 by Troy - Expression Unit Tests"""

import typing
import unittest

from pyc6t.frontend import extdef
from pyc6t.frontend.c6tstate import ParseState
from pyc6t.frontend.expr import Node, expression
from pyc6t.frontend.outexpr import outexpr
from pyc6t.frontend.symtab import FrozenSym, Storage, Symbol
from pyc6t.frontend.type6 import Type, TypeString


def inode(label: str, *children: Node, value: typing.Any = None) -> Node:
    """Construct a node with type int."""
    return Node(label, TypeString(Type.INT), tuple(children), value)


class TestExpr(unittest.TestCase):
    """Test expression parser."""

    def test_cond(self):
        """Test ... ? ... : ... operators."""
        self.cmpsrc(
            ["foobar(foo, bar)", "{", "return (foo ? bar : foo);", "}"],
            [
                "_foobar:.export _foobar",
                "useregs 0",
                "auto 10",
                "load",
                "auto 12",
                "load",
                "auto 10",
                "load",
                "cond",
                "ret",
                "retnull",
            ],
        )

    def test_assign(self):
        """Test assign statements."""
        source = [
            "foo(bar)",
            "float bar;",
            "{",
            "static a, *b;",
            "static double x, *y;",
            "static float z;",
            "z = a = *b = x = *y = bar;",
            "}",
        ]
        response = [
            "_foo:.export _foo",
            ".bss",
            "L1:.ds 2",
            "L2:.ds 2",
            "L3:.ds 8",
            "L4:.ds 2",
            "L5:.ds 4",
            ".text",
            "useregs 0",
            "name L5",
            "name L1",
            "name L2",
            "load",
            "name L3",
            "name L4",
            "load",
            "auto 10",
            "dload",
            "dassign",
            "dassign",
            "toint",
            "assign",
            "assign",
            "toflt",
            "fassign",
            "eval",
            "retnull",
        ]
        self.cmpsrc(source, response)

    def cmpsrc(self, source: list[str], response: list[str]):
        """Compare the source code to the output IR. Both source and response
        IR are in the format of a list of strings with one line per string.
        """
        state = ParseState("\n".join(source))
        extdef.extdef(state)
        self.assertTrue(state.eof())
        self.assertEqual(state.errcount, 0)
        self.assertEqual(state.out_ir.splitlines(keepends=False), response)

    def test_string(self):
        """Test string output."""
        source = r'puts("hello world\n"),puts("\001\"\02\"\3")'
        response = [
            "name _puts",
            ".string",
            "L1:.db 104,101,108,108,111,32,119,111,114,108,100,10,0",
            ".text",
            "name L1",
            "null",
            "arg",
            "call",
            "name _puts",
            ".string",
            "L2:.db 1,34,2,34,3,0",
            ".text",
            "name L2",
            "null",
            "arg",
            "call",
            "comma",
        ]
        state = ParseState(source)
        state.localscope = True
        node = expression(state)
        outexpr(state, node)
        self.assertEqual(state.out_ir.splitlines(keepends=False), response)
        self.assertEqual(state.errcount, 0)

    def test_rshift(self):
        """Test rshifts are working properly, with sign extension."""
        self.dotest("(-10)>>3", inode("con", value=0xFFFE))

    def parse(self, source: str):
        """Parse a C expression source."""
        state = ParseState(source)
        node = expression(state)
        self.assertEqual(state.errcount, 0)
        self.assertIsNotNone(state.match("eof"))
        return node

    def dotest(self, source: str, node: Node):
        """Test a single expression."""
        self.assertEqual(self.parse(source), node)

    def test_call(self):
        """Test a call expression."""
        state = ParseState("foo(foo)")
        state.localscope = True
        node = expression(state)
        self.assertIsNotNone(state.match("eof"))
        self.assertIn("foo", state.symtab)
        symbol = state.symtab["foo"]
        self.assertEqual(
            symbol,
            Symbol(Storage.EXTERN, "foo", TypeString(Type.FUNC, Type.INT), local=True),
        )
        namenode = Node(
            "name", TypeString(Type.FUNC, Type.INT), value=FrozenSym.fromsym(symbol)
        )
        other = inode(
            "call",
            namenode,
            Node(
                "arg",
                TypeString(Type.INT),
                (
                    Node(
                        "addr", TypeString(Type.POINT, Type.FUNC, Type.INT), (namenode,)
                    ),
                    Node("nop", TypeString(Type.INT)),
                ),
            ),
        )
        self.assertEqual(node, other)
