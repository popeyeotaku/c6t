"""C6T - C version 6 by Troy - Expression Unit Tests"""

import typing
import unittest

from c6tstate import ParseState
from expr import Node, expression
from type6 import Type, TypeString
from symtab import Symbol, Storage


def inode(label: str, *children: Node, value: typing.Any = None) -> Node:
    """Construct a node with type int."""
    return Node(label, TypeString(Type.INT), list(children), value)


class TestExpr(unittest.TestCase):
    """Test expression parser."""

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

    def test_expr(self):
        """Some basic expression tests."""
        self.dotest(
            "2+15/3",
            inode(
                "add",
                inode("con", value=2),
                inode("div", inode("con", value=15), inode("con", value=3)),
            ),
        )

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
        other = inode(
            "call",
            Node("name", TypeString(Type.FUNC, Type.INT), value=symbol),
            Node(
                "addr",
                TypeString(Type.POINT, Type.FUNC, Type.INT),
                [Node("name", TypeString(Type.FUNC, Type.INT), value=symbol)],
            ),
        )
        self.assertEqual(node, other)
