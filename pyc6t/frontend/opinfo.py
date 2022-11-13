"""C6T - C version 6 by Troy - Operator Info"""

from .nlab import NLab

CALL = {NLab.CALL, NLab.UCALL}

ASSIGNS = {
    NLab.ASSIGN,
    NLab.ASNADD,
    NLab.ASNSUB,
    NLab.ASNMULT,
    NLab.ASNDIV,
    NLab.ASNMOD,
    NLab.ASNRSHIFT,
    NLab.ASNLSHIFT,
    NLab.ASNAND,
    NLab.ASNEOR,
    NLab.ASNOR,
}

UNARY = (
    NLab.NEG,
    NLab.NOT,
    NLab.ADDR,
    NLab.DEREF,
    NLab.PREINC,
    NLab.PREDEC,
    NLab.POSTINC,
    NLab.POSTDEC,
    NLab.TOINT,
    NLab.TOFLT,
    NLab.COMPL,
)

COMMAS = {NLab.COMMA, NLab.ARG}

COMMUTATIVE = {NLab.ADD, NLab.MULT, NLab.AND, NLab.OR, NLab.EOR}

NEEDLVAL = {*ASSIGNS, NLab.POSTINC, NLab.PREINC, NLab.POSTDEC, NLab.PREDEC, NLab.DOT}

ISLVAL = {NLab.NAME, NLab.DEREF, NLab.ARROW, NLab.DOT}

SUPPORTS_FLOAT = {
    NLab.ADD,
    NLab.SUB,
    NLab.MULT,
    NLab.DIV,
    NLab.LESS,
    NLab.GREAT,
    NLab.LEQU,
    NLab.GEQU,
    NLab.EQU,
    NLab.NEQU,
    NLab.TOINT,
    NLab.ASSIGN,
}

LESSGREAT = {NLab.LESS, NLab.GREAT, NLab.LEQU, NLab.GEQU}

CMP = {*LESSGREAT, NLab.EQU, NLab.NEQU}

ISINT = {*CMP, NLab.LOGOR, NLab.LOGAND}

NOFLTOP = {NLab.TOINT, NLab.TOFLT, NLab.DOT, NLab.ARROW}
