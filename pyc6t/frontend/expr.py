"""C6T - C version 6 by Troy - Expression Node Parsing

Parsing starts at either expr15 (if you want to see commas) or expr14 (if you
don't). Each level of precedence has a corresponding expr value - expr1 at the
highest priority, expr15 at the lowest. Each priority number corresponds
to a section in the Research Unix Version 6 C Reference Manual: expr1 is
secion 7.1, expr2 is section w7.2, etc.
"""

from __future__ import annotations

import dataclasses
import typing

from . import lexer, nlab, opinfo, util
from .c6tstate import ParseState
from .nlab import UCMP, NLab
from .symtab import FrozenSym, Storage, Symbol
from .type6 import Type, TypeElem, TypeString


@dataclasses.dataclass(frozen=True)
class Node:
    """An expression node."""

    label: NLab
    typestr: TypeString
    children: tuple[Node, ...] = ()
    value: typing.Hashable = None

    def __post_init__(self) -> None:
        assert isinstance(self.label, NLab)

    @typing.overload
    def __getitem__(self, i: slice) -> tuple[Node, ...]:
        ...

    @typing.overload
    def __getitem__(self, i: int) -> Node:
        ...

    def __getitem__(self, i: int | slice) -> Node | tuple[Node, ...]:
        return self.children[i]

    def __iter__(self) -> typing.Iterator[Node]:
        return iter(self.children)

    def copy(
        self, *, label: NLab | None = None, typestr: TypeString | None = None
    ) -> Node:
        """Return a shallow copy of the node, optionally with a new label or
        type string.
        """
        if label is None:
            label = self.label
        if typestr is None:
            typestr = self.typestr
        return Node(label, typestr, self.children, self.value)

    def __hash__(self) -> int:
        return hash(
            (
                self.label,
                self.typestr,
                len(self.children),
                frozenset(self.children),
                self.value,
            )
        )

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
            return set(self.children) == set(other.children)
        return self.children == other.children


def expression(
    state: ParseState, *, seecommas: bool = True, post_to_pre: bool = False
) -> Node:
    """Parse an expression with conversions."""
    if seecommas:
        node = expr15(state)
    else:
        node = expr14(state)
    node = build(state, None, node)  # Flush final conversions
    if post_to_pre:
        if node.label == NLab.POSTINC:
            node = node.copy(label=NLab.PREINC)
        elif node.label == NLab.POSTDEC:
            node = node.copy(label=NLab.PREDEC)
    return node


def conexpr(state: ParseState, *, seecommas: bool = True) -> int:
    """Parse a constant expression."""
    node = expression(state, seecommas=seecommas)
    if node.label != NLab.CON:
        state.error("expected constant expression")
        return 1  # Good default for arrays
    assert isinstance(node.value, int)
    return node.value


def build(state: ParseState, label: NLab | None, *childargs: Node) -> Node:
    """Construct a non-leaf node with type conversions."""
    children: list[Node] = list(childargs)
    if len(children) > 1:
        for i, child in enumerate(children[1:]):
            children[i + 1] = fixfunc(fixarray(child))
    if children:
        if label is not None and label != NLab.ADDR:
            children[0] = fixarray(children[0])
            if label is not None and label not in opinfo.CALL:
                children[0] = fixfunc(children[0])

    if label is None:
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
        case NLab.COND:
            assert left and right
            if right.label != NLab.COLON:
                state.error("bad conditional operator")
            return Node(label, right.typestr, tuple(children))
        case NLab.COMMA | NLab.ARG | NLab.LOGAND | NLab.LOGOR:
            return Node(label, typestr, tuple(children))
        case NLab.CALL | NLab.UCALL:
            assert left is not None
            typestr = left.typestr
            if left.typestr[0].label != Type.FUNC:
                state.error("call of non-function")
            else:
                typestr = left.typestr.pop()
            return Node(label, typestr, tuple(children))
        case NLab.DEREF:
            assert left is not None
            if left.label == NLab.ADDR:
                # pylint:disable=unsubscriptable-object
                return left[0]
            if not left.typestr.pointer:
                state.error("deref of non-pointer")
            return Node(label, left.typestr.pop(), tuple(children))
        case NLab.ADDR:
            assert left is not None
            if left.label == NLab.DEREF:
                # pylint:disable=unsubscriptable-object
                node = left[0].copy(typestr=TypeString(Type.POINT, *left[0].typestr))
                return node
            if left.label not in opinfo.ISLVAL:
                state.error("expected an lval")
            return Node(label, TypeString(Type.POINT, *left.typestr), (left,))
        case _:
            pass
    if label in opinfo.NEEDLVAL:
        assert left is not None
        if left.label not in opinfo.ISLVAL:
            state.error("expected an lval")
    if label in opinfo.UNARY:
        assert left is not None and right is None
        if label == NLab.TOFLT:
            typestr = TypeString(Type.DOUBLE)
        elif label == NLab.TOINT:
            typestr = TypeString(Type.INT)
        else:
            typestr = left.typestr
        return fold(Node(label, typestr, tuple(children)))

    assert left and right

    if Type.STRUCT in (left.typestr[0].label, right.typestr[0].label):
        state.error("illegal structure operation")
        left = left.copy(typestr=TypeString(Type.INT))
        right = right.copy(typestr=TypeString(Type.INT))

    conversion: Type | None = stdconv(left, right)

    if label in opinfo.ASSIGNS:
        if left.typestr.pointer and right.typestr.floating:
            state.error("cannot assign float to a pointer type")
        if left.typestr.floating and not right.typestr.floating:
            right = build(state, NLab.TOFLT, right)
        elif right.typestr.floating and not left.typestr.floating:
            right = build(state, NLab.TOINT, right)
        elif left.typestr.pointer and label != NLab.ASSIGN:
            right = build(state, NLab.MULT, right, con(left.typestr.sizenext()))
        return Node(label, right.typestr, (left, right))
    if label == NLab.COLON and left.typestr.pointer and left.typestr == right.typestr:
        conversion = None
    elif label in opinfo.CMP:
        if label in opinfo.LESSGREAT and conversion == Type.POINT:
            label = UCMP[label]
        if conversion == Type.POINT:
            conversion = None
    match conversion:
        case None:
            pass
        case Type.INT:
            if left.typestr.floating:
                left = build(state, NLab.TOINT, left)
            if right.typestr.floating:
                right = build(state, NLab.TOINT, right)
        case Type.POINT:
            if label == NLab.SUB and left.typestr == right.typestr:
                sizeleft, sizeright = (
                    (node.typestr.sizenext() if node.typestr.pointer else 1)
                    for node in (left, right)
                )
                size = max(sizeleft, sizeright)
                subbed = fold(Node(NLab.SUB, TypeString(Type.INT), (left, right)))
                if size == 1:
                    return subbed
                return fold(
                    Node(
                        NLab.DIV,
                        TypeString(Type.INT),
                        (
                            subbed,
                            con(size),
                        ),
                    )
                )
            if left.typestr.pointer:
                typestr = left.typestr
                sizenext = typestr.sizenext()
                if sizenext != 1:
                    right = build(state, NLab.MULT, right, con(sizenext))
            else:
                typestr = right.typestr
                sizenext = typestr.sizenext()
                if sizenext != 1:
                    left = build(state, NLab.MULT, left, con(sizenext))
        case Type.FLOAT:
            typestr = TypeString(Type.DOUBLE)
            if not left.typestr.floating:
                left = build(state, NLab.TOFLT, left)
            elif not right.typestr.floating:
                right = build(state, NLab.TOFLT, right)
        case _:
            raise ValueError(conversion)
    if label in opinfo.ISINT:
        typestr = TypeString(Type.INT)
    return fold(Node(label, typestr, (left, right)))


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
    cons: list[int] = []
    for child in node.children:
        if child.label != NLab.CON:
            return node
        assert isinstance(child.value, int)
        cons.append(child.value)
    match node.label:
        case NLab.ADD:
            result = con(sum(cons))
        case NLab.SUB:
            result = con(cons[0] - cons[1])
        case NLab.MULT:
            result = con(cons[0] * cons[1])
        case NLab.DIV:
            result = con(cons[0] // cons[1])
        case NLab.MOD:
            result = con(cons[0] % cons[1])
        case NLab.AND:
            result = con(cons[0] & cons[1])
        case NLab.OR:
            result = con(cons[0] | cons[1])
        case NLab.EOR:
            result = con(cons[0] ^ cons[1])
        case NLab.LSHIFT:
            result = con(cons[0] << cons[1])
        case NLab.RSHIFT:
            if cons[0] & 0x8000:
                cons[0] = -((cons[0] ^ 0xFFFF) + 1)  # Force sign extension
            result = con(cons[0] >> cons[1])
        case NLab.NEG:
            result = con(-cons[0])
        case NLab.COMPL:
            result = con(cons[0] ^ 0xFFFF)
        case _:
            return node
    return result


def fixarray(node: Node) -> Node:
    """If the node is array type and fits other qualifications, return an
    'addr' node to it of type pointer to its subtype.
    """
    if node.label != NLab.ADDR and node.typestr[0].label == Type.ARRAY:
        node = Node(NLab.ADDR, TypeString(Type.POINT, *node.typestr.pop()), (node,))
    return node


def fixfunc(node: Node) -> Node:
    """Alter a reference to a function to a pointer to it."""
    if node.label not in opinfo.CALL and node.typestr[0].label == Type.FUNC:
        node = Node(NLab.ADDR, TypeString(Type.POINT, *node.typestr), (node,))
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
    if operator == "." and node.label not in opinfo.ISLVAL:
        state.error("missing required lval")
    return Node(
        NLab.DOT if operator == "." else NLab.ARROW, typestr, (node, con(offset))
    )


def con(i: int) -> Node:
    """Return a constant integer node."""
    return Node(NLab.CON, TypeString(Type.INT), value=util.word(i))


def binary(
    subparser: typing.Callable[[ParseState], Node], labels: dict[str, NLab]
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
                node = Node(NLab.NAME, symbol.typestr, value=FrozenSym.fromsym(symbol))
            case "con":
                node = con(tkn.value)
            case "fcon":
                node = Node(NLab.FCON, TypeString(Type.DOUBLE), value=tkn.value)
            case "string":
                node = Node(
                    NLab.STRING,
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
                node = build(state, NLab.DEREF, build(state, NLab.ADD, node, right))
            case "(":
                if state.match(")"):
                    node = build(state, NLab.UCALL, node)
                else:
                    args: Node = Node(NLab.NOP, TypeString(Type.INT))
                    while not state.match(")"):
                        state.earlyeof()
                        args = build(state, NLab.ARG, expr14(state), args)
                        if not state.peekmatch(")"):
                            state.need(",")
                    args = build(state, None, args)
                    node = build(state, NLab.CALL, node, args)
            case "." | "->":
                name = state.need("name")
                if name is not None:
                    node = domember(state, node, name.value, tkn.label)
            case _:
                raise ValueError(tkn)
    return node


def expr2(state: ParseState) -> Node:
    """Unary operators."""
    if tkn := state.match("*", "&", "-", "!", "++", "--", "sizeof", "~"):
        match tkn.label:
            case "~":
                node = build(state, NLab.COMPL, expr2(state))
            case "*":
                node = build(state, NLab.DEREF, expr2(state))
            case "&":
                node = build(state, NLab.ADDR, expr2(state))
            case "-":
                node = build(state, NLab.NEG, expr2(state))
            case "!":
                node = build(state, NLab.NOT, expr2(state))
            case "++":
                node = build(state, NLab.PREINC, expr2(state))
            case "--":
                node = build(state, NLab.PREDEC, expr2(state))
            case "sizeof":
                node = con(expr2(state).typestr.size)
            case _:
                raise ValueError(tkn)
    else:
        node = expr1(state)
    while tkn := state.match("++", "--"):
        label = NLab.POSTINC if tkn.label == "++" else NLab.POSTDEC
        node = build(state, label, node)
    return node


expr3 = binary(expr2, {"*": NLab.MULT, "/": NLab.DIV, "%": NLab.MOD})
expr4 = binary(expr3, {"+": NLab.ADD, "-": NLab.SUB})
expr5 = binary(expr4, {">>": NLab.RSHIFT, "<<": NLab.LSHIFT})
expr6 = binary(
    expr5, {"<": NLab.LESS, ">": NLab.GREAT, "<=": NLab.LEQU, ">=": NLab.GEQU}
)
expr7 = binary(expr6, {"==": NLab.EQU, "!=": NLab.NEQU})
expr8 = binary(expr7, {"&": NLab.AND})
expr9 = binary(expr8, {"^": NLab.EOR})
expr10 = binary(expr9, {"|": NLab.OR})
expr11 = binary(expr10, {"&&": NLab.LOGAND})
expr12 = binary(expr11, {"||": NLab.LOGOR})


def expr13(state: ParseState) -> Node:
    """Handle conditional (? :) operator."""
    node = expr12(state)
    while state.match("?"):
        left = expr12(state)
        state.need(":")
        right = expr12(state)
        node = build(state, NLab.COND, node, build(state, NLab.COLON, left, right))
    return node


def expr14(state: ParseState) -> Node:
    """Handle assignment operators."""
    node = expr13(state)
    while tkn := state.match(*lexer.ASSIGNS.keys()):
        node = build(state, nlab.ASSIGNS[tkn.label], node, expr14(state))
    return node


expr15 = binary(expr14, {",": NLab.COMMA})
