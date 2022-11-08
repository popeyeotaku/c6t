"""C6T - C version 6 by Troy - Main Command Line Test"""

import unittest

from pyc6t.frontend import main


class TestMain(unittest.TestCase):
    """Test the command line routine for C6T."""

    def testmain(self):
        """Make sure main runs correctly."""
        main.main(["test/test_main.c", "-X", "test/test_main_append.s"])
