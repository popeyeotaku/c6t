"""C6T - C version 6 by Troy - Statement Parsing"""

from dataclasses import dataclass, field
from typing import Callable, TypedDict

from . import expr, outexpr
from .c6tstate import ParseState
from .symtab import Storage, Symbol
from .type6 import Type, TypeElem, TypeString


@dataclass
class CaseCollection:
    """A complete list of cases for a switch statement, with default."""

    cases: dict[int, int] = field(default_factory=dict)
    default_static: int | None = None

    def __len__(self) -> int:
        return len(self.cases)


StateStks = TypedDict(
    "StateStks",
    {"contstk": list[int], "brkstk": list[int], "casestk": list[CaseCollection]},
)

StateFunc = Callable[[ParseState, StateStks], None]


def ifstate(state: ParseState, stks: StateStks) -> None:
    """Parse an if statement."""
    lab1 = state.static()
    node = parenexpr(state)
    fltflag = node.typestr.floating
    outexpr.outexpr(state, node)
    state.brz(lab1, fltflag)
    statement(state, stks)
    if state.match("else"):
        lab2 = state.static()
        state.jmpstatic(lab2)
        state.defstatic(lab1)
        statement(state, stks)
        state.defstatic(lab2)
    else:  # Ironic, ain't it?
        state.defstatic(lab1)


def whilestate(state: ParseState, stks: StateStks) -> None:
    """Parse a while statement."""
    stks["contstk"].append(state.static())
    stks["brkstk"].append(state.static())
    state.defstatic(stks["contstk"][-1])
    node = parenexpr(state)
    fltflag = node.typestr.floating
    outexpr.outexpr(state, node)
    state.brz(stks["brkstk"][-1], fltflag)
    statement(state, stks)
    state.jmpstatic(stks["contstk"][-1])
    state.defstatic(stks["brkstk"][-1])
    stks["contstk"].pop()
    stks["brkstk"].pop()


def dostate(state: ParseState, stks: StateStks) -> None:
    """Parse a do statement."""
    static = state.static()
    state.defstatic(static)
    stks["contstk"].append(state.static())
    stks["brkstk"].append(state.static())
    statement(state, stks)
    state.need("while")
    node = parenexpr(state)
    state.need(";")
    state.defstatic(stks["contstk"][-1])
    outexpr.outexpr(state, node)
    state.brz(stks["brkstk"][-1], node.typestr.floating)
    state.jmpstatic(static)
    state.defstatic(stks["brkstk"][-1])
    stks["brkstk"].pop()
    stks["contstk"].pop()


def forstate(state: ParseState, stks: StateStks) -> None:
    """Parse a for statement."""
    state.need("(")
    if state.match(";"):
        init = None
    else:
        init = expr.expression(state, post_to_pre=True)
        state.need(";")
    if state.match(";"):
        check = None
    else:
        check = expr.expression(state)
        state.need(";")
    if state.match(")"):
        update = None
    else:
        update = expr.expression(state, post_to_pre=True)
        state.need(")")
    if init:
        outexpr.outexpr(state, init)
        state.asm("eval")
    stks["contstk"].append(state.static())
    stks["brkstk"].append(state.static())
    if update:
        static = state.static()
    else:
        static = stks["contstk"][-1]
    state.defstatic(static)
    if check:
        outexpr.outexpr(state, check)
        state.brz(stks["brkstk"][-1], check.typestr.floating)
    statement(state, stks)
    if update:
        state.defstatic(stks["contstk"][-1])
        outexpr.outexpr(state, update)
        state.asm("eval")
        state.jmpstatic(static)
    else:
        state.jmpstatic(stks["contstk"][-1])
    state.defstatic(stks["brkstk"][-1])
    stks["brkstk"].pop()
    stks["contstk"].pop()


def switchstate(state: ParseState, stks: StateStks) -> None:
    """Parse a switch statement."""
    node = parenexpr(state)
    static = state.static()
    state.jmpstatic(static)
    stks["brkstk"].append(state.static())
    stks["casestk"].append(CaseCollection())
    statement(state, stks)
    state.defstatic(static)
    doswitch(state, node, stks["casestk"].pop(), stks["brkstk"].pop())


def casestate(state: ParseState, stks: StateStks) -> None:
    """Parse a case statement."""
    con = expr.conexpr(state)
    state.need(":")
    if not stks["casestk"]:
        state.error("case outside of switch")
        statement(state, stks)
        return
    cases = stks["casestk"][-1]
    if con in cases.cases:
        state.error(f"redefined case {con}")
    else:
        static = state.static()
        cases.cases[con] = static
        state.defstatic(static)
    statement(state, stks)


def defaultstate(state: ParseState, stks: StateStks) -> None:
    """Parse a default statement."""
    state.need(":")
    if not stks["casestk"]:
        state.error("default outside of switch")
        statement(state, stks)
        return
    cases = stks["casestk"][-1]
    if cases.default_static:
        state.error("multiple default statements")
    else:
        static = state.static()
        cases.default_static = static
        state.defstatic(static)
    statement(state, stks)


def breakstate(state: ParseState, stks: StateStks) -> None:
    """Parse a break statement."""
    state.need(";")
    if not stks["brkstk"]:
        state.error("nothing to break to")
    else:
        state.jmpstatic(stks["brkstk"][-1])


def contstate(state: ParseState, stks: StateStks) -> None:
    """Parse a continue statement."""
    state.need(";")
    if not stks["contstk"]:
        state.error("nothing to continue to")
    else:
        state.jmpstatic(stks["contstk"][-1])


# pylint:disable=unused-argument
def retstate(state: ParseState, stks: StateStks) -> None:
    """Parse a return statement."""
    if state.match(";"):
        retnull(state)
    else:
        outexpr.outexpr(state, (node := parenexpr(state)))
        state.need(";")
        state.asm(f"{'f' if node.typestr.floating else ''}ret")


# pylint:disable=unused-argument
def gotostate(state: ParseState, stks: StateStks) -> None:
    """Parse a goto statement."""
    node = expr.expression(state)
    state.need(";")
    outexpr.outexpr(state, node)
    state.asm("goto")


# pylint:disable=unused-argument
def nullstate(state: ParseState, stks: StateStks) -> None:
    """Parse a null statement."""
    return


def cmpstate(state: ParseState, stks: StateStks) -> None:
    """Parse a compound statement."""
    while not state.match("}"):
        state.earlyeof()
        statement(state, stks)


STATEMENTS: dict[str, StateFunc] = {
    "if": ifstate,
    "while": whilestate,
    "do": dostate,
    "for": forstate,
    "switch": switchstate,
    "case": casestate,
    "default": defaultstate,
    "break": breakstate,
    "continue": contstate,
    "return": retstate,
    "goto": gotostate,
    ";": nullstate,
    "{": cmpstate,
}


def statement(state: ParseState, stks: StateStks | None = None) -> None:
    """Parse a single statement recursively."""
    assert state.localscope is True
    state.goseg("text")
    if stks is None:
        stks = {"contstk": [], "brkstk": [], "casestk": []}
    if tkn := state.match(*STATEMENTS.keys()):
        STATEMENTS[tkn.label](state, stks)
    else:
        if tkn := state.match("name"):
            if state.match(":"):
                gotolab(state, tkn.value, stks)
                statement(state, stks)
                return
            state.unsee(tkn)
        exprstate(state)


def gotolab(state: ParseState, name: str, stks: StateStks) -> None:
    """Parse a goto label."""
    if name in state.symtab:
        symbol = state.symtab[name]
        if symbol.undef:
            symbol.undef = False
        if symbol.storage != Storage.STATIC:
            state.error(f"redefined goto label {name}")
        assert isinstance(symbol.offset, int)
        static = symbol.offset
    else:
        static = state.static()
        symbol = Symbol(
            Storage.STATIC,
            static,
            TypeString(TypeElem(Type.ARRAY, 1), Type.INT),
            local=True,
        )
        state.symtab[name] = symbol
    state.defstatic(static)


def exprstate(state: ParseState) -> None:
    """Parse an expression statement."""
    node = expr.expression(state, seecommas=True, post_to_pre=True)
    state.need(";")
    outexpr.outexpr(state, node)
    state.asm("eval")


def retnull(state: ParseState) -> None:
    """Assemble an empty return statement with no value."""
    state.asm("retnull")


def parenexpr(state: ParseState) -> expr.Node:
    """Parse an expression in parenthesis."""
    state.need("(")
    node = expr.expression(state)
    state.need(")")
    return node


def doswitch(
    state: ParseState, node: expr.Node, cases: CaseCollection, brklab: int
) -> None:
    """Assemble a switch statement."""
    assert state.curseg == "text"
    state.goseg("data")
    table = state.static()
    state.defstatic(table)
    for con, label in cases.cases.items():
        state.pseudo("dw", str(con), f"L{label}")
    state.goseg("text")
    outexpr.outexpr(state, node)
    state.asm("name", f"L{table}")
    default = cases.default_static
    if default is None:
        default = brklab
    state.asm("name", f"L{default}")
    state.asm("con", str(len(cases)))
    state.asm("doswitch")
    state.defstatic(brklab)
