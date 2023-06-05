#include "poplink.h"

/* list all names in a poplink a.out */

char *mode "%o";

#define BLK32K 64

struct asym symbol;
struct aheader header;

names(file)
{
	register char *class;

	if (read(file, &header, sizeof(header)) != sizeof(header)) {
bad:
		printf("\nbad file\n");
		exit(1);
	}

	if (header.amagic != AMAGIC) goto bad;

	useek(file, header.atext);
	useek(file, header.adata);
	useek(file, header.artext);
	useek(file, header.ardata);

	while (read(file, &symbol, sizeof(symbol)) == sizeof(symbol)) {
		switch (class = symbol.aclass&0377&~AEXPORT) {
		case ATEXT:
			class = "text";
			break;
		case ADATA:
			class = "data";
			break;
		case ABSS:
			class = "bss";
			break;
		case ACOMMON:
			class = "comm";
			break;
		case AABS:
			class = "abs";
			break;
		case AUNDEF:
			class = "undef";
			break;
		default:
			printf("bad class %o\n", class);
			goto bad;
		}

		printf(mode, symbol.aval);
		printf("\t%c%s\t%s\n",
			symbol.aclass&AEXPORT ? '^' : 0,
			class,
			symbol.aname
		);
	}

	close(file);
}

main(argc, argv)
char **argv;
{
	register file;
	register char *pnt;

	if (argc > 1 && argv[1][0] == '-') {
		--argc; ++argv;
		pnt = &argv[0][1];
		while (*pnt) switch (*pnt++) {
		case 'h':
		case 'x':
			mode = "%x";
			break;
		case 'o':
			mode = "%o";
			break;
		case 'd':
		case 'l':
			mode = "%l";
			break;
		}
	}

	if (argc > 1) while (--argc) {
		printf("%s:\n", *++argv);
		file = open(*argv, 0);
		if (file < 0) continue;
		names(file);
	}
	else {
		file = open("a.out.80", 0);
		if (file < 0) exit(1);
		names(file);
	}
}

useek(file, offset) char *offset;
{
	if (offset&0100000) {
		seek(file, BLK32K, 4);
		offset =& 077777;
	}
	seek(file, offset, 1);
}
