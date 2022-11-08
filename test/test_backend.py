"""Test backend."""

import unittest
from pathlib import Path

from pyc6t.backend import vm
from pyc6t.frontend import frontend


class VM(unittest.TestCase):
    """Tests for VM backend codegen."""

    def test_vm_main(self):
        """Test the VM off test_main.c"""
        path = Path("test") / Path("test_main.c")
        ir_asm = frontend.compile_c6t(path.read_text("ascii"))
        asm = vm.BackendVM(ir_asm).codegen()
        path = Path("test") / Path("test_main.s")
        path.write_text(asm, "ascii")
