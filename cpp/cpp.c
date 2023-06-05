#

/* C6T Preprocessor */

#define NAME 9

#define LINE 512
char line[LINE];

int linenum 1;

char *cmdline;

#define MACROS 300
struct macro {
	char mname[NAME];
	char *mtext;
} macros[MACROS], *lastmac macros;

#define MACTEXT (4*1024)
char mactext[MACTEXT], *textpnt mactext;

#define BUFLEN (518/2)
int mainbuf[BUFLEN], incbuf[BUFLEN];

char peekc, eof;

main(argc, argv) char **argv;
{
	extern fout;

	fout = dup(1);	/* make output buffered */
	if (argc > 1) {
		if (fopen(argv[1], mainbuf) < 0)
			exit(1);
	}

	if ((peekc = getchar()) != '#') {
		while (putchar(getchar()))
			;
	} else {
		do {
			inline();
			if (line[0] == '#') {
				command();
				putchar('\n');
			} else outline();
		} while (!eof);
	}
	flush();
	exit(0);
}

getchar()
{
	register c;

	if (c = peekc) {
		peekc = 0;
		return (c);
	}
	if (eof) return;
	if (incbuf[0]) {
		c = getc(incbuf);
		if (c < 0) {
			putchar('@');
			incbuf[0] = 0;
			c = getc(mainbuf);
		}
	} else c = getc(mainbuf);

	if (c == -1) {
		eof++;
		return(0);
	}
	return (c);
}

inline()
{
	register c, prevc;
	register char *pnt;
	static char inquote;

	pnt = line;

	while (c = getchar()) {
		if (!inquote && c == '/' && (peekc = getchar()) == '*') {
			peekc = prevc = 0;
			while (c = getchar()) {
				if (prevc == '*' && c == '/') {
					c = ' ';
					break;
				}
				if (c == '\n')
					if (pnt < &line[LINE-1]) *pnt++ = c;
				prevc = c;
			}
			if (!c) break;
		}
		if (!(pnt > line && pnt[-1] == '\\')) {
			if (c == '\n') break;
			else if (inquote && c == inquote)
				inquote = 0;
			else if (!inquote && (c == '\'' || c == '"'))
				inquote = c;
		}
		if (pnt < &line[LINE-1]) *pnt++ = c;
	}
	*pnt = 0;
}

outline()
{
	register char *pnt, c;
	register i;
	static char name[NAME], *oldpnt;

	pnt = line;

	while (c = *pnt++) {
		if (c == '\'' || c == '"') {
			putchar(c);
			while (*pnt) {
				putchar(*pnt);
				if (*pnt == c && pnt[-1] != '\\') {
					pnt++;
					break;
				}
				pnt++;
			}
		}
		else if (alpha(c)) {
			oldpnt = pnt-1;
			i = 0;
			do {
				if (i < NAME-1) name[i++] = c;
			} while (alphanum(c = *pnt++));
			pnt--;
			name[i] = 0;

			if (i = findmac(name)) {
				putchar(' ');
				puts(i->mtext);
				putchar(' ');
			}
			else while (oldpnt < pnt)
				putchar(*oldpnt++);
		}
		else putchar(c);
	}
	putchar('\n');
}

alpha(c)
{
	return (
		(c >= 'A' && c <= 'Z')
		|| (c >= 'a' && c <= 'z')
		|| (c == '_')
	);
}

alphanum(c)
{
	return (
		(c >= '0' && c <= '9')
		|| alpha(c)
	);
}

puts(string)
{
	register char *s, c;

	if (s = string) while (c = *s++) putchar(c);
}

findmac(name)
{
	register struct macro *macpnt;

	for (macpnt = macros; macpnt < lastmac; macpnt++)
		if (strequ(name, macpnt->mname)) return (macpnt);

	return (0);
}

strequ(left, right)
{
	register char *s1, *s2, c;

	s1 = left;
	s2 = right;

	do {
		if ((c = *s1++) != *s2++)
			return (0);
	} while (c);
	return (1);
}

command()
{
	cmdline = &line[1];	/* skip leading '#' */

	while (*cmdline == ' ' || *cmdline == '\t')
		cmdline++;

	if (match("include")) doinc();
	else if (match("define")) dodef();
}

match(string)
{
	register char *spnt, *lpnt, c;

	lpnt = cmdline;
	spnt = string;

	while (c = *spnt++)
		if (*lpnt++ != c) return (0);

	cmdline = lpnt;
	return (1);
}

doinc()
{
	register char *pnt, *start;

	if (incbuf[0]) {
		error("only one level includes supported");
		return;
	}

	pnt = cmdline;

	while (*pnt == ' ' || *pnt == '\t')
		pnt++;

	if (*pnt++ != '"') {
		error("missing filename");
		return;
	}

	start = pnt;

	while (*pnt && *pnt != '"')
		pnt++;

	*pnt = 0;

	if (fopen(start, incbuf) < 0) {
		error("cannot open include file \"%s\"", start);
		incbuf[0] = 0;
		return;
	}
	putchar('@');
}

error(msg, arg)
{
	extern fout;
	register oldout;

	oldout = fout;
	flush();
	fout = 2;

	printf("%l: ", linenum);
	printf(msg, arg);
	putchar('\n');

	flush();
	fout = oldout;
}

dodef()
{
	register i, c, *mac;
	static char name[NAME];

	while (*cmdline == ' ' || *cmdline == '\t') cmdline++;

	if (!alpha(*cmdline)) {
		error("bad define name");
		return;
	}

	while (alphanum(c = *cmdline++)) {
		if (i < NAME-1) name[i++] = c;
	}
	name[i] = 0;

	if (findmac(name)) {
		error("redefined %s", name);
		return;
	}

	mac = lastmac++;
	if (mac >= &macros[MACROS]) memcrash();

	for (i = 0; i < NAME; i++)
		mac->mname[i] = name[i];

	mac->mtext = textpnt;

	while (c = *cmdline++) {
		if (c == ' ' || c == '\t') {
			putmac(' ');
			while ((c = *cmdline) == ' ' || c == '\t')
				cmdline++;
		}
		else if (c == '\'' || c == '"') {
			putmac(c);
			while (*cmdline) {
				putmac(*cmdline);
				if (*cmdline == c && cmdline[-1] != '\\')
					break;
				cmdline++;
			}
		}
		else putmac(c);
	}
	putmac(0);
}

putmac(c)
{
	if (textpnt >= &mactext[MACTEXT])
		memcrash();
	*textpnt++ = c;
}

memcrash()
{
	error("OUT OF MEMORY");
	abort();
}
