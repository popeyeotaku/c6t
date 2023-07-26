#include "../poplink/poplink.h"
#include "asm.h"

/* C6T Assembler C File */

char tname[16];

int curseg -1;

int *exppnt expland, *argpnt argland;

alpha(c)
{
	return (
		(c >= 'a' && c <= 'z')
		|| (c >= 'A' && c <= 'Z')
		|| (c == '_')
		|| (c == '.')
	);
}

alphanum(c)
{
	return (
		(c >= '0' && c <= '9')
		|| alpha(c)
	);
}

/* Append a single element to the expression buffer */
putexp(e)
{
	if (exppnt >= &expland[EXPLAND])
		memcrash();
	*exppnt++ = e;
}

memcrash()
{
	crash("OUT OF MEMORY ERROR");
}

crash(msg, arg)
{
	yyerror(msg, arg);
	unlink(tname);
	abort();
}

yyerror(msg, arg)
{
	register oldout;
	extern fout, yyline;

	oldout = fout;
	flush();
	fout = 2;
	printf("%l: ", yyline);
	printf(msg, arg);
	putchar('\n');

	flush();
	fout = oldout;
	errcount++;
}

cleanup()
{
	exppnt = expland;
	argpnt = argland;
}

econ(val)
{
	register *pnt;

	pnt = exppnt;
	putexp(EABS);
	putexp(val);
	return (pnt);
}

ename(sym)
{
	register *pnt;

	pnt = exppnt;

	if ((sym->aclass&0377&~AEXPORT) == PABS) {
		putexp(EABS);
		putexp(sym->aval);
	} else {
		putexp(EOFFSET);
		putexp(sym);
		putexp(0);
	}

	return (pnt);
}

eneg(exp)
int *exp;
{
	if (needabs(exp)) return;
	exp[1] = -exp[1];
}

needabs(exp) int *exp;
{
	if (exp && exp[0] == EABS)
		return (0);

	yyerror("require absolute expression");
	return (1);
}

/* Evaluate an operation on the left and maybe right expressions, then
 * return the new value.
 * The new value might be one of the arguments modified inplace.
 * The only things passed should be EOFFSET, ESEG, or EABS; not EHILO.
 */
eval(op, left, right)
int left[], right[];
{
	register i;

	switch (op) {
	default:
	bad:
		yyerror("bad op '%c'", op);
		return (left);
	case '+':
		if (left[0] != EABS) {
			if (needabs(right)) return (left);
			left[2] =+ right[1];
			return (left);
		}
		if (right[0] != EABS) {
			if (needabs(left)) return(left);
			right[2] =+ left[1];
			return (right);
		}
		left[1] =+ right[1];
		return (left);
	case '-':
		/* allow backward reference relative within a segment */
		if (i=chkrel(left,right))
			return (i);

		if (left[0] != EABS) {
			if (needabs(right)) return (left);
			left[2] =- right[1];
			return (left);
		}
		if (right[0] != EABS) goto bad;
		left[1] =- right[1];
		return (left);
	case '*':
		if (needabs(left) || needabs(right)) return (left);
		left[1] =* right[1];
		return (left);
	case '/':
		if (needabs(left)||needabs(right)) return (left);
		left[1] =/ right[1];
		return (left);
	}
}

chk1rel(exprpnt, segdest, valdest) int *exprpnt, *segdest, *valdest;
{
	if (exprpnt[0] == ESEG) {
		*segdest = exprpnt[1];
		*valdest = exprpnt[2];
		return (1);
	}
	if (exprpnt[0] == EOFFSET) {
		*segdest = exprpnt[1]->aclass&0377&~AEXPORT;
		if (*segdest == PCOMMON)
			*segdest = 0;
		*valdest = exprpnt[2]+exprpnt[1]->aval;
		return (1);
	}
	return (0);
}

chkrel(left, right) int left[], right[];
{
	static lseg, lval, rseg, rval;

	if (!chk1rel(left, &lseg, &lval) || !chk1rel(right, &rseg, &rval))
		return (0);
	if (!lseg && !rseg)
		return (0);

	if (lseg == rseg)
		return (econ(lval-rval));
	if (!lseg && left[0] == EOFFSET)
		return (erel(rseg, -rval, left[1]));
	if (!rseg && right[0] == EOFFSET)
		return (erel(lseg, -lval, right[1]));

	return (0);
}

erel(seg, val, sym)
{
	register *pnt;


	pnt = exppnt;
	putexp(EREL);
	putexp(seg);
	putexp(val);
	putexp(sym);

	return (pnt);
}

/* Make an expression into a hi or lo byte */
ehilo(hilo, exp)
{
	register *pnt;

	pnt = exppnt;
	putexp(EHILO);
	putexp(hilo == '>' ? AHI : ALO);
	putexp(exp);
	return (pnt);
}

addarg(arg)
{
	if (argpnt >= &argland[ARGLAND])
		memcrash();

	*argpnt++ = arg;
}

main(argc, argv) char **argv;
{
	extern fin, yyline, yydebug;
	register char *pnt;

	if (argc > 1 && argv[1][0] == '-') {
		pnt = &argv[1][1];
		--argc; ++argv;
		while (*pnt) switch (*pnt++) {
		case 'd':
			yydebug++;
			break;
		case 's':
			if (argc > 1) {
				header.astart = atoi(argv[1]);
				--argc; ++argv;
			}
			break;
		}
	}

	if (argc > 1) {
		fin = open(argv[1], 0);
		if (fin < 0) exit(1);
	}

	yyline = 1;

	mktemp();	/* setup temporary file and output to text seg */

	goseg(PTEXT);

	opinit();	/* local init (place register labels
			 * into symbol table for 8080, etc.)
			 */

	yyparse();	/* assemble to the temp file */

	if (errcount) {
		unlink(tname);
		exit(1);
	}

	concat();	/* place temp file data into final a.out,
			 * fixing up link offsets + handling forward
			 * references.
			 */
	unlink(tname);
	exit(errcount > 0);
}

/* Require an expression to be an absolute value, and return the value.
 */
expabs(exp) int exp[];
{
	if (needabs(exp)) return (0);
	return (exp[1]);
}

setequ(sym, exp)
{
	if (redef(sym)) return;
	sym->aclass = PABS|(sym->aclass&AEXPORT);
	sym->aval = expabs(exp);
}

redef(sym)
{
	register class;

	class = sym->aclass&0377 & ~AEXPORT;
	if (class && class != PCOMMON) {
		yyerror("redefined %s", sym->aname);
		return (1);
	}
	return (0);
}

label(sym)
{
	if (redef(sym)) return;

	sym->aclass = curseg | (sym->aclass&AEXPORT);
	sym->aval = *curpc;
}

lookup(name)
{
	register struct asym *pnt, *start;

	pnt = start = &symtab[hash(name)%SYMTAB];

	do {
		if (!pnt->aname[0]) {
			namecopy(name, pnt->aname);
			pnt->aval = pnt->aclass = 0;
			return (pnt);
		}

		if (strcmp(name, pnt->aname))
			return (pnt);

		if (++pnt >= &symtab[SYMTAB])
			pnt = symtab;
	} while (pnt != start);

	memcrash();
}

hash(name)
{
	register char *pnt;
	register h, c;

	h = 0;
	pnt = name;

	while (c = *pnt++) h = (h<<3)^c;

	return (h&077777);	/* unsigned */
}

namecopy(str1, str2)
{
	register char *s1, *s2;
	register i;

	i = 0;
	s1 = str1;
	s2 = str2;

	while (i++ < ANAME-1 && *s1)
		*s2++ = *s1++;
	*s2 = 0;
}

strcmp(str1, str2)
{
	register char *s1, *s2;
	register c;

	s1 = str1; s2 = str2;
	do {
		if ((c = *s1++) != *s2++)
			return (0);
	} while (c);
	return (1);
}

casecmp(str1, str2)
{
	register char *s1, *s2;
	register c;

	s1 = str1; s2 = str2;

	do {
		if ((c = *s1++) >= 'A' && c <= 'Z')
			c =- 'A' - 'a';
		if (c != *s2++) return (0);
	} while (c);
	return (1);
}

putbyte(val)
{
	if (curseg != PBSS)
		putc(val, &tempbuf);
	*curpc =+ 1;
}

putword(val)
{
	if (curseg != PBSS)
		putw(val, &tempbuf);
	*curpc =+ 2;
}

expbyte(expression)
{
	register *exp, hilo;

	exp = expression;

	if (exp[0] == EHILO) {
		hilo = exp[1];
		exp = exp[2];
	} else hilo = ALO;

	switch (exp[0]) {
	case EABS:
		putbyte(hilo == AHI ? exp[1]>>8 : exp[1]);
		break;
	case EOFFSET:
		putbyte(putlink(hilo, exp[1], exp[2]));
		break;
	case ESEG:
		putbyte(seglink(hilo, exp[1], exp[2]));
		break;
	case EREL:
		putbyte(segrel(hilo, exp));
		break;
	default:
		crash("bad exp %l", exp[0]);
	}
}

expword(expression)
{
	register *exp, hilo, val;

	exp = expression;

	if (exp[0] == EHILO) {
		hilo = exp[1];
		exp = exp[2];
	} else hilo = 0;

	switch (exp[0]) {
	case EABS:
		switch (hilo) {
		case AHI:
			putword((exp[1]>>8)&0377);
			break;
		case ALO:
			putword(exp[1]&0377);
			break;
		default:
			putword(exp[1]);
			break;
		}
		break;
	case EREL:
		val = segrel(hilo, exp);
		goto postlink;
	case ESEG:
		val = seglink(hilo, exp[1], exp[2]);
		goto postlink;
	case EOFFSET:
		val = putlink(hilo, exp[1], exp[2]);
postlink:
		if (hilo) {
			putbyte(val);
			putbyte(0);
		} else putword(val);
		break;
	default:
		crash("BAD EXPRESSION %o", exp[0]);
	}
}

segrel(hilo, exp) int exp[];
{
	register value;
	register char *nampnt, c;

	value = exp[2];
	if (curseg == PBSS) return (value);

	putw(*curpc - *prevlink, &linkbuf);
	*curlink =+ 2;
	*prevlink = *curpc;

	putc(hilo, &linkbuf);
	*curlink =+ 1;
	if (hilo == AHI) {
		putc(value, &linkbuf);
		*curlink =+ 1;
		value = (value>>8)&0377;
	} else if (hilo == ALO) value = value&0377;

	putc(PREL, &linkbuf);
	putc(exp[1], &linkbuf);
	*curlink =+ 2;

	nampnt = exp[3]->aname;
	do {
		c = *nampnt++&0377;
		putc(c, &linkbuf);
		*curlink =+ 1;
	} while (c);

	return (value);
}


needargs(count)
{
	if (argpnt - argland != count) {
		yyerror("bad arg count");
		return (1);
	}
	return (0);
}

/* Output a first past link chunk, returning the value to be output
 * in the segment.
 */
putlink(hilo, symbol, value)
{
	register *sym, val;
	register char *name;
	static char class;

	if (curseg == PBSS) return (value);

	sym = symbol;
	val = value;

	/* Calculate final value */
	class = sym->aclass&0377&~AEXPORT;
	if (class && class != PCOMMON)
		val =+ sym->aval;
	if (class == PABS)
		/* don't bother with a link if an absolute value */
		goto done;

	/* Write link offset */
	/* Update offset */
	putw(*curpc - *prevlink, &linkbuf);
	*curlink =+ 2;
	*prevlink = *curpc;

	/* Write hilo byte(s) */
	putc(hilo, &linkbuf);
	if (hilo == AHI) {
		putc(val, &linkbuf);
		*curlink =+ 2;
	} else *curlink =+ 1;

	/* Write class */
	*curlink =+ 1;
	if (class && class != PCOMMON)
		putc(class, &linkbuf);
	else {
		/* handle undefined */
		putc(0, &linkbuf);
		name = sym->aname;
		do {
			putc(*name, &linkbuf);
			*curlink =+ 1;
		} while (*name++);
	}

	done:
	switch (hilo) {
	case AHI:
		return ((val>>8)&0377);
	case ALO:
		return (val&0377);
	default:
		return (val);
	}
}

seglink(hilo, seg, val)
{
	if (curseg == PBSS) return (val);

	putw(*curpc - *prevlink, &linkbuf);
	*curlink =+ 2;
	*prevlink = *curpc;

	putc(hilo,&linkbuf);
	if (hilo == AHI) {
		putc(val, &linkbuf);
		*curlink =+ 2;
	} else *curlink =+ 1;

	putc(seg, &linkbuf);
	*curlink =+ 1;

	switch (hilo) {
	case AHI:
		return ((val>>8)&0377);
	case ALO:
		return (val&0377);
	default:
		return (val);
	}
}

umax(left, right)
char *left, *right;
{
	return (left > right ? left : right);
}

symplain(expression)
{
	register *exp;

	exp = expression;

	if (exp && exp[0] == EOFFSET && exp[2] == 0)
		return (exp[1]);
	yyerror("required plain symbol");
	return (0);
}

goseg(seg)
{
	if (seg == curseg) return;

	fflush(&tempbuf);
	fflush(&linkbuf);

	switch (seg) {
	case PTEXT:
		seek(tempbuf.fnum, 0, 0);
		seek(linkbuf.fnum, BLK64K*3, 3);
		curpc = &header.atext;
		curlink = &header.artext;
		break;
	case PDATA:
		seek(tempbuf.fnum, BLK64K, 3);
		seek(linkbuf.fnum, BLK64K*(3+1), 3);
		curpc = &header.adata;
		curlink = &header.ardata;
		break;
	case PBSS:
		curpc = &header.abss;
		break;
	case PSTRING:
		seek(tempbuf.fnum, BLK64K*2, 3);
		seek(linkbuf.fnum, BLK64K*(3+2), 3);
		curpc = &strpc;
		curlink = &strlink;
		break;
	default:
		crash("BAD SEGMENT %l", seg);
		break;
	}

	curseg = seg;
	prevlink = &prevtab[curseg-1];
	useek(tempbuf.fnum, *curpc);
	if (curseg != PBSS)
		useek(linkbuf.fnum, *curlink);
}

useek(file, offset)
char *offset;
{
	if (offset&0100000) {
		seek(file, BLK32K, 4);
		offset =& 077777;
	}
	seek(file, offset, 1);
}

irq()
{
	unlink(tname);
	exit(1);
}

mktemp()
{
	extern char peekc;

	tmpname(tname);
	close(creat(tname, 0666));
	signal(1, irq);
	signal(2, irq);

	tempbuf.fnum = open(tname, 2);
	linkbuf.fnum = open(tname, 2);

	if (tempbuf.fnum < 0 || linkbuf.fnum < 0)
		crash("temp error");

	/* make sure file has write size */
	seek(tempbuf.fnum, BLK64K*6, 3);
		/* seek past end of temp */
	write(tempbuf.fnum, peekc, 1);
		/* value doesn't matter */
	seek(tempbuf.fnum, 0, 0);
}

concat()
{
	goseg(PTEXT);
	putw(-1, &linkbuf);
	*curlink =+ 2;
	goseg(PDATA);
	putw(-1, &linkbuf);
	*curlink =+ 2;
	goseg(PSTRING);
	putw(-1, &linkbuf);
	*curlink =+ 2;

	close(creat("a.out.80", 0666));
	outbuf.fnum = open("a.out.80", 1);
	outlink.fnum = open("a.out.80", 1);

	if (outbuf.fnum < 0 || outlink.fnum < 0)
		crash("a.out error");

	fflush(&tempbuf);
	fflush(&linkbuf);
	tempbuf.fcount = linkbuf.fcount = 0;

	seek(tempbuf.fnum, 0, 0);
	seek(linkbuf.fnum, 3*BLK64K, 3);

	seek(outbuf.fnum, sizeof(header), 0);
	seek(outlink.fnum, sizeof(header), 0);
	useek(outlink.fnum, header.atext);
	useek(outlink.fnum, header.adata);
	useek(outlink.fnum, strpc);

	outseg(PTEXT);
	putw(-1, &outlink);
	header.artext = rsize+2;
	backlink = rsize = 0;

	tempbuf.fcount = linkbuf.fcount = 0;
	seek(tempbuf.fnum, BLK64K, 3);
	seek(linkbuf.fnum, 4*BLK64K, 3);

	outseg(PDATA);

	tempbuf.fcount = linkbuf.fcount = 0;
	seek(tempbuf.fnum, 2*BLK64K, 3);
	seek(linkbuf.fnum, 5*BLK64K, 3);

	outseg(PSTRING);
	putw(-1, &outlink);
	header.ardata = rsize+2;

	fflush(&outbuf);
	fflush(&outlink);
	fixsyms();
	outsyms(outlink.fnum);

	fixheader();
	seek(outbuf.fnum, 0, 0);
	write(outbuf.fnum, &header, sizeof(header));
}

fixsyms()
{
	register struct asym *sympnt;

	for (sympnt = symtab; sympnt < &symtab[SYMTAB]; sympnt++) {
		if (!sympnt->aname[0]) continue;

		switch (sympnt->aclass&0377&~AEXPORT) {
		case 0:
			break;
		case PTEXT:
			sympnt->aclass = ATEXT | (sympnt->aclass&AEXPORT);
			sympnt->aval =+ header.astart;
			break;
		case PDATA:
			sympnt->aclass = ADATA | (sympnt->aclass&AEXPORT);
			sympnt->aval =+ header.astart + header.atext;
			break;
		case PSTRING:
			sympnt->aclass = ADATA | (sympnt->aclass&AEXPORT);
			sympnt->aval =+ header.astart + header.atext
				+ header.adata;
			break;
		case PBSS:
			sympnt->aclass = ABSS | (sympnt->aclass&AEXPORT);
			sympnt->aval =+ header.astart + header.atext
				+ header.adata + strpc;
			break;
		case PABS:
			sympnt->aclass = AABS|(sympnt->aclass&AEXPORT);
			break;
		case PCOMMON:
			sympnt->aclass = ACOMMON|(sympnt->aclass&AEXPORT);
			break;
		default:
			crash("bad class %o", sympnt->aclass);
		}
	}
}

outsyms(file)
{
	register struct asym *sympnt;

	for (sympnt = symtab; sympnt < &symtab[SYMTAB]; sympnt++) {
		if (!sympnt->aname[0]) continue;

		write(file, sympnt, sizeof(*sympnt));
		header.asymsize =+ sizeof(*sympnt);
	}
}

outseg(seg)
{
	register char *pc, *nextlink, *endpc;
	static char *oldpc;

	pc = seg == PSTRING ? header.adata : 0;
	nextlink = getw(&linkbuf);
	if (nextlink != -1) nextlink =+ pc;

	switch (seg) {
	case PTEXT:
		endpc = header.atext;
		break;
	case PDATA:
		endpc = header.adata;
		break;
	case PSTRING:
		endpc = strpc+header.adata;
		break;
	}

	while (pc != endpc) {
		if (pc > endpc)
			crash("PAST END OF SEGMENT");
		if (nextlink != -1 && nextlink == pc) {
			oldpc = pc;
			pc =+ fixlink(pc);
			nextlink = getw(&linkbuf);
			if (nextlink != -1) nextlink =+ oldpc;
		}
		else {
			putc(getc(&tempbuf), &outbuf);
			pc++;
		}
	}
}

fixlink(pc)
{
	register hilo, class, value;

	hilo = getc(&linkbuf);

	if (hilo) {
		value = getc(&tempbuf)&0377;
		if (hilo == AHI)
			value = (value << 8) | (getc(&linkbuf) & 0377);
	}
	else value = getw(&tempbuf);

	class = getc(&linkbuf);

	if (class == PREL) return (fixrel(pc, hilo, value));
	else if (!class) return (fixundef(pc, hilo, value));
	else return (fixseg(pc, hilo, class, value));
}

fixrel(pc, hilo, value)
{
	static class, symclass;
	register i, c, *sym;
	static char name[ANAME];

	class = getc(&linkbuf);

	i = 0;
	while (c = getc(&linkbuf))
		if (i < ANAME-1) name[i++] = c;
	name[i] = 0;

	sym = lookup(name);
	if (!sym) {
notdef:
		yyerror("bad expr: %s must be defined in this object", name);
		goto done;
	}

	symclass = sym->aclass&0377&~AEXPORT;
	if (!symclass) goto notdef;

	if (symclass != class) {
		yyerror("bad expr: %s in wrong segment", name);
		yyerror("(should be %o)", class);
		yyerror("(is %o)", sym->aclass&0377&~AEXPORT);
		errcount =- 2;
		goto done;
	}

	value = sym->aval + value;
	/* this is an absolute value w/o need of link info,
	 * since the start of the segment + a constant -
	 * the start of the segment, remvoes the
	 * segment's start from the equation entirely.
	 */
done:
	switch (hilo) {
	case AHI:
		putc((value>>8)&0377, &outbuf);
		return (1);
	case ALO:
		putc(value&0377, &outbuf);
		return (1);
	default:
		putw(value, &outbuf);
		return (2);
	}
}

fixseg(pc, hilo, class, value)
char *pc;
{
	switch (class) {
	default:
		crash("bad class %o", class);
	case PTEXT:
		value =+ header.astart;
		class = ATEXT;
		break;
	case PDATA:
		value =+ header.astart + header.atext;
		class = ADATA;
		break;
	case PSTRING:
		value =+ header.astart + header.atext + header.adata;
		class = ADATA;
		break;
	case PBSS:
		value =+ header.astart + header.atext + header.adata
			+ strpc;
		class = ABSS;
		break;
	case PABS:
		goto out;	/* output an absolute symbol w/o linkage */
	}

	putw(pc - backlink, &outlink);
	rsize =+ 2;
	backlink = pc;

	putc(hilo, &outlink);
	if (hilo == AHI) {
		putc(value&0377, &outlink);
		rsize =+ 2;
	} else rsize++;
	putc(class, &outlink);
	rsize++;

out:
	switch (hilo) {
	case ALO:
		putc(value&0377, &outbuf);
		return (1);
	case AHI:
		putc((value>>8)&0377, &outbuf);
		return (1);
	default:
		putw(value, &outbuf);
		return (2);
	}
}

fixundef(pc, hilo, value)
char *pc;
{
	static char name[ANAME];
	register i, c, *sym;

	i = 0;
	while (c = getc(&linkbuf))
		if (i < ANAME-1) name[i++] = c;
	name[i] = 0;

	sym = lookup(name);
	c = sym->aclass&0377&~AEXPORT;
	if (c && c != PCOMMON)
		/* we found the symbol! it was a forward reference */
		/* it hasn't been fixed yet, so we can redirect it to
		 * fixseg.
		 */
		return(fixseg(pc, hilo, c, value + sym->aval));

	/* else, it's a real undefined */
	undefs++;
	putw(pc - backlink, &outlink);
	rsize =+ 2;
	backlink = pc;
	putc(hilo, &outlink);
	if (hilo == AHI) {
		putc(value&0377, &outlink);
		rsize =+ 2;
	} else rsize++;

	putc(0, &outlink);
	rsize++;
	i = 0;
	do {
		putc((c = name[i++]), &outlink);
		rsize++;
	} while (c);

	switch (hilo) {
	case ALO:
		putc(value&0377, &outbuf);
		return (1);
	case AHI:
		putc((value>>8)&0377, &outbuf);
		return (1);
	default:
		putw(value, &outbuf);
		return (2);
	}
}

fixhead()
{
	header.amagic = 0417;
	header.aflags = undefs ? 0 : AEXEC;
	header.adata =+ strpc;
}

epc()
{
	register *pnt;

	pnt = exppnt;
	putexp(ESEG);
	putexp(curseg);
	putexp(*curpc);
	return (pnt);
}
