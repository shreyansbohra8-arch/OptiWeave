"""Custom exception hierarchy for OptiWeave."""
from __future__ import annotations


class OptiWeaveError(Exception):
    """Base class for all OptiWeave errors."""


class SourceError(OptiWeaveError):
    """An error tied to a location in the source program."""

    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        self.message = message
        self.line = line
        self.column = column
        location = f"line {line}, column {column}: " if line else ""
        super().__init__(f"{location}{message}")


class LexerError(SourceError):
    """Invalid character or malformed token."""


class ParseError(SourceError):
    """Syntax error."""


class SemanticError(SourceError):
    """Semantic (scope/type) error."""


class SemanticErrors(OptiWeaveError):
    """Raised when semantic analysis finds one or more errors."""

    def __init__(self, errors: list[SemanticError]) -> None:
        self.errors = errors
        super().__init__("; ".join(str(e) for e in errors))


class IRError(OptiWeaveError):
    """Malformed intermediate representation."""


class ExecutionError(OptiWeaveError):
    """A program failed at run time (e.g. division by zero)."""


class ExecutionLimitError(ExecutionError):
    """The IR interpreter exceeded its step budget."""


class ToolchainError(OptiWeaveError):
    """GCC missing or failed."""


class ModelNotFoundError(OptiWeaveError):
    """No trained model artifact exists."""


class IncompatibleModelError(OptiWeaveError):
    """Model artifact does not match the current feature set / version."""


class DatasetError(OptiWeaveError):
    """Dataset file missing or malformed."""
