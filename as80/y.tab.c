#
# define NAME 257
# define CON 258
# define PSEUDO 259
# define COMMON 260
# define EXPORT 261
# define OPCODE 262
# define NEG 263
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
		pcommon(yypv[2], yypv[4]);
	} break;
case 24: {
		setequ(yypv[1], yypv[3]);
	} break;
case 25: {
		pexport(yypv[1]);
	} break;
case 26: {
		pexport(yypv[3]);
	} break;
case 27: {
		yyval = opcode(yypv[1]);
	} break;
case 30: {
		addarg(yypv[1]);
	} break;
case 32: {
		addarg(yypv[3]);
	} break;
}
}
int yyerrval 256;


#include "../poplink/poplink.h"
#include "asm.h"

char peekc;

int pstkn[] { PSEUDO, COMMON, EXPORT } ;

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

		if (nbuf[0] == '.' && (i = grabpseudo(nbuf, &yylval)))
			return (pstkn[i-1]);
		if (grabop(nbuf, &yylval))
			return (OPCODE);
		yylval = lookup(nbuf);
		return (NAME);
	}

	return (yylval = c);
}

int yyact[] {0,12305,4096,16384,4352,8197,4106,8196,0,12289
,4353,8199,4355,8200,4356,8202,4357,8201,4358,8204
,12307,12305,4106,8206,0,12304,4154,8207,4157,8208
,0,4353,8215,4354,8216,4141,8218,4138,8217,4136
,8219,4158,8213,4156,8214,12316,4353,8221,0,4353
,8222,0,12311,12290,12306,4353,8215,4354,8216,4141
,8218,4138,8217,4136,8219,4158,8213,4156,8214,0
,12308,12319,12318,4139,8227,4141,8228,4138,8229,4143
,8230,12301,4353,8215,4354,8216,4141,8218,4138,8217
,4136,8219,0,12292,12293,12294,4140,8235,12309,12313
,4140,8236,0,12315,12291,12312,4140,8237,12317,4139
,8227,4141,8228,4138,8229,4143,8230,12302,4139,8227
,4141,8228,4138,8229,4143,8230,12303,12299,4139,8227
,4141,8228,4138,8229,4143,8230,4137,8242,0,4353
,8243,0,4138,8229,4143,8230,12295,4138,8229,4143
,8230,12296,12297,12298,12300,12314,12310,12320,-1};

int yypact[] {0,1,2,9,10,21,22,25,26,31
,46,49,52,31,53,21,54,55,70,71
,72,73,82,82,93,94,95,82,82,96
,99,100,103,104,105,106,82,82,82,82
,109,118,127,128,139,55,55,142,147,152
,153,154,155,156,157,-1};

int yyr1[] {0,1,1,1,3,3,3,3,3,3
,3,3,3,4,4,4,2,5,5,6
,6,6,6,6,6,8,8,9,7,7
,10,11,11,-1};

int yyr2[] {0,1,3,4,1,1,1,3,3,3
,3,2,3,1,2,2,2,0,3,0
,2,2,4,1,3,1,3,2,0,2
,1,0,3,-1};

int yygo[] {0,-1,1,4,13,14,32,-1,2,21
,39,22,40,26,41,27,42,35,46,36
,47,37,48,38,49,-1,20,16,33,44
,52,45,53,-1,19,-1,3,-1,6,12
,31,-1,17,-1,28,-1,11,-1,18,-1
,34,-1};

int yypgo[] {0,1,3,9,27,35,37,39,43,45
,47,49,-1};

int nterms 21;
int nnonter 11;
int nstate 54;
char *yysterm[] {
"error",
"NAME",
"CON",
"PSEUDO",
"COMMON",
"EXPORT",
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
"explist",
"op",
"arghead",
"argtail" };
