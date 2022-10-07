"""C6T - C version 6 by Troy - Statement Unit Tests"""

import unittest

import extdef
from c6tstate import ParseState


class StateTest(unittest.TestCase):
    """Test cases for statements."""

    def test_fbrz(self):
        """Test floating brz statements."""
        self.dosrc(
            [
                "foo(bar) float bar;",
                "{",
                "if (bar) bar =* 2;",
                "while (bar) bar =- 1;",
                "do bar =+ 1; while (bar < 10.0);",
                "for (bar = 0; bar < 10; bar =+ 1);",
                "return (bar);",
                "}",
            ],
            [
                "_foo:.export _foo",
                "useregs 0",
                "auto 10",
                "dload",
                "fbrz L1",
                "auto 10",
                "con 2",
                "toflt",
                "dasnmult",
                "eval",
                "L1:L2:auto 10",
                "dload",
                "fbrz L3",
                "auto 10",
                "con 1",
                "toflt",
                "dasnsub",
                "eval",
                "jmp L2",
                "L3:L4:auto 10",
                "con 1",
                "toflt",
                "dasnadd",
                "eval",
                "L5:auto 10",
                "dload",
                "fcon 10.0",
                "fless",
                "brz L6",
                "jmp L4",
                "L6:auto 10",
                "con 0",
                "toflt",
                "dassign",
                "eval",
                "L9:auto 10",
                "dload",
                "con 10",
                "toflt",
                "fless",
                "brz L8",
                "L7:auto 10",
                "con 1",
                "toflt",
                "dasnadd",
                "eval",
                "jmp L9",
                "L8:auto 10",
                "dload",
                "fret",
                "retnull",
            ],
        )

    def dosrc(self, source: list[str], result: list[str]):
        """Given a source and IR output, both in the format of a list of
        strings w/ one line per string, compile the source and assert that
        there were no errors, AND the result matches.
        """
        state = ParseState("\n".join(source))
        extdef.extdef(state)
        self.assertTrue(state.eof())
        self.assertEqual(state.errcount, 0)
        self.assertEqual(state.out_ir.splitlines(keepends=False), result)

    def test_if(self):
        """Test the if statement."""
        source = [
            "foobar(foo, bar)",
            "{",
            "if (foo)",
            "return (bar);",
            "if (bar)",
            "return (foo);",
            "else",
            "return (-1);",
            "}",
        ]
        result = [
            "_foobar:.export _foobar",
            "useregs 0",
            "auto 10",
            "load",
            "brz L1",
            "auto 12",
            "load",
            "ret",
            "L1:auto 12",
            "load",
            "brz L2",
            "auto 10",
            "load",
            "ret",
            "jmp L3",
            "L2:con 65535",
            "ret",
            "L3:retnull",
        ]
        self.dosrc(source, result)

    def test_while(self):
        """Test while statements."""
        self.dosrc(
            [
                "foobar(foo, bar)",
                "{",
                "while (foo--)",
                "if (++bar) break;",
                "else continue;",
                "}",
            ],
            [
                "_foobar:.export _foobar",
                "useregs 0",
                "L1:auto 10",
                "con 1",
                "postdec",
                "brz L2",
                "auto 12",
                "con 1",
                "preinc",
                "brz L3",
                "jmp L2",
                "jmp L4",
                "L3:jmp L1",
                "L4:jmp L1",
                "L2:retnull",
            ],
        )

    def test_do(self):
        """Test do statements."""
        self.dosrc(
            [
                "foobar(foo, bar)",
                "{",
                "do",
                "{",
                "if (--foo) continue;",
                "else if (bar++) break;",
                "} while (bar--);",
                "}",
            ],
            [
                "_foobar:.export _foobar",
                "useregs 0",
                "L1:auto 10",
                "con 1",
                "predec",
                "brz L4",
                "jmp L2",
                "jmp L5",
                "L4:auto 12",
                "con 1",
                "postinc",
                "brz L6",
                "jmp L3",
                "L6:L5:L2:auto 12",
                "con 1",
                "postdec",
                "brz L3",
                "jmp L1",
                "L3:retnull",
            ],
        )

    def test_goto(self):
        """Test goto statements."""
        self.dosrc(
            ["foo()", "{", "goto A;", "B:goto B;", "A:", ";", "}"],
            [
                "_foo:.export _foo",
                "useregs 0",
                "name L1",
                "goto",
                "L2:name L2",
                "goto",
                "L1:retnull",
            ],
        )

    def test_for(self):
        """Test for statements."""
        self.dosrc(
            [
                "foobar(foo,bar)",
                "int *foo;",
                "{",
                "register i, t, oldt;",
                "for (i = t = oldt = 0; i < bar; i++) {",
                "t =+ foo[i];",
                "if (t < oldt) break;",
                "else oldt = t;",
                "continue;",
                "}",
                "return (t);",
                "}",
            ],
            [
                "_foobar:.export _foobar",
                "useregs 3",
                "reg 0",
                "reg 1",
                "reg 2",
                "con 0",
                "assign",
                "assign",
                "assign",
                "eval",
                "L3:reg 0",
                "load",
                "auto 12",
                "load",
                "less",
                "brz L2",
                "reg 1",
                "auto 10",
                "load",
                "reg 0",
                "load",
                "con 2",
                "mult",
                "add",
                "load",
                "asnadd",
                "eval",
                "reg 1",
                "load",
                "reg 2",
                "load",
                "less",
                "brz L4",
                "jmp L2",
                "jmp L5",
                "L4:reg 2",
                "reg 1",
                "load",
                "assign",
                "eval",
                "L5:jmp L1",
                "L1:reg 0",
                "con 1",
                "preinc",
                "eval",
                "jmp L3",
                "L2:reg 1",
                "load",
                "ret",
                "retnull",
            ],
        )

    def test_switch(self):
        """Test switch statements."""
        self.dosrc(
            [
                "foo(bar)",
                "{",
                "switch (bar)",
                "{",
                "case 0:",
                "return (0);",
                "case 1:",
                "break;",
                "case 2:",
                "return (1);",
                "default:",
                "return (bar);",
                "}",
                "return (bar*2);",
                "}",
            ],
            [
                "_foo:.export _foo",
                "useregs 0",
                "jmp L1",
                "L3:con 0",
                "ret",
                "L4:jmp L2",
                "L5:con 1",
                "ret",
                "L6:auto 10",
                "load",
                "ret",
                "L1:.data",
                "L7:.dw 0,L3",
                ".dw 1,L4",
                ".dw 2,L5",
                ".text",
                "auto 10",
                "load",
                "name L7",
                "name L6",
                "con 3",
                "doswitch",
                "L2:auto 10",
                "load",
                "con 2",
                "mult",
                "ret",
                "retnull",
            ],
        )
