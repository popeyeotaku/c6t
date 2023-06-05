#
# define NAME 257
# define CON 258
# define PSEUDO 259
# define OPCODE 260
# define NEG 261
#define yyclearin yychar = -1
#define yyerrok yyerrflag = 0
extern int yychar, yyerrflag;

int yyval 0;
int *yypv;
int yylval 0;
yyactr(__np__){

switch(__np__){

case 1: {
		cleanup();
	} break;
case 2: {
		cleanup();
	} break;
case 3: {
		cleanup();
	} break;
case 4: {
		yyval = ename(yypv[1]);
	} break;
case 5: {
		yyval = econ(yypv[1]);
	} break;
case 6: {
		yyval = epc();
	} break;
case 7: {
binop:
		yyval = eval(yypv[2], yypv[1], yypv[3]);
	} break;
case 8: {
		goto binop;
	} break;
case 9: {
		goto binop;
	} break;
case 10: {
		goto binop;
	} break;
case 11: {
		yyval = eneg(yypv[2]);
	} break;
case 12: {
		yyval = yypv[2];
	} break;
case 14: {
hilo:
		yyval = ehilo(yypv[1], yypv[2]);
	} break;
case 15: {
		goto hilo;
	} break;
case 18: {
		label(yypv[2]);
	} break;
case 20: {
		pseudo(yypv[1]);
	} break;
case 22: {
		setequ(yypv[1], yypv[3]);
	} break;
case 23: {
		yyval = opcode(yypv[1]);
	} break;
case 26: {
		addarg(yypv[1]);
	} break;
case 28: {
		addarg(yypv[3]);
	} break;
}
}
int yyerrval 256;


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

int yyact[] {0,12305,4096,16384,4352,8197,4106,8196,0,12289
,4353,8199,4355,8200,4356,8202,12307,12305,4106,8204
,0,12304,4154,8205,4157,8206,0,4353,8213,4354
,8214,4141,8216,4138,8215,4136,8217,4158,8211,4156
,8212,12312,12309,12290,12306,4353,8213,4354,8214,4141
,8216,4138,8215,4136,8217,4158,8211,4156,8212,0
,12308,12315,12314,4139,8222,4141,8223,4138,8224,4143
,8225,12301,4353,8213,4354,8214,4141,8216,4138,8215
,4136,8217,0,12292,12293,12294,12311,12291,12310,4140
,8230,12313,4139,8222,4141,8223,4138,8224,4143,8225
,12302,4139,8222,4141,8223,4138,8224,4143,8225,12303
,12299,4139,8222,4141,8223,4138,8224,4143,8225,4137
,8235,0,4138,8224,4143,8225,12295,4138,8224,4143
,8225,12296,12297,12298,12300,12316,-1};

int yypact[] {0,1,2,9,10,17,18,21,22,27
,42,27,43,17,44,45,60,61,62,63
,72,72,83,84,85,72,72,86,87,88
,89,72,72,72,72,92,101,110,111,45
,122,127,132,133,134,135,-1};

int yyr1[] {0,1,1,1,3,3,3,3,3,3
,3,3,3,4,4,4,2,5,5,6
,6,6,6,8,7,7,9,10,10,-1};

int yyr2[] {0,1,3,4,1,1,1,3,3,3
,3,2,3,1,2,2,2,0,3,0
,2,1,3,2,0,2,1,0,3,-1};

int yygo[] {0,-1,1,4,11,12,27,-1,2,19
,34,20,35,24,36,25,37,30,39,31
,40,32,41,33,42,-1,18,14,28,38
,44,-1,17,-1,3,-1,6,10,26,-1
,15,-1,9,-1,16,-1,29,-1};

int yypgo[] {0,1,3,9,27,33,35,37,41,43
,45,-1};

int nterms 19;
int nnonter 10;
int nstate 45;
char *yysterm[] {
"error",
"NAME",
"CON",
"PSEUDO",
"OPCODE",
"NEG",
0 };

char *yysnter[] {
"$accept",
"program",
"line",
"e",
"expr",
"labels",
"cmd",
"args",
"op",
"arghead",
"argtail" };
