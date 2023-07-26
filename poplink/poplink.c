#include "poplink.h"

/* PopLink - C6T Linker */

#define SYMTAB 512	/* size of symbol table */

#define NOBJS 32	/* number of object files supported */

int nobj;	/* actual number of object files */

char otname[16], ltname[16];


struct aheader oheads[NOBJS];

struct file {
	int fdesc;
	int fcount;
	char *fpnt;
	char fdata[512];
} objbuf, linkbuf, outbuf, outlink;

char *linkpos, *prevlink, *linkpc;
int undefs;

struct asym symtab[SYMTAB];

int xflag;

struct aheader header;

char *onames[NOBJS];

char *offsets[3];

#define BLK32K 64

main(argc, argv) char **argv;
{
	register char *pnt;

	while (--argc) {
		++argv;
		if (argv[0][0] == '-') {
			pnt = &argv[0][1];
			while (*pnt) switch (*pnt++) {
			case 'x':
				xflag++;
				continue;
			case 's':
				if (argc < 1) continue;
				--argc; ++argv;
				header.astart = atoi(*argv);
				break;
			}
			continue;
		}
		if (nobj >= NOBJS) {
			printf("too many object files\n");
			exit(1);
		}
		onames[nobj++] = *argv;
	}

	mktemp();

	doheaders();

	dosyms();

	dosegs(ATEXT);
	dosegs(ADATA);

	concat();

	report();

	exit(0);
}

doheaders()
{
	register i, file;

	header.atext = header.adata = header.abss = 0;
	for (i = 0; i < nobj; i++) {
		file = open(onames[i], 0);
		if (file < 0) fcrash();

		if (read(file, &oheads[i], sizeof(header)) != sizeof(header))
			fcrash();
		close(file);
		if (oheads[i].amagic != AMAGIC)
			fcrash();

		header.atext =+ oheads[i].atext;
		header.adata =+ oheads[i].adata;
		header.abss =+ oheads[i].abss;
	}
}

fcrash()
{
	printf("file err\n");
	unlink(otname);
	unlink(ltname);
	abort();
}

dosyms()
{
	static struct asym cursym;
	register i, file, *newsym;
	static class;

	offsets[0] = header.astart;
	offsets[1] = header.astart + header.atext;
	offsets[2] = header.astart + header.atext + header.adata;

	for (i = 0; i < nobj; i++) {
		file = open(onames[i], 0);
		if (file < 0) fcrash();

		seek(file, sizeof(header), 0);
		useek(file, oheads[i].atext);
		useek(file, oheads[i].adata);
		useek(file, oheads[i].artext);
		useek(file, oheads[i].ardata);

		while (read(file, &cursym, sizeof(cursym))
				== sizeof(cursym)) {
			if (cursym.aclass&AEXPORT) {
				newsym = lookup(cursym.aname);

				if (class=newsym->aclass&0377&~AEXPORT) {
					if (class==ACOMMON
					&&(cursym.aclass&0377&~AEXPORT)
					==ACOMMON) {
						newsym->aclass=|
							cursym.aclass&AEXPORT;
						newsym->aval=umax(
							newsym->aval,
							cursym.aval);
						continue;
					}
					if (class!=ACOMMON) continue;
				}

				newsym->aclass = cursym.aclass;
				newsym->aval = cursym.aval;
				switch (cursym.aclass&0377&~AEXPORT) {
				case ATEXT:
					newsym->aval =+ offsets[0]
						-oheads[i].astart;
					break;
				case ADATA:
					newsym->aval =+ offsets[1]
						-oheads[i].astart
						-oheads[i].atext;
					break;
				case ABSS:
					newsym->aval =+ offsets[2]
						-oheads[i].astart
						-oheads[i].atext
						-oheads[i].adata;
					break;
				}
			}
		}
		close(file);
		offsets[0] =+ oheads[i].atext;
		offsets[1] =+ oheads[i].adata;
		offsets[2] =+ oheads[i].abss;
	}

	if (xflag) return;
	docommons();

	addsym("_etext", header.astart+header.atext);
	addsym("_edata", header.astart+header.atext+header.adata);
	addsym("_end", header.astart+header.atext+header.adata+header.abss);
}

umax(left, right) char *left, *right;
{
	return (right > left ? right : left);
}

addsym(name, value)
{
	register *sym;

	sym = lookup(name);
	sym->aclass = AEXPORT|AABS;
	sym->aval = value;
}

docommons()
{
	register struct asym *sym;
	register char *size;

	for (sym = symtab; sym < &symtab[SYMTAB]; sym++) {
		if (!sym->aname[0]) continue;
		if ((sym->aclass&0377&~AEXPORT) != ACOMMON)
			continue;

		sym->aclass = (sym->aclass&AEXPORT)|ABSS;
		size = sym->aval;
		sym->aval = header.astart+header.atext+header.adata+
				header.abss;
		header.abss =+ size;
	}
}

useek(file, offset) char *offset;
{
	if (offset&0100000) {
		seek(file, BLK32K, 4);
		offset =& 077777;
	}
	seek(file, offset, 1);
}

lookup(name)
char *name;
{
	register struct asym *sympnt, *symbeg;
	register i;

	sympnt = symbeg = &symtab[hash(name)%SYMTAB];

	do {
		if (!sympnt->aname[0]) {
			for (i = 0; i < ANAME; i++)
				sympnt->aname[i] = name[i];
			sympnt->aclass = sympnt->aval = 0;
			return (sympnt);
		}
		if (strequ(name, sympnt->aname))
			return (sympnt);

		if (++sympnt >= &symtab[SYMTAB])
			sympnt = symtab;
	} while (sympnt != symbeg);

	printf("out of symbol table space\n");
	unlink(otname);
	unlink(ltname);
	abort();
}

strequ(left, right)
{
	register char *s1, *s2;
	register c;

	s1 = left; s2 = right;

	do {
		if ((c = *s1++) != *s2++)
			return (0);
	} while (c);
	return (1);
}

hash(name)
{
	register char *pnt;
	register h, c;

	h = 0;
	pnt = name;

	while (c = *pnt++)
		h = (h<<3)^c;

	return (h&077777);	/* unsigned */
}

irq()
{
	unlink(otname);
	unlink(ltname);
	exit(1);
}

mktemp()
{
	tmpname(otname); tmpname(ltname);

	if (fcreat(otname, &outbuf) < 0)
		fcrash();
	if (fcreat(ltname, &outlink) < 0) {
		unlink(otname);
		fcrash();
	}
	signal(1, irq);
	signal(2, irq);
}

/* Place the link temp onto the output file, place the symbols,
 * then rename to the final file.
 */
concat()
{
	register struct asym *sym;
	register c;

	fflush(&outlink);
	for (sym = symtab; sym < &symtab[SYMTAB]; sym++) {
		if (!sym->aname[0]) continue;
		write(outlink.fdesc, sym, sizeof(*sym));
		header.asymsize =+ sizeof(*sym);
	}
	close(outlink.fdesc);

	fflush(&outbuf);
	close(outbuf.fdesc);

	if (fcreat("a.out.80", &outbuf) < 0)
		fcrash();
	header.amagic = AMAGIC;
	if (!xflag && undefs == 0) header.aflags =| AEXEC;
	write(outbuf.fdesc, &header, sizeof(header));

	if (fopen(otname, &objbuf) < 0)
		fcrash();
	while ((c = getc(&objbuf)) >= 0)
		putc(c, &outbuf);
	close(objbuf.fdesc);
	unlink(otname);

	if (fopen(ltname, &objbuf) < 0)
		fcrash();
	while ((c = getc(&objbuf)) >= 0)
		putc(c, &outbuf);
	close(&objbuf);
	unlink(ltname);

	fflush(&outbuf);
	close(outbuf.fdesc);
}

dosegs(seg)
{
	register i;

	offsets[0] = header.astart;
	offsets[1] = header.astart + header.atext;
	offsets[2] = header.astart + header.atext + header.adata;

	linkpc = prevlink = 0;

	for (i = 0; i < nobj; i++) {
		if (fopen(onames[i], &objbuf) < 0)
			fcrash();
		if (fopen(onames[i], &linkbuf) < 0)
			fcrash();

		seek(objbuf.fdesc, sizeof(header), 0);
		seek(linkbuf.fdesc, sizeof(header), 0);

		if (seg == ADATA)
			useek(objbuf.fdesc, oheads[i].atext);

		useek(linkbuf.fdesc, oheads[i].atext);
		useek(linkbuf.fdesc, oheads[i].adata);
		if (seg == ADATA)
			useek(linkbuf.fdesc, oheads[i].artext);

		objbuf.fcount = linkbuf.fcount = 0;
		do1seg(seg, i);

		close(objbuf.fdesc);
		close(linkbuf.fdesc);

		offsets[0] =+ oheads[i].atext;
		offsets[1] =+ oheads[i].adata;
		offsets[2] =+ oheads[i].abss;
	}

	putw(-1, &outlink);
	linkpos =+ 2;
	if (seg == ATEXT)
		header.artext = linkpos;
	else
		header.ardata = linkpos;
	linkpos = 0;
}

do1seg(seg, fnum)
{
	register char *pc, *endpc;
	register nextlink;
	static char *oldpc;
	static c;

	pc = 0;
	endpc = seg == ADATA ? oheads[fnum].adata : oheads[fnum].atext;

	nextlink = getw(&linkbuf);
	if (nextlink != -1) nextlink =+ pc;

	while (pc != endpc) {
		if (pc > endpc) {
			printf("OUT OF SYNC, PAST END OF SEGMENT");
			unlink(ltname);
			unlink(otname);
			abort();
		}
		if (nextlink != -1 && pc == nextlink) {
			oldpc = pc;
			pc =+ dolink(seg, fnum);
			linkpc =+ pc - oldpc;
			nextlink = getw(&linkbuf);
			if (nextlink != -1) nextlink =+ oldpc;
		}
		else {
			c = getc(&objbuf);
			if (c < 0) {
				printf("early eof!!\n");
				unlink(ltname);
				unlink(otname);
				abort();
			}
			putc(c, &outbuf);
			pc++; linkpc++;
		}
	}
}

dolink(seg, fnum)
{
	register hilo, i, value;
	static char name[ANAME], c;
	static class;

	hilo = getc(&linkbuf);
	if (hilo) {
		value = getc(&objbuf);
		if (hilo == AHI)
			value = (value<<8)|(getc(&linkbuf)&0377);
	} else value = getw(&objbuf);

	class = getc(&linkbuf);
	switch (class) {
	default:
		printf("BAD CLASS %o\n", class);
		unlink(ltname);
		unlink(otname);
		abort();
	case ATEXT:
		value =+ offsets[0]-oheads[fnum].astart;
		break;
	case ADATA:
		value =+ offsets[1]-oheads[fnum].astart-oheads[fnum].atext;
		break;
	case ABSS:
		value =+ offsets[2]-oheads[fnum].astart
			-oheads[fnum].atext-oheads[fnum].adata;
		break;
	case AUNDEF:
		i = 0;
		while (c = getc(&linkbuf))
			if (i < ANAME-1) name[i++] = c;
		name[i] = 0;

		i = lookup(name);

		class = i->aclass&0377&~AEXPORT;
		switch (class) {
		case ATEXT:
		case ADATA:
		case ABSS:
			value =+ i->aval;
			goto output;
		case AABS:
			value =+ i->aval;
			goto nolink;
		case AUNDEF:
		case ACOMMON:
			break;
		default:
			printf("bad sym class %o\n", class);
			unlink(ltname);
			unlink(otname);
			abort();
		}

		undefs++;
		putw(linkpc - prevlink, &outlink);
		prevlink = linkpc;
		linkpos =+ 2;
		putc(hilo, &outlink);
		if (hilo == AHI) {
			putc(value&0377, &outlink);
			linkpos =+ 2;
		} else linkpos++;
		putc(AUNDEF, &outlink);
		linkpos++;
		i = 0;
		do {
			putc(name[i], &outlink);
			linkpos++;
		} while (name[i++]);
		goto nolink;
	}
output:
	putw(linkpc - prevlink, &outlink);
	prevlink = linkpc;
	linkpos =+ 2;
	putc(hilo, &outlink);
	if (hilo == AHI) {
		putc(value&0377, &outlink);
		linkpos =+ 2;
	} else linkpos++;
	putc(class, &outlink);
	linkpos++;
nolink:
	switch (hilo) {
	case AHI:
		putc(value>>8, &outbuf);
		return (1);
	case ALO:
		putc(value, &outbuf);
		return (1);
	default:
		putw(value, &outbuf);
		return (2);
	}
}

report()
{
	register struct asym *sym;
	register headered, class;

	if (xflag) return;
	headered = 0;
	for (sym = symtab; sym < &symtab[SYMTAB]; sym++) {
		if (!sym->aname[0]) continue;
		class = sym->aclass&0377&~AEXPORT;
		if (class) continue;
		if (!headered) {
			printf("undefined:\n");
			headered++;
		}
		printf("%s\n", sym->aname);
	}
}
