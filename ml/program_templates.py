"""Parameterised OptiWeave program families used to build the benchmark corpus.

Each category has five *families* (distinct program shapes). A family function takes a
seeded ``random.Random`` and returns source text, so the two variants of a family share
structure but differ in constants, sizes and statement counts. Families are the unit of
grouping for leakage-free evaluation.
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


Family = Callable[[random.Random], str]

CATEGORIES: dict[str, tuple[str, list[Family]]] = {
    "arithmetic-heavy": ("arith", [arith_f1, arith_f2, arith_f3, arith_f4, arith_f5]),
    "loop-heavy": ("loop", [loop_f1, loop_f2, loop_f3, loop_f4, loop_f5]),
    "branch-heavy": ("branch", [branch_f1, branch_f2, branch_f3, branch_f4, branch_f5]),
    "constant-heavy": ("const", [const_f1, const_f2, const_f3, const_f4, const_f5]),
    "redundant-expression-heavy": ("redundant", [red_f1, red_f2, red_f3, red_f4, red_f5]),
    "mixed": ("mixed", [mixed_f1, mixed_f2, mixed_f3, mixed_f4, mixed_f5]),
}
VARIANTS_PER_FAMILY = 2
