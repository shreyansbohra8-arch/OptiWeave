"""Token definitions for the OptiWeave language."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # literals / names
    INT_LIT = auto()
    FLOAT_LIT = auto()
    BOOL_LIT = auto()
    IDENT = auto()
    # keywords
    KW_INT = auto()
    KW_FLOAT = auto()
    KW_BOOL = auto()
    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_PRINT = auto()
    # arithmetic
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    # relational
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    EQ = auto()
    NE = auto()
    # logical
    AND = auto()
    OR = auto()
    NOT = auto()
    # other
    ASSIGN = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    SEMI = auto()
    EOF = auto()


KEYWORDS = {
    "int": TokenType.KW_INT,
    "float": TokenType.KW_FLOAT,
    "bool": TokenType.KW_BOOL,
    "if": TokenType.KW_IF,
    "else": TokenType.KW_ELSE,
    "while": TokenType.KW_WHILE,
    "print": TokenType.KW_PRINT,
    "true": TokenType.BOOL_LIT,
    "false": TokenType.BOOL_LIT,
}

# Longest operators first so that e.g. "<=" is not read as "<" "=".
OPERATORS = {
    "&&": TokenType.AND, "||": TokenType.OR,
    "<=": TokenType.LE, ">=": TokenType.GE, "==": TokenType.EQ, "!=": TokenType.NE,
    "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR,
    "/": TokenType.SLASH, "%": TokenType.PERCENT,
    "<": TokenType.LT, ">": TokenType.GT, "!": TokenType.NOT, "=": TokenType.ASSIGN,
    "(": TokenType.LPAREN, ")": TokenType.RPAREN,
    "{": TokenType.LBRACE, "}": TokenType.RBRACE, ";": TokenType.SEMI,
}

TYPE_KEYWORDS = {TokenType.KW_INT: "int", TokenType.KW_FLOAT: "float", TokenType.KW_BOOL: "bool"}


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int
    value: object = None

    def __str__(self) -> str:
        return f"{self.type.name}({self.lexeme!r}) @ {self.line}:{self.column}"
