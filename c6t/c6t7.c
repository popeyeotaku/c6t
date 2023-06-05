#include "c6t.h"

/* C6T - C version 6 by Troy - PART SEVEN */

/* Parse a class, returning a flag for if we saw one.
 */
grabclass()
{
	register t;

	switch (t = token()) {
	case EXTERN:
	case AUTO:
	case STATIC:
	case REGISTER:
		curclass = t;
		return (1);
	}
	peektkn = t;
	return (0);
}

/* Parse a base type, returning a flag for if we
 * saw one.
 */
grabtype()
{
	switch (peektkn = token()) {
	default:
		return (0);
	case INT:
		basetype.tystr = TYINT;
		break;
	case CHAR:
		basetype.tystr = TYCHAR;
		break;
	case FLOAT:
		basetype.tystr = TYFLOAT;
		break;
	case DOUBLE:
		basetype.tystr = TYDOUBLE;
		break;
	case STRUCT:
		peektkn = 0;
		instruct();
		return (1);
	}
	peektkn = 0;
	return (1);
}

/* Callback function for external definition speifiers.
 */
cbext(symbol)
{
	register *sym;

	sym = symbol;
	if ((peektkn = token()) == COMMA || peektkn == SEMICOLON)
		common(sym);
	else if ((curtype.tystr&TYMOD)==TYFUNC) funcinit(sym);
	else datainit(sym);
	cleanup();
}

/* Output to the backend a piece of data that is marked common.
 */
common(symbol)
{
	register *sym;

	sym = symbol;
	if (sym->sclass) {
		if (sym->stype.tystr == curtype.tystr && sym->sclass
				== EXTERN)
			return;
		redef(sym->sname);
	}
	sym->sclass = EXTERN;
	tycopy(&curtype, &sym->stype);
	if ((curtype.tystr&TYMOD)==TYFUNC) return;
	goseg(BSS);
	printf("COMMON %x,%l\n", sym->sname, tysize(&curtype));
}

/* Handle an initialized function; that is, a function which
 * has defined statements etc.
 */
funcinit(symbol)
{
	register *sym;
	extern cbparam(), cblocal();

	if ((sym = symbol)->sclass && (sym->stype.tystr&TYMOD)!=TYFUNC)
		redef(sym->sname);
	if (curtype.tystr == (TYFLOAT|TYFUNC))
		curtype.tystr = TYDOUBLE|TYFUNC;
	else if (curtype.tystr == (TYCHAR|TYFUNC))
		curtype.tystr = TYINT|TYFUNC;
	tycopy(&curtype, &sym->stype);
	sym->sclass = EXTERN;
	goseg(CODE);
	printf("%x:\n\nFUNC %x\nEXPORT %x\n",
		sym->sname,
		sym->sname,
		sym->sname
	);

	sizebak = sizei;
	localscope++;
	speclist(ARG, cbparam);
	finalparams();
	need(LBRACE);
	curreg = curauto = 0;
	speclist(AUTO, cblocal);
	goseg(CODE);
	printf("USEDREGS %l\nAUTOS %l\n", curreg, -curauto);
	while (!match(RBRACE)) {
		earlyeof();
		statement();
	}

	localscope = 0;
	sizei = sizebak;
	cleanup();
	goseg(CODE);
	printf("RETNULL\nENDFUNC\n");
}

/* Issue an error if we hit end of file, and end compilation.
 */
earlyeof()
{
	if (match(EOF)) crash("unexpected end of file");
}

/* Clean up symbol table and nodes.
 */
cleanup()
{
	register struct node *npnt;
	register struct symbol *sympnt;

	argcount = 0;
	for (sympnt = symtab; sympnt <= &symtab[SYMTAB]; sympnt++) {
		if (sympnt->sflags&SUNDEF) {
			error("undefined symbol %n", sympnt->sname);
			sympnt->sname[0] = 0;
		}
		else if (sympnt->sflags&SLOCAL)
			sympnt->sname[0] = 0;
	}

	for (npnt = nland; npnt < &nland[NLAND]; npnt++)
		npnt->nlab = 0;
}

/* Parse a specifier, returning a pointer to its symbol table entry,
 * or 0 if no specifier seen.
 */
spec()
{
	register *sym;
	register t, mod;

	/* Setup curtype for the parse. */
	curtype.tystr = 0;
	curtype.tystruct = basetype.tystruct;
	curtype.tyarray = sizei;

	/* Do the actual parsing, modifiers now in
	 * curtype.tystr.
	 */
	sym = speclo();

	/* Save modifiers, apply base type.
	 */
	t = curtype.tystr;
	curtype.tystr = basetype.tystr;
	/* Reverse type modifier order. */
	while (mod = t&TYMOD) {
		typush(&curtype, mod);
		t = (t>>TYLEN)&~TYTOP;
	}
	return (sym);
}

/* Low level parsing of a specifier.
 */
speclo()
{
	register *sym, t;

	/* Left side */
	switch (t = token()) {
	case MULT:
		sym = speclo();
		typush(&curtype, TYPOINT);
		return (sym);
	case NAME:
		sym = lookup(tname);
		break;
	case LPAREN:
		sym = speclo();
		need(RPAREN);
		break;
	default:
		peektkn = t;
		return (0);
	}

	/* Right side */
	for (ever) switch (t = token()) {
	case LPAREN:
		if (!match(RPAREN))
			argnames();
		typush(&curtype, TYFUNC);
		continue;
	case LBRACK:
		if (match(RBRACK))
			typush(&curtype, TYARRAY, 1);
		else {
			typush(&curtype, TYARRAY, conexpr());
			need(RBRACK);
		}
		continue;
	default:
		peektkn = t;
		return (sym);
	}
}

/* Parse an integer constant expression. */
conexpr()
{
	register *n, i;

	n = expr(0);	/* no commas */
	if (n->nlab != CON) {
		error("expected constant expression");
		i = 1;
	}
	else i = n->nval;
	nfree(n);
	return (i);
}

/* Issue an error that a symbol is already defined.
 */
redef(name)
{
	error("%n already defined", name);
}

/* Read in argument NAMEs in a function specifier.
 */
argnames()
{
	register *sym;

	do {
		if (!match(NAME)) break;
		sym = lookup(tname);
		if (sym->sclass) redef(sym->sname);
		sym->sclass = ARG;
		sym->soffset = argcount++;
		sym->stype.tystr = TYINT;
		sym->sflags = SLOCAL;
	} while (match(COMMA));
	need(RPAREN);
}

/* Callback for a specifier list of parameters.
 */
cbparam(symbol)
{
	register *sym;

	sym = symbol;
	if (sym->sclass != ARG) {
		error("%n not an argument", sym->sname);
		return;
	}

	/* Fix the type */
	switch (curtype.tystr&TYMOD) {
	case TYFUNC:
		error("cannot pass function types");
		break;
	case TYARRAY:
		typop(&curtype);
		typush(&curtype, TYPOINT);
		break;
	case 0:
		switch (curtype.tystr&TYBASE) {
		case TYCHAR:
			curtype.tystr = TYINT;
			break;
		case TYSTRUCT:
			error("cannot pass a struct type");
			break;
		case TYFLOAT:
			curtype.tystr = TYDOUBLE;
			break;
		}
	}

	tycopy(&curtype, &sym->stype);
}

/* Finalize parameter types */
finalparams()
{
	register i;
	register struct symbol *sym;
	register offset;

	offset = ARGOFFSET;

	for (i = 0; i < argcount; i++) {
		for (sym = symtab; sym < &symtab[SYMTAB]; sym++) {
			if (sym->sclass == ARG && sym->soffset == i) {
				sym->sclass = AUTO;
				sym->soffset = offset;
				offset =+ tysize(&sym->stype);
				break;
			}
		}
	}
	argcount = 0;
}

/* Parse a STRUCT basetype (STRUCT keyword already seen).
 * Set basetype to its type.
 */
instruct()
{
	register *name, oldsize, size;
	auto *oldst;
	extern cbmember();

	basetype.tystr = TYINT;	/* Default for an error condition */

	if (match(NAME))
		name = tag(tname);
	else name = 0;

	if (match(LBRACE)) {
		oldsize = membsize;
		if (name && !name->sclass) {
			oldst = curst;
			curst = name;
			name->soffset = oldst;
		}
		membsize = 0;

		speclist(MEMBER, cbmember);
		need(RBRACE);

		size = membsize;
		membsize = oldsize;
		if (name && !name->sclass) {
			curst = oldst;
			name->soffset = 0;
		}
	}
	else size = 0;

	if (name && !size) {
		if (!name->sclass) {
			if (stchain(name)) {
				basetype.tystr = TYSTRUCT;
				basetype.tystruct = addsize(0);
				return;
			}
			else {
				error("struct %n not defined",
					name->sname);
				return;
			}
		}
		basetype.tystr = TYSTRUCT;
		basetype.tystruct = name->soffset;
	}
	else if (!name && size) {
		basetype.tystr = TYSTRUCT;
		basetype.tystruct = addsize(size);
	}
	else if (name && size) {
		if (name->sclass) redef(name->sname);
		name->sclass = STRUCT;
		name->soffset = basetype.tystruct = addsize(size);
		basetype.tystr = TYSTRUCT;
		name->sflags = localscope ? SLOCAL : 0;
	}
	else error("bad STRUCT spec");
}

/* Callback for a member speclist.
 */
cbmember(symbol)
{
	register *sym;

	/* Get the tag instead of the plain symbol */
	sym = tag(symbol->sname);
	/* Clear out uneeded symbol. */
	if (symbol->sname[0] != '.' && !symbol->sclass)
		symbol->sname[0] = 0;

	/* Allow redefined MEMBERs if they're compatible */
	if (sym->sclass == MEMBER && sym->soffset == membsize &&
			sym->stype.tystr == curtype.tystr) {
		membsize =+ tysize(&sym->stype);
		return;
	}
	if (sym->sclass) {
		redef(sym->sname);
		return;
	}

	sym->sclass = MEMBER;
	tycopy(&curtype, &sym->stype);
	sym->soffset = membsize;
	membsize =+ tysize(&curtype);
	sym->sflags = localscope ? SLOCAL : 0;
}

/* Return a flag if the given tag symbol can be reached via the curst
 * chain.
 */
stchain(cmpsym)
struct symbol *cmpsym;
{
	register struct symbol *stsym;

	for (stsym = curst; stsym; stsym = stsym->soffset)
		if (stsym == cmpsym) return (1);
	return (0);
}
