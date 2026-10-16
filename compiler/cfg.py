"""Control-flow graph with dominators and natural-loop back-edge detection."""
from __future__ import annotations

from dataclasses import dataclass, field

from compiler.basic_blocks import BasicBlock, build_basic_blocks
from compiler.ir import CondJump, IRProgram, Jump
from utils.exceptions import IRError


@dataclass
class CFG:
    blocks: list[BasicBlock]
    successors: dict[int, list[int]] = field(default_factory=dict)
    predecessors: dict[int, list[int]] = field(default_factory=dict)

    # -- construction --------------------------------------------------------------
    @classmethod
    def build(cls, ir: IRProgram) -> "CFG":
        blocks = build_basic_blocks(ir)
        label_to_block = {b.label: b.id for b in blocks if b.label}
        succ = {b.id: [] for b in blocks}
        pred = {b.id: [] for b in blocks}

        def add(src: int, dst: int) -> None:
            if dst not in succ[src]:
                succ[src].append(dst)
                pred[dst].append(src)

        def target(label: str) -> int:
            if label not in label_to_block:
                raise IRError(f"Jump to undefined label {label}")
            return label_to_block[label]

        for b in blocks:
            term = b.terminator
            if isinstance(term, Jump):
                add(b.id, target(term.target))
            elif isinstance(term, CondJump):
                add(b.id, target(term.true_target))
                add(b.id, target(term.false_target))
            elif b.id + 1 < len(blocks):
                add(b.id, b.id + 1)  # fall-through
        return cls(blocks, succ, pred)

    # -- queries -------------------------------------------------------------------
    @property
    def entry(self) -> int | None:
        return self.blocks[0].id if self.blocks else None

    @property
    def edges(self) -> list[tuple[int, int]]:
        return [(s, d) for s in sorted(self.successors) for d in self.successors[s]]

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def reachable(self) -> set[int]:
        if self.entry is None:
            return set()
        seen, stack = set(), [self.entry]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.successors[n])
        return seen

    def dominators(self) -> dict[int, set[int]]:
        """Iterative dominator computation over the reachable subgraph."""
        reach = self.reachable()
        if not reach:
            return {}
        dom = {n: set(reach) for n in reach}
        dom[self.entry] = {self.entry}
        changed = True
        while changed:
            changed = False
            for n in sorted(reach):
                if n == self.entry:
                    continue
                preds = [p for p in self.predecessors[n] if p in reach]
                new = set(reach)
                for p in preds:
                    new &= dom[p]
                new |= {n}
                if new != dom[n]:
                    dom[n] = new
                    changed = True
        return dom

    def back_edges(self) -> list[tuple[int, int]]:
        """Edges (tail -> header) where the header dominates the tail (natural loops)."""
        dom = self.dominators()
        return [(s, d) for (s, d) in self.edges
                if s in dom and d in dom[s]]

    # -- export --------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "blocks": [{"id": b.name, "instructions": [str(i) for i in b.instructions]}
                       for b in self.blocks],
            "edges": [[f"B{s}", f"B{d}"] for s, d in self.edges],
            "back_edges": [[f"B{s}", f"B{d}"] for s, d in self.back_edges()],
        }

    def to_dot(self) -> str:
        """Graphviz DOT source (renderable without Graphviz installed, e.g. by Streamlit)."""
        back = set(self.back_edges())
        lines = ["digraph CFG {", '  node [shape=box, fontname="Consolas", fontsize=10];']
        for b in self.blocks:
            body = "\\l".join(str(i).replace('"', "'") for i in b.instructions) + "\\l"
            lines.append(f'  {b.name} [label="{b.name}\\n{body}"];')
        for s, d in self.edges:
            style = ' [color=red, label="back"]' if (s, d) in back else ""
            lines.append(f"  B{s} -> B{d}{style};")
        lines.append("}")
        return "\n".join(lines)


def build_cfg(ir: IRProgram) -> CFG:
    return CFG.build(ir)
