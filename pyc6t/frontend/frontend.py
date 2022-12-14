"""C6T - C version 6 by Troy - Compiler Front-End.
"""

from . import c6tstate, extdef, preproc


def compile_c6t(source: str) -> str:
    """Compile a C6T source file, returning the stack-based IR representation."""
    source = preproc.preproc(source)
    state = c6tstate.ParseState(source)
    while not state.eof():
        extdef.extdef(state)
    if state.errcount:
        raise c6tstate.C6TCrash(f"errors: {state.errcount}")
    return state.out_ir
