"""Leader identification and basic-block construction."""
from __future__ import annotations

from dataclasses import dataclass, field

from compiler.ir import CondJump, IRProgram, Jump, Label


@dataclass
class BasicBlock:
    id: int
    instructions: list = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"B{self.id}"

    @property
    def label(self) -> str | None:
        if self.instructions and isinstance(self.instructions[0], Label):
            return self.instructions[0].name
        return None

    @property
    def terminator(self):
        if self.instructions and isinstance(self.instructions[-1], (Jump, CondJump)):
            return self.instructions[-1]
        return None

    def to_text(self) -> str:
        return "\n".join(str(i) for i in self.instructions)


def find_leaders(ir: IRProgram) -> list[int]:
    """Indices of leader instructions.

    Leaders: the first instruction, every label (all jump targets are labels), and
    every instruction that follows a jump / conditional jump.
    """
    leaders: set[int] = set()
    n = len(ir.instructions)
    if n:
        leaders.add(0)
    for i, ins in enumerate(ir.instructions):
        if isinstance(ins, Label):
            leaders.add(i)
        if isinstance(ins, (Jump, CondJump)) and i + 1 < n:
            leaders.add(i + 1)
    return sorted(leaders)


def build_basic_blocks(ir: IRProgram) -> list[BasicBlock]:
    leaders = find_leaders(ir)
    blocks: list[BasicBlock] = []
    for k, start in enumerate(leaders):
        end = leaders[k + 1] if k + 1 < len(leaders) else len(ir.instructions)
        blocks.append(BasicBlock(k, list(ir.instructions[start:end])))
    return blocks
