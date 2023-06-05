%token NAME CON PSEUDO OPCODE

%left '+' '-'
%left '*' '/'
%right NEG

%%

program :
	line
	= {
		cleanup();
	}
	| program '\n' line
	= {
		cleanup();
	}
	| program error '\n' line
	= {
		cleanup();
	}
	;

e :
	NAME
	= {
		$$ = ename($1);
	}
	| CON
	= {
		$$ = econ($1);
	}
	| '*'
	= {
		$$ = epc();
	}
	| e '+' e
	= {
binop:
		$$ = eval($2, $1, $3);
	}
	| e '-' e
	= {
		goto binop;
	}
	| e '*' e
	= {
		goto binop;
	}
	| e '/' e
	= {
		goto binop;
	}
	| '-' e %prec NEG
	= {
		$$ = eneg($2);
	}
	| '(' e ')'
	= {
		$$ = $2;
	}
	;

expr :
	e
	| '>' e
	= {
hilo:
		$$ = ehilo($1, $2);
	}
	| '<' e
	= {
		goto hilo;
	}
	;

line :
	labels cmd
	;

labels :
	/* empty */
	| labels NAME ':'
	= {
		label($2);
	}
	;

cmd :
	/* empty */
	| PSEUDO args
	= {
		pseudo($1);
	}
	| op
	| NAME '=' expr
	= {
		setequ($1, $3);
	}
	;

op :
	OPCODE args
	= {
		$$ = opcode($1);
	}
	;

args :
	/* empty */
	| arghead argtail
	;

arghead :
	expr
	= {
		addarg($1);
	}
	;

argtail :
	/* empty */
	| argtail ',' expr
	= {
		addarg($3);
	}
	;

%%

#include "../poplink/poplink.h"
#include "asm.h"

char peekc;

yylex()
{
	extern yylval, yyline;
	register i, c, base;
	static char nbuf[NAMELEN];

	if (c = peekc) peekc = 0;
	else c = getchar();

	while (c == ' ' || c == '\t')
		c = getchar();

	if (c == '\'') {
		yylval = getchar();
		if ((peekc = getchar()) == '\'')
			peekc = 0;
		return (CON);
	}

	if (c == ';')
		while ((c = getchar()) && c != '\n')
			;

	if (c == '\n')
		yyline++;
	else if (c >= '0' && c <= '9') {
		i = 0;
		base = c == '0' ? 8 : 10;
		do {
			i = i * base + c - '0';
		} while ((c = getchar()) >= '0' && c <= '9');
		peekc = c;
		yylval = i;
		return (CON);
	}
	else if (alpha(c)) {
		i = 0;
		do {
			if (i < NAMELEN-1) nbuf[i++] = c;
		} while (alphanum(c = getchar()));
		peekc = c;
		nbuf[i] = 0;

		if (nbuf[0] == '.' && grabpseudo(nbuf, &yylval))
			return (PSEUDO);
		if (grabop(nbuf, &yylval))
			return (OPCODE);
		yylval = lookup(nbuf);
		return (NAME);
	}

	return (yylval = c);
}
