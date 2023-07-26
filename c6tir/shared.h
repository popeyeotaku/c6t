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
#define PRE 36
#define POST 37
#define CPRE 38
#define CPOST 39
#define CALL 40
#define ARG 41
#define TOFLT 42
#define TOINT 43
#define ULESS 44
#define UGREAT 45
#define ULEQU 46
#define UGEQU 47
#define AUTO 48
#define ASNADD 49
#define ASNSUB 50
#define ASNMULT 51
#define ASNDIV 52
#define ASNMOD 53
#define ASNRSHIFT 54
#define ASNLSHIFT 55
#define ASNAND 56
#define ASNEOR 57
#define ASNOR 58
#define CASNADD 59
#define CASNSUB 60
#define CASNMULT 61
#define CASNDIV 62
#define CASNMOD 63
#define CASNRSHIFT 64
#define CASNLSHIFT 65
#define CASNAND 66
#define CASNEOR 67
#define CASNOR 68
#define COMMA 69
