"""Adapter exposing token streams from the public grammar engine."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import NamedTuple, Protocol

from textmate_grammar import INITIAL, Registry, parse_raw_grammar
from textmate_grammar.engine import Grammar, ITokenizeLineResult


class TokenRecord(NamedTuple):
    """One token record in a tokenization stream."""

    line: int
    start: int
    end: int
    scopes: tuple[str, ...]
    content: str


class Tokenizer(Protocol):
    def tokenize(self, text: str) -> list[TokenRecord]: ...


class NewEngineAdapter(Tokenizer):
    """Adapter over the grammar-driven engine, loaded from a corpus grammar file."""

    def __init__(self, grammar_path: Path) -> None:
        self._grammar_path = grammar_path
        self._registry = Registry({"load_grammar": self._load_grammar})
        grammar = self._registry.loadGrammar(self._scope_name())
        if not isinstance(grammar, Grammar):
            raise ValueError(f"Could not load grammar from {grammar_path}")
        self._grammar = grammar

    def _scope_name(self) -> str:
        parsed = parse_raw_grammar(
            self._grammar_path.read_text(encoding="utf-8"), str(self._grammar_path)
        )
        return str(parsed["scopeName"])

    def _load_grammar(self, scope_name: str):
        raw = parse_raw_grammar(
            self._grammar_path.read_text(encoding="utf-8"), str(self._grammar_path)
        )
        return raw if raw.get("scopeName") == scope_name else None

    def tokenize(self, text: str) -> list[TokenRecord]:
        return self.tokenize_with_state(text)[0]

    def tokenize_with_state(self, text: str) -> tuple[list[TokenRecord], list[str]]:
        """Return records and oracle-compatible final name-scope frames."""
        records: list[TokenRecord] = []
        state = INITIAL
        for line_number, line in enumerate(text.split("\n")):
            result: ITokenizeLineResult = self._grammar.tokenizeLine(line, state)
            state = result.ruleStack
            for token in result.tokens:
                start = token.startIndex
                end = min(token.endIndex, len(line))
                if end > start:
                    records.append(
                        TokenRecord(line_number, start, end, tuple(token.scopes), line[start:end])
                    )
        frames = []
        item = state
        while item is not None:
            frames.append(" ".join(item.nameScopesList.get_scope_names()) if item.nameScopesList else "")
            item = item.parent
        frames.reverse()
        return records, frames


@cache
def new_matlab_adapter() -> NewEngineAdapter:
    from .corpus import matlab_spec

    return NewEngineAdapter(matlab_spec.grammar)


@cache
def new_markdown_adapter() -> NewEngineAdapter:
    from .corpus import markdown_spec

    return NewEngineAdapter(markdown_spec.grammar)


@cache
def new_vendored_adapter(language: str) -> NewEngineAdapter:
    """New engine wired to a third-party grammar declared in the differential corpus."""
    from .corpus import CORPUS_LANGUAGES

    return NewEngineAdapter(CORPUS_LANGUAGES[language].grammar)


def get_adapter(language: str, engine: str = "new") -> NewEngineAdapter:
    """Return a differential adapter (the new engine is the default and only engine)."""
    if engine != "new":
        raise ValueError(f"Unknown engine {engine!r}; only 'new' is supported")
    if language == "matlab":
        return new_matlab_adapter()
    if language == "markdown":
        return new_markdown_adapter()
    if language in {"python", "typescript"}:
        return new_vendored_adapter(language)
    raise KeyError(f"No new-engine adapter registered for language {language!r}")
