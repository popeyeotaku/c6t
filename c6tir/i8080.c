#include "shared.h"
#include "i8080.h"

/* C6TIR Backend Code for Intel 8080/Zilog Z80 */

/* Our new set of nodes with additional data.
 */
struct node {
	struct templ *ntempl[2];
		/* Cached templates to compute into HL or DE.
		 * (=0 if not yet matched, -1 if no match exists).
		 */
} nland[CNLAND];
#define NOTEMPL 0177777
#define EMPTYTEMPL (0)

/* Return the new node corresponding to a core node.
 */
newnode(cnode)
struct cnode *cnode;
{
	return (&nland[cnode - cnland]);
}

/* Clear all new nodes */
clrnews()
{
	register struct node *pnt;

	for (pnt = nland; pnt < &nland[CNLAND]; pnt++) {
		pnt->ntempl[0] = pnt->ntempl[1] = EMPTYTEMPL;
	}
}

/* Output to define a label here */
deflab(label)
{
	printf("%s:", label);
}

/* Return the codegen template for the given core node to match it
 * into the given register.
 */
ntempl(cnode, reg)
{
	register *tpnt, *cn;
	register struct templ *templ;

	if (!(cn = cnode)) return (NOTEMPL);
	tpnt = &((newnode(cn))->ntempl)[reg];
	if (*tpnt == EMPTYTEMPL) {
		for (templ = templand; templ->tlab; templ++)
			if (tmatch(cn, templ, reg))
				return (*tpnt = templ);
		return (*tpnt = NOTEMPL);
	}
	else return (*tpnt);
}

/* Return a flag if the template matches the given core node and
 * register.
 */
tmatch(cnode, templ, reg)
{
	register *n, *t;

	n = cnode;
	t = templ;

	if (reg == DE && t->tdiff != DEITHER)
		return (0);
	if (t->tlab != n->nlab)
		return (0);
	if (t->tleft) {
		if (!n->nleft) return (0);
		if (n->nleft->nlab != t->tleft) return (0);
	}
	if (t->tright) {
		if (!n->nright) return (0);
		if (n->nright->nlab != t->tright) return (0);
	}
	return (1);
}

/* Return the left subtree node, if any, for the given node and
 * template.
 */
tleft(cnode, templ)
{
	if (!cnode) return (0);
	if (templ->tflags&TLSKIP)
		if (templ->tflags&TRSKIP) return (0);
		else return (cnode->nright);
	return (cnode->nleft);
}

/* Return the right subtree node, if any, for the given node and
 * template.
 */
tright(cnode, templ)
{
	if (!cnode) return (0);
	if (templ->tflags&TLSKIP)
		return (0);
	if (templ->tflags&TRSKIP) return (0);
	return (cnode->nright);
}

/* Return a flag if the template and all subtree templates can
 * be computed into the given register w/o using any binary
 * or special codegen templates -- in other words, all into the one
 * register all the way down.
 */
unarily(cnode, reg)
{
	register *n, t;

	if (!(n = cnode)) return (1);
	t = ntempl(n, reg);
	if (t == (NOTEMPL))
		return (0);
	switch (t->tdiff) {
	default:
		crash("BAD DIFFICULTY");
	case DHL:
		if (reg==DE) return (0);
		/* fall thru */
	case DEITHER:
		return (
			unarily(tleft(n, t), reg) &&
			unarily(tright(n, t), reg)
		);
	case DBIN:
	case DSPECIAL:
		return (0);
	}
}

/* Assemble a core node tree into the given register. */
asmtree(cnode, reg)
{
	register *n, t;
	register badsides;	/* flag for if the child templates end
				 * up on the wrong side (right should
				 * be in DE, left should be in HL)
				 */

	if (!(n = cnode)) return;

	t = ntempl(n, reg);
	if (t == NOTEMPL)
		crash("NO CODEGEN TEMPLATE");

	switch (t->tdiff) {
	case DHL:
	case DEITHER:
		asmtree(tleft(n, t), reg);
		asmtempl(n, t, reg);
		break;
	default:
		crash("BAD DIFFICULTY");
	case DBIN:
		if (reg!=HL) crash("CANNOT ASSEMBLE INTO HL");
		badsides = 0;

		if (unarily(n->nright, DE)) {
			asmtree(n->nleft, HL);
			asmtree(n->nright, DE);
		}
		else if (unarily(n->nleft, DE)) {
			asmtree(n->nright, HL);
			asmtree(n->nleft, DE);
			badsides = 1;
		}
		else if (unarily(n->nleft, HL)) {
			asmtree(n->nright, HL);
			xchg();
			asmtree(n->nleft, HL);
		}
		else if (unarily(n->nright, HL)) {
			asmtree(n->nleft, HL);
			xchg();
			asmtree(n->nright, HL);
			badsides = 1;
		}
		else {
			asmtree(n->nright, HL);
			printf("push h\n");
			asmtree(n->nleft, HL);
			printf("pop d\n");
		}

		if (badsides && !(t->tflags&TCOMMUT))
			xchg();
		asmtempl(n, t, reg);
		break;
	case DSPECIAL:
		if (reg != HL) crash("BAD REGISTER FOR SPECIALS");
		switch (n->nlab) {
		default:
			crash("BAD SPECIAL");
		case COMMA:
			asmtree(n->nleft, HL);
			asmtree(n->nright, HL);
			break;
		case QUEST:
			asmtree(n->nleft, HL);
			test(HL);
			badsides = ++nextstatic;
			t = ++nextstatic;
			printf("jz LL%l\n", badsides);
			asmtree(n->nright->nleft, HL);
			printf("jmp LL%l\n", t);
			printf("LL%l:", badsides);
			asmtree(n->nright->nright, HL);
			printf("LL%l:", t);
			break;
		case PRE:
		case POST:
		case CPRE:
		case CPOST:
			asmtree(n->nleft, HL);
			asmtempl(n, t, HL);
			break;
		case LOGOR:
		case LOGAND:
			asmtree(n->nleft, HL);
			asmtempl(n, t, HL);
			badsides = nextstatic;
			asmtree(n->nright, HL);
			printf("LL%l:", badsides);
			break;
		case ARG:
			asmtree(tleft(n, t), HL);
			asmtempl(n, t, HL);
			asmtree(tright(n, t), HL);
			break;
		case CALL:
			asmtree(tleft(n, t), HL);
			asmtree(tright(n, t), HL);
			asmtempl(n, t, HL);
			badsides = funcargs(n->nleft);
			while (badsides--) printf("pop d\n");
			break;
		}
		break;
	}
}

/* Assemble the xchg instruction */
xchg()
{
	printf("xchg\n");
}

/* Assemple the given template */
asmtempl(cnode, templ, reg)
{
	register *n;
	register char *str;
	register c;
	static *t;
	static char *start;
	static count;
	static int labs[2], *lab;

	labs[0] = labs[1] = 0;
	t = templ;
	n = cnode;

	if (!(str = t->tstr)) return;
	while (c = *str++) switch (c) {
	default:
		putchar(c);
		continue;
	case 'L':
		if (n) n = n->nleft;
		continue;
	case 'R':
		if (n) n = n->nright;
		continue;
	case 'V':
		output(n->nname, n->ncon);
		n = cnode;
		continue;
	case 'G':
		if (*str == 'L') {
			str++;
			putchar(reg == DE ? 'e' : 'l');
		}
		else putchar(reg == DE ? 'd' : 'h');
		continue;
	case 'P':
		if (start) {
			if (--count > 0) str = start;
			else start = 0;
		} else {
			start = str;
			count = n->ncon;
			n = cnode;
		}
		continue;
	case 'T':
		lab = &labs[*str++ - '0'];
		if (!*lab) *lab = ++nextstatic;
		printf("LL%l", *lab);
		continue;
	}
}

/* Assemble a complete expression tree */
asmexpr(cnode)
{
	clrnews();
	asmtree(cnode, HL);
}

backcmd(cmd, args, n)
int *args;
{
	n = fixup(n);

	switch (cmd) {
	default:
		crash("BAD COMMAND");
	case SWITCH:
		pushargs(args);
		asmexpr(n);
		printf("push h\njmp cswitch\n");
		break;
	case SWEASY:
		sweasy(args, n);
		break;
	case BYTE:
	case WORD:
		printf(".d%c ", cmd == BYTE ? 'b' : 'w');
		outlist(args, 0);
		putchar('\n');
		break;
	case STORAGE:
		printf(".ds ");
		outarg(args);
		putchar('\n');
		break;
	case AUTOS:
		if (*args == ACON && args[1] == 0) break;
		printf("lxi h,-");
		outarg(args);
		printf("\ndad sp\nsphl\n");
		break;
	case USEDREGS:
		break;
	case RET:
		asmexpr(n);
		/* fall thru */
	case RETNULL:
		printf("jmp cret\n");
		break;
	case FUNC:
		printf("call csave\n");
		break;
	case EXPORT:
		printf(".export ");
		outlist(args, 0);
		putchar('\n');
	case ENDFUNC:
		break;
	case JMP:
		printf("jmp ");
		outarg(args);
		putchar('\n');
		break;
	case BRZ:
		if (n->nlab == LOG) asmexpr(n->nleft);
		else if (n->nlab == LOGNOT) asmexpr(n->nleft);
		else asmexpr(n);
		test(HL);
		printf("j%s ", n->nlab == LOGNOT ? "nz" : "z");
		outarg(args);
		putchar('\n');
		break;
	case EVAL:
		asmexpr(n);
		break;
	case END:
		break;
	case CODE:
		printf(".code\n");
		break;
	case DATA:
		printf(".data\n");
		break;
	case BSS:
		printf(".bss\n");
		break;
	case STRING:
		printf(".string\n");
		break;
	case STKJMP:
		if (n->nlab == CON) {
			printf("jmp ");
			output(n->nname, n->ncon);
			putchar('\n');
		} else {
			asmexpr(n);
			printf("pchl\n");
		}
		break;
	case COMMON:
		printf(".common ");
		outlist(args, 0);
		putchar('\n');
		break;
	}
}

pushargs(args) int *args;
{
	if (args[0] == ALIST) {
		pushargs(args[1]);
		pushargs(args[2]);
	} else {
		printf("lxi h,");
		outarg(args);
		printf("\npush h\n");
	}
}

char *regnames[] { "reg0", "reg1", "reg2" };

/* Perform local conversions */
fixup(npnt)
{
	register *new, *n;

	if (!(n = npnt)) return (0);

	n->nleft = fixup(n->nleft);
	n->nright = fixup(n->nright);

	switch (n->nlab) {
	case LOGOR:
	case LOGAND:
		new = cnalloc(LOG);
		new->nleft = n;
		if (n->nleft->nlab == LOG) n->nleft = n->nleft->nleft;
		if (n->nright->nlab == LOG)
			n->nright = n->nright->nleft;
		n = new;
		break;
	case EQU:
	case NEQU:
		new = cnalloc(n->nlab == EQU ? LOGNOT : LOG);
		n->nlab = SUB;
		new->nleft = coptim(n);
		n = new;
		break;
	case REG:
		n->nlab = CON;
		n->nname = regnames[n->ncon];
		n->ncon = 0;
		break;
	}
	return (n);
}

/* Assemble to test the given register */
test(reg)
{
	register char *name;

	name = (reg == HL) ? "hl" : "de";

	printf("mov a,%c\nora %c\n", name[0], name[1]);
}

funcargs(n)
{
	if (!n) return (0);
	if (n->nlab == ARG)
		return (funcargs(n->nleft) + funcargs(n->nright));
	return (1);
}

/* Handle an easy switch.
 *
 * Compute the expression minus the starting value (arg 3),
 * if greater than the table len (arg 4), jump to the default (arg 2).
 * Else, multiply by 2 and jump to that plus the table (arg 1).
 */
sweasy(args, n)
{
	static struct { int *stable, *sdef, *sbeg, *slen; } swdata;
	static *index;

	index = &swdata;
	linlist(args, &index);

	asmexpr(n);
	if (!(swdata.sbeg[0] == ACON && swdata.sbeg[1] == 0)) {
		printf("lxi d,-");
		outarg(swdata.sbeg);
		printf("\ndad d\n");
	}
	printf("lxi d,");
	outarg(swdata.slen);
	printf("\nmov a,l\nsub e\nmov a,h\nsbb d\n");
	/* carry set if borrow, meaning A < arg */
	printf("jnc ");
	outarg(swdata.sdef);
	printf("\ndad h\nlxi d,");
	outarg(swdata.stable);
	printf("\ndad d\nmov a,m\ninx h\nmov h,m\nmov l,a\npchl\n");
}

/* Linearize the contents of a ALIST */
linlist(args, dest)
int args[], **dest;
{
	if (!args) return;
	if (args[0] == ALIST) {
		linlist(args[1], dest);
		linlist(args[2], dest);
	} else {
		**dest = args;
		*dest =+ 1;
	}
}
