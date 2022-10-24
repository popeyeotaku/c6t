"""C6T VM backend."""

from typing import Any

from .shared import BackendABC, Node


class BackendVM(BackendABC[str]):
    """C6T VM backend codegen."""

    def __init__(self, source: str) -> None:
        super().__init__(source)
        self._asm: str = ""

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

    def docmd(self, cmd: str, *args: Any) -> None:
        match cmd:
            case "eval":
                self.outnode(self.nodestk.pop())
            case "brz":
                self.outnode(
                    Node("brz", [self.nodestk.pop(), Node("name", value=args[0])])
                )
            case _:
                self.asm(cmd, *(str(arg) for arg in args))

    def outnode(self, node: Node) -> None:
        """Assemble a given node."""
        match node.label:
            case "call":
                raise NotImplementedError
            case _:
                for child in node.children:
                    self.outnode(child)
                if node.value is not None:
                    self.asm(node.label, node.value)
                else:
                    self.asm(node.label)
