#define AMAGIC 0417

struct aheader {
	int amagic;
	int aflags;
	char *atext, *adata, *abss;
	char *artext, *ardata;
	char *asymsize, *astart;
};

#define AEXEC 01

#define ANAME 9

struct asym {
	char aname[ANAME];
	char aclass;
	int aval;
};

#define AUNDEF 0
#define ATEXT 1
#define ADATA 2
#define ABSS 3
#define AABS 4
#define ACOMMON 5
#define AEXPORT 0200

#define AHI 1
#define ALO 2
#define AWORD 0
