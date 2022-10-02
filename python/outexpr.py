"""C6T - C version 6 by Troy - Expression Ouptut"""

from typing import Literal
from c6tstate import ParseState
from expr import Node
from symtab import Symbol, Storage
from type6 import TypeString, Type
import opinfo

TypeChar = Literal[""] | Literal["c"] | Literal["f"] | Literal["d"]

OPCODES: dict[str, str] = {}


def outexpr(state: ParseState, node: Node) -> None:
    """Output assembly for an expression tree."""
    if special(state, node):
        return
    if node.children:
        outexpr(state, node[0])
        label = node[0].label
        if label not in opinfo.NEEDLVAL:
            rval(state, node[0])
        for child in node[1:]:
            outexpr(state, child)
            rval(state, child)
    state.asm(OPCODES[node.label])


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
    match node.label:
        case "addr" | "deref":
            outexpr(state, node[0])
        case "name":
            symbol: Symbol = node.value
            match symbol.storage:
                case Storage.AUTO:
                    state.asm("pushframe", str(symbol.offset))
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
        case _:
            return False
    return True
