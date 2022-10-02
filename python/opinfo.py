"""C6T - C version 6 by Troy - Operator Info"""

import lexer

CALL = {"call", "ucall"}

UNARY = ("neg", "not", "addr", "deref", "preinc", "predec", "postinc", "postdec")

COMMUTATIVE = {"add", "mult", "and", "or", "eor"}

NEEDLVAL = {*lexer.ASSIGNS.values(), "postinc", "preinc", "postdec", "predec", "dot"}

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
}
