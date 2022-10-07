"""C6T - C version 6 by Troy - External Definition Parsing.

A C6T program is a series of external definitions, which declare data and
functions to exist, and optionally also initializer them. Function definitions
can be thought of as a special case of initialized data extdefs.

A central element of all this is the type declaration list. Since it is used
in many different places, we have a special function to handle one which
gets passed a callback function for different situations.
"""

import math
from typing import Callable, Literal

import expr
import statement
from c6tstate import MAXREGS, ParseState
from expr import conexpr
from symtab import Storage, Symbol
from type6 import Type, TypeElem, TypeString

START_OFFSET = 10  # Starting offset of parameters from the frame pointer


def extdef(state: ParseState):
    """Parse an external definition."""
    assert state.localscope is False
    typedecl_list(state, extdef_callback, need_typeclass=False)


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
        assert state.peekmatch(",", ";")
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
    assert not state.peekmatch(",", ";")
    state.goseg("data")
    state.deflabel("_" + name)
    state.pseudo("export", "_" + name)
    if (
        state.peekmatch("string")
        and len(typestr) == 2
        and typestr[0].label == Type.ARRAY
        and typestr[1].label == Type.CHAR
    ):
        token = state.match("string")
        assert token is not None and isinstance(token.value, bytes)
        state.pseudo("db", *(str(byte) for byte in token.value))
        realbytes = len(token.value)
    else:
        if state.peekmatch("{"):
            realbytes = datalist(state, typestr)
        else:
            realbytes = dataelem(state, typestr)
    if typestr[0].label == Type.ARRAY:
        if realbytes > typestr.size:
            arraysize = math.ceil(realbytes / typestr.sizenext())
            typestr = TypeString(TypeElem(Type.ARRAY, arraysize), *typestr.pop())
    if typestr.size > realbytes:
        state.pseudo("ds", str(typestr.size - realbytes))
    state.symtab[name].typestr = typestr


def datalist(state: ParseState, typestr: TypeString) -> int:
    """Parse a comma seperated list of data expressions, outputting them, and
    returning the total output size in bytes.
    """
    state.need("{")
    realsize = 0
    while not state.match("}"):
        state.earlyeof()
        realsize += dataelem(state, typestr)
        if not state.peekmatch("}"):
            state.need(",")
    return realsize


INIT_TYPE_CODES = {Type.INT: "w", Type.CHAR: "b", Type.FLOAT: "f", Type.DOUBLE: "d"}


def sign(i: int | float) -> Literal["-"] | Literal["+"]:
    """Return a sign character for the number."""
    if i < 0:
        return "-"
    return "+"


def dataelem(state: ParseState, typestr: TypeString) -> int:
    """Parse a single expression in a data initializer, output it, and return
    the total size in bytes.
    """
    try:
        basetype = init_type(typestr)
    except ValueError:
        state.error("bad type for an initializer")
        return 0
    try:
        name, con = dataexpr(state)
    except ValueError:
        state.error("bad data initializer")
        return 0
    if isinstance(con, float):
        assert name is None
        if basetype.label not in (Type.FLOAT, Type.DOUBLE):
            basetype = TypeElem(Type.DOUBLE)
    code = INIT_TYPE_CODES[basetype.label]
    if name and con:
        state.pseudo(f"d{code}", f"_{name}{sign(con)}{abs(con)}")
    elif name:
        state.pseudo(f"d{code}", f"_{name}")
    else:
        state.pseudo(f"d{code}", str(con))
    return basetype.size


def init_type(typestr: TypeString) -> TypeElem:
    """Return the base init type for a data initializer from the given
    TypeString. In other words, which data type should be output in the
    initializer assembly.
    """
    match typestr[0].label:
        case Type.POINT | Type.STRUCT | Type.INT:
            return TypeElem(Type.INT)
        case Type.FUNC:
            raise ValueError(typestr)
        case Type.ARRAY:
            return init_type(typestr.pop())
        case Type.CHAR | Type.FLOAT | Type.DOUBLE:
            return typestr[0]


def dataexpr(state: ParseState) -> tuple[str | None, int | float]:
    """Parse a data initializer expression. It should resolve to either an
    extern NAME, an integer or floating constant, or an extern plus an integer
    constant. Return these values.
    """
    node = expr.expression(state, seecommas=False)
    if (con := datacon(node)) is not None:
        return None, con
    if (name := dataname(node)) is not None:
        return name, 0
    if node.label == "add":
        name, con = dataname(node[0]), datacon(node[1])
        if name is None or not isinstance(con, int):
            con, name = datacon(node[0]), dataname(node[1])
        if name is None or not isinstance(con, int):
            raise ValueError(node)
        return name, con
    if node.label == "sub":
        name, con = dataname(node[0]), datacon(node[1])
        if name is None or not isinstance(con, int):
            raise ValueError(node)
        # pylint:disable=invalid-unary-operand-type
        return name, -con
    if node.label == "addr" and node[0].label == "dot":
        assert node[0][0].label == "name"
        assert isinstance(node[0][0].value, Symbol)
        assert isinstance(node[0][0].value.offset, str)
        assert node[0][1].label == "con"
        assert isinstance(node[0][1].value, int)
        return node[0][0].value.offset, node[0][1].value
    raise ValueError(node)


def datacon(node: expr.Node) -> int | float | None:
    """Return if the node is a valid data initializer constant (con or fcon),
    returning its value if so or None if not.
    """
    if node.label in ("con", "fcon"):
        assert isinstance(node.value, (int, float))
        return node.value
    return None


def dataname(node: expr.Node) -> str | None:
    """Checks if the node is a valid data initializer NAME
    (addr -> name node). If so, return the node name. Else, return None.
    """
    if node.label == "addr" and node[0].label == "name":
        assert isinstance(node[0].value, Symbol)
        assert isinstance(node[0].value.offset, str)
        return node[0].value.offset
    return None


def funcdef(state: ParseState, name: str, args: list[str], typestr: TypeString) -> None:
    """Parse a function definition."""
    state.goseg("text")
    state.deflabel("_" + name)
    state.pseudo("export", "_" + name)
    symbol = Symbol(Storage.EXTERN, name, typestr)
    state.symtab[name] = symbol
    state.golocal()
    grabparams(state, args)
    state.need("{")
    grablocals(state)
    state.goseg("text")
    while not state.match("}"):
        state.earlyeof()
        statement.statement(state)
    statement.retnull(state)
    state.exitlocal()


def grabparams(state: ParseState, args: list[str]) -> None:
    """Parse parameter type declarations."""
    argsyms: list[Symbol] = []
    for arg in args:
        symbol = Symbol(Storage.AUTO, 0, typestr=TypeString(Type.INT), local=True)
        argsyms.append(symbol)
        state.symtab[arg] = symbol

    def param_callback(
        state: ParseState,
        count: int,
        name: str,
        args: list[str],
        typestr: TypeString,
        storage: Storage,
    ) -> bool:
        """Callback after seeing a parameter declaration."""
        if name not in state.symtab or (
            name in state.symtab and state.symtab[name] not in argsyms
        ):
            state.error(f"undefined parameter {name}")
        else:
            symbol = state.symtab[name]
            symbol.typestr = typestr
        return False

    typedecl_list(state, param_callback, need_typeclass=True)
    auto_offset = START_OFFSET
    for sym in argsyms:
        match sym.typestr[0].label:
            case Type.FLOAT:
                sym.typestr = TypeString(Type.DOUBLE)
            case Type.ARRAY:
                sym.typestr = TypeString(Type.POINT, *sym.typestr.pop())
            case Type.CHAR:
                sym.typestr = TypeString(Type.INT)
            case Type.STRUCT:
                state.error("cannot pass structs")
            case _:
                pass

        sym.offset = auto_offset
        auto_offset += sym.typestr.size


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
            state.goseg("bss")
            state.defstatic(offset)
            state.pseudo("ds", str(typestr.size))
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
    while not state.eof():
        # Each step thru the loop processes one line of declarators
        # (from the typeclass to the trailling semicolon)
        # Unless the callback returns True, in which case we exit early.
        count = 0
        basetype, storage = typeclass(state)
        if basetype is None and storage is None and need_typeclass:
            break
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
                if not state.need(";"):
                    return gotany
                break
            gotany = True
            if callback(state, count, name, args, typestr, storage):
                break
            if not state.peekmatch(";"):
                state.need(",")
            count += 1
    return gotany


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
                return grabstruct(state)
            case _:
                raise ValueError(tkn)
    return None


def grabstruct(state: ParseState) -> TypeElem:
    """Grab a structure type spec, filling it in the tag table if necessary
    and returning the proper type elem with size.
    """
    fillin = False
    size = 0
    if token := state.match("name"):
        assert isinstance(token.value, str)
        name = token.value
        if name not in state.tags:
            state.tags[name] = Symbol(
                Storage.STRUCT, offset=0, typestr=TypeString(TypeElem(Type.STRUCT, 0))
            )
            fillin = True
    else:
        name = None
    membersize = grabmembers(state)
    if membersize is None and name is None:
        state.error("missing struct spec")
    elif membersize is None and name is not None:
        if fillin:
            state.error(f"undefined struct tag {name}")
        else:
            size = state.tags[name].offset
            assert isinstance(size, int)
    elif membersize is not None and name is not None:
        if fillin:
            size = membersize
            state.tags[name].offset = size
            state.tags[name].typestr = TypeString(TypeElem(Type.STRUCT, size))
        else:
            if state.tags[name].offset != membersize:
                state.error(f"bad struct redef {name}")
    else:
        raise ValueError(membersize, name)
    return TypeElem(Type.STRUCT, size)


def grabmembers(state: ParseState) -> int | None:
    """See any potential member type declarations are part of a struct type
    spec, returning the size of all members if any (None if not).
    """
    if not state.match("{"):
        return None
    offset = 0

    # pylint:disable=unused-argument
    def member_callback(
        state: ParseState,
        count: int,
        name: str,
        args: list[str],
        typestr: TypeString,
        storage: Storage,
    ) -> bool:
        """Callback for member definitions."""
        nonlocal offset
        if name in state.tags:
            member = state.tags[name]
            if (
                member.storage == Storage.MEMBER
                and member.typestr == typestr
                and member.offset == offset
            ):
                pass
            else:
                state.error("member redefinition")
        state.tags[name] = Symbol(
            Storage.MEMBER, offset, typestr, local=state.localscope
        )
        offset += typestr.size
        return False

    while not state.match("}"):
        state.earlyeof()
        if not typedecl_list(state, member_callback, need_typeclass=True):
            state.need("}")
            break
    return offset


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
