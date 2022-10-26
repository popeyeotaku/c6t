"""C6T - C version 6 by Troy - Frontend Command Line"""

import argparse
import sys
from pathlib import Path, PurePosixPath

import backend.shared
import backend.vm
import preproc
import vm.vm_asm
from frontend import compile_c6t

BACKENDS = {"vm": (backend.vm.BackendVM, vm.vm_asm.Assembler)}

parser = argparse.ArgumentParser(description="Frontend for the C6T compiler")
parser.add_argument(
    "files", type=str, metavar="file", help="the source files", nargs="+"
)
parser.add_argument(
    "-I",
    dest="preproc",
    help="only output a preprocessed file",
    action="store_true",
    default=False,
)
parser.add_argument(
    "-S",
    dest="outasm",
    help="only output an assembly file",
    action="store_true",
    default=False,
)
parser.add_argument(
    "-b",
    dest="backend",
    type=str,
    choices=list(BACKENDS),
    default="vm",
    help="choice of backend",
)
parser.add_argument(
    "-R", dest="outir", help="only output IR", action="store_true", default=False
)
parser.add_argument(
    "-X", dest="append", type=str, default=None, help="filename to append onto asm"
)


def main(argv: list[str]):
    """Run the frontend parser on the given arguments."""
    args = parser.parse_args(argv)
    if args.backend not in BACKENDS:
        raise ValueError(f"no such backend {args.backend}")
    backvm, backasm = BACKENDS[args.backend]
    if args.append:
        assert isinstance(args.append, str)
        append = Path(PurePosixPath(args.append)).read_text("ascii")
    else:
        append = ""
    for file in args.files:
        assert isinstance(file, str)
        srcpath = Path(PurePosixPath(file))
        csrc = srcpath.read_text("ascii")
        if args.preproc:
            srcpath.with_suffix(".i").write_text(preproc.preproc(csrc), "ascii")
            continue
        irsrc = compile_c6t(csrc)
        if args.outir:
            srcpath.with_suffix(".ir").write_text(irsrc, "ascii")
            continue
        asmsrc = backvm(irsrc).codegen()
        if args.outasm:
            srcpath.with_suffix(".s").write_text(asmsrc, "ascii")
            continue
        binary = backasm(asmsrc + append).assemble()
        srcpath.with_suffix(".o").write_bytes(binary)


if __name__ == "__main__":
    main(sys.argv[1:])
