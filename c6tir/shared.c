#include "shared.h"

/* C6TIR - Backend for C6T - SHARED CODE */

struct cnode **cnpnt cnstk;

/* Return a flag if the character is alphabetic */
alpha(c)
{
	return (
		(c >= 'a' && c <= 'z')
		|| (c >= 'A' && c <= 'Z')
		|| (c == '_')
		|| (c == '.')
		|| (c == '~')
	);
}

/* Return a flag if the character is alphabetic or numeric */
alphanum(c)
{
	return (
		(c >= '0' && c <= '9')
		|| alpha(c)
	);
}

/* Return a flag if two null terminated strings compare equal */
strcmp(string1, string2)
{
	register char *s1, *s2;

	s1 = string1;
	s2 = string2;

	for (;;) {
		if (*s1 != *s2) return (0);
		if (!*s1++ || !*s2++) break;
	}
	return (1);
}

struct kwinfo {
	char *kwname;
	int kwval;
} cmdtab[] {
	"BYTE", BYTE,
	"WORD", WORD,
	"FLOAT", FLOAT,
	"DOUBLE", DOUBLE,
	"STORAGE", STORAGE,
	"AUTOS", AUTOS,
	"USEDREGS", USEDREGS,
	"RET", RET,
	"FRET", FRET,
	"RETNULL", RETNULL,
	"FUNC", FUNC,
	"EXPORT", EXPORT,
	"ENDFUNC", ENDFUNC,
	"JMP", JMP,
	"BRZ", BRZ,
	"FBRZ", FBRZ,
	"EVAL", EVAL,
	"SWITCH", SWITCH,
	"END", END,
	"CODE", CODE,
	"DATA", DATA,
	"BSS", BSS,
	"STRING", STRING,
	"STKJMP", STKJMP,
	"COMMON", COMMON,
	"SWEASY", SWEASY,
	0,
}, nodetab[] {
	"NULL", NULL,
	"CON", CON,
	"FCON", FCON,
	"LOAD", LOAD,
	"CLOAD", CLOAD,
	"FLOAD", FLOAD,
	"DLOAD", DLOAD,
	"ASSIGN", ASSIGN,
	"CASSIGN", CASSIGN,
	"FASSIGN", FASSIGN,
	"DASSIGN", DASSIGN,
	"QUEST", QUEST,
	"COLON", COLON,
	"LOGOR", LOGOR,
	"LOGAND", LOGAND,
	"OR", OR,
	"EOR", EOR,
	"AND", AND,
	"EQU", EQU,
	"NEQU", NEQU,
	"LESS", LESS,
	"GREAT", GREAT,
	"LEQU", LEQU,
	"GEQU", GEQU,
	"RSHIFT", RSHIFT,
	"LSHIFT", LSHIFT,
	"ADD", ADD,
	"SUB", SUB,
	"MULT", MULT,
	"DIV", DIV,
	"MOD", MOD,
	"NEG", NEG,
	"LOGNOT", LOGNOT,
	"LOG", LOG,
	"COMPL", COMPL,
	"PREINC", PREINC,
	"PREDEC", PREDEC,
	"POSTINC", POSTINC,
	"POSTDEC", POSTDEC,
	"CPREINC", CPREINC,
	"CPREDEC", CPREDEC,
	"CPOSTINC", CPOSTINC,
	"CPOSTDEC", CPOSTDEC,
	"CALL", CALL,
	"ARG", ARG,
	"TOFLT", TOFLT,
	"TOINT", TOINT,
	"ULESS", ULESS,
	"UGREAT", UGREAT,
	"ULEQU", ULEQU,
	"UGEQU", UGEQU,
	"AUTO", AUTO,
	"REG", REG,
	"ASNADD", ASNADD,
	"ASNSUB", ASNSUB,
	"ASNMULT", ASNMULT,
	"ASNDIV", ASNDIV,
	"ASNMOD", ASNMOD,
	"ASNRSHIFT", ASNRSHIFT,
	"ASNLSHIFT", ASNLSHIFT,
	"ASNAND", ASNAND,
	"ASNEOR", ASNEOR,
	"ASNOR", ASNOR,
	"CASNADD", CASNADD,
	"CASNSUB", CASNSUB,
	"CASNMULT", CASNMULT,
	"CASNDIV", CASNDIV,
	"CASNMOD", CASNMOD,
	"CASNRSHIFT", CASNRSHIFT,
	"CASNLSHIFT", CASNLSHIFT,
	"CASNAND", CASNAND,
	"CASNEOR", CASNEOR,
	"CASNOR", CASNOR,
	"COMMA", COMMA,
	0,
};

/* Push a core node onto the stack */
push(node)
{
	if (cnpnt >= &cnstk[CNSTK])
		crash("OUT OF NODE STACK SPACE");
	*cnpnt++ = node;
}

/* Crash with an error message */
crash(msg)
{
	extern fout, yyline;

	flush();
	fout = 2;
	printf("%l: %s\n", yyline, msg);
	flush();
	abort();
}

char *namepnt nameland;
int *argpnt argland;

/* Place a new value into the argland */
putarg(i)
{
	if (argpnt >= &argland[ARGLAND])
		crash("OUT OF ARG SPACE");
	*argpnt++ = i;
}

/* Place a character into the NAMELAND */
namec(c)
{
	if (namepnt >= &nameland[NAMELAND])
		crash("OUT OF NAME SPACE");
	*namepnt++ = c;
}

/* Place a NAME into the NAMELAND */
putname(name)
{
	register char *n, c, *new;

	if (new = findname(n = name)) return (new);
	new = namepnt;
	while (c = *n++) namec(c);
	namec(0);
	return (new);
}

/* Create and return a CON arg */
con(i)
{
	register *new;

	new = argpnt;
	putarg(ACON);
	putarg(i);
	return (new);
}

/* Create and return a NAME arg */
name(n)
{
	register *new;

	new = argpnt;
	putarg(ANAME);
	putarg(putname(n));
	return (new);
}

/* Create and return an OFFSET arg */
offset(n, i)
{
	register *new;

	new = argpnt;
	putarg(AOFFSET);
	putarg(putname(n));
	putarg(i);
	return (new);
}

/* Create and return an ARGLIST arg */
arglist(left, right)
{
	register *new;

	new = argpnt;
	putarg(ALIST);
	putarg(left);
	putarg(right);
	return (new);
}

/* Find an existing NAME in NAMELAND, returning it if found.
 * Else, return 0.
 */
findname(n)
{
	register char *pnt;

	for (pnt = nameland; pnt < namepnt; ) {
		if (strcmp(n, pnt)) return (pnt);

		/* Skip to next null terminator */
		while (*pnt && pnt < namepnt) pnt++;
		/* Skip that null terminator to next string */
		pnt++;
	}
	return (0);
}

/* Cleanup after every line */
cleanup()
{
	argpnt = argland;
}

/* Remove a core node from the node stack */
pop()
{
	if (cnpnt <= cnstk) crash("NO NODE TO POP");
	return (*--cnpnt);
}

/* Table for number of children for each node */
char childtab[] {
	0,	/* NULL */
	0,	/* CON */
	0,	/* FCON */
	1,	/* LOAD */
	1,	/* CLOAD */
	1,	/* FLOAD */
	1,	/* DLOAD */
	2,	/* ASSIGN */
	2,	/* CASSIGN */
	2,	/* FASSIGN */
	2,	/* DASSIGN */
	2,	/* QUEST */
	2,	/* COLON */
	2,	/* LOGOR */
	2,	/* LOGAND */
	2,	/* OR */
	2,	/* EOR */
	2,	/* AND */
	2,	/* EQU */
	2,	/* NEQU */
	2,	/* LESS */
	2,	/* GREAT */
	2,	/* LEQU */
	2,	/* GEQU */
	2,	/* RSHIFT */
	2,	/* LSHIFT */
	2,	/* ADD */
	2,	/* SUB */
	2,	/* MULT */
	2,	/* DIV */
	2,	/* MOD */
	1,	/* NEG */
	1,	/* LOGNOT */
	1,	/* LOG */
	1,	/* COMPL */
	0,	/* REG */
	1,	/* PREINC */
	1,	/* PREDEC */
	1,	/* POSTINC */
	1,	/* POSTDEC */
	1,	/* CPREINC */
	1,	/* CPREDEC */
	1,	/* CPOSTINC */
	1,	/* CPOSTDEC */
	2,	/* CALL */
	2,	/* ARG */
	1,	/* TOFLT */
	1,	/* TOINT */
	2,	/* ULESS */
	2,	/* UGREAT */
	2,	/* ULEQU */
	2,	/* UGEQU */
	0,	/* AUTO */
	2,	/* ASNADD */
	2,	/* ASNSUB */
	2,	/* ASNMULT */
	2,	/* ASNDIV */
	2,	/* ASNMOD */
	2,	/* ASNRSHIFT */
	2,	/* ASNLSHIFT */
	2,	/* ASNAND */
	2,	/* ASNEOR */
	2,	/* ASNOR */
	2,	/* CASNADD */
	2,	/* CASNSUB */
	2,	/* CASNMULT */
	2,	/* CASNDIV */
	2,	/* CASNMOD */
	2,	/* CASNRSHIFT */
	2,	/* CASNLSHIFT */
	2,	/* CASNAND */
	2,	/* CASNEOR */
	2,	/* CASNOR */
	2,	/* COMMA */
};

/* Construct a new core node. */
build(lab, args)
int *args;
{
	register *n;

	if (lab == NULL) return (0);

	n = cnalloc(lab);

	switch (childtab[lab]) {
	case 0:
		break;
	case 2:
		n->nright = pop();
		/* fall thru */
	case 1:
		n->nleft = pop();
		break;
	default:
		crash("BAD CHILD COUNT");
	}

	if (args) switch (*args) {
	case ACON:
		n->ncon = args[1];
		break;
	case ANAME:
		n->nname = args[1];
		break;
	case AOFFSET:
		n->nname = args[1];
		n->ncon = args[2];
		break;
	default:
		crash("BAD NODE ARGS");
	}
	return (coptim(n));
}

/* Allocate a core node */
cnalloc(lab)
{
	register struct cnode *pnt;

	for (pnt = cnland; pnt < &cnland[CNLAND]; pnt++) {
		if (pnt->nlab == UNALLOC) {
			clear(pnt, sizeof(*pnt));
			pnt->nlab = lab;
			return (pnt);
		}
	}
	crash("OUT OF CORE NODES");
}

/* Optimize core nodes */
coptim(npnt)
{
	register *n, i;

	n = npnt;

again:
	switch (n->nlab) {
	case SUB:
		if (conbasic(n->nright)) {
			n->nright->ncon = -n->nright->ncon;
			n->nlab = ADD;
			goto again;
		}
		if (zero(n->nright)) return (n->nleft);
		break;
	case ADD:
		if (chain(n, n->nleft, n->nright)) goto again;
		if (conbasic(n->nleft) && (n->nright->nlab == CON
				|| n->nright->nlab == AUTO)) {
			/* handle a plain integer being added to a
			 * "name" con.
			 */
			n->nright->ncon =+ n->nleft->ncon;
			n = n->nright;
			goto again;
		}
		if (conbasic(n->nright) && (n->nleft->nlab == CON
				|| n->nleft->nlab == AUTO)) {
			/* same as last but for other side */
			n->nleft->ncon =+ n->nright->ncon;
			n = n->nleft;
			goto again;
		}
		if (zero(n->nleft)) return (n->nright);
		if (zero(n->nright)) return (n->nleft);
		break;
	case MULT:
		if (chain(n, n->nleft, n->nright)) goto again;
		if (one(n->nleft)) return (n->nright);
		if (one(n->nright)) return (n->nleft);
		if ((i = pow2(n->nright)) != -1) {
			n->nlab = LSHIFT;
			n->nright->ncon = i;
			goto again;
		}
		if ((i = pow2(n->nleft)) != -1) {
			n->nlab = LSHIFT;
			n->nleft->ncon = i;
			i = n->nleft;
			n->nleft = n->nright;
			n->nright = i;
			goto again;
		}
		break;
	case DIV:
		if (one(n->nright)) return (n->nleft);
		if (zero(n->nleft)) return (n->nright);
		if ((i = pow2(n->nright)) != -1) {
			n->nlab = RSHIFT;
			n->nright->ncon = i;
			goto again;
		}
		break;
	case MOD:
		if ((i = pow2(n->nright)) != -1) {
			n->nlab = AND;
			n->nright->ncon = (1<<i)-1;
			goto again;
		}
		break;
	case OR:
	case AND:
	case EOR:
		if (chain(n, n->nleft, n->nright)) goto again;
		break;
	case EQU:
	case NEQU:
		if (zero(n->nright)) {
			n->nlab = n->nlab == EQU ? LOGNOT : LOG;
			n->nright = 0;
			goto again;
		} else if (zero(n->nleft)) {
			n->nlab = n->nlab == EQU ? LOGNOT : LOG;
			n->nleft = n->nright;
			n->nright = 0;
			goto again;
		}
		break;
	}

	return (n);
}

/* Return a flag if the node is a CON w/o a NAME, only a number */
conbasic(n)
{
	return (n && n->nlab == CON && !n->nname);
}

chain(npnt, lpnt, rpnt)
{
	register *n, *left, *right;

	if (!(n = npnt)) return (0);

	if (!(left = lpnt)) return (0);
	if (!(right = rpnt)) return (0);

	if (conbasic(left) && right->nlab == n->nlab) {
		if (conbasic(right->nleft)) {
			_chain(n, left, right->nleft);
			n->nright = right->nright;
			return (1);
		}
		if (conbasic(right->nright)) {
			_chain(n, left, right->nright);
			n->nright = right->nleft;
			return (1);
		}
		if (right->nleft->nlab == n->nlab)
			return (chain(n, left, right->nleft));
		if (right->nright->nlab == n->nlab)
			return (chain(n, left, right->nright));
	} else if (conbasic(right) && left->nlab == n->nlab) {
		if (conbasic(left->nleft)) {
			_chain(n, right, left->nleft);
			n->nleft = left->nright;
			return (1);
		}
		if (conbasic(left->nright)) {
			_chain(n, right, left->nright);
			n->nleft = left->nleft;
			return (1);
		}
		if (left->nleft->nlab == n->nlab)
			return (chain(n, left->nleft, right));
		if (left->nright->nlab == n->nlab)
			return (chain(n, left->nright, right));
	}
	return (0);
}

_chain(n, left, right)
{
	switch (n->nlab) {
	default:
		crash("BAD CHAIN");
	case ADD:
		left->ncon =+ right->ncon;
		break;
	case MULT:
		left->ncon =* right->ncon;
		break;
	case AND:
		left->ncon =& right->ncon;
		break;
	case OR:
		left->ncon =| right->ncon;
		break;
	case EOR:
		left->ncon =^ right->ncon;
		break;
	}
}

pow2(n)
{
	register i, c;
	if (n && n->nlab == CON && !n->nname) {
		c = n->ncon;
		for (i = 0; i < 16; i++)
			if (1<<i == c) return (i);
	}
	return (-1);
}

iscon(n, val)
{
	return (n && n->nlab == CON && !n->nname && n->ncon == val);
}

zero(n)
{
	return (iscon(n, 0));
}

one(n)
{
	return (iscon(n, 1));
}

/* Clear a number of bytes */
clear(start, count)
{
	register char *pnt;
	register i;

	pnt = start;
	i = count;

	while (i--) *pnt++ = 0;
}

/* Table of argument counts for each command (-1 if variable count).
 */
char cmdargs[] {
	0,	/* NULL */
	-1,	/* BYTE */
	-1,	/* WORD */
	-1,	/* FLOAT */
	-1,	/* DOUBLE */
	1,	/* STORAGE */
	1,	/* AUTOS */
	1,	/* USEDREGS */
	0,	/* RET */
	0,	/* FRET */
	0,	/* RETNULL */
	1,	/* FUNC */
	-1,	/* EXPORT */
	0,	/* ENDFUNC */
	1,	/* JMP */
	1,	/* BRZ */
	1,	/* FBRZ */
	0,	/* EVAL */
	3,	/* SWITCH */
	0,	/* END */
	0,	/* CODE */
	0,	/* DATA */
	0,	/* BSS */
	0,	/* STRING */
	0,	/* STKJMP */
	2,	/* COMMON */
	4,	/* SWEASY */
};

/* Table of flags for if a command consumes a node.
 */
char cmdnode[] {
	0,	/* NULL */
	0,	/* BYTE */
	0,	/* WORD */
	0,	/* FLOAT */
	0,	/* DOUBLE */
	0,	/* STORAGE */
	0,	/* AUTOS */
	0,	/* USEDREGS */
	1,	/* RET */
	1,	/* FRET */
	0,	/* RETNULL */
	0,	/* FUNC */
	0,	/* EXPORT */
	0,	/* ENDFUNC */
	0,	/* JMP */
	1,	/* BRZ */
	1,	/* FBRZ */
	1,	/* EVAL */
	1,	/* SWITCH */
	0,	/* END */
	0,	/* CODE */
	0,	/* DATA */
	0,	/* BSS */
	0,	/* STRING */
	1,	/* STKJMP */
	0,	/* COMMON */
	1,	/* SWEASY */
};

/* Execute a command */
docmd(cmd, args)
{
	register *n;

	if (cmdargs[cmd] != -1 && argcount(args) != cmdargs[cmd])
		crash("BAD ARG COUNT FOR COMMAND");

	if (cmdnode[cmd]) {
		n = pop();
		if (cnpnt != cnstk) crash("TOO MANY NODES");
	} else n = 0;

	cmdoptim(cmd, args, n);
	backcmd(cmd, args, n);

	/* Free all nodes */
	clearn();
	/* Remove all NAMEs */
	namepnt = nameland;
}

/* Optimize commands before executing on backend */
cmdoptim(cmd, args, n)
{
	switch (cmd) {
	case EVAL:
		switch (n->nlab) {
		case POSTINC:
			n->nlab = PREINC;
			break;
		case POSTDEC:
			n->nlab = PREDEC;
			break;
		case CPOSTINC:
			n->nlab = CPREINC;
			break;
		case CPOSTDEC:
			n->nlab = CPREDEC;
			break;
		}
		break;
	}
}

/* Free all core nodes */
clearn()
{
	register struct cnode *pnt;

	for (pnt = cnland; pnt < &cnland[CNLAND]; pnt++)
		pnt->nlab = UNALLOC;
}

/* Calculate number of arguments */
argcount(arg)
int *arg;
{
	if (!arg) return (0);
	if (*arg == ALIST)
		return (argcount(arg[1]) + argcount(arg[2]));
	return (1);
}

yyinit(argc, argv) char **argv;
{
	extern fin, fout, yydebug;
	register i;

	clearn();

	fout = dup(1);	/* make output buffered */

	if (argc > 1) {
		--argc;
		fin = open(*++argv, 0);
		if (fin < 0) return;
	}
	if (argc > 1) yydebug++;
}

/* Output a NAME and CON combo */
output(n, c)
{
	if (n && c)
		printf("%s+%l", n, c);
	else if (n)
		printf("%s", n);
	else printf("%l", c);
}

/* Output an argument */
outarg(arg)
int *arg;
{
	if (!arg) crash("NO ARG");
	switch (*arg) {
	case ACON:
		output(0, arg[1]);
		break;
	case ANAME:
		output(arg[1], 0);
		break;
	case AOFFSET:
		output(arg[1], arg[2]);
		break;
	default:
		crash("BAD ARG");
	}
}

/* Output an argument list seperated by commas */
outlist(args, count)
int *args;
{
	register c;

	if (!args) return (count);
	else if (*args == ALIST) {
		if (c = count) putchar(',');
		c = outlist(args[1], c);
		if (c) putchar(',');
		return (outlist(args[2], c));
	}
	else {
		outarg(args);
		return (count+1);
	}
}

yyaccpt()
{
	flush();
	exit(0);
}

casecmp(left, right)
{
	register char *s1, *s2, c;

	s1 = right;
	s2 = left;

	do {
		c = *s1++;
		if (c>='a' && c<='z')
			c =- 'a' - 'A';
		if (c != *s2++)
			return (0);
	} while (c);
	return (1);
}
