"""IR -> C code generation, plus safe GCC compilation / execution helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from compiler.ir import (Assign, BinOp, CondJump, Const, IRProgram, Jump, Label, Print, UnOp,
                         Var, value_type)
from config import settings

C_PRELUDE = r"""#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

/* Runtime helpers: OptiWeave defines division by zero as a runtime error. */
static long long ow_div_i(long long a, long long b) {
    if (b == 0) { fprintf(stderr, "runtime error: division by zero\n"); exit(1); }
    if (b == -1) return (long long)(0ULL - (unsigned long long)a);
    return a / b;
}
static long long ow_mod_i(long long a, long long b) {
    if (b == 0) { fprintf(stderr, "runtime error: modulo by zero\n"); exit(1); }
    if (b == -1) return 0;
    return a % b;
}
static double ow_div_f(double a, double b) {
    if (b == 0.0) { fprintf(stderr, "runtime error: division by zero\n"); exit(1); }
    return a / b;
}
static void ow_print_bool(bool v) { puts(v ? "true" : "false"); }
"""

C_TYPES = {"int": "long long", "float": "double", "bool": "bool"}


class CodeGenerator:
    """Translates an :class:`IRProgram` into a standalone C11 program."""

    def __init__(self, ir: IRProgram) -> None:
        self.ir = ir

    # -- operand rendering ---------------------------------------------------------------
    def _type_of(self, op) -> str:
        if isinstance(op, Const):
            return value_type(op.value)
        return self.ir.var_types.get(op.name, "int")

    def _operand(self, op) -> str:
        if isinstance(op, Var):
            return op.name
        v = op.value
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, float):
            text = repr(v)
            return f"({text})" if v < 0 else text
        return f"({v}LL)" if v < 0 else f"{v}LL"

    def _binop(self, ins: BinOp) -> str:
        l, r = self._operand(ins.left), self._operand(ins.right)
        both_int = self._type_of(ins.left) == "int" and self._type_of(ins.right) == "int"
        if ins.op == "/":
            return f"ow_div_i({l}, {r})" if both_int else f"ow_div_f({l}, {r})"
        if ins.op == "%":
            return f"ow_mod_i({l}, {r})"
        return f"{l} {ins.op} {r}"

    def _print(self, ins: Print) -> str:
        t = self._type_of(ins.src)
        v = self._operand(ins.src)
        if t == "bool":
            return f"ow_print_bool({v});"
        if t == "float":
            return f'printf("%.6f\\n", (double)({v}));'
        return f'printf("%lld\\n", (long long)({v}));'

    # -- program -------------------------------------------------------------------------
    def generate(self) -> str:
        lines = [C_PRELUDE, "int main(void) {"]
        for name in sorted(self.ir.var_types):
            ctype = C_TYPES[self.ir.var_types[name]]
            init = "false" if ctype == "bool" else ("0.0" if ctype == "double" else "0")
            lines.append(f"    {ctype} {name} = {init};")
        lines.append("")
        for ins in self.ir.instructions:
            if isinstance(ins, Label):
                lines.append(f"{ins.name}:;")
            elif isinstance(ins, Assign):
                lines.append(f"    {ins.dst} = {self._operand(ins.src)};")
            elif isinstance(ins, BinOp):
                lines.append(f"    {ins.dst} = {self._binop(ins)};")
            elif isinstance(ins, UnOp):
                lines.append(f"    {ins.dst} = {ins.op}{self._operand(ins.src)};")
            elif isinstance(ins, Jump):
                lines.append(f"    goto {ins.target};")
            elif isinstance(ins, CondJump):
                lines.append(f"    if ({self._operand(ins.cond)}) goto {ins.true_target}; "
                             f"else goto {ins.false_target};")
            elif isinstance(ins, Print):
                lines.append(f"    {self._print(ins)}")
        lines.append("    return 0;")
        lines.append("}")
        return "\n".join(lines) + "\n"


def generate_c(ir: IRProgram) -> str:
    return CodeGenerator(ir).generate()


# -- GCC integration ---------------------------------------------------------------------
def find_gcc() -> str | None:
    """Locate GCC: $OPTIWEAVE_GCC first, then PATH."""
    override = os.environ.get(settings.GCC_ENV_VAR)
    if override and Path(override).exists():
        return override
    return shutil.which("gcc")


GCC_INSTALL_HELP = (
    "GCC was not found. On Windows install MSYS2 (https://www.msys2.org), run "
    "'pacman -S mingw-w64-ucrt-x86_64-gcc' in the UCRT64 shell, then add "
    "C:\\msys64\\ucrt64\\bin to PATH (or set OPTIWEAVE_GCC to the full gcc.exe path) "
    "and verify with 'gcc --version'."
)


@dataclass
class CompileResult:
    ok: bool
    exe_path: Path | None = None
    stderr: str = ""
    compile_time_s: float = 0.0
    message: str = ""


@dataclass
class RunResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    times_s: list = field(default_factory=list)
    timed_out: bool = False

    @property
    def median_time_s(self) -> float | None:
        if not self.times_s:
            return None
        s = sorted(self.times_s)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def compile_c(c_source: str, workdir: str | Path, stem: str = "program",
              timeout: float = settings.COMPILE_TIMEOUT_S) -> CompileResult:
    """Compile C source with GCC (-O0). Never uses a shell."""
    gcc = find_gcc()
    if gcc is None:
        return CompileResult(False, message=GCC_INSTALL_HELP)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    c_path = workdir / f"{stem}.c"
    exe_path = workdir / (f"{stem}.exe" if os.name == "nt" else stem)
    c_path.write_text(c_source, encoding="utf-8")
    cmd = [gcc, *settings.GCC_FLAGS, str(c_path), "-o", str(exe_path)]
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=False)
    except subprocess.TimeoutExpired:
        return CompileResult(False, message=f"GCC timed out after {timeout}s")
    except OSError as exc:
        return CompileResult(False, message=f"Could not launch GCC: {exc}")
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        return CompileResult(False, stderr=proc.stderr, compile_time_s=elapsed,
                             message="GCC reported errors")
    return CompileResult(True, exe_path, proc.stderr, elapsed, "OK")


def run_executable(exe_path: str | Path, repeats: int = 1,
                   timeout: float = settings.RUN_TIMEOUT_S) -> RunResult:
    """Run a compiled program ``repeats`` times, timing each run with perf_counter."""
    result = RunResult(ok=True)
    for i in range(max(1, repeats)):
        start = time.perf_counter()
        try:
            proc = subprocess.run([str(exe_path)], capture_output=True, text=True,
                                  timeout=timeout, shell=False)
        except subprocess.TimeoutExpired:
            return RunResult(ok=False, stderr=f"Timed out after {timeout}s", timed_out=True,
                             times_s=result.times_s)
        except OSError as exc:
            return RunResult(ok=False, stderr=f"Could not run program: {exc}")
        elapsed = time.perf_counter() - start
        result.times_s.append(elapsed)
        if i == 0:
            result.stdout, result.stderr, result.returncode = proc.stdout, proc.stderr, proc.returncode
        if proc.returncode != 0:
            result.ok = False
            result.stdout, result.stderr, result.returncode = proc.stdout, proc.stderr, proc.returncode
            return result
    return result


def compile_and_run(c_source: str, repeats: int = 1) -> tuple[CompileResult, RunResult | None]:
    """Compile in a throw-away temporary directory and run once (or ``repeats`` times)."""
    with tempfile.TemporaryDirectory(prefix="optiweave_") as tmp:
        comp = compile_c(c_source, tmp)
        if not comp.ok:
            return comp, None
        return comp, run_executable(comp.exe_path, repeats)
