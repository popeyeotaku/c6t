"""C6T - C version 6 by Troy - Frontend Expression Node Labels"""

from enum import Enum, auto, unique

from . import lexer


@unique
class NLab(Enum):
    """All the possible labels for an expression node."""

    PREINC = auto()
    PREDEC = auto()
    POSTINC = auto()
    POSTDEC = auto()
    ADDR = auto()
    COND = auto()
    COMMA = auto()
    ARG = auto()
    LOGAND = auto()
    LOGOR = auto()
    CALL = auto()
    UCALL = auto()
    DEREF = auto()
    ASSIGN = auto()
    ASNADD = auto()
    ASNSUB = auto()
    ASNMULT = auto()
    ASNDIV = auto()
    ASNMOD = auto()
    ASNRSHIFT = auto()
    ASNLSHIFT = auto()
    ASNAND = auto()
    ASNEOR = auto()
    ASNOR = auto()
    NEG = auto()
    NOT = auto()
    TOINT = auto()
    TOFLT = auto()
    COMPL = auto()
    ADD = auto()
    MULT = auto()
    AND = auto()
    OR = auto()
    EOR = auto()
    DOT = auto()
    NAME = auto()
    ARROW = auto()
    SUB = auto()
    DIV = auto()
    LESS = auto()
    GREAT = auto()
    LEQU = auto()
    GEQU = auto()
    EQU = auto()
    NEQU = auto()
    CON = auto()
    UGEQU = auto()
    ULEQU = auto()
    UGREAT = auto()
    ULESS = auto()
    COLON = auto()
    FCON = auto()
    STRING = auto()
    NOP = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    MOD = auto()

    @property
    def opcode(self) -> str:
        """The IR opcode representation of the node label."""
        return self.name.lower()


UCMP = {
    NLab.GREAT: NLab.UGREAT,
    NLab.LESS: NLab.ULESS,
    NLab.GEQU: NLab.UGEQU,
    NLab.LEQU: NLab.ULEQU,
}

ASSIGNS = {key: value.upper() for key, value in lexer.ASSIGNS.items()}
