#include "c6t.h"

/* C6T - C version 6 by Troy - PART ZERO */

/* Refill both readahead characters from getchar() */
fill2()
{
	readahead[0] = getchar();
	readahead[1] = getchar();
}

/* Advance on character in the readahead. Move the second readahead
 * character to the first position, and refill the second readahead
 * from getchar().
 */
fill1()
{
	readahead[0] = readahead[1];
	readahead[1] = getchar();
}

/* Skip leading whitespace */
whitespace()
{
	for (ever) switch (readahead[0]) {
	case '\n':
		if (countlines) line++;
		/* fall thru */
	case ' ':
	case '\t':
		fill1();
		continue;
	case '@':
		countlines = !countlines;
		fill1();
		continue;
	default:
		/* Since we guarentee the environment more than usual
		 * C, we can use multi-char character
		 * constants!
		 */
		if (readahead[0].integ == '/*') {
			/* comment start! (as you can see) */
			fill2();
			while (readahead[0]) {
				/* 0 is the EOF character, so this will
				 * exit the loop on EOF.
				 */
				if (readahead[0].integ == '*/') {
					fill2();
					break;
				}
				if (readahead[0] == '\n' && countlines)
					line++;
				fill1();
			}
			continue;
		} else return;
	}
}

/* Return the next input token label number.
 */
token()
{
	register c;

	/* Handle a peeked token. */
	if (c = peektkn) {
		peektkn = 0;	/* Undo the peek */
		return (c);
	}

retry:
	whitespace();

	/* Handle two-character operators */
	switch (readahead[0].integ) {
	case '=+':
		fill2();
		return (ASNADD);
	case '=-':
		fill2();
		return (ASNSUB);
	case '=*':
		fill2();
		return (ASNMULT);
	case '=/':
		fill2();
		return (ASNDIV);
	case '=%':
		fill2();
		return (ASNMOD);
	case '=&':
		fill2();
		return (ASNAND);
	case '=^':
		fill2();
		return (ASNEOR);
	case '=|':
		fill2();
		return (ASNOR);
	case '||':
		fill2();
		return (LOGOR);
	case '&&':
		fill2();
		return (LOGAND);
	case '==':
		fill2();
		return (EQU);
	case '!=':
		fill2();
		return (NEQU);
	case '<=':
		fill2();
		return (LEQU);
	case '>=':
		fill2();
		return (GEQU);
	case '>>':
		fill2();
		return (RSHIFT);
	case '<<':
		fill2();
		return (LSHIFT);
	case '++':
		fill2();
		return (PREINC);
	case '--':
		fill2();
		return (PREDEC);
	case '->':
		fill2();
		return (ARROW);
	}

	if (!(c = readahead[0])) return (EOF);

	if (num(c) || (c == '.' && num(readahead[1])))
		return (grabnum());
	if (alpha(c)) return (grabname());
		/* also handles keywords */

	/* We have to handle this character no matter what! */
	fill1();

	switch (c) {
	case '\'':
		return (grabcc());
	case '"':
		return (grabstr());
	case '{':
		return (LBRACE);
	case '}':
		return (RBRACE);
	case ';':
		return (SEMICOLON);
	case '=':
		if (readahead[0].integ == '>>') {
			fill2();
			return (ASNRSHIFT);
		}
		if (readahead[0].integ == '<<') {
			fill2();
			return (ASNLSHIFT);
		}
		return (ASSIGN);
	case ',':
		return (COMMA);
	case '?':
		return (QUEST);
	case ':':
		return (COLON);
	case '|':
		return (OR);
	case '^':
		return (EOR);
	case '&':
		return (AND);
	case '<':
		return (LESS);
	case '>':
		return (GREAT);
	case '+':
		return (ADD);
	case '-':
		return (SUB);
	case '*':
		return (MULT);
	case '/':
		return (DIV);
	case '%':
		return (MOD);
	case '!':
		return (LOGNOT);
	case '~':
		return (COMPL);
	case '(':
		return (LPAREN);
	case ')':
		return (RPAREN);
	case '[':
		return (LBRACK);
	case ']':
		return (RBRACK);
	case '.':
		return (DOT);
	}

	error("bad input character '%c'", c);
	goto retry;
}

/* Return a flag if the character is numerical */
num(c)
{
	return (c >= '0' && c <= '9');
}

/* Return a flag if the character is alphabetic */
alpha(c)
{
	return (
		(c >= 'a' && c <= 'z')
		|| (c == '_')
		|| (c >= 'A' && c <= 'Z')
	);
}

/* Return a flag if the character is alphabetic or numeric */
alphanum(c)
{
	return (alpha(c) || num(c));
}

/* This table of keywords relies on the order of the enumerations for
 * the keywords.
 */
char *kwtab[] {
	"int", "char", "float", "double", "struct", "auto", "extern",
	"register", "static", "goto", "return", "sizeof", "break",
	"continue", "if", "else", "for", "do", "while", "switch",
	"case", "default", "entry", 0
};

/* Read in a NAME or keyword (leading alpha already seen).
 */
grabname()
{
	register i;

	i = 0;
	while (alphanum(readahead[0])) {
		if (i < NAMELEN) tname[i++] = readahead[0];
		fill1();
	}
	/* Null pad */
	while (i < NAMELEN) tname[i++] = 0;

	/* Search for keyword */
	for (i = 0; kwtab[i]; i++)
		if (namcmp(kwtab[i], tname)) return (INT+i);
	return (NAME);
}

/* Read in an integral or floating constant.
 * TODO: actually do floats
 */
grabnum()
{
	register n, base;

	n = 0;
	base = readahead[0] == '0' ? 8 : 10;

	while (num(readahead[0])) {
		n = n * base + readahead[0] - '0';
		fill1();
	}

	tval = n;
	return (CON);
}

/* Grab a character constant.
 * Leading ' has already been skipped.
 */
grabcc()
{
	register i;

	i = 0;

	while (readahead[0] && !cmatch('\''))
		i = (i << 8) | (dochar() & 0377);
	tval = i;
	return (CON);
}

/* Grab a string literal.
 * Leading " has already been skipped.
 */
grabstr()
{
	register i, c;

	i = 0;

	while (readahead[0] && !cmatch('"')) {
		c = dochar();
		if (i < STRMAX) tstr[i++] = c;
	}
	tlen = i;
	return (STRING);
}

/* If the next readahead character matches, fill past it and return
 * true. Else, return 0 and don't skip any characters.
 */
cmatch(c)
{
	if (readahead[0] == c) {
		fill1();
		return (1);
	}
	return (0);
}

/* Process a character in a character constant or string literal.
 */
dochar()
{
	register c;

	if (cmatch('\\')) {
		switch (readahead[0]) {
		case 'b':
			fill1();
			return (010);
		case 'n':
			fill1();
			return (012);
		case 'r':
			fill1();
			return (015);
		case '0':
		case '1':
		case '2':
		case '3':
		case '4':
		case '5':
		case '6':
		case '7':
			return (ccoctal());
		}
	}
	c = readahead[0];
	fill1();
	return (c);
}

/* Read in an octal character constant element.
 */
ccoctal()
{
	register i, c;

	c = 0;
	for (i = 0; i < 3; i++)
		if (readahead[0] >= '0' && readahead[0] <= '7') {
			c = c << 3 | (readahead[0] - '0');
			fill1();
		} else break;

	return (c);
}
