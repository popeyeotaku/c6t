#include "../poplink/poplink.h"
#include "asm.h"

/* 8080 Opcode support for C6T Assembler */

char *opnames[] {
	"in",
	"out",
	"ei",
	"di",
	"hlt",
	"rst",
	"cmc",
	"stc",
	"nop",
	"inr",
	"dcr",
	"cma",
	"daa",
	"push",
	"pop",
	"dad",
	"inx",
	"dcx",
	"xchg",
	"xthl",
	"sphl",
	"rlc",
	"rrc",
	"ral",
	"rar",
	"mov",
	"stax",
	"ldax",
	"add",
	"adc",
	"sub",
	"sbb",
	"ana",
	"xra",
	"ora",
	"cmp",
	"sta",
	"lda",
	"shld",
	"lhld",
	"lxi",
	"mvi",
	"adi",
	"aci",
	"sui",
	"sbi",
	"ani",
	"xri",
	"ori",
	"cpi",
	"pchl",
	"jmp",
	"jc",
	"jnc",
	"jz",
	"jnz",
	"jm",
	"jp",
	"jpe",
	"jpo",
	"call",
	"cc",
	"cnc",
	"cz",
	"cnz",
	"cm",
	"cp",
	"cpe",
	"cpo",
	"ret",
	"rc",
	"rnc",
	"rz",
	"rnz",
	"rm",
	"rp",
	"rpe",
	"rpo",
	0,
};

/* This table contains info on each opcode, in the order of the
 * opnames table.
 * The opcode byte to be output is in the low 8 bits, and the mode for
 * the format of the output is in the hi 8 bits.
 */
#define OP1 (1<<8)	/* opcode followed by 1 byte */
#define OPNO (2<<8)	/* opcode by itself */
#define OPMID (3<<8)	/* opcode with arg or'd into middle bits */
#define OPBOTH (4<<8)	/* opcode with two args or'd into middle
			 * low bits
			 */
#define OPLO (5<<8)	/* opcode with arg or'd into low bits */
#define OP2 (6<<8)	/* opcode followed by twobyte arg */
#define OPMID1 (7<<8)	/* opcode with arg1 or'd into middle bits,
			 * and arg2 followed in one byte.
			 */
#define OPMID2 (8<<8)	/* opcode with arg1 or'd into middle bits,
			 * and arg2 followed in two bytes
			 */
int opinfo[] {
	0333|OP1,	/* in */
	0323|OP1,	/* out */
	0373|OPNO,	/* ei */
	0363|OPNO,	/* di */
	0166|OPNO,	/* hlt */
	0307|OPMID,	/* rst */
	0077|OPNO,	/* cmc */
	0067|OPNO,	/* stc */
	0000|OPNO,	/* nop */
	0004|OPMID,	/* inr */
	0005|OPMID,	/* dcr */
	0057|OPNO,	/* cma */
	0047|OPNO,	/* daa */
	0305|OPMID,	/* push */
	0301|OPMID,	/* pop */
	0011|OPMID,	/* dad */
	0003|OPMID,	/* inx */
	0013|OPMID,	/* dcx */
	0353|OPNO,	/* xchg */
	0343|OPNO,	/* xthl */
	0371|OPNO,	/* sphl */
	0007|OPNO,	/* rlc */
	0017|OPNO,	/* rrc */
	0027|OPNO,	/* ral */
	0037|OPNO,	/* rar */
	0100|OPBOTH,	/* mov */
	0002|OPMID,	/* stax */
	0012|OPMID,	/* ldax */
	0200|OPLO,	/* add */
	0210|OPLO,	/* adc */
	0220|OPLO,	/* sub */
	0230|OPLO,	/* sbb */
	0240|OPLO,	/* ana */
	0250|OPLO,	/* xra */
	0260|OPLO,	/* ora */
	0270|OPLO,	/* cmp */
	0062|OP2,	/* sta */
	0072|OP2,	/* lda */
	0042|OP2,	/* shld */
	0052|OP2,	/* lhld */
	0001|OPMID2,	/* lxi */
	0006|OPMID1,	/* mvi */
	0306|OP1,	/* adi */
	0316|OP1,	/* aci */
	0326|OP1,	/* sui */
	0336|OP1,	/* sbi */
	0346|OP1,	/* ani */
	0356|OP1,	/* xri */
	0366|OP1,	/* ori */
	0376|OP1,	/* cpi */
	0351|OPNO,	/* pchl */
	0303|OP2,	/* jmp */
	0332|OP2,	/* jc */
	0322|OP2,	/* jnc */
	0312|OP2,	/* jz */
	0302|OP2,	/* jnz */
	0372|OP2,	/* jm */
	0362|OP2,	/* jp */
	0352|OP2,	/* jpe */
	0342|OP2,	/* jpo */
	0315|OP2,	/* call */
	0334|OP2,	/* cc */
	0324|OP2,	/* cnc */
	0314|OP2,	/* cz */
	0304|OP2,	/* cnz */
	0374|OP2,	/* cm */
	0364|OP2,	/* cp */
	0354|OP2,	/* cpe */
	0344|OP2,	/* cpo */
	0311|OPNO,	/* ret */
	0330|OPNO,	/* rc */
	0320|OPNO,	/* rnc */
	0310|OPNO,	/* rz */
	0300|OPNO,	/* rnz */
	0370|OPNO,	/* rm */
	0360|OPNO,	/* rp */
	0350|OPNO,	/* rpe */
	0340|OPNO,	/* rpo */
};

struct table {
	char *tstr;
	int tval;
} tabinit[] {
	"b", 00, "B", 00,
	"c", 01, "C", 01,
	"d", 02, "D", 02,
	"e", 03, "E", 03,
	"h", 04, "H", 04,
	"l", 05, "L", 05,
	"m", 06, "M", 06,
	"a", 07, "A", 07,
	"sp", 06, "SP", 06,
	"psw", 06, "PSW", 06,
	0,
};

opinit()
{
	register struct table *pnt;
	register *sym;

	for (pnt = tabinit; pnt->tstr; pnt++) {
		sym = lookup(pnt->tstr);
		sym->aclass = PABS;
		sym->aval = pnt->tval;
	}
}

/* Place an opcode into the output file */
opcode(op)
{
	register code;

	code = opinfo[op]&0377;

	switch (opinfo[op]&(0377<<8)) {
	default:
		crash("BAD OPCODE MODE %o", opinfo[op]&(0377<<8));
	case OPNO:
		putbyte(code);
		break;
	case OP1:
		if (needargs(1)) return;
		putbyte(code);
		expbyte(argland[0]);
		break;
	case OP2:
		if (needargs(1)) return;
		putbyte(code);
		expword(argland[0]);
		break;
	case OPMID:
		if (needargs(1)) return;
		putbyte(code|(expabs(argland[0])<<3));
		break;
	case OPLO:
		if (needargs(1)) return;
		putbyte(code|expabs(argland[0]));
		break;
	case OPBOTH:
		if (needargs(2)) return;
		putbyte(code|(expabs(argland[0])<<3)|expabs(argland[1]));
		break;
	case OPMID1:
		if (needargs(2)) return;
		putbyte(code|(expabs(argland[0])<<3));
		expbyte(argland[1]);
		break;
	case OPMID2:
		if (needargs(2)) return;
		putbyte(code|(expabs(argland[0])<<3));
		expword(argland[1]);
		break;
	}
}

grabop(name, dest) int *dest;
{
	register char **tabpnt, *tabname;

	for (tabpnt = opnames; tabname = *tabpnt; tabpnt++)
		if (casecmp(name, tabname)) {
			*dest = tabpnt - opnames;
			return (1);
		}

	return (0);
}
