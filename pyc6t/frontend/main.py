"""C6T - C version 6 by Troy - Frontend Command Line"""

import argparse
import sys
from pathlib import Path, PurePosixPath

from ..backend import vm, i8080
from ..vm import vm_asm
from . import preproc
from .frontend import compile_c6t

BACKENDS = {"vm": (vm.BackendVM, vm_asm.Assembler), '8080': (i8080.BackendFile, None)}

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
parser.add_argument(
    "-Y", dest="symtab", action="store_true", default=False, help="output symbol table"
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
        if backasm is None:
            return
        assembler = backasm(asmsrc + append)
        binary = assembler.assemble()
        if args.symtab:
            symtab = [
                (name, value)
                for name, value in assembler.symtab.items()
                if name[0] != "L"
            ]
            symtext = ""
            for name, value in sorted(symtab, key=lambda s: s[1]):
                symtext += f"{name}: {hex(value)}\n"
            srcpath.with_suffix(".sym").write_text(symtext, "ascii")
        srcpath.with_suffix(".o").write_bytes(binary)


if __name__ == "__main__":
    main(sys.argv[1:])
