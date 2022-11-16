"""C6T Backend for Intel 8080"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, auto
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Callable, Iterator, Type

from . import shared


class Reg(IntEnum):
    """An intel 8080 register pair."""

    HL = auto()
    DE = auto()


@dataclass(frozen=True)
class Node80:
    """An expression tree node for the Intel 8080 backend."""

    label: str
    left: Node80 | None = None
    right: Node80 | None = None
    value: str | int | float | None = None

    @property
    def children(self) -> list[Node80]:
        """A list of non-None children in the Node."""
        return [child for child in (self.left, self.right) if child]

    @cached_property
    def argcount(self) -> int:
        """Return the number of argument nodes recursively."""
        if self.label == "arg":
            return 1
        return sum((child.argcount for child in self.children))

    @classmethod
    def convert(cls, node: Node80 | shared.Node) -> Node80:
        """Convert recursively shared Backend nodes to our nodes, with
        appropriate other modifications.
        """
        if isinstance(node, Node80):
            return node
        label = node.label
        children = [Node80.convert(child) for child in node.children] + [None, None]
        value = node.value if isinstance(node.value, (int | str | float)) else None

        if label.startswith("asn") or label.startswith("casn"):
            if label.startswith("casn"):
                label = label.removeprefix("casn")
                code = "c"
            else:
                label = label.removeprefix("asn")
                code = ""
            # TODO: this should only evaluate the left side once, instead!
            right = shared.Node(
                label,
                [shared.Node(f"{code}load", [node.children[0]]), node.children[1]],
            )
            return Node80(f"{code}assign", children[0], cls.convert(right))

        match label:
            case "commute":
                children[1] = Node80("name", value=0xFFFF)
                label = "eor"
            case "neg":
                children[0] = Node80("eor", children[0], Node80("name", value=0xFFFF))
                children[1] = Node80("name", value=1)
                label = "add"
            case "con":
                label = "name"
            case "reg":
                label = "name"
                value = f"reg{value}"
            case "ucall":
                label = "call"
                value = 0
            case "call":
                assert children[1] is not None
                value = children[1].argcount
            case "not":
                label = "lognot"
            case "logand" | "logor":
                children = [Node80(label, children[0], children[1]), None]
                label = "log"
            case "equ" | "nequ":
                children = [Node80("sub", children[0], children[1])]
                label = "lognot" if label == "equ" else "log"
            case _:
                raise NotImplementedError
        return Node80(label, children[0], children[1], value)


class Cost(IntEnum):
    """The cost class of a codegen template."""

    HL = 1
    ANY = 2
    BINARY = 3
    SPECIAL = 4


@dataclass(frozen=True)
class NodeSpec:
    """A specification for a node to be used in a template."""

    label: str
    value: str | int | float | None = None

    @lru_cache
    def match(self, node: Node80 | None) -> bool:
        """Return a flag for if the node can match this specification."""
        if node is None:
            return False
        if node.label != self.label:
            return False
        if self.value is not None and self.value != node.value:
            return False
        return True

    @classmethod
    def fromstr(cls, source: str) -> NodeSpec:
        """Create a NodeSpec from a source string."""
        elems = [elem.strip() for elem in source.split(maxsplit=3)]
        try:
            label = elems[0].lower()
        except IndexError as error:
            raise ValueError(f"bad source string {repr(source)}") from error
        if len(elems) > 1:
            if len(elems) != 3:
                raise ValueError(f"bad source string {repr(source)}")
            valtype: Type[int] | Type[float] | Type[str]
            match elems[1]:
                case "i":
                    valtype = int
                case "f":
                    valtype = float
                case "s":
                    valtype = str
                case _:
                    raise ValueError(f"bad source string {repr(source)}")
            value = valtype(elems[2])
        else:
            value = None
        return NodeSpec(label, value)


@dataclass(frozen=True)
class Template:
    """An Intel 8080 codegen template."""

    node: NodeSpec
    code: str
    cost: Cost
    commutative: bool = False
    left: NodeSpec | None = None
    right: NodeSpec | None = None
    skip: tuple[bool, bool] = (False, False)

    @classmethod
    @lru_cache
    def _matchspec(
        cls, specs: tuple[NodeSpec | None, ...], nodes: tuple[Node80 | None, ...]
    ) -> bool:
        """Return a flag for if any non-None specs match their corresponding
        nodes.
        """
        for spec, node in zip(specs, nodes):
            if spec is not None:
                if not spec.match(node):
                    return False
        return True

    @lru_cache
    def match(self, node: Node80) -> bool:
        """Return a flag for if the node can match this specification."""
        if self.node != node:
            return False
        if self.commutative:
            flipped = self._matchspec((self.left, self.right), (node.right, node.left))
            return flipped or self._matchspec(
                (self.left, self.right), (node.left, node.right)
            )
        return self._matchspec((self.left, self.right), (node.left, node.right))

    @lru_cache
    def children(self, node: Node80) -> list[Node80]:
        """Return a list of the children who would need to be evaluated for
        this Node.

        Args:
            node (Node80): The node whose children should be returned

        Returns:
            list[Node80]: The children in question.
        """
        children = [node.left, node.right]
        if self.skip[0]:
            children[0] = None
        if self.skip[1]:
            children[1] = None
        return [child for child in children if child is not None]

    @classmethod
    def fromstr(cls, lines: list[str]) -> Template:
        """Construct a template from a list of lines."""
        if len(lines) != 5:
            raise ValueError(f"bad fromat for template {lines}")
        node = NodeSpec.fromstr(lines[0])
        cost = Cost[lines[1].split()[0].strip().upper()]
        flags = [elem.strip().casefold() for elem in lines[1].split()[1:]]
        commutative = "commute".casefold() in flags
        skipleft = "skipleft".casefold() in flags
        skipright = "skipright".casefold() in flags
        left = (
            None
            if lines[2].casefold() == "None".casefold()
            else NodeSpec.fromstr(lines[2])
        )
        right = (
            None
            if lines[3].casefold() == "None".casefold()
            else NodeSpec.fromstr(lines[3])
        )
        code = lines[4].replace("\\n", "\n")
        return Template(
            node, code, cost, commutative, left, right, (skipleft, skipright)
        )


class TemplateCollection:
    """A group of Templates which can be matched to Node80s."""

    TEMPLATE_LINES = 5

    def __iter__(self) -> Iterator[Template]:
        return iter(self._templates)

    def asdict(self) -> dict[str, list[Template]]:
        """Construct a dicitionary of templates."""
        tldict: dict[str, list[Template]] = {}
        for template in self:
            if template.node.label not in tldict:
                tldict[template.node.label] = []
            tldict[template.node.label].append(template)
        return tldict

    def __repr__(self) -> str:
        return self.__class__.__name__ + repr(self.templates)

    def __init__(self, *templates: Template) -> None:
        self._templates = templates

    @property
    def templates(self) -> tuple[Template, ...]:
        """All templates within the collection."""
        return self._templates

    @lru_cache
    def _select(self, func: Callable[[Template], bool]) -> tuple[Template, ...]:
        """Return a cached tuple of all templates which the function returns
        True on.

        Args:
            func (Callable[[Template], bool]): A filter function for templates.

        Returns:
            tuple[Template, ...]: The filtered templates.
        """
        return tuple((template for template in self.templates if func(template)))

    @lru_cache
    def _match_cost(self, node: Node80, cost: Cost) -> Template:
        """Match a Node80 with a particular Cost to the best possible template.

        Args:
            node (Node80): A node to be matched.
            cost (Cost): The cost requested.

        Raises:
            ValueError: No matching template found.

        Returns:
            Template: The template found.
        """
        templates = self._select(
            lambda t: t.label == node.label and t.cost == cost and t.match(node)
        )
        try:
            return templates[0]
        except IndexError as error:
            raise ValueError(
                f"no template for label {repr(node.label)} on cost {cost.name}"
            ) from error

    @lru_cache
    def match(self, node: Node80, reg: Reg = Reg.HL) -> Template:
        """Match the given node to a codegen template, trying to get it into
        the given register if possible.

        Args:
            node (Node80): The node to be matched
            reg (Reg, optional): The register we want it in. Defaults to
                                 Reg.HL.

        Raises:
            ValueError: No template found.

        Returns:
            Template: The matched template.
        """
        if reg == Reg.DE:
            costs = (Cost.ANY, Cost.HL, Cost.BINARY, Cost.SPECIAL)
        else:
            costs = (Cost.HL, Cost.ANY, Cost.BINARY, Cost.SPECIAL)
        for cost in costs:
            try:
                return self._match_cost(node, cost)
            except ValueError:
                continue
        raise ValueError(f"no matching template on node {repr(node)}")

    @lru_cache
    def cost(self, node: Node80, reg: Reg = Reg.HL) -> Cost:
        """Return the cost to compute the given node, recursively.

        Args:
            node (Node80): The node
            reg (Reg, optional): The register destination to be passed to
                                 self.match() -- ideally try to match a
                                 template that can put it here.
                                 Defaults to Reg.HL.

        Returns:
            Cost: The maximum of all ocsts.
        """
        template = self.match(node, reg)
        return max(
            template.cost, *(self.cost(child, reg) for child in template.children(node))
        )

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, TemplateCollection):
            return self.templates == __o.templates
        return False

    def __hash__(self) -> int:
        return hash(self.templates)

    @classmethod
    def fromstr(cls, source: str) -> TemplateCollection:
        """Construct a Template Collection from a string."""
        lines = source.splitlines(keepends=False)
        templates: list[Template] = []
        for i in range(0, len(lines), cls.TEMPLATE_LINES + 1):
            templates.append(Template.fromstr(lines[i : i + cls.TEMPLATE_LINES]))
        return TemplateCollection(*templates)


class Assembler:
    """A class which can accumulate assembly code."""

    def __init__(self) -> None:
        self._asmsrc = ""

    @property
    def asmsrc(self) -> str:
        """The assembler source text."""
        return self._asmsrc

    def asm(self, text: str) -> None:
        """Assemble one or more lines of text."""
        for line in text.splitlines():
            self._asmsrc += f"\t{line.strip()}"

    def deflabel(self, label: str) -> None:
        """Assemble a label definition."""
        self._asmsrc += f"{label}:"


class Evaluator:
    """Evaluates expression nodes."""

    def __init__(self, templates: TemplateCollection) -> None:
        self._templates = templates

    def asm(self, assembler: Assembler, node: Node80) -> None:
        """Assemble the given node recursively."""
        self._eval(assembler, node, Reg.HL)

    def _asmnode(
        self, assembler: Assembler, node: Node80, template: Template, reg: Reg
    ) -> None:
        """Assemble, nonrecursively, a single codegen template."""
        raise NotImplementedError

    def _special(self, assembler: Assembler, node: Node80, template: Template) -> None:
        """Assemble recursively a special codegen template."""
        raise NotImplementedError

    def _eval(self, assembler: Assembler, node: Node80, reg: Reg) -> None:
        """Assemble the node via the given assembler recursively, trying to
        get it into the given reg.
        """
        template = self._templates.match(node, reg)
        match template.cost:
            case Cost.HL:
                assert len(template.children(node)) <= 1
                assert reg == Reg.HL
                for child in template.children(node):
                    self._eval(assembler, child, reg)
                self._asmnode(assembler, node, template, reg)
            case Cost.ANY:
                assert len(template.children(node)) <= 1
                for child in template.children(node):
                    self._eval(assembler, child, reg)
                self._asmnode(assembler, node, template, reg)
            case Cost.SPECIAL:
                assert reg == Reg.HL
                self._special(assembler, node, template)
            case Cost.BINARY:
                assert reg == Reg.HL
                children = template.children(node)
                assert len(children) == 2
                cost = [self._templates.cost(child) for child in children]
                assert len(cost) == 2
                match tuple(cost):
                    case (Cost.HL, Cost.ANY) | (Cost.ANY, Cost.ANY):
                        self._eval(assembler, children[0], Reg.HL)
                        self._eval(assembler, children[1], Reg.DE)
                    case (Cost.HL, Cost.HL):
                        self._eval(assembler, children[1], Reg.HL)
                        assembler.asm("xchg")
                        self._eval(assembler, children[0], Reg.HL)
                    case (Cost.ANY, Cost.HL):
                        self._eval(assembler, children[1], Reg.HL)
                        self._eval(assembler, children[0], Reg.DE)
                        if not template.commutative:
                            assembler.asm("xchg")
                    case (Cost.BINARY, Cost.ANY) | (Cost.SPECIAL, Cost.ANY):
                        self._eval(assembler, children[0], Reg.HL)
                        self._eval(assembler, children[1], Reg.DE)
                    case (Cost.ANY, Cost.BINARY) | (Cost.ANY, Cost.SPECIAL):
                        self._eval(assembler, children[1], Reg.HL)
                        self._eval(assembler, children[0], Reg.DE)
                        if not template.commutative:
                            assembler.asm("xchg")
                    case (Cost.BINARY, Cost.HL) | (Cost.SPECIAL, Cost.HL):
                        self._eval(assembler, children[0], Reg.HL)
                        assembler.asm("xchg")
                        self._eval(assembler, children[1], Reg.HL)
                        if not template.commutative:
                            assembler.asm("xchg")
                    case (Cost.HL, Cost.BINARY) | (Cost.HL, Cost.SPECIAL):
                        self._eval(assembler, children[1], Reg.HL)
                        assembler.asm("xchg")
                        self._eval(assembler, children[0], Reg.HL)
                    case (Cost.BINARY, Cost.BINARY) | (Cost.SPECIAL, Cost.SPECIAL) | (
                        Cost.BINARY,
                        Cost.SPECIAL,
                    ) | (Cost.SPECIAL, Cost.BINARY):
                        self._eval(assembler, children[1], Reg.HL)
                        assembler.asm("push h")
                        self._eval(assembler, children[0], Reg.HL)
                        assembler.asm("pop d")
                    case _:
                        raise ValueError(
                            f"unsupported cost {cost}, this is probably a bug"
                        )
                self._asmnode(assembler, node, template, reg)
            case _:
                raise ValueError(f"bad cost {Template.cost}")


class Backend8080(shared.BackendABC[str], Assembler):
    """C6T Backend for Intel 8080."""

    def __init__(self, source: str, templates: TemplateCollection) -> None:
        super().__init__(source)
        self._templates = templates
        self._evaluator = Evaluator(self._templates)
        self._curstatic = 0

    @property
    def templates(self) -> TemplateCollection:
        """Return the collection of templates."""
        return self._templates

    def nextstatic(self) -> str:
        """Return the next static label."""
        self._curstatic += 1
        return f"LL{self._curstatic}"

    def eval(self, node: shared.Node | Node80) -> None:
        """Assemble a shared backend node.

        Args:
            node (shared.Node): The node to be assembled.
        """
        self._evaluator.asm(self, Node80.convert(node))

    def docmd(self, cmd: str, *args: Any) -> None:
        match cmd:
            case ".export":
                pass
            case "useregs":
                pass
            case "brz":
                assert isinstance(args[0], str)
                self.eval(
                    Node80("brz", Node80.convert(self.nodestk.pop()), value=args[0])
                )
            case "eval":
                self.eval(self.nodestk.pop())
            case "jmp":
                assert isinstance(args[0], str)
                self.asm(f"jmp {args[0]}")
            case "retnull":
                self.asm("ret")
            case "ret":
                self.eval(self.nodestk.pop())
                self.asm("ret")
            case ".text" | ".data" | ".bss" | ".string":
                self.asm(cmd)
            case ".dw" | ".db" | ".df" | ".dd":
                self.asm(f"{cmd} {','.join((str(arg) for arg in args))}")
            case "doswitch":
                raise NotImplementedError
            case ".common":
                self.asm(f"{cmd} {','.join((str(arg) for arg in args))}")
            case "dropstk":
                assert isinstance(args[0], int)
                self.asm(f"lxi h,{args[0]}\ndad sp\nsphl")
            case "goto":
                self.eval(self.nodestk.pop())
                self.asm("pchl")
            case _:
                raise ValueError(f"unsupported backend command {cmd}")

    def deflab(self, label: str) -> None:
        self.deflabel(label)

    def wrapup(self) -> str:
        return self.asmsrc + "\n"


class BackendFile(Backend8080):
    """Construct a backend from a given filename."""

    def __init__(self, source: str, template_path: Path | None = None) -> None:
        if template_path is None:
            template_path = Path("pyc6t", "backend", "i8080.templates")
        templates = TemplateCollection.fromstr(template_path.read_text("utf8"))
        super().__init__(source, templates)
