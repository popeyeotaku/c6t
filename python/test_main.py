"""C6T - C version 6 by Troy - Main Command Line Test"""

import pathlib
import unittest

import main


class TestMain(unittest.TestCase):
    """Test the command line routine for C6T."""

    def testmain(self):
        """Make sure main runs correctly."""
        main.main(['python/test_main.c', '-X', 'python/test_main_append.s'])
