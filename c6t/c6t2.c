#include "c6t.h"

/* C6T - C version 6 by Troy - PART TWO */

/* Top level expression parsing routine. Pass it a flag for if you
 * want to see commas or not.
 */
expr(seecommas)
{
	register *n;

	n = seecommas ? exp15() : exp14();
	return (build(EOF, n));
}

/* These are the main expression parsing routines.
 * They work via recursive descent, which eats up a
 * huge chunk of stack space. Probably should be replaced with a
 * shunting yard at some point.
 * The good news is they only use register variables, so if your
 * backend always saves those on the stack like it should, you
 * won't get any additional stack use other than the minimum.
 *
 * exp15 thru exp1 correspond to sections 7.1 to 7.15 in the
 * Unix Sixth Edition C Reference Manual.
 */
exp15()
{
	register *n;

	n = exp14();
	while (match(COMMA))
		n = build(COMMA, n, exp14());
	return (n);
}

exp14()
{
	register *n, t;

	n = exp13();
	switch (t = token()) {
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
		/* Call ourself for right assoc. */
		return (build(t, n, exp14()));
	}
	peektkn = t;
	return (n);
}

exp13()
{
	register *n, *left, *right;

	n = exp12();
	while (match(QUEST)) {
		left = exp12();
		need(COLON);
		right = exp12();
		n = build(QUEST, n, build(COLON, left, right));
	}
	return (n);
}

exp12()
{
	register *n;

	n = exp11();
	while (match(LOGOR))
		n = build(LOGOR, n, exp11());
	return (n);
}

exp11()
{
	register *n;

	n = exp10();
	while (match(LOGAND))
		n = build(LOGAND, n, exp10());
	return (n);
}

exp10()
{
	register *n;

	n = exp9();
	while (match(OR))
		n = build(OR, n, exp9());
	return (n);
}

exp9()
{
	register *n;

	n = exp8();
	while (match(EOR))
		n = build(EOR, n, exp8());
	return (n);
}

exp8()
{
	register *n;

	n = exp7();
	while (match(AND))
		n = build(AND, n, exp7());
	return (n);
}

exp7()
{
	register *n, t;

	n = exp6();
	for (ever) switch (t = token()) {
	case EQU:
	case NEQU:
		n = build(t, n, exp6());
		continue;
	default:
		peektkn = t;
		return (n);
	}
}

exp6()
{
	register *n, t;

	n = exp5();
	for (ever) switch (t = token()) {
	case LESS:
	case GREAT:
	case LEQU:
	case GEQU:
		n = build(t, n, exp5());
		continue;
	default:
		peektkn = t;
		return (n);
	}
}

exp5()
{
	register *n, t;

	n = exp4();
	for (ever) switch (t = token()) {
	case RSHIFT:
	case LSHIFT:
		n = build(t, n, exp4());
		continue;
	default:
		peektkn = t;
		return (n);
	}
}

exp4()
{
	register *n, t;

	n = exp3();
	for (ever) switch (t = token()) {
	case ADD:
	case SUB:
		n = build(t, n, exp3());
		continue;
	default:
		peektkn = t;
		return (n);
	}
}

exp3()
{
	register *n, t;

	n = exp2();
	for (ever) switch (t = token()) {
	case MULT:
	case DIV:
	case MOD:
		n = build(t, n, exp2());
		continue;
	default:
		peektkn = t;
		return (n);
	}
}

exp2()
{
	register *n, t;

	switch (t = token()) {
	case MULT:
		t = DEREF;
		goto unary;
	case AND:
		t = ADDR;
		goto unary;
	case SUB:
		t = NEG;
		goto unary;
	case LOGNOT:
	case COMPL:
	case PREINC:
	case PREDEC:
	unary:
		return (build(t, exp2()));
	case SIZEOF:
		n = exp2();
		t = tysize(&n->ntype);
		nfree(n);
		return (con(t));
	}

	peektkn = t;
	n = exp1();
	for (ever) switch (t = token()) {
	case PREINC:
	case PREDEC:
		n = build(t + POSTINC - PREINC, n);
		continue;
	default:
		peektkn = t;
		return (n);
	}
}

exp1()
{
	register *n, t, *pnt;

	switch (t = token()) {
	case CON:
	case FCON:
	case STRING:
	case NAME:
		n = leaf(t);
		break;
	case LPAREN:
		n = exp15();
		need(RPAREN);
		break;
	default:
		peektkn = t;
		error("missing primary expression");
		errskip();
		n = con(1);	/* Good default for arrays */
		break;
	}

	for (ever) switch (t = token()) {
	case LBRACK:
		n = build(DEREF, build(ADD, n, exp15()));
		need(RBRACK);
		continue;
	case LPAREN:
		pnt = 0;
		if ((peektkn = token()) != RPAREN) do {
			pnt = build(ARG, exp14(), pnt);
		} while (match(COMMA));
		need(RPAREN);
		n = build(CALL, n, pnt);
		continue;
	case DOT:
	case ARROW:
		if (!match(NAME))
			error("missing member name");
		else n = domember(t, n, tname);
		continue;
	default:
		peektkn = t;
		return (n);
	}
}

/* Skip to the next terminal token (used for error realignment).
 */
errskip()
{
	register t;

	token();	/* Skip current token */
	for (ever) switch (t = token()) {
	case RBRACE:
	case SEMICOLON:
	case EOF:
		peektkn = t;
		return;
	}
}
