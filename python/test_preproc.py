"""C6T - C version 6 by Troy - Preprocessor Tests"""

import unittest

import preproc


class TestPreproc(unittest.TestCase):
    """Tests for the C6T preprocessor."""

    def cmp(self, source: list[str], preproced: list[str]):
        """Do a test compared the source to the preprocessed output."""
        self.assertEqual("\n".join(preproced), preproc.preproc("\n".join(source)))

    def test_define(self):
        """Test define macros."""
        self.cmp(
            ["#", "#define FOO foo", "#define BAR bar", "FOO BAR"],
            ["", "", "", " foo   bar "],
        )

    def test_include(self):
        """Test include macros."""
        self.cmp(
            ["#", "#define FOO foo", '#include "python/test_preproc.c"', "FOO BAR"],
            ["", "", "", "@/* C6T include tests */", "", "", "@", " foo   bar "],
        )

    def test_comment(self):
        """Test comment stripping."""
        self.cmp(
            ["#", "#define FOOBAR FOO/*foobar*/BAR", "FOOBAR"], ["", "", " FOO BAR "]
        )
