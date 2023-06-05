#include "c6t.h"

/* C6T - C version 6 by Troy - PART ONE */

/* Low level printf - pass a pointer to the arguments.
 */
_printf(fmt, argpnt)
{
	register char *f;
	register *pnt;
	register c;

	pnt = argpnt;
	f = fmt;
	while (c = *f++) {
		if (c == '%') switch (c = *f++) {
		case 0:
			return;
		case 'c':
			if (c = *pnt++) putchar(c);
			break;
		case 'l':
			putnum(*pnt++, 10);
			break;
			break;
		case 'd':
			c = *pnt++;
			if (c < 0) {
				putchar('-');
				c = -c;
			}
			putnum(c, 10);
			break;
		case 't':
			putchar('L');
			putnum(*pnt++, 10);
			break;
		case 'o':
			putnum(*pnt++, 8);
			break;
		case 's':
			puts(*pnt++);
			break;
		case 'e':
			puts(enumstr(*pnt++));
			break;
		case 'n':
			putnam(*pnt++);
			break;
		case 'x':
			putchar('_');
			putnam(*pnt++);
			break;
		default:
			putchar(c);
			break;
		}
		else putchar(c);
	}
}

/* Output a number at a given base, unsigned.
 */
putnum(num, base)
{
	register div, rem;
	extern ldivr;

	div = ldiv(0, num, base);
	rem = ldivr;

	if (div) putnum(div, base);
	putchar('0' + rem);
}

/* Custom printf.
 * Since C6T guarentees args pushed onto stack in reverse order,
 * passing a pointer to an argument and advancing up it will allow
 * each arg to be accessed programatically.
 */
printf(fmt, args)
{
	_printf(fmt, &args);
}

/* Low level error printing; pass pointer to arguments.
 */
_error(fmt, argpnt)
{
	extern fout;
	register oldout;

	oldout = fout;
	flush();
	fout = 2;
	printf("%l: ", line);
	_printf(fmt, argpnt);
	putchar('\n');
	errcount++;
	flush();
	fout = oldout;
}

/* Hi level error printing */
error(fmt, args)
{
	_error(fmt, &args);
}

/* Compare two NAMEs (do NOT rely on the source string being
 * NAMELEN bytes long, it might come from another source.
 */
namcmp(name1, name2)
{
	register char *n1, *n2;
	register i;

	n1 = name1;
	n2 = name2;

	i = NAMELEN;

	while (i--) {
		if (*n1 != *n2) return (0);
		if (!*n1++ || !*n2++) break;
	}
	return (1);
}

/* If we match the token label, return true. If not, peek the
 * next token and return false.
 */
match(lab)
{
	if ((peektkn = token()) == lab) {
		peektkn = 0;
		return (1);
	}
	return (0);
}

/* If we don't match() the given token label, issue an error.
 */
need(lab)
{
	if (!match(lab)) error("missing expected token %e", lab);
}

/* Allocate a new node.
 * Give it the label, with int type, and empty children.
 */
nalloc(lab)
{
	register struct node *n;

	for (n = nland; n < &nland[NLAND]; n++) {
		if (!n->nlab) {
			clear(n, sizeof(*n));
			n->nlab = lab;
			n->ntype.tystr = TYINT;
			return (n);
		}
	}
	crash("OUT OF NODE MEMORY");
}

/* Allocate a new node with the given children.
 */
node(lab, left, right)
{
	register *n;

	n = nalloc(lab);
	n->nleft = left;
	n->nright = right;
	return (n);
}

/* Give an error, then crash.
 */
crash(fmt, args)
{
	_error(fmt, &args);
	abort();
}

/* Create an integer constant node with the given value.
 */
con(value)
{
	register *n;

	n = nalloc(CON);
	n->nval = value;
	return (n);
}

/* Construct a leaf node from the current token value.
 */
leaf(label)
{
	register *n, *sym, oldseg;

	switch (label) {
	default:
		crash("LABEL %e NOT A LEAF", label);
	case CON:
		return (con(tval));
	case FCON:
		crash("FLOATING CONSTANTS NOT SUPPORTED");
	case NAME:
		n = nalloc(NAME);
		n->nval = sym = lookup(tname);
		if (!sym->sclass) {
			/* undefined NAME. If in localscope... */
			if (localscope) {
				sym->sflags = SLOCAL;
				/* If the next token is a (, assume
				 * function returning int.
				 */
				if ((peektkn = token()) == LPAREN) {
					sym->stype.tystr = TYFUNC|TYINT;
					sym->sclass = EXTERN;
				}
				else {
					/* Assume undefined goto
					 * label.
					 */
					sym->sflags =| SUNDEF;
					sym->sclass = STATIC;
					sym->soffset = ++nextstatic;
					sym->stype.tystr =
						TYARRAY|TYINT;
					sym->stype.tyarray = 0;
				}
			}
			else {
				/* In extern scope, assume an extern int
				 * defined somewhere else.
				 */
				sym->sclass = EXTERN;
				sym->stype.tystr = TYINT;
			}
		}
		tycopy(&sym->stype, &n->ntype);
		return (n);
	case STRING:
		n = nalloc(STRING);
		n->ntype.tystr = TYARRAY|TYCHAR;
		n->ntype.tyarray = addsize(tlen+1);
		oldseg = goseg(STRING);
		deflab(n->nval = ++nextstatic);
		dumpstr();
		goseg(oldseg);
		return (n);
	}
}

/* Lookup a NAME in the symbol table. If not found, create an entry.
 */
lookup(name)
{
	register struct symbol *sym, *start;

	sym = start = &symtab[hash(name) % SYMTAB];

	do {
		if (!sym->sname[0]) {
			clear(sym, sizeof(*sym));
			namcopy(name, sym->sname);
			sym->stype.tystr = TYINT;
			sym->sflags = localscope ? SLOCAL : 0;
			return (sym);
		}
		if (namcmp(sym->sname, name))
			return (sym);
		if (++sym >= &symtab[SYMTAB]) sym = symtab;
	} while (sym != start);

	crash("OUT OF SYMBOL TABLE SPACE");
}

/* Hash a NAME. */
hash(name)
{
	register i, h;
	register char *pnt;

	pnt = name;
	h = 0;
	i = NAMELEN;
	while (i--)
		h =+ *pnt++&0377;
	return (h & 077777);
		/* That clears the sign bit; forgetting to put that
		 * in caused MONTHS of issues in earlier versions
		 * of C6T due to pointers in lookup() going out of
		 * range.
		 */
}

/* Set a range of memory to 0 */
clear(start, span)
{
	register char *pnt;
	register i;

	i = span;
	pnt = start;
	while (i--) *pnt++ = 0;
}

/* Copy a range of bytes */
copy(source, dest, count)
{
	register char *src, *dst;
	register i;

	src = source;
	dst = dest;
	i = count;

	while (i--) *dst++ = *src++;
}

/* Copy a type struct. */
tycopy(source, dest)
struct type *source, *dest;
{
	copy(source, dest, sizeof(*dest));
}

/* Copy a NAME, not relying on the actual byte length of the source.
 */
namcopy(source, dest)
{
	register char *src, *dst;
	register i;

	src = source;
	dst = dest;
	for (i = 0; i < NAMELEN; i++)
		if (!(dst[i] = src[i])) break;
	while (i < NAMELEN) dst[i++] = 0;
}
