#include "poplink.h"

/* dump all link info in text format */

#define BLK64K 128

char *clstab[] {
	"undef", "text", "data", "bss", "abs", "common"
};

int fin[518/2];

dumpseg()
{
	register char *offset, i;
	register c;

	offset = 0;
	for (;;) {
		i = getw(fin);
		printf("relative %o, ", i);
		if (i == -1)
			break;
		offset =+ i;
		printf("offset %o, ", offset);
		c = getc(fin);
		if (c&AEXPORT) {
			printf("exported ");
			c =& ~AEXPORT;
		}

		if (c < AUNDEF || c > ACOMMON) {
			printf("unknown class %o\n", c);
			break;
		} else printf("class %s, ", clstab[c]);

		switch (getc(fin)) {
		case AHI:
			printf("hilo=hi(%o)", getc(fin));
			break;
		case ALO:
			printf("hilo=lo");
			break;
		default:
			printf("hilo=word");
			break;
		}

		if (c == AUNDEF) {
			printf(", name=");
			while (c = getc(fin))
				putchar(c);
		}
		putchar('\n');
	}
	printf("last offset:%o\n", offset);
}

dumpfile(name)
{
	extern fout;
	static struct aheader header;

	if (fopen(name, fin) < 0) {
		flush();
		fout = 2;
		printf("unable to open %s\n", name);
		flush();
		fout = 1;
		return;
	}

	if (read(fin[0], &header, sizeof(header)) != sizeof(header)) {
notobj:
		flush();
		fout = 2;
		printf("%s not an object file\n", name);
		flush();
		fout = 1;
		close(fin[0]);
		return;
	}
	if (header.amagic != AMAGIC) goto notobj;

	useek(fin[0], header.atext+header.adata);

	printf("%s text:\n", name);
	dumpseg();
	printf("%s data:\n", name);
	dumpseg();
	close(fin[0]);
}

useek(file, offset)
{
	if (offset < 0) {
		offset =& 077777;
		seek(file, BLK64K, 3);
	}
	seek(file, offset, 1);
}

main(argc, argv) char **argv;
{
	while (--argc)
		dumpfile(*++argv);
}
