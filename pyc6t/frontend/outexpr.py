"""C6T - C version 6 by Troy - Expression Ouptut"""

from typing import Literal

from pyc6t.frontend.nlab import NLab

from . import opinfo, util
from .c6tstate import ParseState
from .expr import Node
from .symtab import FrozenSym, Storage
from .type6 import Type, TypeString

TypeChar = Literal["", "c", "f", "d"]

CNVLAB: dict[NLab, NLab | None] = {
    NLab.ADDR: None,
    NLab.DEREF: None,
    NLab.DOT: NLab.ADD,
    NLab.ARROW: NLab.ADD,
}


def outexpr(state: ParseState, node: Node) -> None:
    """Output assembly for an expression tree, then rval it."""
    asmexpr(state, node)
    rval(state, node)


def asmexpr(state: ParseState, node: Node) -> None:
    """Output assembly for an expression node, recursively down its childdren."""
    if special(state, node):
        return
    if node.children:
        asmexpr(state, node[0])
        if node.label not in opinfo.NEEDLVAL:
            rval(state, node[0])
        for child in node[1:]:
            asmexpr(state, child)
            rval(state, child)
    if node.label in CNVLAB:
        label = CNVLAB[node.label]
    else:
        label = node.label
    if label is None:
        return
    opcode = label.opcode
    if label not in opinfo.NOFLTOP and any(
        (node.typestr.floating) for node in [node] + list(node.children)
    ):
        if (label == NLab.COMMA and node[0].typestr.floating) or label == NLab.ARG:
            pass
        else:
            opcode = "f" + opcode
    state.asm(opcode)


def rval(state: ParseState, node: Node) -> None:
    """If the node is an lval, load it."""
    if node.label in opinfo.ISLVAL:
        char = typechar(node.typestr)
        state.asm(f"{char}load")


def typechar(typestr: TypeString) -> TypeChar:
    """Return a modifier character for loads/stores based on the type: '' for
    int, 'c' for char, 'f' for float, 'd' for double.
    """
    match typestr[0].label:
        case Type.INT | Type.POINT:
            return ""
        case Type.CHAR:
            return "c"
        case Type.FLOAT:
            return "f"
        case Type.DOUBLE:
            return "d"
        case _:
            raise ValueError(typestr[0].label)


def con0(node: Node) -> bool:
    """Return a flag for if the node is constant zero."""
    return node.label == NLab.CON and node.value == 0


def special(state: ParseState, node: Node) -> bool:
    """Check if a node is special cased for assembly - if so, assmble it and
    return True. Else, do nothing and return False.
    """
    if node.label in (NLab.DOT, NLab.ARROW, NLab.SUB, NLab.ADD) and con0(node[1]):
        asmexpr(state, node[0])
        if node.label != NLab.DOT:
            rval(state, node[0])
        return True
    if node.label == NLab.ADD and con0(node[0]):
        asmexpr(state, node[1])
        rval(state, node[1])
        return True
    if node.label in opinfo.ASSIGNS:
        opcode = typechar(node[0].typestr) + node.label.opcode
        asmexpr(state, node[0])
        asmexpr(state, node[1])
        rval(state, node[1])
        state.asm(opcode)
        return True
    match node.label:
        case NLab.NOP:
            state.asm("null")
            return True
        case NLab.ADDR:
            asmexpr(state, node[0])
        case NLab.COND:
            for child in (node[0], node[1][0], node[1][1]):
                asmexpr(state, child)
                rval(state, child)
            state.asm("cond")
        case NLab.STRING:
            assert isinstance(node.value, bytes)
            oldseg = state.goseg("string")
            static = state.static()
            state.defstatic(static)
            state.pseudo("db", *(str(char) for char in node.value))
            state.goseg(oldseg)
            state.asm("name", f"L{static}")
        case NLab.NAME:
            assert isinstance(node.value, FrozenSym)
            symbol: FrozenSym = node.value
            match symbol.storage:
                case Storage.AUTO:
                    assert isinstance(symbol.offset, int)
                    state.asm("auto", str(util.word(symbol.offset)))
                case Storage.STATIC:
                    state.asm("name", f"L{symbol.offset}")
                case Storage.EXTERN:
                    state.asm("name", f"_{symbol.offset}")
                case Storage.REGISTER:
                    state.asm("reg", str(symbol.offset))
                case _:
                    raise ValueError(node, symbol)
        case NLab.CON:
            state.asm("con", str(node.value))
        case NLab.FCON:
            state.asm("fcon", str(node.value))
        case NLab.UCALL:
            asmexpr(state, node[0])
            state.asm("ucall")
        case NLab.CALL:
            asmexpr(state, node[0])
            asmexpr(state, node[1])
            rval(state, node[1])
            state.asm("call")
        case NLab.PREINC | NLab.POSTINC | NLab.PREDEC | NLab.POSTDEC:
            asmexpr(state, node[0])
            if node[0].typestr.pointer:
                size = node[0].typestr.sizenext()
            else:
                size = 1
            state.asm("con", str(size))
            state.asm(node.label.opcode)
        case _:
            return False
    return True
