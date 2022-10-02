"""C6T - C version 6 by Troy - Compiler Front-End.
"""

import extdef
import preproc
import state


def compile_c6t(source: str) -> str:
    """Compile a C6T source file, returning the stack-based IR representation."""
    if source[0] == "#":
        source = preproc.preproc(source)
    state = state.ParseState(source)
    while not state.eof:
        extdef.extdef(state)
    return state.out_ir
