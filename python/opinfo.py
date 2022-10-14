"""C6T - C version 6 by Troy - Operator Info"""

import lexer

CALL = {"call", "ucall"}

ASSIGNS = {*lexer.ASSIGNS.values()}

UNARY = (
    "neg",
    "not",
    "addr",
    "deref",
    "preinc",
    "predec",
    "postinc",
    "postdec",
    "toint",
    "toflt",
    'compl',
)

COMMAS = {'comma', 'arg'}

COMMUTATIVE = {"add", "mult", "and", "or", "eor"}

NEEDLVAL = {*ASSIGNS, "postinc", "preinc", "postdec", "predec", "dot"}

ISLVAL = {"name", "deref", "arrow", "dot"}

SUPPORTS_FLOAT = {
    "add",
    "sub",
    "mult",
    "div",
    "less",
    "great",
    "lequ",
    "gequ",
    "equ",
    "nequ",
    "toint",
    'assign',
}

LESSGREAT = {"less", "great", "lequ", "gequ"}

CMP = {*LESSGREAT, "equ", "nequ"}

ISINT = {*CMP}

NOFLTOP = {"toint", "toflt", "dot", "arrow"}
