#include "c6t.h"

/* C6T - C version 6 by Troy - PART THREE */

/* This constructs a new non-leaf expression tree node with the
 * given label and children, handling all typing and conversions.
 */
build(lab, left, right)
{
	register *n, info, i;

	info = opinfo(lab);
	n = info&OPUNARY ? node(lab, left, 0) : node(lab, left, right);
	n->nright = handfunc(handarray(n->nright));
	if (lab != ADDR) {
		n->nleft = handarray(n->nleft);
		if (lab != CALL) n->nleft = handfunc(n->nleft);
	}

	if (lab == EOF) {
		i = n->nleft;
		n->nleft = 0;
		nfree(n);
		return (i);
	}

	if ((isflt(n->nleft) || isflt(n->nright)) && info&OPFLTCONV) {
		if (!isflt(n->nleft)) n->nleft = build(TOFLT, n->nleft);
		else if (!isflt(n->nright))
			n->nright = build(TOFLT, n->nright);
	}

	if (info&OPASSIGN && !isflt(n->nleft) && isflt(n->nright))
		n->nright = build(TOINT, n->nright);

	if (lab == TOFLT) n->ntype.tystr = TYDOUBLE;
	else if (info&OPTYLEFT)
		tycopy(&n->nleft->ntype, &n->ntype);
	else if (info&OPTYRIGHT)
		tycopy(&n->nright->ntype, &n->ntype);
	else if (info&OPISINT)
		n->ntype.tystr = TYINT;
	else {
		if (isflt(n->nleft) || isflt(n->nright))
			n->ntype.tystr = TYDOUBLE;
		else if (ispnt(n->nleft))
			tycopy(&n->nleft->ntype, &n->ntype);
		else if (ispnt(n->nright))
			tycopy(&n->nright->ntype, &n->ntype);
		else n->ntype.tystr = TYINT;
	}

	if (info&OPDEREF) typop(&n->ntype);
	else if (info&OPINCREF) typush(&n->ntype, TYPOINT);

	if ((isflt(n->nleft) || isflt(n->nright)) && !(info&OPYESFLT)) {
		error("float unsupported for operation %e", lab);
		n->ntype.tystr = TYINT;
	}


	if (info&OPPNTCONV) {
		if (ispnt(n->nleft) && !ispnt(n->nright))
			n->nright = build(MULT, n->nright,
				con(sizenext(&n->nleft->ntype)));
		else if (!ispnt(n->nleft) && ispnt(n->nright)
				&& !(info&OPASSIGN))
			n->nleft = build(MULT, n->nleft,
			con(sizenext(&n->nright->ntype)));
	}

	switch (lab) {
	case SUB:
		if (ispnt(n->nleft) && n->nleft->ntype.tystr ==
				n->nright->ntype.tystr)
			return (build(DIV, fold(n),
				con(sizenext(&n->nleft->ntype))));
		break;
	case DEREF:
		if (!ispnt(n->nleft))
			error("dereference of non-pointer");
		if (n->nleft->nlab == ADDR) {
			i = n->nleft->nleft;
			n->nleft->nleft = 0;
			nfree(n);
			return (i);
		}
		break;
	case ADDR:
		if (!lval(n->nleft))
			error("address operator on non-address");
		if (n->nleft->nlab == DEREF) {
			i = n->nleft->nleft;
			n->nleft->nleft = 0;
			nfree(n);
			typush(&i->ntype, TYPOINT);
			return (i);
		}
		break;
	case LESS:
	case GREAT:
	case LEQU:
	case GEQU:
		if ((ispnt(n->nleft) || ispnt(n->nright))
				&& !isflt(n->nleft)
				&& !isflt(n->nright))
			n->nlab =+ ULESS - LESS;
		break;
	case CALL:
		if ((n->nleft->ntype.tystr&TYMOD) != TYFUNC)
			error("call of non-function");
		break;
	}

	return (fold(n));
}

/* Return a flag if the node is allocated and a pointer type. */
ispnt(n)
{
	return (n && n->ntype.tystr&TYPOINT);
}

/* Return a flag if the node is allocated and a floating
 * type.
 */
isflt(n)
{
	return (n && (n->ntype.tystr&TYMOD) == 0 && n->ntype.tystr
		&TYFLOAT);
}

/* Return a flag if the node is allocated and an lval (an unloaded
 * address or register variable).
 */
lval(n)
{
	if (n) switch (n->nlab) {
	case NAME:
	case DEREF:
	case DOT:
	case ARROW:
	case STRING:
		return (1);
	}
	return (0);
}

/* Free a node and its children.
 */
nfree(n)
{
	if (n && n->nlab) {
		if (!(opinfo(n->nlab)&OPLEAF)) {
			nfree(n->nleft);
			nfree(n->nright);
		}
		n->nlab = 0;
	}
}

/* Convert a reference to an array to an address node of a pointer
 * to what the array points.
 *
 * This is done because the actual CPU cannot load an array.
 * Therefore, it only ever contains the address
 * of one, and that is a pointer.
 * It also allows multi-dimension arrays to work.
 */
handarray(n)
{
	if (!n) return (0);
	if (n->nlab != ADDR && (n->ntype.tystr&TYMOD) == TYARRAY) {
		n = node(ADDR, n, 0);
		tycopy(&n->nleft->ntype, &n->ntype);
		typop(&n->ntype);
		typush(&n->ntype, TYPOINT);
	}
	return (n);
}

/* Convert a function type to a pointer to a function, which it is
 * seen as in all non-CALL contexts.
 * Like arrays, this is because the CPU cannot contain an actual
 * function.
 */
handfunc(n)
{
	if (n && (n->ntype.tystr&TYMOD) == TYFUNC)
		n = build(ADDR, n);
	return (n);
}

/* Return the size of a given type struct in bytes.
 */
tysize(type)
{
	register t;

	t = type->tystr;
	switch (t&TYMOD) {
	case TYPOINT:
		return (2);
	case TYFUNC:
		return (0);
	case TYARRAY:
		return (sizeland[type->tyarray&0377]*sizenext(type));
	case 0:
		switch (t&TYBASE) {
		case TYINT:
			return (2);
		case TYCHAR:
			return (1);
		case TYFLOAT:
			return (4);
		case TYDOUBLE:
			return (8);
		case TYSTRUCT:
			return (sizeland[type->tystruct&0377]);
		}
	}
	crash("BAD TYPE STRING %o", t);
}

/* Return the size of a type with its top modifier removed.
 */
sizenext(type)
{
	struct type popped;

	tycopy(type, &popped);
	typop(&popped);
	return (tysize(&popped));
}
