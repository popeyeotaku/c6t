#

#define ever ;;

main(argc, argv) char **argv;
{
    while (argc = argc - 1)
        puts(*(argv = argv + 1));
}

puts(string)
{
    register char *s;
    register c;

    if (s = string) for (ever) {
        c = *s;
        s = s + 1;
        if (!c) break;
        putchar(c);
    }
}