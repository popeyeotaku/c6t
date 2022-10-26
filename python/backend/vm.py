"""C6T VM backend."""

from typing import Any

from .shared import BackendABC, Node

ASNOPS = ("asnmult", "asnadd", "asnor", "asnrshift", "asnsub", "asnand")


class BackendVM(BackendABC[str]):
    """C6T VM backend codegen."""

    def __init__(self, source: str) -> None:
        super().__init__(source)
        self._asm: str = ""
        self.curlab = 0

    def nextlab(self) -> str:
        """Return the next temporary label."""
        self.curlab += 1
        return f"LL{self.curlab}"

    def wrapup(self) -> str:
        return self._asm

    def asm(self, opcode: str, *operands: str) -> None:
        """Assemble a line of code."""
        line = f"\t{opcode}"
        if operands:
            line += " " + ",".join(operands)
        self._asm += line + "\n"

    def deflab(self, label: str) -> None:
        self._asm += f"{label}:"

    def doswitch(
        self, tablelen: Node, tablelab: Node, deflab: Node, expr: Node
    ) -> None:
        """Handle a switch statement."""
        self.outnode(deflab)
        self.outnode(tablelab)
        self.outnode(tablelen)
        self.outnode(expr)
        self.asm("jmp", "doswitch")

    def docmd(self, cmd: str, *args: Any) -> None:
        match cmd:
            case "goto":
                self.outnode(self.nodestk.pop())
                self.asm("stkjmp")
            case "doswitch":
                switchlen = self.nodestk.pop()
                switchdef = self.nodestk.pop()
                switchtable = self.nodestk.pop()
                switchexpr = self.nodestk.pop()
                self.doswitch(switchlen, switchdef, switchtable, switchexpr)
            case "ret":
                self.outnode(self.nodestk.pop())
                self.asm("ret")
            case "eval":
                self.outnode(self.nodestk.pop())
                self.asm("drop")
            case "brz":
                self.outnode(Node("brz", [self.nodestk.pop()], value=args[0]))
            case _:
                self.asm(cmd, *(str(arg) for arg in args))

    def callargs(self, node: Node) -> list[Node]:
        """Return a list of all arguments of a call.

        Call with callargs(node.children[1]), where [1] is the children node.
        """
        match node.label:
            case "null":
                return []
            case "arg":
                children = []
                for child in node.children:
                    children.extend(self.callargs(child))
                return children
            case _:
                return [node]

    def outnode(self, node: Node) -> None:
        """Assemble a given node."""
        if node.label in ASNOPS or node.label in (("c" + asnop for asnop in ASNOPS)):
            label = node.label
            if label[0] == "c":
                label = label[1:]
                mode = "c"
            else:
                mode = ""
            operator = label.removeprefix("asn")
            addr = node[0]
            mod = node[1]
            if addr.label == "reg":
                nodeasn = Node(
                    "assign", [addr, Node(operator, [Node("load", [addr]), mod])]
                )
                self.outnode(nodeasn)
            else:
                self.outnode(addr)
                self.asm("dup")
                self.outnode(mod)
                self.asm(operator)
                self.asm(f"{mode}assign")
            return
        if (
            node.label in ("load", "cload", "assign", "cassign")
            and node[0].label == "reg"
        ):
            match node.label:
                case "load" | "cload":
                    self.asm("grabreg", str(node[0].value))
                case "assign" | "cassign":
                    self.outnode(node[1])
                    self.asm("putreg", str(node[0].value))
                case _:
                    raise ValueError("bad node with reg child", node.label)
            return
        match node.label:
            case "logand" | "logor":
                branch = "brz" if node.label == "logand" else "bnz"
                lab = self.nextlab()
                self.outnode(node[0])
                self.asm("log")
                self.asm("dup")
                self.asm(branch, lab)
                self.asm("drop")
                self.outnode(node[1])
                self.asm("log")
                self.deflab(lab)
            case "reg":
                raise ValueError("illegal context for reg")
            case "null":
                pass
            case "arg":
                raise ValueError("shouldn't get a raw arg node", node)
            case "call" | "ucall":
                args: list[Node]
                if node.label == "ucall":
                    args = []
                else:
                    args = self.callargs(node.children[1])
                for arg in reversed(args):
                    self.outnode(arg)
                self.outnode(node[0])
                self.asm("call")
                self.asm("dropargs", str(len(args)))  # Doesnt support floating
            case "preinc" | "predec" | "postinc" | "postdec":
                assert node[1].label == "con"
                assert isinstance(node[1].value, int)
                if node[0].label == "reg":
                    self.asm(f"reg{node.label}", str(node[0].value), str(node[1].value))
                else:
                    self.outnode(node[0])
                    self.asm(node.label, str(node[1].value))
            case _:
                for child in node.children:
                    self.outnode(child)
                if node.value is not None:
                    self.asm(node.label, str(node.value))
                else:
                    self.asm(node.label)
