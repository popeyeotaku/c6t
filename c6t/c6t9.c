#include "c6t.h"

/* C6T - C version 6 by Troy - PART NINE */

/* Add a CASE entry */
addcase(con, lab)
{
	if (!begcase) {
		error("case outside of switch");
		return;
	}
	if (endcase >= &caseland[CASELAND])
		crash("OUT OF CASE SPACE");

	endcase->clab = lab;
	endcase->cval = con;
	endcase++;
}

/* Output a switch statement */
outswitch(n, lab1)
{
	register casenum, tablab;
	register struct caseinfo *cpnt;
	static def, range;

	goseg(CODE);
	jump(curbrk);
	deflab(lab1);

	if (!(def = curdef)) def = curbrk;

	casenum = endcase - begcase;
	if (!casenum) {
		goseg(CODE);
		outexpr(n);
		nfree(n);
		jump(def);
		return;
	}
	if (casenum == 1) {
		n = build(EOF, build(EQU, n, con(begcase->cval)));
		brz(n, def);
		nfree(n);
		jump(begcase->clab);
		return;
	}

	sortcase();
	/* If the range of the cases is not too different from the number of cases,
	 * use a direct table lookup instead.
	 */
	range = (endcase-1)->cval - begcase->cval;
	if (range > 0 && range <= 3*casenum) {
		goseg(DATA);
		deflab(tablab = ++nextstatic);
		cpnt = begcase;
		for (casenum = begcase->cval; casenum <= (endcase-1)->cval; casenum++) {
			if (cpnt->cval == casenum) {
				printf("WORD %t\n", cpnt->clab);
				cpnt++;
			} else printf("WORD %t\n", def);
		}

		goseg(CODE);
		outexpr(n);
		nfree(n);
		printf("SWEASY %t,%t,%l,%l\n", tablab, def, begcase->cval, range);
		return;
	}

	goseg(DATA);
	deflab(tablab = ++nextstatic);

	for (cpnt=begcase; cpnt < endcase; cpnt++)
		printf("WORD %l,%t\n", cpnt->cval, cpnt->clab);
	goseg(CODE);
	outexpr(n);
	nfree(n);
	printf("SWITCH %t,%t,%l\n", tablab, def, casenum);
}

/* Sort all cases in ascending order */
sortcase()
{
	/* sorry for using bubblesort, don't want to have to link in qsort */
	register struct caseinfo *cpnt;
	static char swapped;
	register savelab, saveval;

	do {
		swapped = 0;
		for (cpnt = begcase; cpnt < endcase-1; cpnt++)
			if (cpnt->cval > (cpnt+1)->cval) {
				swapped++;
				savelab = cpnt->clab;
				saveval = cpnt->cval;
				cpnt->cval = (cpnt+1)->cval;
				cpnt->clab = (cpnt+1)->clab;
				(cpnt+1)->cval = saveval;
				(cpnt+1)->clab = savelab;
			}
	} while (swapped);
}

/* Parse and output an initialized piece of data */
datainit(sym)
{
	register elemtype, elems, t;
	static size;

	goseg(DATA);
	printf("%x:EXPORT %x\n", sym->sname, sym->sname);
	if (sym->sclass) {
		if (sym->stype.tystr != curtype.tystr
				&& sym->sclass != EXTERN)
			redef(sym);
	}
	else sym->sclass = EXTERN;
	sym->sflags = 0;
	tycopy(&curtype, &sym->stype);

	if (curtype.tystr == (TYARRAY|TYCHAR) && match(STRING)) {
		dumpstr();
		elems = sizeland[curtype.tyarray]&0377;
		if (elems > tlen+1)
			printf("STORAGE %l\n", elems-(tlen+1));
		else
			curtype.tyarray = addsize(tlen+1);
	}
	else {
		t = curtype.tystr;
		while ((t&TYMOD)==TYARRAY)
			t = ((t>>TYLEN)&~(TYTOP|TYBASE))|(t&TYBASE);
		switch (elemtype = t) {
		case TYINT:
			printf("WORD ");
			break;
		case TYCHAR:
			printf("BYTE ");
			break;
		case TYFLOAT:
			printf("FLOAT ");
			break;
		case TYDOUBLE:
			printf("DOUBLE ");
			break;
		default:
			printf("WORD ");
			elemtype = TYINT;
			break;
		}

		if (match(LBRACE)) {
			elems = 0;
			do {
				earlyeof();
				if ((peektkn=token())
					==RBRACE) break;
				elems =+ initelem(elemtype);
				if ((peektkn=token())
						!= RBRACE) {
					if (elems%8==0) {
					putchar('\n');
					switch (elemtype) {
					case TYINT:
					default:
						printf("WORD ");
						break;
					case TYCHAR:
						printf("BYTE ");
						break;
					case TYFLOAT:
						printf("FLOAT ");
						break;
					case TYDOUBLE:
						printf("DOUBLE ");
						break;
					}}
					else putchar(',');
				}
			} while (match(COMMA));
			skipneed(RBRACE);
		} else elems = initelem(elemtype);
		printf("\n");

		switch (elemtype) {
		case TYINT:
			size = elems*2;
			break;
		case TYCHAR:
			size = elems;
			break;
		case TYFLOAT:
			size = elems*4;
			break;
		case TYDOUBLE:
			size = elems*8;
			break;
		default:
			crash("BAD INIT");
		}

		if ((curtype.tystr&TYMOD)==TYARRAY) {
			elems = roundup(size, sizenext(&curtype));
			if (ugt(elems, sizeland[curtype.tyarray&0377]))
				sizeland[curtype.tyarray&0377] = elems;
			size = elems * sizenext(&curtype);
		}
		if (tysize(&curtype) - size)
			printf("STORAGE %l\n", tysize(&curtype) - size);
	}
}

/* Return the two numbers, divided unsigned, and rounded up.
 */
roundup(left, right)
{
	extern ldivr;
	register i;

	i = ldiv(0, left, right);
	return (i + ldivr ? 1 : 0);
}

/* Unsigned greater than flag */
ugt(left, right)
char *left, *right;	/* pointers compare unsigned */
{
	return (left > right);
}

/* Parse an initializer expression, consisting of an ADDR->NAME,
 * a CON, an FCON, or an ADDR->NAME plus a CON.
 * Returns the node of the COn/FCON part, and sets the pointed
 * namedest to the symbol for the NAME part, or 0 if no NAME.
 */
initexpr(namedest, strdest)
struct symbol **namedest;
int **strdest;
{
	register *n, *n2;

	n = expr(0);
	switch (n->nlab) {
	case STRING:
		*strdest = n->nval;
		*namedest = 0;
		nfree(n);
		return (0);
	case CON:
	case FCON:
		*namedest = *strdest = 0;
		return (n);
	case ADDR:
		if (n->nleft->nlab == NAME) {
			*namedest = n->nleft->nval;
			*strdest = 0;
			nfree(n);
			return (0);
		}
		if (n->nleft->nlab == STRING) {
			*namedest = 0;
			*strdest = n->nleft->nval;
			nfree(n);
			return (0);
		}
		break;
	case ADD:
		if (n->nleft->nlab == ADDR
				&& (n->nleft->nleft->nlab == NAME
				|| n->nleft->nleft->nlab == STRING)
				&& n->nright->nlab == CON) {
			n2 = n->nleft;
			n->nleft = n->nright;
			n->nright = n2;
		}
		if (n->nleft->nlab == CON
				&& n->nright->nlab == ADDR
				&& n->nright->nleft->nlab == NAME) {
			n2 = n->nleft;
			*namedest = n->nright->nleft->nval;
			n->nleft = 0;
			*strdest = 0;
			nfree(n);
			return (n2);
		}
		if (n->nleft->nlab == CON
				&& n->nright->nlab == ADDR
				&& n->nright->nleft->nlab == STRING) {
			n2 = n->nleft;
			*namedest = 0;
			*strdest = n->nright->nleft->nval;
			n->nleft = 0;
			nfree(n);
			return (n2);
		}
		break;
	}
	*namedest = 0;
	return (0);
}

/* Parse and output a single initializer element, and return the number
 * of basic elemtypes handled.
 */
initelem(elemtype)
{
	register *n, val, lab;
	static *name, strlab;

	strdumped = 0;
	n = initexpr(&name, &strlab);
	if (strdumped) {
		switch (elemtype) {
		case TYINT:
		default:
			printf("WORD ");
			break;
		case TYCHAR:
			printf("BYTE ");
		case TYFLOAT:
			printf("FLOAT ");
		case TYDOUBLE:
			printf("DOUBLE ");
			break;
		}
	}
	if (!n && !name && !strlab) {
		error("missing initializer expression");
		return (0);
	}

	if (n) {
		lab = n->nlab;
		val = n->nval;
		nfree(n);
	}
	else lab = val = 0;

	if ((elemtype == TYFLOAT || elemtype == TYDOUBLE)
			&& lab != FCON) {
		error("expected floating initializer");
		return (0);
	}

	if (strlab && lab)
		printf("%t+%l", strlab, val);
	else if (strlab)
		printf("%t", strlab);
	else if (name && lab)
		printf("%x+%l", name, val);
	else if (name)
		printf("%x", name);
	else if (lab == FCON)
		crash("FLOATING INITIALIZERS NOT SUPPORTED");
	else if (lab == CON)
		printf("%l", val);
	else crash("BAD INITIALIZER");

	switch (elemtype) {
	default:
		crash("BAD TYPE ELEM %o", elemtype);
	case TYINT:
	case TYSTRUCT:
		return (lab == FCON ? 4 : 1);
	case TYCHAR:
		return (lab == FCON ? 8 : 1);
	case TYFLOAT:
	case TYDOUBLE:
		return (1);
	}

	crash("BAD INITIALIZER");
}
