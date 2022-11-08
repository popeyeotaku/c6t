"""C6T - C version 6 by Troy - Lexer Unit Tests."""

import unittest

from pyc6t.frontend import lexer


class Lexer(unittest.TestCase):
    """Tests for the input tokenizer."""

    def test_op(self):
        """Test operator parsing."""
        tkn = lexer.Tokenizer("=++++*/***/*")
        labels = ("=+", "++", "+", "*", "*", "eof")
        for label, token in zip(labels, tkn):
            self.assertEqual(label, token.label)

    def test_name(self):
        """Test NAME/keyword parsing."""
        tkn = lexer.Tokenizer("int foo bar intchar int char ")
        labels = ("int", "name", "name", "name", "int", "char", "eof")
        values = (None, "foo", "bar", "intchar", None, None, None)
        for label, value, token in zip(labels, values, tkn):
            self.assertEqual(token.label, label)
            if value is not None:
                self.assertEqual(token.value, value)

    def test_con(self):
        """Test CON tokens."""
        tkn = lexer.Tokenizer("010 999999")
        labels = ("con", "con", "eof")
        values = (8, 999999 & 0xFFFF, None)
        for label, value, token in zip(labels, values, tkn):
            self.assertEqual(label, token.label)
            if value is not None:
                self.assertEqual(token.value, value)

    def test_fcon(self):
        """Test FCON tokens."""
        tkn = lexer.Tokenizer("3.14159 5e-2 6e2")
        labels = ("fcon", "fcon", "fcon", "eof")
        values = (3.14159, 0.05, 600.0, None)
        for label, value, token in zip(labels, values, tkn):
            self.assertEqual(label, token.label)
            if value is not None:
                self.assertEqual(value, token.value)

    def test_charcon(self):
        """Test character constants."""
        tkn = lexer.Tokenizer("'12' '34'")
        values = (0x3132, 0x3334)
        for token, value in zip(tkn, values):
            self.assertEqual(token.label, "con")
            self.assertEqual(token.value, value)
