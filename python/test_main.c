#

main(argc, argv) char **argv;
{
    while (--argc) puts(*++argv);
}

puts(string)
{
    register char *s;
    register c;

    if (s = string) while (c = *s++) putchar(c);
}