"""Small MATLAB convenience wrapper around the public grammar engine."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from ...engine import Grammar, IToken, Registry, parse_raw_grammar

_GRAMMAR_PATH = Path(__file__).with_name("MATLAB.tmLanguage")
_SCOPE_NAME = "source.matlab"


def _load_grammar(scope_name: str):
    if scope_name != _SCOPE_NAME:
        return None
    return parse_raw_grammar(_GRAMMAR_PATH.read_text(encoding="utf-8"), str(_GRAMMAR_PATH))


_registry = Registry({"load_grammar": _load_grammar})


@cache
def matlab_grammar() -> Grammar:
    """Return the module-cached MATLAB grammar."""
    grammar = _registry.load_grammar(_SCOPE_NAME)
    if not isinstance(grammar, Grammar):
        raise RuntimeError("Could not load the bundled MATLAB grammar")
    return grammar


def tokenize_matlab(path_or_text: str | Path) -> list[list[IToken]]:
    """Tokenize a MATLAB source path or text, returning tokens grouped by line."""
    text = _read_source(path_or_text)
    grammar = matlab_grammar()
    state = None
    lines: list[list[IToken]] = []
    for line in text.split("\n"):
        result = grammar.tokenizeLine(line, state)
        state = result.ruleStack
        lines.append(result.tokens)
    return lines


def _read_source(path_or_text: str | Path) -> str:
    if isinstance(path_or_text, Path):
        return path_or_text.read_text(encoding="utf-8")
    candidate = Path(path_or_text)
    try:
        if "\n" not in path_or_text and candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    except OSError:
        pass
    return path_or_text


__all__ = ["matlab_grammar", "tokenize_matlab"]
