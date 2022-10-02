"""C6T - C version 6 by Troy - Operator Info"""

import lexer

CALL = {"call", "ucall"}

COMMUTATIVE = {"add"}

NEEDLVAL = {*lexer.ASSIGNS.values(), "postinc", "preinc", "postdec", "predec", "dot"}

ISLVAL = {"name", "deref", "arrow", "dot"}
