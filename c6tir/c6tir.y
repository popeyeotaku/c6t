/* C6TIR Backend Parser */

%token NAME NODE CMD CON

%left '+' '-'

%%

program :
	line
	| program '\n' line
	| program error '\n' line
	;

line :
	labels statement
	= {
		cleanup();
	}
	;

labels :
	/* empty */
	| labels label
	;

label :
	NAME ':'
	= {
		deflab($1);
	}
	;

statement :
	cmd
	| node
	| /* empty */
	;

cmd :
	CMD args
	= {
		docmd($1, $2);
	}
	;

node :
	NODE args
	= {
		push(build($1, $2));
	}
	;

args :
	/* empty */
	= {
		$$ = 0;
	}
	| arglist trailcomma
	;

trailcomma :
	/* empty */
	| ','
	;

arglist :
	arg
	| arglist ',' arg
	= {
		$$ = arglist($1, $3);
	}
	;

arg :
	NAME
	= {
		$$ = name($1);
	}
	| CON
	= {
		$$ = con($1);
	}
	| NAME op CON
	= {
		if ($2 == '-') $3 = -$3;
		$$ = offset($1, $3);
	}
	| CON op NAME
	= {
		if ($2 == '-') crash("CANNOT SUBTRACT A NAME");
		$$ = offset($3, $1);
	}
	;

op :
	'+'
	| '-'
	;

%%

#define BUFLEN 16

int bufcount;
char namebuf[2][BUFLEN+1];
char peekc;

yylex()
{
	extern yyline, yylval;
	extern struct { char *kwname; int kwval;} cmdtab[], nodetab[];
	register char *buf;
	register c, i;

	if (!yyline) yyline = 1;

	if (peekc) {
		c = peekc;
		peekc = 0;
	} else c = getchar();

	/* whitespace */
	while (c == ' ' || c == '\t') c = getchar();
	/* skip comments */
	if (c == ';')
		while ((c = getchar()) && c != '\n');

	if (c >= '0' && c <= '9') {
		i = 0;
		do {
			i = i * 10 + c - '0';
		} while ((c = getchar()) >= '0' && c <= '9');
		peekc = c;
		yylval = i;
		return (CON);
	}

	if (alpha(c)) {
		i = 0;
		buf = namebuf[bufcount++&1];
		do {
			if (i < BUFLEN) buf[i++] = c;
		} while (alphanum(c = getchar()));
		peekc = c;
		buf[i] = 0;

		for (i = 0; cmdtab[i].kwname; i++) {
			if (casecmp(cmdtab[i].kwname, buf)) {
				yylval = cmdtab[i].kwval;
				return (CMD);
			}
		}
		for (i = 0; nodetab[i].kwname; i++) {
			if (casecmp(nodetab[i].kwname, buf)) {
				yylval = nodetab[i].kwval;
				return (NODE);
			}
		}
		yylval = buf;
		return (NAME);
	}

	if (c == '\n') yyline++;
	return (c);
}

yyerror(msg)
{
	extern fout, yyline;
	register oldout;

	oldout = fout;
	flush();
	fout = 2;
	printf("%l: %s\n", yyline, msg);
	flush();
	fout = oldout;
}
