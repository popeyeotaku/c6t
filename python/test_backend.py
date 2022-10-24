"""Test backend."""

import unittest
from pathlib import Path

import backend.vm
import frontend


class VM(unittest.TestCase):
    """Tests for VM backend codegen."""

    def test_vm_main(self):
        """Test the VM off test_main.c"""
        path = Path("python") / Path("test_main.c")
        ir_asm = frontend.compile_c6t(path.read_text("ascii"))
        asm = backend.vm.BackendVM(ir_asm).codegen()
        path = Path("python") / Path("test_main.s")
        path.write_text(asm, "ascii")
