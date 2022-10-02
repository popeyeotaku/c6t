"""C6T - C version 6 by Troy - Expression Node Parsing"""

import dataclasses
import typing

from typing_extensions import Self

import lexer
import util
from c6tstate import ParseState
from symtab import Storage, Symbol
from type6 import Type, TypeElem, TypeString


@dataclasses.dataclass
class Node:
    """An expression node."""

    label: str
    typestr: TypeString
    children: list[Self] = dataclasses.field(default_factory=list)
    value: typing.Any = None

    def __getitem__(self, i: int) -> Self:
        return self.children[i]


def build(label: str, *children: Node) -> Node:
    """Construct a non-leaf node with type conversions."""
    raise NotImplementedError


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
            node = build(labels[tkn.label], subparser(state))
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
                node = build("deref", build("add", node, right))
            case "(":
                if state.match(")"):
                    node = build("ucall", node)
                else:
                    args = expr15(state)
                    state.need(")")
                    node = build("call", node, args)
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
                node = build("deref", expr2(state))
            case "&":
                node = build("addr", expr2(state))
            case "-":
                node = build("neg", expr2(state))
            case "!":
                node = build("not", expr2(state))
            case "++":
                node = build("preinc", expr2(state))
            case "--":
                node = build("predec", expr2(state))
            case "sizeof":
                node = con(expr2(state).typestr.size)
            case _:
                raise ValueError(tkn)
    else:
        node = expr1(state)
    while tkn := state.match("++", "--"):
        label = "postinc" if tkn.label == "++" else "postdec"
        node = build(label, node)
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
        node = build("cond", build("colon", left, right))
    return node


def expr14(state: ParseState) -> Node:
    """Handle assignment operators."""
    node = expr13(state)
    while tkn := state.match(*lexer.ASSIGNS.keys()):
        node = build(lexer.ASSIGNS[tkn.label], expr14(state))
    return node


expr15 = binary(expr14, {",": "comma"})
