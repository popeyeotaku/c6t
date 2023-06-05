#include "../poplink/poplink.h"
#include "asm.h"

/* Pseudo Code support */

struct table {
	char *tname;
	int tval;
} pstab[] {
	".text", PTEXT,
	".code", PTEXT,
	".data", PDATA,
	".string", PSTRING,
	".bss", PBSS,
	".common", PCOMMON,
	".export", PEXPORT,
	".db", PDB,
	".byte", PDB,
	".dw", PDW,
	".word", PDW,
	".ds", PDS,
	0,
};

grabpseudo(name, dest)
int *dest;
{
	register struct table *tabpnt;
	register char *tabname;

	for (tabpnt = pstab; tabname = tabpnt->tname; tabpnt++) {
		if (casecmp(name, tabname)) {
			*dest = tabpnt->tval;
			return (1);
		}
	}

	return (0);
}

/* Process a pseudo-op */
pseudo(ps)
{
	register *pnt, *sym, i;

	switch (ps) {
	case PTEXT:
	case PDATA:
	case PSTRING:
	case PBSS:
		needargs(0);
		goseg(ps);
		break;
	case PCOMMON:
		needargs(2);
		sym = symplain(argland[0]);
		if (!sym) return;
		if (redef(sym)) return;
		sym->aclass = AEXPORT|PCOMMON;
		sym->aval = umax(sym->aval, expabs(argland[1]));
		break;
	case PEXPORT:
		for (pnt = argland; pnt < argpnt; pnt++) {
			if (!(sym = symplain(*pnt))) return;
			sym->aclass =| AEXPORT;
		}
		break;
	case PDB:
	case PDW:
		for (pnt = argland; pnt < argpnt; pnt++) {
			if (ps == PDB)
				expbyte(*pnt);
			else expword(*pnt);
		}
		break;
	case PDS:
		needargs(1);
		i = expabs(argland[0]);
		while (i--) putbyte(0);
		break;
	default:
		crash("BAD PSEUDO %o", ps);
	}
}
