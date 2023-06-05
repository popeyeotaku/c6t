#include "poplink.h"

/* print size of object files */

struct aheader header;

int total[3];

main(argc, argv) char **argv;
{
	if (argc <= 1)
		report("a.out.80");
	else if (argc == 2)
		report(argv[1]);
	else {
		while (--argc) {
			report(*++argv);
			total[0] =+ header.atext;
			total[1] =+ header.adata;
			total[2] =+ header.abss;
		}
		printf("total:\t%l+%l+%l=%l\n",
			total[0],
			total[1],
			total[2],
			total[0]+total[1]+total[2]
		);
	}
}

report(name)
{
	register file, count;

	if ((file = open(name, 0)) < 0) {
bad:
		printf("cannot open %s\n", name);
		return;
	}
	count = read(file, &header, sizeof(header));
	close(file);

	if (count != sizeof(header)) goto bad;

	if (header.amagic != AMAGIC) {
		printf("%s not an a.out", name);
		return;
	}

	printf("%s:\t%l+%l+%l=%l\n",
		name,
		header.atext,
		header.adata,
		header.abss,
		header.atext+header.adata+header.abss
	);
}
