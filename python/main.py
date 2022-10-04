"""C6T - C version 6 by Troy - Frontend Command Line"""

import argparse
import pathlib
import sys

from frontend import compile_c6t

parser = argparse.ArgumentParser(description="Frontend for the C6T compiler")
parser.add_argument("files", type=str, help="the source files", nargs="+")


def main(argv: list[str]):
    """Run the frontend parser on the given arguments."""
    args = parser.parse_args(argv)
    for file in args.files:
        assert isinstance(file, str)
        path = pathlib.Path(file)
        out_ir = compile_c6t(path.read_text("ascii"))
        path.with_suffix(".ir").write_text(out_ir, encoding="ascii")


if __name__ == "__main__":
    main(sys.argv[1:])
