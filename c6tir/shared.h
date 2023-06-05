/* C6TIR Header File */

/* SIZE PARAMETERS */
#define CNLAND 64
#define CNSTK 16
#define ARGLAND (256*2*2)
#define NAMELAND (256*(8+1))
#define NAMELEN 8

/* CORE NODE STRUCT */
struct cnode {
	int nlab;
	struct cnode *nleft, *nright;
	int ncon;
	char *nname;
} cnland[CNLAND], *cnstk[CNSTK], **cnpnt;

/* ARG AREAS */
int argland[ARGLAND], *argpnt;
char nameland[NAMELAND], *namepnt;

/* TYPE ENUMERATIONS */
#define WTYPE 0
#define CTYPE 1
#define FTYPE 2
#define DTYPE 3

/* ARG ENUMERATIONS */
#define ACON 1
#define ANAME 2
#define AOFFSET 3
#define ALIST 4

/* COMMAND ENUMERATIONS */
#define BYTE 1
#define WORD 2
#define FLOAT 3
#define DOUBLE 4
#define STORAGE 5
#define AUTOS 6
#define USEDREGS 7
#define RET 8
#define FRET 9
#define RETNULL 10
#define FUNC 11
#define EXPORT 12
#define ENDFUNC 13
#define JMP 14
#define BRZ 15
#define FBRZ 16
#define EVAL 17
#define SWITCH 18
#define END 19
#define CODE 20
#define DATA 21
#define BSS 22
#define STRING 23
#define STKJMP 24
#define COMMON 25
#define SWEASY 26

/* NODE ENUMERATIONS */
#define UNALLOC (-1)
#define NULL 0
#define CON 1
#define FCON 2
#define LOAD 3
#define CLOAD 4
#define FLOAD 5
#define DLOAD 6
#define ASSIGN 7
#define CASSIGN 8
#define FASSIGN 9
#define DASSIGN 10
#define QUEST 11
#define COLON 12
#define LOGOR 13
#define LOGAND 14
#define OR 15
#define EOR 16
#define AND 17
#define EQU 18
#define NEQU 19
#define LESS 20
#define GREAT 21
#define LEQU 22
#define GEQU 23
#define RSHIFT 24
#define LSHIFT 25
#define ADD 26
#define SUB 27
#define MULT 28
#define DIV 29
#define MOD 30
#define NEG 31
#define LOGNOT 32
#define LOG 33
#define COMPL 34
#define REG 35
#define PREINC 36
#define PREDEC 37
#define POSTINC 38
#define POSTDEC 39
#define CPREINC 40
#define CPREDEC 41
#define CPOSTINC 42
#define CPOSTDEC 43
#define CALL 44
#define ARG 45
#define TOFLT 46
#define TOINT 47
#define ULESS 48
#define UGREAT 49
#define ULEQU 50
#define UGEQU 51
#define AUTO 52
#define ASNADD 53
#define ASNSUB 54
#define ASNMULT 55
#define ASNDIV 56
#define ASNMOD 57
#define ASNRSHIFT 58
#define ASNLSHIFT 59
#define ASNAND 60
#define ASNEOR 61
#define ASNOR 62
#define CASNADD 63
#define CASNSUB 64
#define CASNMULT 65
#define CASNDIV 66
#define CASNMOD 67
#define CASNRSHIFT 68
#define CASNLSHIFT 69
#define CASNAND 70
#define CASNEOR 71
#define CASNOR 72
#define COMMA 73
