"""C6T - C version 6 by Troy - Expression Ouptut"""

from c6tstate import ParseState
from expr import Node
from symtab import Symbol, Storage


def outexpr(state: ParseState, node: Node) -> None:
    """Output assembly for an expression tree."""
    match node.label:
        case 'addr' | 'deref':
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
        case _:
            raise NotImplementedError
