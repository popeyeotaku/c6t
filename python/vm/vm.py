"""C6T VM"""

import math
import sys
from typing import Any, Callable, TextIO

OPNAMES: tuple[str, ...] = (
    "auto",
    "predec",
    "brz",
    "preinc",
    "load",
    "name",
    "call",
    "dropargs",
    "jmp",
    "retnull",
    "assign",
    "postinc",
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
)
OPCODES: dict[str, int] = {opname: opcode for opcode, opname in enumerate(OPNAMES)}
OPNUMS: dict[int, str] = {opnum: opname for opname, opnum in OPCODES.items()}
OPARGS: tuple[str, ...] = (
    "useregs",
    "auto",
    "predec",
    "brz",
    "auto",
    "preinc",
    "name",
    "dropargs",
    "jmp",
    "postinc",
    "grabreg",
    "putreg",
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


class VM:
    """C6T VM."""

    def __init__(self, program: bytes) -> None:
        self.mem = bytearray(0xFFFF + 1)
        self._prg = program
        self.regs = {reg: 0 for reg in REGS}
        self.stdout = sys.stdout

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

    def step(self) -> None:
        """Single step the VM."""
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


@addop("brz")
# pylint:disable=unused-argument
def do_brz(c6tvm: VM, opcode: str, args: list[int]) -> None:
    """Pop a word off the stack and branch to the arg if it equals 0."""
    arg = args[0]
    word = c6tvm.pop()
    if word == 0:
        c6tvm.regs["pc"] = arg


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
    c6tvm.regs["sp"] -= arg * 2
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
