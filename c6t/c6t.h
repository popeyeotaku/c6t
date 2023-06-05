#
/* C6T - C version 6 by Troy - HEADER FILE */

/* --ADJUSTABLE PARAMETERS:
 * These parameters are used to size internal data. If the compiler
 * crashes due to lack of memory, try increasing these. If they're
 * too big for your computer, lower them.
 */
#define NAMELEN 8	/* Significant characters in a NAME
			 * ("idenfitier" to y'all scholars)
			 */
#define SYMTAB 200	/* Number of entries in the symbol table */
#define NLAND 128	/* Number of expression tree nodes */
#define SIZELAND 150	/* Table that stores sizes of arrays and
			 * structs.
			 * MUST BE AT MOST 256 ENTRIES - index has
			 * to fit in one byte.
			 */
#define CASELAND 128	/* Maximum number of cases in all structs */
#define STRMAX 256	/* Max size of a string literal */

/* --TYPE SYSTEM:
 * C6T guarentees several things about the target environment.
 * With respect to types, it guarentees 8-bit bytes; 16-bit, little-
 * endian integers, 4 byte floats, 8 byte doubles, and no alignment.
 * If your target platform does not fit these requirements, sorry, it
 * does mine. Either virtualize or run an interpreter.
 *
 * Since types are stored in both symbols and nodes - our two biggest
 * data types - we need them to be as small as possible. This is
 * complicated by the fact that types are recursive.
 *
 * The type string itself is stored in a single int.
 * The low 3 bits are the base type. A recursive chain of modifiers then
 * branches out to the left: the topmost modifier is in the two bits
 * next to the base, with the lower modifier next to it. While that
 * may seem backwards, in this manner we can always test the topmost
 * modifier easily since we know where it is, and that's always the
 * one we care about.
 * The struct base type and the array modifier type have an
 * associated size (unlike modern C, C6T does not attach members to a
 * given struct tag - all members exist in one tag scope).
 * These sizes are stored in the sizeland table,
 * which is less than 256 entries long - so we can
 * use a one byte index into them. (Though since C6T chars are always 
 * signed, we have to mask out the low 8 bits just in case).
 * We assume array sizes are linearly allocated, so by incrementing
 * or decrementing an array index we can get to the previous or next
 * array size. Therefore, we only need on array index for all the
 * array modifiers. (If we get an invalid index, we will never check
 * its value, so it's fine).
 * Therefore, we can store a complete type in only 4 bytes!
 */
struct type {
	int tystr;
	char tyarray, tystruct;
};

/* Now to define the values and masks for a type string.
 */
#define TYINT 01
#define TYCHAR 03
#define TYFLOAT 04
#define TYDOUBLE 06
#define TYSTRUCT 00
/* The bits are layed out so that tystr&TYINT is also true for TYCHAR,
 * and tystr&TYFLOAT is also true for TYDOUBLE.
 */
#define TYPOINT 010
#define TYARRAY 030
#define TYFUNC 020
/* The bits are layed out so that tystr&TYPOINT is also true for
 * TYARRAY.
 */

/* And some mask values. */
#define TYBASE 07
#define TYMOD 030
#define TYLEN 2	/* length of a type modifier in bits */
#define TYTOP 0140000	/* the top 2 bits, for masking out the sign */

/* Next, the size table itself! */
int sizeland[SIZELAND];
int sizei;	/* The current index into sizeland, since we allocate
		 * linearly.
		 */
int sizebak;	/* For backing up sizei, so we can recover some size
		 * when exiting local scope.
		 */

/* --SYMBOL TABLE:
 * C6T features a wildly simpler scope system than modern C.
 * There is only one level of locals for functions; compound statements
 * do not get their own. Instead of having these
 * mask out externs, it is in fact illegal to redeclare an extern with
 * the same name as a local. When exiting a function, all locals get
 * removed from the symbol table.
 * Similarly, struct and member NAMEs (called "tags") get their own
 * scope. Tags specified within a function (either
 * the parameters or the locals proper) are flagged as local and
 * also get cleared out on function exit.
 * In fact, however, tags are prepended with an illegal NAME character
 * ('.') and stored in the normal symbol table. That way, only one
 * simple table can be used for the entire scope space.
 *
 * (Note that parameters are also considered locals).
 */
struct symbol {
	char sname[NAMELEN];
		/* sname[0] being null indicates this entry is
		 * unallocated.
		 * NAMEs are null padded, but not necessarily null
		 * terminated (gotta save that one byte! The symbol
		 * table is one of our biggest data structures!)
		 */
	char sclass;
		/* This holds the storage class of the symbol.
		 * A value of 0 indicates this symbol entry has a name
		 * attached, but is otherwise empty and invalid.
		 */
	char sflags;
		/* These flags are defined below.
		 */
	struct type stype;
	int soffset;
		/* Use depends upon the storage class:
		 * EXTERNs do not employ it,
		 * MEMBERs store the offset from the start of the
		 * struct,
		 * STRUCTs store the size of the struct in bytes,
		 * STATICs store the static label number,
		 * AUTOs store the offset from the frame pointer,
		 * REGISTERS store the register number.
		 */
} symtab[SYMTAB];
/* Only NAMELEN+8 bytes per symbol! Not too shabby.
 */


/* Now for some flags. */
#define SLOCAL 01	/* A lcal symbol, is removed on exit of
			 * function.
			 */
#define SUNDEF 02	/* An undefined local. Complain if never
			 * defined on function exit.
			 */

/* --NODES:
 * Expression trees employ a binary node system. They are allocated
 * and freed from a global array.
 * A node with a 0 label is considered unallocated.
 */

/* This first struct MUST be the largest one.
 */
struct node {
	char nlab;
	struct type ntype;
	struct node *nleft, *nright;
} nland[NLAND];
/* We don't have unions, but since members are global we can fake them
 * with additional, unnamed structs.
 */
struct {
	char nlab;
	struct type ntype;
	int nval;
};

/* --CASE INFO:
 */
struct caseinfo {
	int clab;
	int cval;
} caseland[CASELAND], *begcase, *endcase;

/* --TOKENIZER VARIABLES:
 */
/* We use two character readahead. */
char readahead[2];	/* Do I lie? */
int line;	/* The current line number. */
char countlines;	/* Flag for if we should keep track of line
			 * numbers. This is flipped by the input char
			 * '@'. The intention is this shall be placed by
			 * the preprocessor, so that included files will
			 * not keep track of line numbers within them.
			 */
int peektkn;	/* token() returns the next input token's label.
		 * If you don't want to use that token immediately,
		 * place its label into peektkn. Then, the token will
		 * be returned again on the next call to token().
		 */
/* The value of the token will be stored in one of these variables.
 */
char tname[NAMELEN];	/* Value of a NAME token. */
int tval;	/* An integral or pointer value. */
char tstr[STRMAX];	/* The value of a STRING token */
int tlen;	/* The length of bytes in the tstr value. */

/* --SPECIFIER VARIABLES:
 */
struct type basetype, curtype;	/* Type structs for the typeclass type
				 * and specifier type respectively.
				 */
int curclass;	/* The class given by the typeclass. */
int curreg, curauto;	/* Count of used registers and
			 * auto stack size for locals.
			 */
int argcount;	/* Count of argument NAMEs seen in a function spec.
		 */
int membsize;	/* Offset in bytes from start of struct */
int curst;	/* If we're definining a new STRUCT, it will be placed
		 * here to allow recursive references.
		 */
int strdumped;	/* Incremented each time a string is dumped; used to
		 * handle resuming a data initializer after switching
		 * into string space.
		 */

/* --STATEMENT VARIABLES:
 */
int curbrk, curcont;	/* Static label numbers for break and continue
			 * statements (0 if none present).
			 */
int curdef;		/* Current default statement static label
			 * (0 if no default set)
			 */

/* --OTHER VARIABLES:
 */
int errcount;	/* Number of errors reported */
char localscope;	/* Flag for if we're inside localscope. */
int nextstatic;	/* Next static label number. Use '++nextstatic'. */
int curseg;	/* The current output segment. */

/* --OPERATOR FLAGS
 * These are used to get info on various expression operators.
 * Primarily used by build().
 */
#define OPUNARY 01
#define OPLEAF 02
#define OPISINT 04
#define OPTYLEFT 010
#define OPTYRIGHT 020
#define OPYESFLT 040
#define OPFLTCONV 0100
#define OPPNTCONV 0200
#define OPDEREF 0400
#define OPINCREF 01000
#define OPASSIGN 02000
#define OPNEEDLVAL 04000

/* --MISCELLANEOUS DEFINES
 */
#define ever ;;	/* for(ever) ... */
struct { int integ; };	/* We don't have unions, but can use this
			 * to fake a type.
			 */
#define ARGOFFSET 10	/* offset from frame pointer of first
			 * argument.
			 */
#define MAXREG 3	/* The number of register variables */

/* --ENUMERATIONS:
 * These are used for several purposes, including token
 * label numbers. They range from 1 to MAXENUM.
 */
#define EOF 1	/* End of file */
#define CON 2	/* Integer constant */
#define FCON 3	/* Floating constant */
#define NAME 4
#define STRING 5
/* Keywords; do not change order! */
#define INT 6
#define CHAR 7
#define FLOAT 8
#define DOUBLE 9
#define STRUCT 10
#define AUTO 11
#define EXTERN 12
#define REGISTER 13
#define STATIC 14
#define GOTO 15
#define RETURN 16
#define SIZEOF 17
#define BREAK 18
#define CONTINUE 19
#define IF 20
#define ELSE 21
#define FOR 22
#define DO 23
#define WHILE 24
#define SWITCH 25
#define CASE 26
#define DEFAULT 27
#define ENTRY 28	/* Not used, but reserved */
/* End of keywords */
#define LBRACE 29
#define RBRACE 30
#define SEMICOLON 31
#define COMMA 32
#define ASSIGN 33
#define ASNADD 34
#define ASNSUB 35
#define ASNMULT 36
#define ASNDIV 37
#define ASNMOD 38
#define ASNRSHIFT 39
#define ASNLSHIFT 40
#define ASNAND 41
#define ASNEOR 42
#define ASNOR 43
#define QUEST 44
#define COLON 45
#define LOGOR 46
#define LOGAND 47
#define OR 48
#define EOR 49
#define AND 50
#define EQU 51
#define NEQU 52
#define LESS 53
#define GREAT 54
#define LEQU 55
#define GEQU 56
#define RSHIFT 57
#define LSHIFT 58
#define ADD 59
#define SUB 60
#define MULT 61
#define DIV 62
#define MOD 63
#define DEREF 64
#define ADDR 65
#define NEG 66
#define LOGNOT 67
#define COMPL 68
#define PREINC 69
#define PREDEC 70
#define POSTINC 71
#define POSTDEC 72
#define LPAREN 73
#define RPAREN 74
#define LBRACK 75
#define RBRACK 76
#define DOT 77
#define ARROW 78
#define CALL 79
#define ARG 80
#define MEMBER 81
#define TOFLT 82
#define TOINT 83
#define CODE 84
#define DATA 85
#define BSS 86
#define ULESS 87
#define UGREAT 88
#define ULEQU 89
#define UGEQU 90
#define MAXENUM 91
