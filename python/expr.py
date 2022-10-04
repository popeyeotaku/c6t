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

    @typing.overload
    def __getitem__(self, i: slice) -> list[Node]:
        ...

    @typing.overload
    def __getitem__(self, i: int) -> Node:
        ...

    def __getitem__(self, i: int | slice) -> Node | list[Node]:
        return self.children[i]

    def __iter__(self) -> typing.Iterator[Node]:
        return iter(self.children)

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


def conexpr(state: ParseState, *, seecommas: bool = True) -> int:
    """Parse a constant expression."""
    node = expression(state, seecommas=seecommas)
    if node.label != "con":
        state.error("expected constant expression")
        return 1  # Good default for arrays
    return node.value


def build(state: ParseState, label: str, *childargs: Node) -> Node:
    """Construct a non-leaf node with type conversions."""
    children: list[Node] = list(childargs)
    if len(children) > 1:
        for i, child in enumerate(children[1:]):
            children[i + 1] = fixfunc(fixarray(child))
    if children:
        if label != "addr":
            children[0] = fixarray(children[0])
            if label not in opinfo.CALL:
                children[0] = fixfunc(children[0])

    if label == "":
        return children[0]

    typestr = TypeString(Type.INT)

    left = children[0] if children else None
    right = children[1] if len(children) > 1 else None

    if (
        any((child.typestr.floating for child in children))
        and label not in opinfo.SUPPORTS_FLOAT
    ):
        state.error("floating type on non-floating operator")

    # Special cases
    match label:
        case "cond":
            assert left and right
            if right.label != "colon":
                state.error("bad conditional operator")
            return Node(label, right.typestr, children)
        case "comma" | "logand" | "logor":
            return Node(label, typestr, children)
        case "call" | "ucall":
            assert left is not None
            typestr = left.typestr
            if left.typestr[0].label != Type.FUNC:
                state.error("call of non-function")
            else:
                typestr = left.typestr.pop()
            return Node(label, typestr, children)
        case "deref":
            assert left is not None
            if left.label == "addr":
                # pylint:disable=unsubscriptable-object
                return left[0]
            if not left.typestr.pointer:
                state.error("deref of non-pointer")
            return Node(label, left.typestr.pop(), children)
        case "addr":
            assert left is not None
            if left.label == "deref":
                # pylint:disable=unsubscriptable-object
                node = left[0].copy()
                node.typestr = TypeString(Type.POINT, *node.typestr)
                return node
            if left.label not in opinfo.ISLVAL:
                state.error("expected an lval")
            return Node(label, TypeString(Type.POINT, *left.typestr), [left])
        case _:
            pass
    if label in opinfo.NEEDLVAL:
        assert left is not None
        if left.label not in opinfo.ISLVAL:
            state.error("expected an lval")
    if label in opinfo.UNARY:
        assert left is not None and right is None
        if label == "toflt":
            typestr = TypeString(Type.DOUBLE)
        elif label == "toint":
            typestr = TypeString(Type.INT)
        else:
            typestr = left.typestr
        return fold(Node(label, typestr, children))

    assert left and right

    if left.typestr[0].label == Type.STRUCT or right.typestr[0].label == Type.STRUCT:
        state.error("illegal structure operation")
        left.typestr = TypeString(Type.INT)
        right.typestr = TypeString(Type.INT)

    conversion: Type | None = stdconv(left, right)
    pntlab = "mult"

    if label in opinfo.ASSIGNS:
        if left.typestr.pointer and right.typestr.floating:
            state.error("cannot assign float to a pointer type")
        if left.typestr.floating and not right.typestr.floating:
            right = build(state, "toflt", right)
        elif right.typestr.floating and not left.typestr.floating:
            right = build(state, "toint", right)
        return Node(label, right.typestr, [left, right])
    if label == "colon" and left.typestr.pointer and left.typestr == right.typestr:
        conversion = None
    elif label in opinfo.CMP:
        if label in opinfo.LESSGREAT and conversion == Type.POINT:
            label = "u" + label
        if conversion == Type.POINT:
            conversion = None
    if conversion == Type.POINT:
        if label == "sub":
            typestr = TypeString(Type.INT)
            pntlab = "div"
    match conversion:
        case None:
            pass
        case Type.INT:
            if left.typestr.floating:
                left = build(state, "toint", left)
            if right.typestr.floating:
                right = build(state, "toint", right)
        case Type.POINT:
            if left.typestr.pointer:
                typestr = left.typestr
                sizenext = typestr.sizenext()
                if sizenext != 1:
                    right = Node(pntlab, typestr, [right, con(sizenext)])
            else:
                typestr = right.typestr
                sizenext = typestr.sizenext()
                if sizenext != 1:
                    left = Node(pntlab, typestr, [left, con(sizenext)])
        case Type.FLOAT:
            typestr = TypeString(Type.DOUBLE)
            if not left.typestr.floating:
                left = build(state, "toflt", left)
            elif not right.typestr.floating:
                right = build(state, "toflt", right)
        case _:
            raise ValueError(conversion)
    if label in opinfo.ISINT:
        typestr = TypeString(Type.INT)
    return fold(Node(label, typestr, [left, right]))


def stdconv(
    left: Node, right: Node
) -> typing.Literal[Type.INT] | typing.Literal[Type.FLOAT] | typing.Literal[Type.POINT]:
    """Given two nodes, return the proper type conversion type for standard conversions.

    Standard conversions are: if either is floating type, the type is floating. Else if
    either is pointer, the type is pointer. Else the type is int.
    """
    if left.typestr.floating or right.typestr.floating:
        return Type.FLOAT
    if left.typestr.pointer or right.typestr.pointer:
        return Type.POINT
    return Type.INT


def fold(node: Node) -> Node:
    """Try to constant fold a node, returning the folded version if so, else
    the original node.
    """
    if any((node.label != "con" for node in node.children)):
        return node
    cons = [child.value for child in node.children]
    match node.label:
        case "add":
            result = con(sum(cons))
        case "sub":
            result = con(cons[0] - cons[1])
        case "mult":
            result = con(cons[0] * cons[1])
        case "div":
            result = con(cons[0] // cons[1])
        case "mod":
            result = con(cons[0] % cons[1])
        case "and":
            result = con(cons[0] & cons[1])
        case "or":
            result = con(cons[0] | cons[1])
        case "eor":
            result = con(cons[0] ^ cons[1])
        case "lshift":
            result = con(cons[0] << cons[1])
        case "rshift":
            if cons[0] & 0x8000:
                cons[0] = -((cons[0] ^ 0xFFFF) + 1)  # Force sign extension
            result = con(cons[0] >> cons[1])
        case "neg":
            result = con(-cons[0])
        case "compl":
            result = con(cons[0] ^ 0xFFFF)
        case _:
            return node
    return result


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
    assert operator in (".", "->")
    offset = 0
    typestr = TypeString(Type.INT)
    if name not in state.tags:
        state.error(f"nonexistant member {name}")
    else:
        symbol = state.tags[name]
        if symbol.storage != Storage.MEMBER:
            state.error(f"{name} not a member")
        else:
            assert isinstance(symbol.offset, int)
            offset = symbol.offset
            typestr = symbol.typestr
    if operator == '.' and node.label not in opinfo.ISLVAL:
        state.error('missing required lval')
    return Node("dot" if operator == "." else "arrow", typestr, [node, con(offset)])


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
                    TypeString(TypeElem(Type.ARRAY, len(tkn.value)), Type.CHAR),
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
        node = build(state, "cond", node, build(state, "colon", left, right))
    return node


def expr14(state: ParseState) -> Node:
    """Handle assignment operators."""
    node = expr13(state)
    while tkn := state.match(*lexer.ASSIGNS.keys()):
        node = build(state, lexer.ASSIGNS[tkn.label], node, expr14(state))
    return node


expr15 = binary(expr14, {",": "comma"})
