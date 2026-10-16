# OptiWeave Language Grammar

OptiWeave (`.ow`) is a restricted C-like language with `int`, `float`, `bool`.

## Lexical structure
* Keywords: `int float bool if else while print true false`
* Identifiers: `[A-Za-z_][A-Za-z0-9_]*`
* Literals: integers (`42`, at most 2^63-1), floats (`3.14`; digits are required on both sides of `.`), `true`, `false`
* Operators: `+ - * / % < > <= >= == != && || ! =`
* Punctuation: `( ) { } ;`
* Comments: `// to end of line` and `/* block */`

## Grammar (EBNF, unambiguous, one token of lookahead)
```
program      = { statement } EOF ;
statement    = declaration | assignment | if_stmt | while_stmt | print_stmt | block ;
declaration  = type IDENT [ "=" expr ] ";" ;
type         = "int" | "float" | "bool" ;
assignment   = IDENT "=" expr ";" ;
if_stmt      = "if" "(" expr ")" block [ "else" ( block | if_stmt ) ] ;
while_stmt   = "while" "(" expr ")" block ;
print_stmt   = "print" "(" expr ")" ";" ;
block        = "{" { statement } "}" ;

expr         = or_expr ;
or_expr      = and_expr { "||" and_expr } ;
and_expr     = equality { "&&" equality } ;
equality     = relational { ( "==" | "!=" ) relational } ;
relational   = additive { ( "<" | ">" | "<=" | ">=" ) additive } ;
additive     = term { ( "+" | "-" ) term } ;
term         = unary { ( "*" | "/" | "%" ) unary } ;
unary        = ( "-" | "!" ) unary | primary ;
primary      = INT | FLOAT | BOOL | IDENT | "(" expr ")" ;
```
Precedence (high to low): unary `- !`; `* / %`; `+ -`; `< > <= >=`; `== !=`; `&&`; `||`.
All binary operators are **left-associative**. Braces are mandatory for `if`/`while` bodies, which removes the
dangling-else ambiguity. `else if` is sugar for `else { if ... }`.

## Semantics and type rules
| Construct | Rule |
|---|---|
| `int op float` | promoted to `float` |
| `/` | both `int`: integer division truncating toward zero (like C); otherwise floating division |
| `%` | only `int % int`; result has the sign of the dividend (like C) |
| `< > <= >=` | numeric operands, result `bool` |
| `== !=` | two numeric operands or two `bool` operands, result `bool` |
| `&& \|\| !` | `bool` operands only; `&&`/`\|\|` **short-circuit** |
| unary `-` | numeric operand (negative literals are unary minus applied to a literal) |
| conditions | `if`/`while` conditions must be `bool` (no int-to-bool conversion) |
| assignment | exact type match; `int -> float` widening allowed; `float -> int` and anything involving `bool` mixed with numbers rejected |
| declaration without initialiser | value is `0`, `0.0` or `false` |
| scope | blocks open a scope; names must be **unique in the whole program** (no shadowing, no reuse in sibling blocks) |
| division by a literal zero | compile-time error; division by a zero *variable* is a run-time error |
| `int` range | 64-bit signed with two's-complement wrap-around (`long long`, GCC `-fwrapv`) |
| `print(e)` | `int` -> `%lld`, `float` -> `%.6f`, `bool` -> `true` / `false`, one value per line |

Unsupported syntax (functions, arrays, `for`, `++`, strings, ...) is rejected with a located error.
