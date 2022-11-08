"""C6T VM"""

from argparse import ArgumentParser
import itertools
import math
import operator
import re
import sys
import time
from collections import deque
from io import SEEK_CUR, SEEK_END, SEEK_SET, StringIO
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Literal, TextIO

# import unicurses

MAX_FILES = 15

OPNAMES: tuple[str, ...] = (
    "auto",
    "preinc",
    "predec",
    "postinc",
    "postdec",
    "brz",
    "load",
    "name",
    "con",
    "call",
    "dropargs",
    "jmp",
    "retnull",
    "assign",
    "cassign",
    "cload",
    "useregs",
    "chrout",
    "drop",
    "grabreg",
    "putreg",
    "regpreinc",
    "regpredec",
    "regpostinc",
    "regpostdec",
    "chrin",
    "irqret",
    "equ",
    "nequ",
    "great",
    "less",
    "gequ",
    "lequ",
    "ugreat",
    "uless",
    "ugequ",
    "ulequ",
    "noirq",
    "yesirq",
    "log",
    "lognot",
    "bnz",
    "dup",
    "add",
    "and",
    "dropstk",
    "stkjmp",
    "sub",
    "div",
    "rshift",
    "lshift",
    "mult",
    "or",
    "open",
    "neg",
    "ret",
    "close",
    "seek",
    "read",
    "write",
    "ldiv",
    "swap",
    "save_state",
    "restore_state",
    "unlink",
    "bnz",
)
OPCODES: dict[str, int] = {opname: opcode for opcode, opname in enumerate(OPNAMES)}
OPNUMS: dict[int, str] = {opnum: opname for opname, opnum in OPCODES.items()}
OPARGS: tuple[str, ...] = (
    "useregs",
    "auto",
    "brz",
    "bnz",
    "auto",
    "preinc",
    "postinc",
    "predec",
    "postdec",
    "name",
    "con",
    "dropargs",
    "jmp",
    "grabreg",
    "putreg",
    "dropstk",
)
OPMULTARGS: dict[str, int] = {
    "regpreinc": 2,
    "regpostinc": 2,
    "regpredec": 2,
    "regpostdec": 2,
}

OPCALLS: dict[str, Callable[[Any, str, list[int]], None]] = {}

REGS: tuple[str, ...] = (
    "reg0",
    "reg1",
    "reg2",
    "pc",
    "sp",
    "fp",
)

IRQ_START = 1
IRQS: tuple[str, ...] = (
    "reset",
    "save",
    "clock",
)


class VM:
    """C6T VM."""

    def __init__(self, program: bytes, debug: bool = False, symfile: str = "") -> None:
        self.mem = bytearray(0xFFFF + 1)
        self._prg = program
        self.regs = {reg: 0 for reg in REGS}
        self.stdout = sys.stdout
        self.inbuf: deque[str] = deque()
        self.inirq: bool = False
        self.blockirq: bool = False
        self.files: list[Any | None] = [None] * MAX_FILES
        self.unlink_queue: set[Path] = set()

        self.debug = debug
        self.breakpoints: set[int] = set()
        self.single = False
        self.symtab: dict[str, int] = {}
        if self.debug and symfile:
            symtxt = Path(symfile).read_text("ascii")
            for match in re.finditer(r"\s*(\S+?): 0x([a-fA-F0-9]+)", symtxt):
                self.symtab[match[1]] = int(match[2], base=16)

    def disasm(self, addr: int) -> tuple[str, int]:
        """Return a disassembled for of an instruction, along with its size
        in bytes.
        """
        opnum = self.fromword(self.grab(addr, 1))
        opcode = OPNUMS[opnum]
        if opcode in OPMULTARGS:
            argcount = OPMULTARGS[opcode]
        elif opcode in OPARGS:
            argcount = 1
        else:
            argcount = 0
        argsnums = [
            self.fromword(self.grab(addr + 1 + i * 2, 2)) for i in range(argcount)
        ]
        args: list[str] = []
        for arg in argsnums:
            if arg in self.symtab.values():
                args.append(self.findsym(arg))
            else:
                args.append(hex(arg))
        return f"{opcode} {','.join(args)}".strip(), 1 + argcount * 2

    @property
    def peekpc(self) -> str:
        """Peek the current instruction."""
        return self.disasm(self.regs["pc"])[0]

    def disasm_mult(self, addr: int, count: int) -> str:
        """Disassemble multiple instructions."""
        out = ""
        for _ in range(count):
            line, size = self.disasm(addr)
            out += f"{self.findsym(addr)}: {line}\n"
            addr += size
        return out

    def peekpc_mult(self, count: int) -> str:
        """Disassemble multiple instructions starting at the current PC."""
        return self.disasm_mult(self.regs["pc"], count)

    @property
    def peekstk(self) -> list[int]:
        """Peek the values from the FP to the SP (including autos)."""
        return list(
            reversed(
                [self.peek(i) for i in range(0, self.regs["fp"] - self.regs["sp"], 2)]
            )
        )

    @property
    def peekstk_sym(self) -> list[str]:
        """Peekstk but each value is looked up via peeksym."""
        out: list[str] = []
        for i in self.peekstk:
            if i in self.symtab.values():
                out.append(self.findsym(i))
            else:
                out.append(hex(i))
        return out

    def addbrk(self, *targets: str | int) -> None:
        """Add a debug breakpoint."""
        for target in targets:
            if isinstance(target, str):
                target = self.symtab[target]
            self.breakpoints.add(target)

    def offbrk(self, *targets: str | int) -> None:
        """Remove a breakpoint."""
        for target in targets:
            if isinstance(target, str):
                target = self.symtab[target]
            self.breakpoints.remove(target)

    def lookup(self, target: str) -> int:
        """Toggle a breakpoint on a VM.findsym() formatted string."""
        if match := re.match(r"(.+)?([+-][0-9]+)", target):
            addr = self.symtab[match[1]] + int(match[2])
        elif match := re.match(r"0x([0-9a-fA-F]+)", target):
            addr = int(match[1], base=16)
        elif match := re.match("[0-9]+", target):
            addr = int(match[0])
        elif target in self.symtab:
            addr = self.symtab[target]
        else:
            raise ValueError(target)
        return addr

    def brk(self, *targets: str) -> None:
        """Toggle breakpoints on each target."""
        for target in targets:
            addr = self.lookup(target)
            if addr in self.breakpoints:
                self.breakpoints.remove(addr)
            else:
                self.breakpoints.add(addr)

    @property
    def brks(self) -> list[str]:
        """findsym representation of breakpoints"""
        return [self.findsym(brk) for brk in self.breakpoints]

    def alloc_file(self) -> int:
        """Return the next unallocated file descriptor, or -1 if none
        available.
        """
        for i, file in enumerate(self.files):
            if not file:
                return i
        return -1

    def grabstr(self, addr: int) -> str:
        """Grab a null-terminated ASCII string starting at the given address
        in the VM's memory.
        """
        grabbed = bytes()
        for i in itertools.count(addr):
            if (i & 0xFFFF) < addr:
                break  # overflow
            byte = self.grab(i, 1)
            if byte[0] == 0:
                break
            grabbed += byte
        return grabbed.decode("ascii")

    def grab_path(self, addr: int) -> Path:
        """Return a pathlib path from an ASCII string in the VM's memory
        starting at the given address.
        """
        pathstr = self.grabstr(addr).removeprefix("/")
        return Path.cwd() / Path(PurePosixPath(pathstr))

    def pop_path(self) -> Path:
        """Return a pathlib path from the ASCII string whose address is stored
        on the bottom of the stack.
        """
        return self.grab_path(self.pop())

    @property
    def prg(self) -> bytes:
        """The bytes of our initialized program."""
        return self._prg

    def copy(self, start: int, data: bytes) -> None:
        """Copy the data into our memory."""
        for i, byte in enumerate(data):
            self.mem[(start + i) & 0xFFFF] = byte

    def grab(self, start: int, count: int) -> bytes:
        """Grab data from our memory."""
        data: list[int] = []
        for i in range(start, start + count):
            data.append(self.mem[i & 0xFFFF])
        return bytes(data)

    def toword(self, i: int) -> bytes:
        """Turn an integer into byte values."""
        bytelen = math.ceil(i.bit_length() / 8) + 1
        ibytes = i.to_bytes(bytelen, "little", signed=True) + bytes(2)
        assert len(ibytes[:2]) == 2
        return ibytes[:2]

    def fromword(self, word: bytes, *, signed: bool = False) -> int:
        """Turn some bytes into a signed integer."""
        return int.from_bytes(word, "little", signed=signed)

    def push(self, i: int) -> None:
        """Push a number onto the VM stack."""
        self.regs["sp"] -= 2
        self.copy(self.regs["sp"], self.toword(i))

    def pop(self, signed: bool = False) -> int:
        """Pop a number off the VM stack."""
        word = self.grab(self.regs["sp"], 2)
        self.regs["sp"] += 2
        return self.fromword(word, signed=signed)

    def run_irq(self, clocks_per_sec: int) -> None:
        """Run with simulated interrupts. Uses unicurses."""
        # pylint:disable=unused-variable
        self.copy(0, self.prg)

        # stdscr = unicurses.initscr()
        # unicurses.clear()
        # unicurses.noecho()
        # unicurses.cbreak()
        # unicurses.clear()
        # unicurses.nodelay(stdscr, 1)

        self.stdout = StringIO()
        self.inbuf = deque()
        outpos = self.stdout.tell()

        hertz = 1 / clocks_per_sec
        start_time = time.monotonic()
        irqdone = 0
        irqleft = 0

        for reg in self.regs:
            self.regs[reg] = 0

        nextirq = ""

        while self.regs["pc"] != 0xFFFF:
            self.step()

            if nextirq:
                self.irq(nextirq)
                nextirq = ""

            # while outpos < self.stdout.tell():
            #     self.stdout.seek(outpos, SEEK_SET)
            #     for char in self.stdout.read():
            #         unicurses.addch(char)
            #     outpos = self.stdout.tell()

            # while (ichar := unicurses.getch()) != unicurses.ERR:
            #     assert isinstance(ichar, int)
            #     self.inbuf.append(chr(ichar & 0o177))

            irqleft = math.floor((time.monotonic() - start_time) / hertz)

            if irqleft > irqdone and not (self.inirq or self.blockirq):
                irqdone += 1
                nextirq = "clock"

        # unicurses.endwin()
        self.closeall()

    def closeall(self) -> None:
        """Close all open files."""
        for i, file in enumerate(self.files):
            if file:
                file.close()
                self.files[i] = None
        for path in self.unlink_queue:
            path.unlink()

    def irq(self, name: str) -> None:
        """Process an IRQ."""
        irqoffset = IRQ_START + IRQS.index(name) * 2
        irqaddr = self.fromword(self.grab(irqoffset, 2))
        # IRQs save all registers starting in the address in IRQsave.
        irqsave = self.fromword(self.grab(IRQ_START + IRQS.index("save") * 2, 2))
        for i, reg in enumerate(self.regs.values()):
            self.copy(irqsave + i * 2, self.toword(reg))
        self.regs["pc"] = irqaddr
        self.inirq = True

    def peekop(self) -> str:
        """Peek the current opcode."""
        return OPNUMS[self.fromword(self.grab(self.regs["pc"], 1))]

    def exec(
        self,
        *args: str,
        start_pc: int = 0,
        start_sp: int = 0xFFFF,
        stdout: TextIO = sys.stdout,
    ) -> None:
        """Run the VM, with an optional starting execution loation and stack
        location, and optional text args to be passed to the program via
        ARGV/ARGC in main. Also allows an optional file for stdout.

        REMEMBER THE FIRST ARG PASSED SHOULD BE THE PROGRAM NAME!!!
        """
        self.files[0] = sys.stdin.buffer
        self.files[1] = stdout.buffer
        self.files[2] = sys.stdout.buffer

        self.copy(0, self.prg)
        self.stdout = stdout
        self.regs["pc"] = start_pc
        stack = start_sp
        argv: list[int] = []
        for arg in args:  # Copy arg text
            argbytes = arg.encode("ascii") + bytes(1)
            stack -= len(argbytes)
            self.copy(stack, argbytes)
            argv.insert(0, stack)
        self.regs["sp"] = stack
        self.regs["fp"] = self.regs["sp"]
        for argaddr in argv:  # push argv array
            self.push(argaddr)
        self.push(self.regs["sp"])  # Push argv array addr for main
        self.push(len(argv))  # Push argc for main
        # Build stack frame
        self.push(0xFFFF)  # Return address for ending exec
        self.push(self.regs["fp"])  # Duplicate frame pointer
        for _ in range(3):
            self.push(0)  # Old reg contents
        self.regs["fp"] = self.regs["sp"]

        self.regs["pc"] = start_pc

        while self.regs["pc"] != 0xFFFF:
            self.step()
        self.closeall()

    def grabpc(self, count: int) -> bytes:
        """Grab count bytes starting at the current PC, advancing the PC."""
        data = self.grab(self.regs["pc"], count)
        self.regs["pc"] += count
        return data

    def peek(self, offset: int = 0) -> int:
        """The current value at the bottom of the stack modified by
        the offset.
        """
        data = self.grab(self.regs["sp"] + offset, 2)
        return self.fromword(data)

    @property
    def hexregs(self) -> dict[str, str]:
        """Hex representation of all registers."""
        return {name: hex(i) for name, i in self.regs.items()}

    def findsym(self, target: int) -> str:
        """The offset from the closest symbol to the given position."""
        if not self.debug:
            return ""
        addrs = [0] + list(sorted(self.symtab.values())) + [0xFFFF]
        found: int | None = None
        for i, addr in enumerate(addrs[:-1]):
            if addr <= target < addrs[i + 1]:
                found = addr
                break
        if found is None or found not in self.symtab.values():
            raise ValueError(target)
        foundname: str | None = None
        for name, addr in self.symtab.items():
            if addr == found:
                foundname = name
                break
        if foundname is None:
            raise ValueError(target)
        diff = target - found
        if diff:
            foundname = f"{foundname}{sign(diff)}{abs(diff)}"
        return foundname

    def peeksym(self) -> str:
        """Peek the symbol offset for the current PC."""
        return self.findsym(self.regs["pc"])

    @property
    def frame(self) -> dict[str, int]:
        """The current stack frame."""
        frame: dict[str, int] = {}
        names = ["reg2", "reg1", "reg0", "fp", "pc"]
        addr = self.regs["fp"]
        for i, name in enumerate(names):
            frame[name] = self.fromword(self.grab(addr + i * 2, 2))
        return frame

    @property
    def hexframe(self) -> dict[str, str]:
        """Hex view of the current stack frame."""
        return {name: hex(i) for name, i in self.frame.items()}

    def step(self) -> None:
        """Single step the VM."""
        if self.debug:
            if self.single:
                breakpoint()
            elif self.regs["pc"] in self.breakpoints:
                breakpoint()
        opcode = self.fromword(self.grabpc(1))
        if opcode not in OPNUMS:
            raise ValueError(f"invalid opcode {opcode}")
        opname = OPNUMS[opcode]
        args: list[int] = []
        if opname in OPMULTARGS:
            for _ in range(OPMULTARGS[opname]):
                args.append(self.fromword(self.grabpc(2)))
        elif opname in OPARGS:
            args = [self.fromword(self.grabpc(2))]
        OPCALLS[opname](self, opname, args)


def addop(*names: str):
    """Decorator to add an opcode handler to the OPCALLS table."""

    def inner(func: Callable[[VM, str, list[int]], None]):
        for name in names:
            OPCALLS[name] = func
        return func

    return inner


@addop("useregs")
# pylint:disable=unused-argument
def do_nop(c6tvm: VM, name: str, args: list[int]) -> None:
    """Perform useregs (does nothing)."""
    return


@addop("auto")
# pylint:disable=unused-argument
def do_auto(c6tvm: VM, name: str, args: list[int]) -> None:
    """Push FP+arg onto the stack."""
    c6tvm.push(args[0] + c6tvm.regs["fp"])


@addop("predec", "preinc", "postinc", "postdec")
def do_incdec(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Inc/decrement the addr on the stack."""
    arg = args[0]
    addr = c6tvm.pop()
    val = c6tvm.fromword(c6tvm.grab(addr, 2))
    match opcode:
        case "predec":
            val -= arg
            newval = val
        case "preinc":
            val += arg
            newval = val
        case "postdec":
            newval = val - arg
        case "postinc":
            newval = val + arg
        case _:
            raise ValueError("bad opcode", opcode)
    c6tvm.copy(addr, c6tvm.toword(newval))
    c6tvm.push(val)


@addop("brz", "bnz")
# pylint:disable=unused-argument
def do_brz(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Pop a word off the stack and branch to the arg if it equals or does not
    equal 0.
    """
    arg = args[0]
    word = c6tvm.pop()
    match opcode:
        case "brz":
            if word == 0:
                c6tvm.regs["pc"] = arg
        case "bnz":
            if word != 0:
                c6tvm.regs["pc"] = arg
        case _:
            raise ValueError(opcode)


@addop("load", "cload")
# pylint:disable=unused-argument
def do_load(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Load byte or int (cload or load) values from the address on the
    stack.
    """
    addr = c6tvm.pop()
    valbytes = c6tvm.grab(addr, 1 if opcode == "cload" else 2)
    val = c6tvm.fromword(valbytes, signed=True)
    c6tvm.push(val)


@addop("name", "con")
# pylint:disable=unused-argument
def do_push(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Push a literal value onto the stack."""
    c6tvm.push(args[0])


@addop("call")
# pylint:disable=unused-argument
def do_call(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Handle a call."""
    # Generate new stack frame
    addr = c6tvm.pop()
    for reg in ("pc", "fp", "reg0", "reg1", "reg2"):
        c6tvm.push(c6tvm.regs[reg])
    # Setup new regs
    c6tvm.regs["fp"] = c6tvm.regs["sp"]
    c6tvm.regs["pc"] = addr


@addop("dropargs")
# pylint:disable=unused-argument
def do_dropargs(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Drop arg words off the stack, keeping the return value at the
    bottom.
    """
    retval = c6tvm.pop()
    arg = args[0]
    c6tvm.regs["sp"] += arg * 2
    c6tvm.push(retval)


@addop("jmp")
# pylint:disable=unused-argument
def do_jmp(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Jump to the inline arg."""
    c6tvm.regs["pc"] = args[0]


@addop("retnull", "ret")
# pylint:disable=unused-argument
def do_ret(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Handle a return instruction."""
    if opcode == "retnull":
        retval = 0
    else:
        retval = c6tvm.pop()
    c6tvm.regs["sp"] = c6tvm.regs["fp"]
    for reg in ("reg2", "reg1", "reg0", "fp", "pc"):
        c6tvm.regs[reg] = c6tvm.pop()
    c6tvm.push(retval)


@addop("assign", "cassign")
# pylint:disable=unused-argument
def do_assign(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Handle a byte or int assignment, leaving the value on the stack."""
    val = c6tvm.toword(c6tvm.pop())
    addr = c6tvm.pop()
    count = 1 if opcode == "cassign" else 2
    c6tvm.copy(addr, val[:count])
    c6tvm.push(c6tvm.fromword(val))


@addop("drop")
# pylint:disable=unused-argument
def do_drop(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Drop a single word from the stack."""
    c6tvm.regs["sp"] += 2


@addop("grabreg")
# pylint:disable=unused-argument
def do_grabreg(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Grab a single register var."""
    arg = args[0] % 3
    c6tvm.push(c6tvm.regs[f"reg{arg}"])


@addop("putreg")
# pylint:disable=unused-argument
def do_putreg(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Put a popped value into a register var."""
    arg = args[0] % 3
    c6tvm.regs[f"reg{arg}"] = c6tvm.peek()


@addop("chrout")
# pylint:disable=unused-argument
def do_chrout(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Place a popped character onto stdout."""
    c6tvm.stdout.write(chr(c6tvm.pop() & 0o177))


@addop("regpostinc", "regpostdec", "regpredec", "regpreinc")
# pylint:disable=unused-argument
def do_regincdec(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Postinc/dec a register."""
    regnum = args[0] % 3
    amount = args[1]
    regname = f"reg{regnum}"
    value = c6tvm.regs[regname]
    match opcode:
        case "regpreinc":
            value = value + amount
            newval = value
        case "regpredec":
            value = value - amount
            newval = value
        case "regpostinc":
            newval = value + amount
        case "regpostdec":
            newval = value - amount
        case _:
            raise ValueError(opcode)
    c6tvm.regs[regname] = newval
    c6tvm.push(value)


@addop("chrin")
# pylint:disable=unused-argument
def do_chrin(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """If there's any characters in the input buffer, push them. ELse, push
    -1.
    """
    if c6tvm.inbuf:
        char = c6tvm.inbuf.popleft()
        c6tvm.push(ord(char) & 0o177)
    else:
        c6tvm.push(-1)


@addop("irqret")
# pylint:disable=unused-argument
def do_irqret(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Return from an IRQ."""
    saveoffset = IRQ_START + IRQS.index("save") * 2
    saveaddr = c6tvm.fromword(c6tvm.grab(saveoffset, 2))
    for i, reg in enumerate(c6tvm.regs):
        c6tvm.regs[reg] = c6tvm.fromword(c6tvm.grab(saveaddr + i * 2, 2))
    c6tvm.inirq = False


@addop(
    "equ", "gequ", "ugequ", "lequ", "ulequ", "great", "ugreat", "less", "uless", "nequ"
)
# pylint:disable=unused-argument
def do_cmp(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Push flag for if two popped values are equal."""
    right = c6tvm.pop()
    left = c6tvm.pop()
    unsigned = opcode[0] == "u"
    if not unsigned:
        left = c6tvm.fromword(c6tvm.toword(left), signed=True)
        right = c6tvm.fromword(c6tvm.toword(right), signed=True)
    opfunc: Callable[[int, int], bool]
    match opcode:
        case "equ":
            opfunc = operator.eq
        case "nequ":
            opfunc = operator.ne
        case "less" | "uless":
            opfunc = operator.lt
        case "lequ" | "ulequ":
            opfunc = operator.le
        case "great" | "ugreat":
            opfunc = operator.gt
        case "gequ" | "ugequ":
            opfunc = operator.ge
        case _:
            raise ValueError(opcode)
    if opfunc(left, right):
        c6tvm.push(1)
    else:
        c6tvm.push(0)


@addop("noirq", "yesirq")
# pylint:disable=unused-argument
def do_flgirq(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Change IRQ flag."""
    match opcode:
        case "yesirq":
            flag = True
        case "noirq":
            flag = False
        case _:
            raise ValueError(opcode)
    c6tvm.blockirq = flag


@addop("log", "lognot")
# pylint:disable=unused-argument
def do_logop(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Pop a value and push 1 or 0 depending on its equality to 0."""
    match opcode:
        case "log":
            iszero = 0
            notzero = 1
        case "lognot":
            iszero = 1
            notzero = 0
        case _:
            raise ValueError(opcode)
    if c6tvm.pop() == 0:
        c6tvm.push(iszero)
    else:
        c6tvm.push(notzero)


@addop("dup")
# pylint:disable=unused-argument
def do_dup(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Duplicate the value on the bottom of the stack."""
    c6tvm.push(c6tvm.peek())


@addop("add", "and", "sub", "div", "mult", "lshift", "rshift", "or")
# pylint:disable=unused-argument
def do_math(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Handle general math operations."""
    right = c6tvm.pop()
    left = c6tvm.pop()
    match opcode:
        case "or":
            opfunc = operator.or_
        case "mult":
            opfunc = operator.mul
        case "lshift":
            opfunc = operator.lshift
        case "div":
            opfunc = operator.floordiv
        case "sub":
            opfunc = operator.sub
        case "rshift":
            left = c6tvm.fromword(c6tvm.toword(left), signed=True)
            opfunc = operator.rshift
        case "and":
            opfunc = operator.and_
        case "add":
            opfunc = operator.add
        case "or":
            opfunc = operator.or_
        case _:
            raise ValueError(opcode)
    c6tvm.push(opfunc(left, right))


@addop("save_state")
# pylint:disable=unused-argument
def do_save_state(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Save registers into the addr on the stack."""
    addr = c6tvm.pop()
    names = ("pc", "fp", "reg0", "reg1", "reg2")
    for i, name in enumerate(names):
        c6tvm.copy(addr + i * 2, c6tvm.toword(c6tvm.frame[name]))


@addop("restore_state")
# pylint:disable=unused-argument
def do_restore_state(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Restore registers from addr on the stack."""
    addr = c6tvm.pop()
    names = ("pc", "fp", "reg0", "reg1", "reg2")
    frame: dict[str, int] = {}
    for i, name in enumerate(names):
        frame[name] = c6tvm.fromword(c6tvm.grab(addr + i * 2, 2))
    c6tvm.regs.update(frame)


@addop("unlink")
# pylint:disable=unused-argument
def do_unlink(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Simulate the Unix 6 unlink command."""
    path = c6tvm.pop_path()
    c6tvm.unlink_queue.add(path)


@addop("dropstk")
# pylint:disable=unused-argument
def do_dropstk(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Drop the stack inline arg bytes."""
    c6tvm.regs["sp"] -= args[0]


@addop("stkjmp")
# pylint:disable=unused-argument
def do_stkjmp(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Jump to the address on the stack."""
    c6tvm.regs["pc"] = c6tvm.pop()


OPEN_MODES: dict[int, str] = {0: "rb", 1: "ab", 2: "r+b", 3: "wb"}


@addop("open")
# pylint:disable=unused-argument
def do_open(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Simulate the Unix6 open command. Has additional mode 3 for creat."""
    path = c6tvm.pop_path()
    # if path not in (
    #     Path(".", "tmp", "e00001").absolute(),
    #     Path(".", "ed", "test", "foo.bar").absolute(),
    # ):
    #     raise ValueError(f"bad path {path}")
    mode = c6tvm.pop()
    descriptor = c6tvm.alloc_file()
    if descriptor == -1:
        c6tvm.push(descriptor)
        return
    if mode not in OPEN_MODES:
        c6tvm.push(-1)
        return
    modestr = OPEN_MODES[mode]
    if not path.exists and "w" not in mode:
        c6tvm.push(-1)
        return
    try:
        file = path.open(modestr)
    # pylint:disable=broad-except
    except BaseException:
        c6tvm.push(-1)
        return
    c6tvm.files[descriptor] = file
    c6tvm.push(descriptor)


@addop("neg")
# pylint:disable=unused-argument
def do_unary(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Unary math operations."""
    val = c6tvm.pop()
    match opcode:
        case "neg":
            opfunc = operator.neg
        case _:
            raise ValueError(opcode)
    c6tvm.push(opfunc(val))


@addop("close")
# pylint:disable=unused-argument
def do_close(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Simulate unix Close call."""
    descriptor = c6tvm.pop()
    try:
        file = c6tvm.files[descriptor]
    except IndexError:
        return
    if file is None:
        return
    file.close()
    c6tvm.files[descriptor] = None


WHENCES = {
    0: SEEK_SET,
    1: SEEK_CUR,
    2: SEEK_END,
}


@addop("seek")
# pylint:disable=unused-argument
def do_seek(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Simulate unix 6 seek call."""
    whence = c6tvm.pop()
    pos = c6tvm.pop()
    descriptor = c6tvm.pop()
    try:
        file = c6tvm.files[descriptor]
    except IndexError:
        return
    if file is None:
        return
    if not file.seekable():
        return
    if whence >= 3:
        whence -= 3
        pos *= 512
    try:
        host_whence = WHENCES[whence]
    except KeyError:
        return
    file.seek(pos, host_whence)


@addop("read", "write")
# pylint:disable=unused-argument
def do_rw(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Simulate a Unix6 read/write call."""
    count = c6tvm.pop()
    buffer = c6tvm.pop()
    descriptor = c6tvm.pop()
    try:
        file = c6tvm.files[descriptor]
    except IndexError:
        c6tvm.push(-1)
        return
    if file is None:
        c6tvm.push(-1)
        return
    match opcode:
        case "read":
            try:
                data = file.read(count)
            # pylint:disable=broad-except
            except BaseException:
                c6tvm.push(-1)
                return
            c6tvm.copy(buffer, data)
            c6tvm.push(len(data))
        case "write":
            data = c6tvm.grab(buffer, count)
            try:
                write_count = file.write(data)
            # pylint:disable=broad-except
            except BaseException:
                c6tvm.push(-1)
                return
            c6tvm.push(write_count)
        case _:
            raise ValueError(opcode)
    file.flush()


LDIV_HI = 0
LDIV_LO = 1


@addop("ldiv")
# pylint:disable=unused-argument
def do_ldiv(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Perform long division (simulates Unix6 C ldiv function)."""
    bot = c6tvm.pop()
    bot = c6tvm.fromword(c6tvm.toword(bot), signed=True)
    toplo = c6tvm.pop()
    tophi = c6tvm.pop()
    topbytes = c6tvm.toword(toplo) + c6tvm.toword(tophi)
    top = c6tvm.fromword(topbytes, signed=True)
    div = math.floor(top / bot)
    remain = math.floor(top % bot)
    c6tvm.push(div)
    c6tvm.push(remain)


@addop("swap")
# pylint:disable=unused-argument
def do_swap(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Swap bottom two elements on stack."""
    right = c6tvm.pop()
    left = c6tvm.pop()
    c6tvm.push(right)
    c6tvm.push(left)


def sign(i: int) -> Literal["+", "-"]:
    """Return the sign of the number."""
    return "-" if i < 0 else "+"


parser = ArgumentParser("vm")
parser.add_argument(
    "-d", dest="debug", default=False, action="store_true", help="enable debug"
)
parser.add_argument(
    "-s",
    metavar="SymTab",
    dest="symtab",
    type=str,
    default="",
    help="symbol table file",
)
parser.add_argument("prgname", type=str, help="program to exec")
parser.add_argument(
    "args",
    metavar="arg",
    type=str,
    nargs="*",
    help="arguments to the VM program (passed thru argc/argv)",
)


def main(args: list[str]) -> None:
    """Main program."""
    parsed = parser.parse_args(args)
    prg = Path(parsed.prgname).read_bytes()
    args = parsed.args
    VM(prg, parsed.debug, parsed.symtab).exec(
        parsed.prgname,
        *args,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
