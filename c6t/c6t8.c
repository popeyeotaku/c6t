#include "c6t.h"

/* C6T - C version 6 by Troy - PART EIGHT */

/* Parse and output a single statement recursively. */
statement()
{
	int lab1,lab2;
	int olddef, oldbrk, oldcont;
	register t, *n;
	int oldcbeg, oldcend;

	goseg(CODE);
	switch (t = token()) {
	case IF:
		pexpr(lab1 = ++nextstatic);
		statement();
		if (match(ELSE)) {
			jump(lab2 = ++nextstatic);
			deflab(lab1);
			statement();
			deflab(lab2);
		} else	/* Ironic, ain't it? */
			deflab(lab1);
		break;
	case LBRACE:
		while (!match(RBRACE)) {
			earlyeof();
			statement();
		}
		break;
	case WHILE:
		oldcont = curcont;
		oldbrk = curbrk;

		deflab(curcont = ++nextstatic);
		pexpr(curbrk = ++nextstatic);
		statement();
		jump(curcont);
		deflab(curbrk);

		curbrk = oldbrk;
		curcont = oldcont;
		break;
	case DO:
		oldbrk = curbrk;
		oldcont = curcont;

		deflab(lab1 = ++nextstatic);
		curcont = ++nextstatic;
		curbrk = ++nextstatic;
		statement();
		need(WHILE);
		deflab(curcont);
		pexpr(curbrk);
		jump(lab1);
		deflab(curbrk);
		need(SEMICOLON);

		curbrk = oldbrk;
		curcont = oldcont;
		break;
	case FOR:
		oldbrk = curbrk;
		oldcont = curcont;

		lab1 = ++nextstatic;
		curcont = ++nextstatic;
		curbrk = ++nextstatic;
		need(LPAREN);
		if (!match(SEMICOLON)) {
			eval(n = expr(1));
			nfree(n);
			need(SEMICOLON);
		}
		deflab(lab1);
		if (!match(SEMICOLON)) {
			brz(n = expr(1), curbrk);
			nfree(n);
			need(SEMICOLON);
		}
		if (!match(RPAREN)) {
			n = expr(1);
			need(RPAREN);
		}
		else n = 0;

		statement();

		deflab(curcont);
		if (n) {
			eval(n);
			nfree(n);
		}
		jump(lab1);
		deflab(curbrk);

		curbrk = oldbrk;
		curcont = oldcont;
		break;
	case SWITCH:
		oldbrk = curbrk;
		oldcbeg = begcase;
		oldcend = endcase;
		olddef = curdef;

		need(LPAREN);
		n = expr(1);
		need(RPAREN);
		curbrk = ++nextstatic;
		curdef = 0;
		if (!(begcase = endcase))
			begcase = endcase = caseland;

		jump(lab1 = ++nextstatic);
		statement();
		outswitch(n, lab1);
		deflab(curbrk);

		curbrk = oldbrk;
		begcase = oldcbeg;
		endcase = oldcend;
		curdef = olddef;
		break;
	case CASE:
		addcase(conexpr(), lab1 = ++nextstatic);
		need(COLON);
		deflab(lab1);
		statement();
		break;
	case DEFAULT:
		need(COLON);
		if (curdef) error("only one default allowed");
		if (!begcase) error("default outside of case");
		deflab(curdef = ++nextstatic);
		statement();
		break;
	case BREAK:
		need(SEMICOLON);
		if (!curbrk) error("nothing to break to");
		else jump(curbrk);
		break;
	case CONTINUE:
		need(SEMICOLON);
		if (!curcont) error("nothing to continue to");
		else jump(curcont);
		break;
	case RETURN:
		if (match(SEMICOLON))
			printf("RETNULL\n");
		else {
			need(LPAREN);
			n = expr(1);
			need(RPAREN);
			need(SEMICOLON);
			outexpr(n);
			printf("%cRET\n", isflt(n) ? 'F' : 0);
			nfree(n);
		}
		break;
	case GOTO:
		outexpr(n = expr(1));
		nfree(n);
		printf("STKJMP\n");
		need(SEMICOLON);
		break;
	case NAME:
		/* Peek the readahead buffer ahead of the next token
		 * (TOTAL KLUDGE)
		 */
		whitespace();
		if (cmatch(':')) {
			n = lookup(tname);
			if (!n->sclass) {
				n->sclass = STATIC;
				n->stype.tystr = TYARRAY|TYINT;
				n->stype.tyarray = 0;
				n->soffset = ++nextstatic;
			}
			else if (n->sflags&SUNDEF) {
				/* undefined LABEL */
				n->sflags =& ~SUNDEF;
			}
			else redef(tname);
			deflab(n->soffset);
			statement();
			return;
		}
		/* else fall thru... */
	default:
		peektkn = t;
		eval(n = expr(1));
		nfree(n);
		need(SEMICOLON);
		break;
	case SEMICOLON:
		break;
	}
}

/* Jump to a static label */
jump(lab)
{
	printf("JMP %t\n", lab);
}

/* Branch to the label if the node = zero */
brz(n, lab)
{
	outexpr(n);
	printf("%cBRZ %t\n", isflt(n) ? 'F' : 0, lab);
}

/* Parse an expression in parenthesis, branch if it is
 * zero to the label, then free the expression tree.
 */
pexpr(lab)
{
	register *n;

	need(LPAREN);
	n = expr(1);
	need(RPAREN);
	brz(n, lab);
	nfree(n);
}

/* Define a static label */
deflab(lab)
{
	printf("%t:", lab);
}

/* Output to backend to evaluate the given expression tree.
 */
eval(n)
{
	outexpr(n);
	printf("EVAL\n");
}
