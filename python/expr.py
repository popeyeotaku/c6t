"""C6T - C version 6 by Troy - Expression Node Parsing

Parsing starts at either expr15 (if you want to see commas) or expr14 (if you
don't). Each level of precedence has a corresponding expr value - expr1 at the
highest priority, expr15 at the lowest. Each priority number corresponds
to a section in the Research Unix Version 6 C Reference Manual: expr1 is
secion 7.1, expr2 is section 7.2, etc.
"""

from __future__ import annotations

import copy
import dataclasses
import typing

from typing_extensions import Self

import lexer
import opinfo
import util
from c6tstate import ParseState
from symtab import Storage, Symbol
from type6 import Type, TypeElem, TypeString


@dataclasses.dataclass
class Node:
    """An expression node."""

    label: str
    typestr: TypeString
    children: list[Node] = dataclasses.field(default_factory=list)
    value: typing.Any = None

    def __getitem__(self, i: int) -> Self:
        return self.children[i]

    def copy(self) -> Self:
        """Return a duplicated version of the node."""
        return copy.deepcopy(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        if (
            other.label != self.label
            or other.typestr != self.typestr
            or other.value != self.value
        ):
            return False
        if len(self.children) != len(other.children):
            return False
        if self.label in opinfo.COMMUTATIVE:
            for child in self.children:
                if child not in other.children:
                    return False
                other.children.remove(child)
            return True
        return self.children == other.children


def expression(
    state: ParseState, *, seecommas: bool = True, post_to_pre: bool = False
) -> Node:
    """Parse an expression with conversions."""
    if seecommas:
        node = expr15(state)
    else:
        node = expr14(state)
    node = build(state, "", node)  # Flush final conversions
    if post_to_pre:
        if node.label == "postinc":
            node.label = "preinc"
        elif node.label == "postdec":
            node.label = "predec"
    return node


def build(state: ParseState, label: str, *childargs: Node) -> Node:
    """Construct a non-leaf node with type conversions."""
    if len(childargs) > 0:
        children = [childargs[0]]
        if label != "addr":
            children[0] = fixarray(children[0])
        if label not in opinfo.CALL:
            children[0] = fixfunc(children[0])
        children.extend([fixarray(fixfunc(child)) for child in childargs[1:]])
    else:
        children = []

    if label == "":
        return children[0]

    if any((node.typestr.floating for node in children)):
        typestr = TypeString(Type.DOUBLE)
    elif any((node.typestr.pointer for node in children)):
        pointers = [node for node in children if node.typestr.pointer]
        typestr = pointers[0].typestr
    else:
        typestr = TypeString(Type.INT)

    if label in opinfo.CALL:
        if children[0].typestr[0].label != Type.FUNC:
            state.error("call of non-function")
        typestr = children[0].typestr.pop()

    node = Node(label, typestr, list(children))

    return node


def fixarray(node: Node) -> Node:
    """If the node is array type and fits other qualifications, return an
    'addr' node to it of type pointer to its subtype.
    """
    if node.label != "addr" and node.typestr[0].label == Type.ARRAY:
        node = Node("addr", TypeString(Type.POINT, *node.typestr.pop()), [node])
    return node


def fixfunc(node: Node) -> Node:
    """Alter a reference to a function to a pointer to it."""
    if node.label not in opinfo.CALL and node.typestr[0].label == Type.FUNC:
        node = Node("addr", TypeString(Type.POINT, *node.typestr), [node])
    return node


def getsym(state: ParseState, name: str) -> Symbol:
    """Get a symbol from the symbol table. Handle cases where it's not
    defined. Used by expr1 to parse NAME primaries.
    """
    if name in state.symtab:
        return state.symtab[name]
    if state.localscope:
        if state.peek().label == "(":
            # Assume function returning int.
            symbol = Symbol(
                Storage.EXTERN, name, TypeString(Type.FUNC, Type.INT), local=True
            )
        else:
            # Assume an undefined goto label.
            symbol = Symbol(
                Storage.STATIC,
                state.static(),
                TypeString(TypeElem(Type.ARRAY, 1), Type.INT),
                local=True,
                undef=True,
            )
    else:
        # Assume extern int.
        symbol = Symbol(Storage.EXTERN, name, TypeString(Type.INT))
    state.symtab[name] = symbol
    return symbol


def domember(state: ParseState, node: Node, name: str, operator: str) -> Node:
    """Handle a member operator (., ->)."""
    raise NotImplementedError


def con(i: int) -> Node:
    """Return a constant integer node."""
    return Node("con", TypeString(Type.INT), value=util.word(i))


def binary(
    subparser: typing.Callable[[ParseState], Node], labels: dict[str, str]
) -> typing.Callable[[ParseState], Node]:
    """Create a usual left-associative binary operator parser."""

    def parser(state: ParseState):
        node = subparser(state)
        while tkn := state.match(*labels.keys()):
            node = build(state, labels[tkn.label], node, subparser(state))
        return node

    return parser


def expr1(state: ParseState) -> Node:
    """Parse a primary expression."""
    if tkn := state.match("name", "con", "fcon", "string", "("):
        match tkn.label:
            case "name":
                symbol = getsym(state, tkn.value)
                node = Node("name", symbol.typestr, value=symbol)
            case "con":
                node = con(tkn.value)
            case "fcon":
                node = Node("fcon", TypeString(Type.DOUBLE), value=tkn.value)
            case "string":
                node = Node(
                    "string",
                    TypeString(TypeElem(Type.ARRAY, len(tkn.value))),
                    value=tkn.value,
                )
            case "(":
                node = expr15(state)
                state.need(")")
            case _:
                raise ValueError(tkn)
    else:
        state.error("missing primary expression")
        node = con(1)  # Good default for arrays
    while tkn := state.match("[", "(", ".", "->"):
        match tkn.label:
            case "[":
                right = expr15(state)
                state.need("]")
                node = build(state, "deref", build(state, "add", node, right))
            case "(":
                if state.match(")"):
                    node = build(state, "ucall", node)
                else:
                    args = expr15(state)
                    state.need(")")
                    node = build(state, "call", node, args)
            case "." | "->":
                name = state.need("name")
                if name is not None:
                    node = domember(state, node, name.value, tkn.label)
            case _:
                raise ValueError(tkn)
    return node


def expr2(state: ParseState) -> Node:
    """Unary operators."""
    if tkn := state.match("*", "&", "-", "!", "++", "--", "sizeof"):
        match tkn.label:
            case "*":
                node = build(state, "deref", expr2(state))
            case "&":
                node = build(state, "addr", expr2(state))
            case "-":
                node = build(state, "neg", expr2(state))
            case "!":
                node = build(state, "not", expr2(state))
            case "++":
                node = build(state, "preinc", expr2(state))
            case "--":
                node = build(state, "predec", expr2(state))
            case "sizeof":
                node = con(expr2(state).typestr.size)
            case _:
                raise ValueError(tkn)
    else:
        node = expr1(state)
    while tkn := state.match("++", "--"):
        label = "postinc" if tkn.label == "++" else "postdec"
        node = build(state, label, node)
    return node


expr3 = binary(expr2, {"*": "mult", "/": "div", "%": "mod"})
expr4 = binary(expr3, {"+": "add", "-": "sub"})
expr5 = binary(expr4, {">>": "rshift", "<<": "lshift"})
expr6 = binary(expr5, {"<": "less", ">": "great", "<=": "lequ", ">=": "gequ"})
expr7 = binary(expr6, {"==": "equ", "!=": "nequ"})
expr8 = binary(expr7, {"&": "and"})
expr9 = binary(expr8, {"^": "eor"})
expr10 = binary(expr9, {"|": "or"})
expr11 = binary(expr10, {"&&": "logand"})
expr12 = binary(expr11, {"||": "logor"})


def expr13(state: ParseState) -> Node:
    """Handle conditional (? :) operator."""
    node = expr12(state)
    while state.match("?"):
        left = expr12(state)
        state.need(":")
        right = expr12(state)
        node = build(state, "cond", build(state, "colon", left, right))
    return node


def expr14(state: ParseState) -> Node:
    """Handle assignment operators."""
    node = expr13(state)
    while tkn := state.match(*lexer.ASSIGNS.keys()):
        node = build(state, lexer.ASSIGNS[tkn.label], expr14(state))
    return node


expr15 = binary(expr14, {",": "comma"})
