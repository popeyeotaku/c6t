"""C6T - C version 6 by Troy - Main Command Line Test"""

import pathlib
import unittest

import main


class TestMain(unittest.TestCase):
    """Test the command line routine for C6T."""

    def testmain(self):
        main.main([str(pathlib.Path(pathlib.PurePosixPath("python/test_main.c")))])
        self.assertTrue(True)
