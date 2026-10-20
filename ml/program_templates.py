"""Parameterised OptiWeave program families used to build the benchmark corpus.

Each category has five *families* (distinct program shapes). A family function takes a
seeded ``random.Random`` and returns source text, so the two variants of a family share
structure but differ in constants, sizes and statement counts. Families are the unit of
grouping for leakage-free evaluation.

Categories added for strategy diversity:
  - algebraic-heavy: programs with strength-reduction / algebraic simplification
    opportunities (favour S7/S8)
  - copy-heavy: programs with copy propagation opportunities (favour S9)
  - propagation-only: programs where CF+CP suffice and DCE/CSE add nothing (favour S2)
"""
from __future__ import annotations

import random
from typing import Callable


def _j(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ arithmetic-heavy
def arith_f1(r: random.Random) -> str:
    n = r.randint(3, 6)
    L = [f"int v0 = {r.randint(2, 20)};", f"int v1 = {r.randint(2, 20)};"]
    for k in range(2, n + 2):
        a, b = r.sample(range(k), 2)
        op = r.choice("+-+*")
        L.append(f"int v{k} = v{a} {op} v{b} + {r.randint(1, 9)};")
    L += [f"print(v{n + 1});", f"print(v{n} % {r.randint(2, 9)});", f"print(v{n} / {r.randint(2, 5)});"]
    return _j(L)


def arith_f2(r: random.Random) -> str:
    n = r.randint(20, 60)
    bound = "n" if r.random() < 0.5 else str(n)
    L = [f"int n = {n};", "int i = 0;", "int acc = 0;", f"while (i < {bound}) {{",
         f"    acc = acc + i * {r.randint(2, 7)} + {r.randint(1, 9)} * i - {r.randint(1, 5)};"]
    if r.random() < 0.5:
        L.append(f"    acc = acc % {r.randint(1000, 9000)};")
    L += ["    i = i + 1;", "}", "print(acc);"]
    return _j(L)


def arith_f3(r: random.Random) -> str:
    n = r.randint(8, 25)
    L = [f"float x = {r.randint(1, 4)}.5;", "int i = 0;", f"while (i < {n}) {{",
         f"    x = x * 1.25 + i - {r.randint(1, 3)}.5;", "    i = i + 1;", "}", "print(x);"]
    if r.random() < 0.5:
        L.append("print(x / 2.0);")
    return _j(L)


def arith_f4(r: random.Random) -> str:
    n = r.randint(15, 50)
    L = ["int i = 0;", "int acc = 0;", f"while (i < {n}) {{"]
    for k in range(r.randint(2, 4)):
        L.append(f"    int junk{k} = i * {r.randint(2, 9)} + {r.randint(1, 9)};")
    L += [f"    acc = acc + i * {r.randint(2, 5)};", "    i = i + 1;", "}", "print(acc);"]
    return _j(L)


def arith_f5(r: random.Random) -> str:
    n = r.randint(1000, 999999)
    L = [f"int n = {n};", "int s = 0;", "while (n > 0) {", "    s = s + n % 10;", "    n = n / 10;", "}", "print(s);"]
    if r.random() < 0.5:
        L.append(f"print(s * {r.randint(2, 5)} + {r.randint(1, 9)});")
    return _j(L)


# ------------------------------------------------------------------ loop-heavy
def loop_f1(r: random.Random) -> str:
    n = r.randint(30, 120)
    L = ["int s = 0;", "int i = 1;", f"while (i <= {n}) {{", "    s = s + i;"]
    if r.random() < 0.5:
        L.append("    s = s + 1;")
    L += [f"    i = i + {r.randint(1, 3)};", "}", "print(s);"]
    return _j(L)


def loop_f2(r: random.Random) -> str:
    a, b = r.randint(5, 14), r.randint(5, 14)
    L = ["int total = 0;", "int i = 0;", f"while (i < {a}) {{", "    int j = 0;", f"    while (j < {b}) {{",
         "        total = total + i * j;", "        j = j + 1;", "    }", "    i = i + 1;", "}", "print(total);"]
    return _j(L)


def loop_f3(r: random.Random) -> str:
    step = r.randint(1, 4)
    L = [f"int n = {r.randint(40, 150)};", "int acc = 0;", "while (n > 0) {", "    acc = acc + n;",
         f"    n = n - {step};", "}", "print(acc);"]
    return _j(L)


def loop_f4(r: random.Random) -> str:
    n = r.randint(10, 40)
    L = ["int a = 0;", "int b = 1;", "int k = 0;", f"while (k < {n}) {{", "    int next = a + b;", "    a = b;",
         "    b = next;", "    k = k + 1;", "}", "print(a);"]
    return _j(L)


def loop_f5(r: random.Random) -> str:
    c, c2, n = r.randint(2, 9), r.randint(2, 9), r.randint(20, 80)
    L = [f"int k = {c};", "int i = 0;", "int s = 0;", f"while (i < {n}) {{", f"    int w = k * {c2};",
         "    s = s + w;", "    i = i + 1;", "}", "print(s);"]
    return _j(L)


# ------------------------------------------------------------------ branch-heavy
def branch_f1(r: random.Random) -> str:
    n, m1, m2 = r.randint(20, 80), r.randint(2, 4), r.randint(5, 7)
    L = ["int a = 0;", "int b = 0;", "int c = 0;", "int i = 0;", f"while (i < {n}) {{",
         f"    if (i % {m1} == 0) {{", "        a = a + 1;", f"    }} else {{", f"        if (i % {m2} == 0) {{",
         "            b = b + 1;", "        } else {", "            c = c + 1;", "        }", "    }",
         "    i = i + 1;", "}", "print(a);", "print(b);", "print(c);"]
    return _j(L)


def branch_f2(r: random.Random) -> str:
    L = ["bool debug = false;", f"int mode = {r.randint(1, 5)};", "if (debug) {", f"    print({r.randint(100, 999)});",
         "} else {", f"    if (mode > {r.randint(1, 4)}) {{", f"        print(mode * {r.randint(2, 9)});", "    } else {",
         f"        print(mode + {r.randint(2, 9)});", "    }", "}"]
    if r.random() < 0.5:
        L += ["if (true) {", "    print(mode);", "}"]
    return _j(L)


def branch_f3(r: random.Random) -> str:
    a, b, c = (r.randint(1, 99) for _ in range(3))
    L = [f"int a = {a};", f"int b = {b};", f"int c = {c};", "int m = a;", "if (b > m) {", "    m = b;", "}",
         "if (c > m) {", "    m = c;", "}", "print(m);"]
    if r.random() < 0.5:
        L += ["if (a == b) {", "    print(1);", "} else {", "    print(0);", "}"]
    return _j(L)


def branch_f4(r: random.Random) -> str:
    n = r.randint(15, 60)
    L = ["int i = 0;", "int hits = 0;", f"while (i < {n}) {{",
         f"    if (i > {r.randint(2, 6)} && i < {r.randint(20, 40)} || i == {r.randint(1, 9)}) {{",
         "        hits = hits + 1;", "    }", "    i = i + 1;", "}", "print(hits);"]
    return _j(L)


def branch_f5(r: random.Random) -> str:
    n = r.randint(10, 40)
    L = ["int i = 0;", "int even = 0;", f"while (i < {n}) {{", "    int tag = 0;", "    if (i % 2 == 0) {",
         "        even = even + 1;", f"        tag = i * {r.randint(2, 5)};", "    } else {", f"        tag = i + {r.randint(1, 9)};",
         "    }", "    i = i + 1;", "}", "print(even);"]
    return _j(L)


# ------------------------------------------------------------------ constant-heavy
def const_f1(r: random.Random) -> str:
    L = []
    for k in range(r.randint(3, 6)):
        L.append(f"int a{k} = {r.randint(1, 9)} * {r.randint(2, 9)} + ({r.randint(5, 20)} - {r.randint(1, 4)}) * {r.randint(1, 4)};")
    L.append("print(" + " + ".join(f"a{k}" for k in range(len(L))) + ");")
    return _j(L)


def const_f2(r: random.Random) -> str:
    L = [f"float p = {r.randint(1, 9)}.5 * 2.0;", f"float q = p + {r.randint(1, 9)}.25 - 1.0;", "float z = q * p;",
         "print(z);", f"print(p / {r.randint(2, 4)}.0);"]
    return _j(L)


def const_f3(r: random.Random) -> str:
    a, b = r.randint(1, 9), r.randint(1, 9)
    L = [f"bool p = {a} < {b + 3};", f"bool q = p && !({a + 2} > {b + 9});", "if (q) {", "    print(1);", "} else {",
         "    print(0);", "}", f"bool w = (p == q) || {a} == {b};", "if (w) {", "    print(2);", "}"]
    return _j(L)


def const_f4(r: random.Random) -> str:
    n = r.randint(4, 8)
    L = [f"int x1 = {r.randint(2, 9)};"]
    for k in range(2, n + 1):
        L.append(f"int x{k} = x{k - 1} {r.choice('+*')} {r.randint(2, 5)};")
    L.append(f"print(x{n});")
    return _j(L)


def const_f5(r: random.Random) -> str:
    n = r.randint(15, 50)
    L = ["int i = 0;", "int acc = 0;", f"while (i < {n}) {{",
         f"    acc = acc + {r.randint(2, 6)} * {r.randint(2, 6)} + {r.randint(1, 9)};", "    i = i + 1;", "}", "print(acc);"]
    return _j(L)


# ------------------------------------------------------------------ redundant-expression-heavy
def red_f1(r: random.Random) -> str:
    n = r.randint(10, 40)
    L = ["int x = 1;", "int y = 2;", "int i = 0;", "int out = 0;", f"while (i < {n}) {{", "    int p = x + y;",
         "    int q = x + y;", f"    out = out + p * q + (x + y) * {r.randint(2, 5)};", "    x = x + 1;", "    y = y + 2;",
         "    i = i + 1;", "}", "print(out);"]
    return _j(L)


def red_f2(r: random.Random) -> str:
    n = r.randint(10, 40)
    L = ["int i = 0;", "int j = 3;", "int k = 5;", "int total = 0;", f"while (i < {n}) {{", "    int p = i * i + j;",
         "    int q = i * i + k;"]
    if r.random() < 0.5:
        L.append("    int r2 = i * i + j;")
        L.append("    total = total + r2;")
    L += ["    total = total + p + q;", "    i = i + 1;", "}", "print(total);"]
    return _j(L)


def red_f3(r: random.Random) -> str:
    n = r.randint(10, 30)
    L = ["int x = 2;", "int y = 3;", "int i = 0;", "int s = 0;", f"while (i < {n}) {{", "    int a = x * y;", "    int b = x * y;",
         "    x = x + 1;", "    int c = x * y;", "    s = s + a + b + c;", "    i = i + 1;", "}", "print(s);"]
    return _j(L)


def red_f4(r: random.Random) -> str:
    n = r.randint(10, 40)
    L = ["int a = 1;", "int b = 2;", "int i = 0;", "int s = 0;", f"while (i < {n}) {{", "    int u = a * b + i;",
         "    int v = b * a + i;", "    s = s + u - v + u;", "    a = a + 1;", "    i = i + 1;", "}", "print(s);"]
    return _j(L)


def red_f5(r: random.Random) -> str:
    n = r.randint(10, 40)
    L = ["int i = 0;", "int s = 0;", f"while (i < {n}) {{", f"    if (i % 2 == 0) {{", f"        s = s + (i * {r.randint(2, 5)} + 1);",
         "    } else {", f"        s = s - (i * {r.randint(2, 5)} + 1);", "    }", "    i = i + 1;", "}", "print(s);"]
    return _j(L)


# ------------------------------------------------------------------ mixed
def mixed_f1(r: random.Random) -> str:
    n = r.randint(15, 50)
    L = ["int i = 0;", "int s = 0;", "int scale = " + str(r.randint(2, 6)) + ";", f"while (i < {n}) {{", "    int p = i * scale + 1;",
         "    int q = i * scale + 1;", "    int unused = i - 7;", "    if (p % 3 == 0) {", "        s = s + p;", "    } else {",
         "        s = s + q * 2;", "    }", "    i = i + 1;", "}", "print(s);"]
    return _j(L)


def mixed_f2(r: random.Random) -> str:
    a, b = r.randint(4, 12), r.randint(4, 12)
    L = ["int i = 0;", "int hits = 0;", f"while (i < {a}) {{", "    int j = 0;", f"    while (j < {b}) {{", "        if (i < j) {",
         "            hits = hits + i + j;", "        }", "        j = j + 1;", "    }", "    i = i + 1;", "}", "print(hits);"]
    return _j(L)


def mixed_f3(r: random.Random) -> str:
    n = r.randint(10, 40)
    L = ["int i = 2;", "int count = 0;", f"while (i < {n}) {{", "    int j = 2;", "    bool prime = true;", "    while (j * j <= i) {",
         "        if (i % j == 0) {", "            prime = false;", "        }", "        j = j + 1;", "    }", "    if (prime) {",
         "        count = count + 1;", "    }", "    i = i + 1;", "}", "print(count);"]
    return _j(L)


def mixed_f4(r: random.Random) -> str:
    L = [f"int n = {r.randint(5, 60)};", "int steps = 0;", "while (n != 1 && steps < 200) {", "    if (n % 2 == 0) {", "        n = n / 2;",
         "    } else {", "        n = 3 * n + 1;", "    }", "    steps = steps + 1;", "}", "print(steps);"]
    return _j(L)


def mixed_f5(r: random.Random) -> str:
    n = r.randint(10, 30)
    L = ["float total = 0.0;", "int i = 0;", f"float rate = {r.randint(1, 4)}.5;", f"while (i < {n}) {{", "    float part = rate * i + 1.0;",
         "    if (part > 10.0) {", "        total = total + part / 2.0;", "    } else {", "        total = total + part;", "    }",
         "    i = i + 1;", "}", "print(total);"]
    return _j(L)


# ------------------------------------------------------------------ algebraic-heavy (favour S7/S8)
def alg_f1(r: random.Random) -> str:
    """Multiply-by-2, add-0, multiply-by-1 patterns in a loop."""
    n = r.randint(15, 50)
    L = ["int i = 0;", "int acc = 0;", f"while (i < {n}) {{",
         "    int a = i * 2;",           # SR: i + i
         "    int b = a + 0;",           # SR: b = a
         "    int c = b * 1;",           # SR: c = b
         "    acc = acc + c;",
         "    i = i + 1;", "}", "print(acc);"]
    return _j(L)


def alg_f2(r: random.Random) -> str:
    """Self-cancellation and multiply-by-zero."""
    L = [f"int x = {r.randint(10, 99)};", f"int y = {r.randint(10, 99)};",
         "int zero = x - x;",            # SR: zero = 0
         "int also_zero = y * 0;",        # SR: also_zero = 0
         f"int keep = x * 1 + {r.randint(1, 9)};",  # SR: keep = x + ...
         "print(zero);", "print(also_zero);", "print(keep);"]
    return _j(L)


def alg_f3(r: random.Random) -> str:
    """Division by 1 and subtract-zero chains."""
    n = r.randint(3, 7)
    L = [f"int v0 = {r.randint(5, 30)};"]
    for k in range(1, n + 1):
        op = r.choice(["/ 1", "- 0", "* 1", "+ 0"])
        L.append(f"int v{k} = v{k - 1} {op};")
    L.append(f"print(v{n});")
    return _j(L)


def alg_f4(r: random.Random) -> str:
    """Mix of multiply-by-2 and real arithmetic in a loop."""
    n = r.randint(10, 40)
    L = ["int i = 0;", "int s = 0;", f"while (i < {n}) {{",
         f"    int doubled = i * 2;",
         f"    int tripled = i * {r.randint(3, 7)};",
         "    s = s + doubled + tripled;",
         "    i = i + 1;", "}", "print(s);"]
    return _j(L)


def alg_f5(r: random.Random) -> str:
    """Nested algebraic identities with all used variables."""
    a, b = r.randint(2, 20), r.randint(2, 20)
    L = [f"int a = {a};", f"int b = {b};",
         "int p = a * 2;",                 # SR: a + a
         "int q = b * 1;",                 # SR: q = b
         "int r1 = p + 0;",                # SR: r1 = p
         "int s = r1 - 0;",                # SR: s = r1
         "int t = q / 1;",                 # SR: t = q
         "print(p);", "print(q);", "print(r1);", "print(s);", "print(t);"]
    return _j(L)


# ------------------------------------------------------------------ copy-heavy (favour S9)
def copy_f1(r: random.Random) -> str:
    """Chains of variable copies, all eventually used."""
    n = r.randint(3, 6)
    L = [f"int src = {r.randint(10, 99)};"]
    for k in range(n):
        L.append(f"int c{k} = {'src' if k == 0 else f'c{k - 1}'};")
    L.append(f"print(c{n - 1});")
    L.append("print(src);")
    return _j(L)


def copy_f2(r: random.Random) -> str:
    """Copy inside a loop with accumulation."""
    n = r.randint(10, 40)
    L = ["int i = 0;", "int val = 5;", "int acc = 0;", f"while (i < {n}) {{",
         "    int tmp = val;",
         "    acc = acc + tmp;",
         "    i = i + 1;", "}", "print(acc);"]
    return _j(L)


def copy_f3(r: random.Random) -> str:
    """Multiple copies from different sources."""
    a, b = r.randint(1, 50), r.randint(1, 50)
    L = [f"int x = {a};", f"int y = {b};",
         "int cx = x;", "int cy = y;",
         "int sum1 = cx + cy;",
         "int dx = cx;", "int dy = cy;",
         "int sum2 = dx + dy;",
         "print(sum1);", "print(sum2);"]
    return _j(L)


def copy_f4(r: random.Random) -> str:
    """Copies with branching."""
    v = r.randint(1, 50)
    L = [f"int x = {v};", "int c = x;",
         f"if (c > {r.randint(10, 30)}) {{",
         "    int d = c;", "    print(d);",
         "} else {", "    int e = c;", "    print(e);", "}"]
    return _j(L)


def copy_f5(r: random.Random) -> str:
    """Copy chain in a loop with conditional use."""
    n = r.randint(10, 30)
    L = ["int i = 0;", "int base = 7;", "int total = 0;", f"while (i < {n}) {{",
         "    int a = base;", "    int b = a;",
         "    if (i % 2 == 0) {", "        total = total + b;",
         "    } else {", "        total = total + a;", "    }",
         "    i = i + 1;", "}", "print(total);"]
    return _j(L)


# ------------------------------------------------------------------ propagation-only (favour S2)
def prop_f1(r: random.Random) -> str:
    """Constant chains: CP helps, DCE/CSE do nothing because all vars are used."""
    a = r.randint(2, 9)
    L = [f"int a = {a};",
         f"int b = a + {r.randint(1, 5)};",
         f"int c = b * {r.randint(2, 4)};",
         f"int d = c - a;",
         "print(a);", "print(b);", "print(c);", "print(d);"]
    return _j(L)


def prop_f2(r: random.Random) -> str:
    """Float constant chain, all used."""
    L = [f"float x = {r.randint(1, 5)}.5;",
         f"float y = x + {r.randint(1, 3)}.25;",
         "float z = y * x;",
         "float w = z - y;",
         "print(x);", "print(y);", "print(z);", "print(w);"]
    return _j(L)


def prop_f3(r: random.Random) -> str:
    """Int chain with branching, all branches print."""
    a = r.randint(1, 20)
    L = [f"int a = {a};",
         f"int b = a * {r.randint(2, 5)};",
         f"int c = b + {r.randint(1, 9)};",
         f"if (c > {r.randint(10, 50)}) {{",
         "    print(c);",
         "} else {", "    print(b);", "}",
         "print(a);"]
    return _j(L)


def prop_f4(r: random.Random) -> str:
    """Long linear constant chain, every intermediate used."""
    n = r.randint(5, 10)
    L = [f"int v0 = {r.randint(1, 9)};"]
    for k in range(1, n + 1):
        op = r.choice(["+", "*"])
        L.append(f"int v{k} = v{k - 1} {op} {r.randint(1, 4)};")
    for k in range(n + 1):
        L.append(f"print(v{k});")
    return _j(L)


def prop_f5(r: random.Random) -> str:
    """Boolean constant propagation chain."""
    a, b = r.randint(1, 20), r.randint(1, 20)
    L = [f"int a = {a};", f"int b = {b};",
         f"bool p = a < b + {r.randint(1, 5)};",
         f"bool q = a + {r.randint(1, 3)} > b;",
         "bool r1 = p && q;",
         "if (r1) {", "    print(1);", "} else {", "    print(0);", "}",
         "print(a);", "print(b);"]
    return _j(L)


Family = Callable[[random.Random], str]

CATEGORIES: dict[str, tuple[str, list[Family]]] = {
    "arithmetic-heavy": ("arith", [arith_f1, arith_f2, arith_f3, arith_f4, arith_f5]),
    "loop-heavy": ("loop", [loop_f1, loop_f2, loop_f3, loop_f4, loop_f5]),
    "branch-heavy": ("branch", [branch_f1, branch_f2, branch_f3, branch_f4, branch_f5]),
    "constant-heavy": ("const", [const_f1, const_f2, const_f3, const_f4, const_f5]),
    "redundant-expression-heavy": ("redundant", [red_f1, red_f2, red_f3, red_f4, red_f5]),
    "mixed": ("mixed", [mixed_f1, mixed_f2, mixed_f3, mixed_f4, mixed_f5]),
    "algebraic-heavy": ("alg", [alg_f1, alg_f2, alg_f3, alg_f4, alg_f5]),
    "copy-heavy": ("copy", [copy_f1, copy_f2, copy_f3, copy_f4, copy_f5]),
    "propagation-only": ("prop", [prop_f1, prop_f2, prop_f3, prop_f4, prop_f5]),
}
VARIANTS_PER_FAMILY = 3
