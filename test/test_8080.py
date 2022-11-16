"""C6T INtel 8080 Backend Tests"""

import unittest

from pyc6t.backend import i8080
from pyc6t.frontend import main


class TestCodegen(unittest.TestCase):
    """Test Intel 8080 code generation."""

    def test_templates(self):
        """Test that the templates load correctly."""
        i8080.BackendFile("")

    def test_codegen(self):
        """Test codegen of test_main.c"""
        main.main(["-S", "-b", "8080", "test/test_main.c"])
