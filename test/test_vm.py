"""Test C6T VM"""

import unittest
from pathlib import Path

from pyc6t.backend import vm as backvm
from pyc6t.frontend import frontend
from pyc6t.vm import vm_asm

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
        csrc = Path("test") / Path("test_main.c")
        irsrc = frontend.compile_c6t(csrc.read_text("ascii"))
        asmsrc = backvm.BackendVM(irsrc).codegen()
        vm_asm.Assembler(asmsrc + PUTCHAR).assemble()


class VMTests(unittest.TestCase):
    """Tests for the VM itself."""
