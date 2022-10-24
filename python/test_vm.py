"""Test C6T VM"""

import unittest
from io import StringIO
from pathlib import Path

import backend.vm
import frontend
import vm.vm
import vm.vm_asm

PUTCHAR = """
_putchar:.export _putchar
auto 10
load
chrout
retnull
"""


class VmAsm(unittest.TestCase):
    """C6T VM Assembler tests."""

    def test_main(self) -> None:
        """Test assembly of the test_main.c file."""
        csrc = Path("python") / Path("test_main.c")
        irsrc = frontend.compile_c6t(csrc.read_text("ascii"))
        asmsrc = backend.vm.BackendVM(irsrc).codegen()
        vm.vm_asm.Assembler(asmsrc + PUTCHAR).assemble()


class VMTests(unittest.TestCase):
    """Tests for the VM itself."""

    def test_main(self) -> None:
        """Test test_main.c file."""
        args = ("foobar", "foo", "bar", "\n")
        argio = StringIO()
        csrc = Path("python") / Path("test_main.c")
        irsrc = frontend.compile_c6t(csrc.read_text("ascii"))
        asmsrc = backend.vm.BackendVM(irsrc).codegen()
        prg = vm.vm_asm.Assembler(asmsrc + PUTCHAR).assemble()
        prgvm = vm.vm.VM(prg)
        prgvm.exec(*args, stdout=argio)
        self.assertEqual(argio.getvalue(), "foobar\n")
