#
# define NAME 257
# define NODE 258
# define CMD 259
# define CON 260
#define yyclearin yychar = -1
#define yyerrok yyerrflag = 0
extern int yychar, yyerrflag;

int yyval 0;
int *yypv;
int yylval 0;
yyactr(__np__){

switch(__np__){

case 4: {
		cleanup();
	} break;
case 7: {
		deflab(yypv[1]);
	} break;
case 11: {
		docmd(yypv[1], yypv[2]);
	} break;
case 12: {
		push(build(yypv[1], yypv[2]));
	} break;
case 13: {
		yyval = 0;
	} break;
case 18: {
		yyval = arglist(yypv[1], yypv[3]);
	} break;
case 19: {
		yyval = name(yypv[1]);
	} break;
case 20: {
		yyval = con(yypv[1]);
	} break;
case 21: {
		if (yypv[2] == '-') yypv[3] = -yypv[3];
		yyval = offset(yypv[1], yypv[3]);
	} break;
case 22: {
		if (yypv[2] == '-') crash("CANNOT SUBTRACT A NAME");
		yyval = offset(yypv[3], yypv[1]);
	} break;
}
}
int yyerrval 256;


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

int yyact[] {0,12293,4096,16384,4352,8197,4106,8196,0,12289
,4353,8202,4354,8204,4355,8203,12298,12293,4106,8206
,0,12292,12294,12296,12297,4154,8207,0,4353,8211
,4356,8212,12301,12290,12295,12299,4140,8216,12303,12305
,4139,8218,4141,8219,12307,4139,8218,4141,8219,12308
,12300,12291,12302,4353,8211,4356,8212,12304,4356,8222
,0,12311,12312,4353,8223,0,12306,12309,12310,-1};

int yypact[] {0,1,2,9,10,17,18,21,22,23
,24,25,28,28,33,17,34,35,36,39
,40,45,50,51,52,53,58,61,62,63
,66,67,68,-1};

int yyr1[] {0,1,1,1,2,3,3,5,4,4
,4,6,7,8,8,10,10,9,9,11
,11,11,11,12,12,-1};

int yyr2[] {0,1,3,4,2,0,2,2,1,1
,0,2,2,0,2,0,1,1,3,1
,1,3,3,1,1,-1};

int yygo[] {0,-1,1,4,13,14,22,-1,2,-1
,3,-1,6,-1,7,-1,8,-1,9,12
,21,-1,16,-1,17,-1,23,24,29,-1
,18,20,28,-1,25,-1};

int yypgo[] {0,1,3,9,11,13,15,17,19,23
,25,27,31,-1};

int nterms 11;
int nnonter 12;
int nstate 32;
char *yysterm[] {
"error",
"NAME",
"NODE",
"CMD",
"CON",
0 };

char *yysnter[] {
"$accept",
"program",
"line",
"labels",
"statement",
"label",
"cmd",
"node",
"args",
"arglist",
"trailcomma",
"arg",
"op" };
