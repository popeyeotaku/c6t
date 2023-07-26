#include "poplink.h"

/* convert a a.out.80 to a CPM COM file. */

struct aheader header;

int ifile[518/2], ofile[518/2];

main(argc, argv) char **argv;
{
	static char *name;
	register char *pc, *endpc;
	register c;

	name = argc > 1 ? argv[1] : "a.out.80";

	if (fopen(name, ifile) < 0)
		exit(1);
	if (fcreat("a.com", ofile) < 0)
		exit(1);

	if (read(ifile[0], &header, sizeof(header)) != sizeof(header))
		exit(1);

	if (header.amagic != AMAGIC) exit(1);
	if (!(header.aflags&AEXEC)) {
		printf("no exec\n");
		exit(1);
	}
	if (header.astart != 0400) {
		printf("doesn't start at 0400\n");
		exit(1);
	}

	endpc = header.atext+header.adata;

	for (pc = 0; pc != endpc; pc++) {
		c = getc(ifile);
		if (c < 0) {
			printf("early eof\n");
			abort();
		}
		putc(c, ofile);
	}

	endpc = header.abss;
	for (pc = 0; pc != endpc; pc++)
		putc(0, ofile);

	fflush(ofile);
	exit(0);
}
