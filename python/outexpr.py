"""C6T - C version 6 by Troy - Expression Ouptut"""

from typing import Literal

import lexer
import opinfo
import util
from c6tstate import ParseState
from expr import Node
from symtab import Storage, Symbol
from type6 import Type, TypeString

TypeChar = Literal[""] | Literal["c"] | Literal["f"] | Literal["d"]

OPCODES: dict[str, str] = {
    "neg": "neg",
    "not": "lognot",
    "mult": "mult",
    "div": "div",
    "mod": "mod",
    "add": "add",
    "sub": "sub",
    "rshift": "rshift",
    "lshift": "lshift",
    "less": "less",
    "great": "great",
    "lequ": "lequ",
    "gequ": "gequ",
    "uless": "uless",
    "ugreat": "ugreat",
    "ulequ": "ulequ",
    "ugequ": "ugequ",
    "equ": "equ",
    "nequ": "nequ",
    "and": "and",
    "or": "or",
    "eor": "eor",
    "logand": "logand",
    "logor": "logor",
    "comma": "comma",
    "dot": "add",
    "arrow": "add",
    "addr": "",
    "deref": "",
    "toint": "toint",
    "toflt": "toflt",
}
OPCODES.update({assign: assign for assign in lexer.ASSIGNS.values()})


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
    if node.label not in OPCODES:
        raise ValueError(node.label)
    opcode = OPCODES[node.label]
    if not opcode:
        return
    if opcode not in opinfo.NOFLTOP and any(
        (node.typestr.floating) for node in [node] + node.children
    ):
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


def special(state: ParseState, node: Node) -> bool:
    """Check if a node is special cased for assembly - if so, assmble it and
    return True. Else, do nothing and return False.
    """
    if node.label in opinfo.ASSIGNS:
        opcode = typechar(node[0].typestr) + node.label
        asmexpr(state, node[1])
        rval(state, node[1])
        asmexpr(state, node[0])
        state.asm(opcode)
        return True
    match node.label:
        case "addr":
            asmexpr(state, node[0])
        case "cond":
            raise NotImplementedError
        case "string":
            assert isinstance(node.value, bytes)
            oldseg = state.goseg("string")
            static = state.static()
            state.defstatic(static)
            state.pseudo("db", *(str(char) for char in node.value))
            state.goseg(oldseg)
            state.asm("name", f"L{static}")
        case "name":
            symbol: Symbol = node.value
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
        case "con":
            state.asm("con", str(node.value))
        case "fcon":
            state.asm("fcon", str(node.value))
        case "ucall":
            asmexpr(state, node[0])
            state.asm("ucall")
        case "call":
            asmexpr(state, node[0])
            asmexpr(state, node[1])
            rval(state, node[1])
            state.asm("call")
        case "preinc" | "predec" | "postinc" | "postdec":
            asmexpr(state, node[0])
            if node[0].typestr.pointer:
                size = node[0].typestr.sizenext()
            else:
                size = 1
            state.asm("con", str(size))
            state.asm(node.label)
        case _:
            return False
    return True
