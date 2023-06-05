#

/* CC6T -- Compiler Command for C version 6 by Troy */

#define TNAMELEN 64
extern int _ntemp;
#define NTNAME 2
char tname[NTNAME][TNAMELEN];

/* Replace these with the locations of these files on your given system. */
char cpp[] "/home/troy/cpp/a.out";
char frontend[] "/home/troy/c6t/a.out";
char backend[] "/home/troy/c6tir/i8080";
char as[] "/home/troy/as80/a.out";
char ld[] "/home/troy/poplink/a.out";

/* The output filename produced by as80/poplink. */
char outname[] "a.out.80";

#define NARGS 64
char *ldargs[NARGS] { ld }, **ldpnt &ldargs[1];
int pflag, cflag, sflag;

irq()
{
	remtemps();
	exit(1);
}

main(argc, argv) char **argv;
{
	register i;
	register char *arg;

	signal(1, irq);
	signal(2, irq);

	if (argc < 1) crash("not enough args");

	for (i = 1; i < argc; i++) {
		_ntemp = 0;	/* reset temp filenames */
		arg = argv[i];
		if (arg[0] == '-') {
			if (arg[1] && arg[2] == 0) switch (arg[1]) {
			case 'P':
				pflag++;
				continue;
			case 'S':
				sflag++;
				continue;
			case 'c':
				cflag++;
				continue;
			}
			addarg(arg);
		}
		else switch (ext(arg)) {
		case 'c':
			cc(arg);
			break;
		case 'a':
			ss(arg);
			break;
		default:
			addarg(arg);
			break;
		}
	}
	if (!cflag && !sflag && !pflag) {
		load();
		crash("unable to run loader");
	} else exit(0);
}

addarg(arg)
{
	if (ldpnt >= &ldargs[NARGS])
		crash("too many args");
	*ldpnt++ = arg;
}

load()
{
	addarg(0);
	execv(ld, ldargs);
}

remtemps()
{
	register i;

	if (i = _ntemp) {
		_ntemp = 0;
		while (i--) {
			tmpname(tname[0]);
			unlink(tname[0]);
		}
	}
}

ext(name)
char name[];
{
	register char *end;

	end = strend(name);
	if (&end[-2] > name && end[-2] == '.')
		return (end[-1]);
	return (0);
}

strend(string)
{
	register char *s;

	if (!(s = string)) return (0);
	while (*s) s++;
	return (s);
}

cc(arg)
{
	printf("%s:\n", arg);
	/* run preprocessor */
	/* arg is input, tname[0] is output */
	if (pflag) withext(tname[0], arg, 'i');
	else tmpname(tname[0]);
	close(creat(tname[0], 0666));
	run(arg, tname[0], cpp, 0);
	if (pflag) return;

	/* run frontend */
	/* tname[0] is input, tname[1] is output */
	tmpname(tname[1]);
	close(creat(tname[1], 0666));
	run(tname[0], tname[1], frontend, 0);
	remove(tname[0]);

	/* run backend */
	/* tname[1] is input, tname[0] is output */
	if (sflag) withext(tname[0], arg, 's');
	else tmpname(tname[0]);
	close(creat(tname[0], 0666));
	run(tname[1], tname[0], backend, 0);
	remove(tname[1]);
	if (sflag) return;

	/* run assembler */
	/* tname[0] is input, assembler outputs on outname */
	run(tname[0], 0, as, 0);
	remove(tname[0]);

	mvobj(arg);
}

run(in, out, cmd, args)
{
	register pid, wid;
	static status;

	switch (pid = fork()) {
	case -1:
		crash("cannot fork to run %s", cmd);
	case 0:
		inout(in, out);
		execl(cmd, &cmd);
		crash("unable to exec %s", cmd);
	default:
		while ((wid=wait(&status))!= -1 && wid != pid)
			;
		if (status)
			crash("bad exit status %o for %s", status, cmd);
	}
}

inout(in, out)
{
	if (in) {
		close(0);
		if (open(in, 0) != 0)
			 crash("cannot open %s for input", in);
	}
	if (out) {
		close(1);
		if (open(out, 1) != 1)
			crash("cannot open %s for output", out);
	}
}

/* assemble source file */
ss(arg)
{
	printf("%s:\n", arg);
	run(arg, 0, as, 0);
	mvobj(arg);
}

move(source, dest)
{
	unlink(dest);
	if (link(source, dest) < 0)
bad:
		crash("unable to move %s to %s", source, dest);
	if (unlink(source) < 0) goto bad;
}

withext(dest, source, newext)
{
	register i;
	register char *d, *s;
	static char *extpos;

	d = dest;
	s = basename(source);

	extpos = strend(s);
	if (&extpos[-2] > s && extpos[-2] == '.')
		extpos = &extpos[-2];

	i = TNAMELEN-3;
	while (i--) {
		if (s == extpos) break;
		*d++ = *s++;
	}
	s = extpos;

	*d++ = '.';
	*d++ = newext;
	*d = 0;
}

basename(string)
{
	register char *start, *end, *pnt;

	start = string;
	pnt = end = strend(start);
	while (--pnt > start) {
		if (pnt[-1] == '/') return (pnt);
	}
	if (pnt < start) return (start);
	return (pnt);
}

mvobj(filename)
{
	register char *pnt, *file;

	pnt = strend(file = basename(filename));
	if (&pnt[-2] > file && pnt[-2] == '.') {
		pnt[-1] = 'o';
		addarg(file);
		move(outname, file);
	}
	else crash("bad filename %s", filename);
}

remove(filename)
{
	if (unlink(filename) < 0)
		crash("unable to remove %s", filename);
}

crash(msg, arg1, arg2)
{
	printf(msg, arg1, arg2);
	putchar('\n');
	flush();
	remtemps();
	exit(1);
}
