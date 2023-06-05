#include "c6t.h"

/* C6T - C version 6 by Troy - PART FOUR */

/* Remove the top modifier from a type struct.
 */
typop(type)
{
	register t;

	t = type->tystr;
	type->tystr = ((t>>TYLEN)&~(TYTOP|TYBASE))|(t&TYBASE);
	if ((t&TYMOD) == TYARRAY)
		type->tyarray--; /* ?? */
}

/* Append a new type modifier to a type struct.
 */
typush(type, mod, size)
{
	register t;

	t = type->tystr;
	type->tystr = ((t&~TYBASE)<<TYLEN)|(t&TYBASE)|mod;
	if (mod == TYARRAY) addsize(size);
}

/* Add a new size into the size table.
 */
addsize(size)
{
	register i;

	if ((i = sizei) >= SIZELAND) crash("OUT OF SIZE TABLE SPACE");
	sizeland[sizei++] = size;
	return (i);
}

/* Create a new member node via a '.' or '->' operator.
 */
domember(lab, n, name)
{
	register *sym;

	sym = tag(name);
	if (sym->sclass != MEMBER) {
		error("no such member %n", name);
		return (n);
	}

	n = node(lab, n, con(sym->soffset));
	tycopy(&sym->stype, &n->ntype);
	return (n);
}

/* Lookup a struct or member tag name.
 */
tag(name)
char *name;
{
	static char tagged[NAMELEN+1];
	register i;
	register char *n;

	if (name[0] == '.') return (lookup(name));
	tagged[0] = '.';
	n = name;
	for (i = 1; i < NAMELEN; i++)
		if (!(tagged[i] = *name++)) break;
	while (i<NAMELEN) tagged[i++]=0;
	return (lookup(tagged));
}

/* Dump a string literal.
 */
dumpstr()
{
	register i;
	register char *pnt;

	strdumped++;
	printf("BYTE ");
	pnt = tstr;
	for (i = 0; i < tlen; i++) {
		if (i%20==0) printf("\nBYTE ");
		printf("%l,", *pnt++&0377);
	}
	printf("0\n");
}

/* Enter a new output segment, returning the old one.
 */
goseg(newseg)
{
	register seg;

	seg = curseg;
	if ((curseg = newseg) != seg) switch (newseg) {
	case CODE:
	case DATA:
	case BSS:
	case STRING:
		printf("\n%e\n", newseg);
		break;
	default:
		crash("BAD SEGMENT %l", newseg);
	}
	return (seg);
}

/* Output an unformatted string.
 */
puts(string)
{
	register char *s;
	register c;

	if (s = string) while (c = *s++) putchar(c);
}

/* Handle constant folding expressions.
 */
fold(n)
{
	register left, right, result;

	if (!n) return (0);
	if (opinfo(n->nlab)&OPLEAF) return (n);
	if (!iscon(n->nleft)) return (n);
	if (n->nright && !iscon(n->nright)) return (n);

	left = n->nleft->nval;
	right = n->nright ? n->nright->nval : 0;

	switch (n->nlab) {
	default:
		return (n);
	case ADD:
		result = left + right;
		break;
	case SUB:
		result = left - right;
		break;
	case MULT:
		result = left * right;
		break;
	case DIV:
		result = left / right;
		break;
	case MOD:
		result = lrem(0, left, right);
		break;
	case AND:
		result = left & right;
		break;
	case OR:
		result = left | right;
		break;
	case EOR:
		result = left ^ right;
		break;
	case LSHIFT:
		result = left << right;
		break;
	case RSHIFT:
		result = left >> right;
		break;
	case NEG:
		result = -left;
		break;
	case COMPL:
		result = ~left;
		break;
	}
	nfree(n);
	return (con(result));
}

/* Return a flag if a node is allocated and an integer constant.
 */
iscon(n)
{
	return (n && n->nlab == CON);
}

/* Callback function for seeing a local specifier.
 */
cblocal(symbol)
{
	register class, *sym;

	if ((class = curclass) == REGISTER && curreg >= MAXREG)
		class = AUTO;
	if ((curtype.tystr&TYMOD)==TYFUNC) {
		class = EXTERN;
		if (curtype.tystr == (TYFUNC|TYCHAR))
			curtype.tystr = TYFUNC|TYINT;
		else if (curtype.tystr == (TYFUNC|TYFLOAT))
			curtype.tystr = TYFUNC|TYDOUBLE;
	}

	/* Fix register type */
	if (class == REGISTER) switch (curtype.tystr) {
	case TYCHAR:
		curtype.tystr = TYINT;
		break;
	case TYFLOAT:
	case TYDOUBLE:
	case TYSTRUCT:
	case TYARRAY:
	case TYFUNC:
		error("bad type for a register");
		break;
	}

	if ((sym = symbol)->sclass) {
		if (sym->sclass == EXTERN && sym->stype.tystr ==
				curtype.tystr)
			;
		else redef(sym->sname);
		return;
	}

	tycopy(&curtype, &sym->stype);
	switch (sym->sclass = class) {
	case AUTO:
		curauto =- tysize(&curtype);
		sym->soffset = curauto;
		break;
	case STATIC:
		goseg(BSS);
		deflab(sym->soffset = ++nextstatic);
		printf("STORAGE %l\n", tysize(&curtype));
		break;
	case EXTERN:
		break;
	case REGISTER:
		sym->soffset = curreg++;
		break;
	default:
		crash("BAD STORAGE CLASS %l", class);
	}
}

main(argc, argv) char **argv;
{
	extern fin, fout;

	if (argc > 1) fin = open(argv[1], 0);
	if (fin < 0) fin = 0;
	fout = dup(1);	/* force buffering */

	line = countlines = 1;
	fill2();

	while (!match(EOF)) extdef();
	printf("END\n");
	flush();
	exit(errcount != 0);
}
