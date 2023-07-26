/* Shared Assembly Support for C6T Assembler */

#define SYMTAB 512	/* number of symbol table entries */
#define EXPLAND 512	/* Size of expression buffer */
#define ARGLAND 256	/* Size of arg list */

#define NAMELEN 9

#define BLK64K 128
#define BLK32K 64

struct asym symtab[SYMTAB];

struct aheader header;

int expland[EXPLAND], *exppnt;
int argland[ARGLAND], *argpnt;

/* Expression Buffer Operations */
#define EABS 0	/* EABS con, just the value */
#define EOFFSET 1	/* EOFFSET sympnt con, the symbol + the con */
#define EHILO 2	/* EHILO hilo epnt */
#define ESEG 3	/* ESEG segnum offset */
#define EREL 4	/* EREL relative within a seg */

int errcount;

int curseg;
char **curpc;	/* points to actual program counter */
char **curlink;	/* position in link data for segment */
char **prevlink;	/* points to PC of the previous link for offsets */

char *backlink;	/* prevlink used when concating the temp file */
char *rsize;	/* size of relocation info for current relocation */

char *strpc, *strlink;	/* pc/link data for string segment */

char *prevtab[3];	/* table of prevlink values */

int undefs;	/* count of undefines */

struct putget {
	int fnum;
	int fcount;
	char *fpnt;
	char fbuf[512];
} tempbuf, linkbuf, outbuf, outlink;

/* PSEUDO-OP Enumerations */
#define PTEXT 1
#define PDATA 2
#define PSTRING 3
#define PBSS 4
#define PCOMMON 5
#define PEXPORT 6
#define PDB 7
#define PDW 8
#define PDS 9
#define PABS 10	/* not a real pseudo, used for symbol classes */
#define PSEG 11	/* same here */
#define PREL 12	/* same here */
