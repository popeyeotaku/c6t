"""C6T - C version 6 by Troy - External Definition Parsing.

A C6T program is a series of external definitions, which declare data and
functions to exist, and optionally also initializer them. Function definitions
can be thought of as a special case of initialized data extdefs.

A central element of all this is the type declaration list. Since it is used
in many different places, we have a special function to handle one which
gets passed a callback function for different situations.
"""

from typing import Callable

import statement
from c6tstate import ParseState, MAXREGS
from expr import conexpr
from symtab import Storage, Symbol
from type6 import Type, TypeElem, TypeString


def extdef(state: ParseState):
    """Parse an external definition."""
    assert state.localscope is False
    typedecl_list(state, extdef_callback, need_typeclass=True)


TypeDeclCallback = Callable[
    [ParseState, int, str, list[str], TypeString, Storage], bool
]


# pylint:disable=unused-argument, too-many-arguments
def extdef_callback(
    state: ParseState,
    count: int,
    name: str,
    args: list[str],
    typestr: TypeString,
    storage: Storage,
) -> bool:
    """Callback function for an external definition. Return a flag for if we
    should end the typedecl list parsing immediately or not.
    """
    if count == 0 and typestr[0].label == Type.FUNC and not state.peekmatch(",", ";"):
        funcdef(state, name, args, typestr)
        return True
    datadef(state, name, typestr)
    return False


def datadef(state: ParseState, name: str, typestr: TypeString) -> None:
    """Parse an externaldata definition, with a possible initializer."""
    symbol = Symbol(Storage.EXTERN, name, typestr)
    state.redef(name)
    state.symtab[name] = symbol
    if symbol.typestr[0].label == Type.FUNC:
        return
    if state.peekmatch(",", ";"):
        state.goseg("bss")
        state.pseudo("common", "_" + name, str(typestr.size))
    else:
        datainit(state, name, typestr)


def datainit(state: ParseState, name: str, typestr: TypeString) -> None:
    """Parse a data initializer.

    The symbol table entry has already been filled, remember to adjust it if
    necessary (array bounds changed, etc).
    """
    raise NotImplementedError


def funcdef(state: ParseState, name: str, args: list[str], typestr: TypeString) -> None:
    """Parse a function definition."""
    state.goseg("text")
    symbol = Symbol(Storage.EXTERN, "_" + name, typestr)
    state.symtab[name] = symbol
    state.golocal()
    grabparams(state, args)
    state.need("{")
    grablocals(state)
    while not state.match("}"):
        state.earlyeof()
        statement.statement(state)
    statement.retnull(state)
    state.exitlocal()


def grabparams(state: ParseState, args: list[str]) -> None:
    """Parse parameter type declarations."""
    raise NotImplementedError


def grablocals(state: ParseState) -> None:
    """Parse local declarations."""
    assert state.auto_offset == 0
    assert state.usedregs == 0
    assert state.localscope
    typedecl_list(state, local_callback, need_typeclass=True)
    state.goseg("text")
    state.asm("useregs", str(state.usedregs))
    if state.auto_offset:
        state.asm("dropstk", str(-state.auto_offset))


# pylint:disable=unused-argument
def local_callback(
    state: ParseState,
    count: int,
    name: str,
    args: list[str],
    typestr: TypeString,
    storage: Storage,
) -> bool:
    """Callback function for seeing a declaration of a local."""
    assert state.localscope
    if storage == Storage.REGISTER and state.usedregs >= MAXREGS:
        storage = Storage.AUTO
    match storage:
        case Storage.EXTERN:
            offset = "_" + name
        case Storage.STATIC:
            offset = state.static()
            oldseg = state.goseg("bss")
            state.defstatic(offset)
            state.pseudo("ds", str(typestr.size))
            state.goseg(oldseg)
        case Storage.AUTO:
            state.auto_offset -= typestr.size
            offset = state.auto_offset
        case Storage.REGISTER:
            offset = state.usedregs
            state.usedregs += 1
        case _:
            raise ValueError(storage)
    symbol = Symbol(storage, offset, typestr, local=True)
    state.symtab[name] = symbol
    return False


def typedecl_list(
    state: ParseState, callback: TypeDeclCallback, *, need_typeclass: bool
) -> bool:
    """Parse a series of type declaration lists. Return a flag for if we
    parsed any.
    """
    gotany = False
    while True:
        count = 0
        if state.eof():
            return gotany
        basetype, storage = typeclass(state)
        if basetype is None and storage is None and need_typeclass:
            return gotany
        if not gotany:
            gotany = (basetype is not None) or (storage is not None)
        if basetype is None:
            basetype = TypeElem(Type.INT)
        if storage is None:
            storage = Storage.AUTO if state.localscope else Storage.EXTERN

        while not state.match(";"):
            state.earlyeof()
            name, typestr, args, grabbed = decl(state, basetype)
            if not grabbed:
                state.need(";")
                break
            gotany = True
            if callback(state, count, name, args, typestr, storage):
                break
            if not state.peekmatch(";"):
                state.need(",")
            count += 1


def decl(
    state: ParseState, basetype: TypeElem
) -> tuple[str, TypeString, list[str], bool]:
    """Try to parse a declarator. Return the name of it, its type string, and
    a flag for if we actually got one or not.
    """
    mods: list[TypeElem] = []
    name, args = declmods(state, mods)
    if name is None:
        return "", TypeString(basetype), [], False
    return name, TypeString(*mods, basetype), args, True


def declmods(state: ParseState, mods: list[TypeElem]) -> tuple[str | None, list[str]]:
    """Parse a declarator. Return the name of the delcarator matched and a
    list of any function arguments, with the stored modifiers in the passed
    list. If the name is None, then we did not find a declarator name.
    """
    args: list[str] = []
    if tkn := state.match("*", "(", "name"):
        match tkn.label:
            case "*":
                name, args = declmods(state, mods)
                mods.append(TypeElem(Type.POINT))
                return name, args
            case "(":
                name, args = declmods(state, mods)
                state.need(")")
            case "name":
                name = tkn.value
            case _:
                raise ValueError(tkn)
    else:
        return None, args
    while tkn := state.match("(", "["):
        match tkn.label:
            case "(":
                if not state.peekmatch(")") and args:
                    state.error(
                        "only one function specifier in a declaration can have arguments"
                    )
                args = grabargs(state)
                state.need(")")
                mods.append(TypeElem(Type.FUNC))
            case "[":
                if state.peekmatch("]"):
                    size = 1
                else:
                    size = conexpr(state)
                state.need("]")
                mods.append(TypeElem(Type.ARRAY, size))
            case _:
                raise ValueError(tkn)
    return name, args


def grabargs(state: ParseState) -> list[str]:
    """Grab up the argument names in a function declarator, leaving the
    trailing right paren.
    """
    args: list[str] = []
    while not state.peekmatch(")"):
        state.earlyeof()
        tkn = state.need("name")
        if tkn is None:
            return args
        args.append(tkn.value)
        if not state.peekmatch(")"):
            state.need(",")
    return args


def typeclass(state: ParseState) -> tuple[TypeElem | None, Storage | None]:
    """Parse a typeclass elements - a base type and/or a storage class, in
    either order. Return the values. Missing values contain None.
    """
    if basetype := grabtype(state):
        return basetype, grabclass(state)
    storage, basetype = grabclass(state), grabtype(state)
    return basetype, storage


def grabtype(state: ParseState) -> TypeElem | None:
    """Grab a base type, if any is present."""
    if tkn := state.match("int", "char", "float", "double", "struct"):
        match tkn.label:
            case "int":
                return TypeElem(Type.INT)
            case "char":
                return TypeElem(Type.CHAR)
            case "float":
                return TypeElem(Type.FLOAT)
            case "double":
                return TypeElem(Type.DOUBLE)
            case "struct":
                raise NotImplementedError
            case _:
                raise ValueError(tkn)
    return None


def grabclass(state: ParseState) -> Storage | None:
    """Parse a storage class, if any is here. Return None if not."""
    if tkn := state.match("auto", "extern", "register", "static"):
        match tkn.label:
            case "auto":
                return Storage.AUTO
            case "extern":
                return Storage.EXTERN
            case "register":
                return Storage.REGISTER
            case "static":
                return Storage.STATIC
            case _:
                raise ValueError(tkn)
    return None
