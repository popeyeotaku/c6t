#include "c6t.h"

/* C6T - C version 6 by Troy - PART SIX */

/* Output an expression tree to the backend */
outexpr(n)
{
	outnode(n);
	rval(n);
}

/* If a node is an lval (an unloaded address or register), issue a
 * backend node to load it.
 */
rval(n)
{
	if (n && lval(n))
		printf("%cLOAD\n", typechar(&n->ntype));
}

/* Given a type string, return a type character
 * for its actual storage in memory (null for word size 'C' for byte
 * size, 'F' for float size, 'D' for double size).
 */
typechar(type)
{
	register t;

	t = type->tystr;
	switch (t&TYMOD) {
	case TYPOINT:
	case TYARRAY:
	case TYFUNC:
		return (0);
	case 0:
		switch (t&TYBASE) {
		case TYINT:
			return (0);
		case TYCHAR:
			return ('C');
		case TYFLOAT:
			return ('F');
		case TYDOUBLE:
			return ('D');
		}
	}
	crash("BAD TYPE STRING %o", t);
}

/* Recursively output an expression tree node to the backend.
 */
outnode(npnt)
{
	register *n, info, i;

	if (!(n = npnt)) return;
	if (n->nlab == 0) return;

	info = opinfo(n->nlab);

	/* Special cases which don't descend */
	switch (n->nlab) {
	case CON:
		printf("CON %l\n", n->nval);
		return;
	case FCON:
		crash("FLOATING CONSTANTS NOT SUPPORTED");
	case NAME:
		if (!n->nval) crash("MISSING NAME SYMBOL");
		switch (n->nval->sclass) {
		default:
			crash("BAD STORAGE CLASS");
		case EXTERN:
			printf("CON %x\n", n->nval->sname);
			return;
		case AUTO:
			printf("AUTO %l\n", n->nval->soffset);
			return;
		case STATIC:
			printf("CON %t\n", n->nval->soffset);
			return;
		case REGISTER:
			printf("REG %l\n", n->nval->soffset);
			return;
		}
		return;
	case STRING:
		printf("CON %t\n", n->nval);
		return;
	case CALL:
		outargs(n->nright);
		outnode(n->nleft);
		printf("CALL\n");
		return;
	}

	/* Normal case, handle children first */
	outnode(n->nleft);
	if (!(info&OPNEEDLVAL)) rval(n->nleft);
	outnode(n->nright);
	rval(n->nright);

	/* Output the actual code */
	switch (n->nlab) {
	default:
		printf("%c%e\n",
			(info&OPYESFLT && (isflt(n->nleft)||isflt(n->nright)))
			? 'F' : 0,
			n->nlab
		);
		break;
	case DOT:
	case ARROW:
		printf("ADD\n");
		break;
	case ADDR:
	case DEREF:
		/* do nothing */
		break;
	case ASSIGN:
	case ASNADD:
	case ASNSUB:
	case ASNMULT:
	case ASNDIV:
	case ASNMOD:
	case ASNRSHIFT:
	case ASNLSHIFT:
	case ASNAND:
	case ASNEOR:
	case ASNOR:
		printf("%c%e\n", typechar(&n->nleft->ntype), n->nlab);
		break;
	case PREINC:
	case PREDEC:
	case POSTINC:
	case POSTDEC:
		i = ispnt(n->nleft) ? sizenext(&n->nleft->ntype) : 1;
		if (n->nlab == PREDEC || n->nlab == POSTDEC)
			i = -i;
		printf("%c%s %l\n",
			typechar(&n->nleft->ntype),
			n->nlab >= POSTINC ? "POST" : "PRE",
			i
		);
		break;
	}
}

/* Output a NAME */
putnam(name)
{
	register char *pnt;
	register i, c;

	if (!(pnt = name)) return;
	i = NAMELEN;
	while (i-- && (c = *pnt++)) putchar(c);
}

/* Output recursively a function call's arguments to the backend.
 */
outargs(n)
{
	if (!n) {
		printf("NULL\n");
		return;
	}
	else if (n->nlab == ARG) {
		outargs(n->nleft);
		outargs(n->nright);
		printf("ARG\n");
	}
	else {
		outnode(n);
		rval(n);
	}
}

/* This code processes a series of specifier lines (called "DECLARATORS"
 * in other versions of C).
 * Each line consists of a leading typeclass, followed by a chain of
 * comma-seperated specifiers, ending with a semicolon.
 * After each specifier is
 * seen, a callback function is executed. Afterwards, in
 * an EXTERN context, if the specifier was function type, the line is
 * ended early, without a trailing semicolon.
 * Also in an EXTERN context, the typeclass is optional.
 */
speclist(context, callback)
int (*callback)();
{
	register *sym, t, exitearly;
again:
	if ((peektkn = token()) == EOF) return;
	if (!typeclass() && context != EXTERN) return;

	do {
		sym = spec();
		if (!sym) break;
		t = curtype.tystr;
		exitearly = (t&TYMOD)==TYFUNC
			&& context == EXTERN
			&& (peektkn=token()) != SEMICOLON
			&& peektkn != COMMA
		;
		(*callback)(sym);
		if (exitearly)
			goto again;
	} while (match(COMMA));
	skipneed(SEMICOLON);
	goto again;
}

/* Like need, but if it doesn't match, also skip
 * to the next terminal token.
 */
skipneed(lab)
{
	if (!match(lab)) {
		error("missing expected %e", lab);
		errskip();
	}
}

/* Process a series of external definitions. */
extdef()
{
	extern cbext();
	speclist(EXTERN, cbext);
}

/* Process a typeclass, returning a flag for if we saw either.
 */
typeclass()
{
	register got;

	curclass = localscope ? AUTO : EXTERN;
	basetype.tystr = TYINT;

	if (grabtype()) {
		grabclass();
		return (1);
	}
	got = grabclass();
	return (got | grabtype());
}
