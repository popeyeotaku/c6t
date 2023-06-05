#

/* Temporary File Library by Troy */

int _ntemp 0;
char _tempn[] "/tmp/tmpa000000";

/* Set a string to a temporary file name.
 * Must be 16 bytes long.
 */
tmpname(target)
{
	register char *src, *dest;
	register pid;

	src = _tempn;
	dest = target;

	while (*dest++ = *src++)
		;

	while (*--dest != 'a')
		;
	*dest++ =+ _ntemp++;

	pid = getpid();
	for (src=5; src != -1; src--)
		*dest++ = '0'+((pid>>(src*3))&07);
}
