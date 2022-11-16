"""C6T INtel 8080 Backend Tests"""

import unittest

from pyc6t.backend import i8080


class TestCodegen(unittest.TestCase):
    """Test Intel 8080 code generation."""

    def test_templates(self):
        """Test that the templates load correctly."""
        i8080.BackendFile("")
