"""C6T - C version 6 by Troy - Expression Unit Tests"""

import typing
import unittest

from c6tstate import ParseState
from expr import Node, expression
from outexpr import outexpr
from type6 import Type, TypeString
from symtab import Symbol, Storage


def inode(label: str, *children: Node, value: typing.Any = None) -> Node:
    """Construct a node with type int."""
    return Node(label, TypeString(Type.INT), list(children), value)


class TestExpr(unittest.TestCase):
    """Test expression parser."""

    def test_string(self):
        """Test string output."""
        source = r'puts("hello world\n");'
        response = [
            "name _puts",
            ".string",
            "L1:.db 104,101,108,108,111,32,119,111,114,108,100,10,0",
            ".text",
            "name L1",
            "call",
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
        namenode = Node("name", TypeString(Type.FUNC, Type.INT), value=symbol)
        other = inode(
            "call",
            namenode,
            Node(
                "addr",
                TypeString(Type.POINT, Type.FUNC, Type.INT),
                [namenode],
            ),
        )
        self.assertEqual(node, other)
