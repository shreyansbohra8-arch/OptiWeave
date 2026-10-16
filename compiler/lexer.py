"""Hand-written lexer for OptiWeave."""
from __future__ import annotations

from compiler.tokens import KEYWORDS, OPERATORS, Token, TokenType
from utils.exceptions import LexerError


class Lexer:
    """Converts source text into a list of :class:`Token` objects."""

    def __init__(self, source: str) -> None:
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1

    # -- character helpers -------------------------------------------------
    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    # -- main loop -----------------------------------------------------------
    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            self._skip_trivia()
            if self.pos >= len(self.src):
                tokens.append(Token(TokenType.EOF, "", self.line, self.col))
                return tokens
            tokens.append(self._next_token())

    def _skip_trivia(self) -> None:
        while self.pos < len(self.src):
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                while self.pos < len(self.src) and self._peek() != "\n":
                    self._advance()
            elif ch == "/" and self._peek(1) == "*":
                line, col = self.line, self.col
                self._advance()
                self._advance()
                while True:
                    if self.pos >= len(self.src):
                        raise LexerError("Unterminated block comment", line, col)
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()
                        self._advance()
                        break
                    self._advance()
            else:
                return

    def _next_token(self) -> Token:
        line, col = self.line, self.col
        ch = self._peek()
        if ch.isascii() and ch.isdigit():
            return self._number(line, col)
        if ch.isascii() and (ch.isalpha() or ch == "_"):
            return self._word(line, col)
        two = ch + self._peek(1)
        if len(two) == 2 and two in OPERATORS:
            self._advance()
            self._advance()
            return Token(OPERATORS[two], two, line, col)
        if ch in OPERATORS:
            self._advance()
            return Token(OPERATORS[ch], ch, line, col)
        if ch in "&|":
            raise LexerError(f"Unexpected character {ch!r}; did you mean {ch * 2!r}?", line, col)
        raise LexerError(f"Unexpected character {ch!r}", line, col)

    def _number(self, line: int, col: int) -> Token:
        start = self.pos
        while self._peek().isascii() and self._peek().isdigit():
            self._advance()
        is_float = False
        if self._peek() == ".":
            if not (self._peek(1).isascii() and self._peek(1).isdigit()):
                raise LexerError("Malformed float literal: digits required after '.'", line, col)
            is_float = True
            self._advance()
            while self._peek().isascii() and self._peek().isdigit():
                self._advance()
        if self._peek().isascii() and (self._peek().isalpha() or self._peek() == "_"):
            raise LexerError("Invalid number literal (identifier characters after digits)", line, col)
        text = self.src[start:self.pos]
        if is_float:
            return Token(TokenType.FLOAT_LIT, text, line, col, float(text))
        return Token(TokenType.INT_LIT, text, line, col, int(text))

    def _word(self, line: int, col: int) -> Token:
        start = self.pos
        while self._peek().isascii() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        text = self.src[start:self.pos]
        ttype = KEYWORDS.get(text)
        if ttype is None:
            return Token(TokenType.IDENT, text, line, col)
        if ttype is TokenType.BOOL_LIT:
            return Token(ttype, text, line, col, text == "true")
        return Token(ttype, text, line, col)


def tokenize(source: str) -> list[Token]:
    """Convenience wrapper."""
    return Lexer(source).tokenize()
