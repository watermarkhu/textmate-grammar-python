"""Adapter exposing the current (legacy) python tokenizer to the differential test harness.

The legacy engine is the recursive-descent approximation of vscode-textmate that this repository
is porting away from (see ``plan/vscode-textmate-parity.md``). This adapter wraps it behind the
``tokenize`` protocol the harness compares against the node oracle:

    TokenRecord = (line:int, start:int, end:int, scopes:tuple[str, ...], content:str)

Tokens are merged the same way ``ContentElement.flatten()`` yields them: consecutive character
positions within a line that carry identical scope names become a single token.
"""

from __future__ import annotations

import plistlib
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, Protocol

from textmate_grammar.engine.raw_grammar import parse_raw_grammar
from textmate_grammar.engine.tokenize import create_grammar
from textmate_grammar.parsers.base import LanguageParser
from textmate_grammar.parsers.matlab import MatlabParser

if TYPE_CHECKING:
    from textmate_grammar.elements import ContentElement


class TokenRecord(NamedTuple):
    """One token of a tokenization stream.

    :ivar line: 0-based index of the line the token belongs to.
    :ivar start: column of the first character of the token.
    :ivar end: column right after the last character of the token.
    :ivar scopes: the token's scope stack, root scope first.
    :ivar content: the token's text content.
    """

    line: int
    start: int
    end: int
    scopes: tuple[str, ...]
    content: str


class Tokenizer(Protocol):
    """The protocol every engine adapter must implement for the differential harness."""

    def tokenize(self, text: str) -> list[TokenRecord]:
        """Tokenize ``text`` and return its token records in stream order."""


def records_from_element(element: ContentElement) -> list[TokenRecord]:
    """Convert a legacy ``ContentElement.flatten()`` stream into :class:`TokenRecord` items.

    ``flatten()`` yields ``(pos, content, scope_names)`` tuples of consecutive character
    positions that carry identical scope names; empty contents (which only exist for empty
    lines and carry no token) are skipped.
    """
    records: list[TokenRecord] = []
    for pos, content, scope_names in element.flatten():
        if content:
            records.append(TokenRecord(pos[0], pos[1], pos[1] + len(content), tuple(scope_names), content))
    return records


class LegacyAdapter(Tokenizer):
    """Differential adapter over the current (legacy) python tokenizer."""

    def __init__(self, parser: LanguageParser) -> None:
        """Initialize the adapter with a (pre-constructed) legacy language parser."""
        self._parser = parser

    def tokenize(self, text: str) -> list[TokenRecord]:
        """Parse ``text`` with the legacy engine and return its merged token records."""
        element = self._parser.parse_string(text)
        if element is None:
            return []
        return records_from_element(element)


class NewEngineAdapter(Tokenizer):
    """Adapter over the grammar-driven engine, loaded from the corpus grammar file."""

    def __init__(self, grammar_path: Path) -> None:
        raw = parse_raw_grammar(grammar_path.read_text(encoding="utf-8"), str(grammar_path))
        self._grammar = create_grammar(
            str(raw["scopeName"]),
            raw,
            external_grammar=lambda _scope: None,
        )

    def tokenize(self, text: str) -> list[TokenRecord]:
        return self.tokenize_with_state(text)[0]

    def tokenize_with_state(self, text: str) -> tuple[list[TokenRecord], list[str]]:
        """Return token records plus oracle-compatible final name-scope frames."""
        records: list[TokenRecord] = []
        state = None
        for line_number, line in enumerate(text.split("\n")):
            result = self._grammar.tokenize_line(line, state)
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


def _repository_file(*path: str) -> str:
    """Path of ``path`` relative to the repository root (computed from this test directory)."""
    root = Path(__file__).resolve().parents[2]
    return str(root.joinpath(*path))


@cache
def matlab_adapter() -> LegacyAdapter:
    """The legacy engine wired up for MATLAB grammars (same setup as test/regression)."""
    return LegacyAdapter(MatlabParser())


@cache
def markdown_adapter() -> LegacyAdapter:
    """The legacy engine wired up for the upstream (vendored) markdown grammar.

    ``MarkdownParser`` reads ``parsers/markdown/grammar.yaml``, which is a snapshot of the
    placeholder-templated ``markdown.tmLanguage.base.yaml`` upstream builds the real
    ``markdown.tmLanguage`` plist from (and which the legacy snapshot cannot yaml-parse by
    itself). The differential harness therefore loads the built upstream plist directly.
    """
    grammar_file = _repository_file("syntaxes", "markdown", "syntaxes", "markdown.tmLanguage")
    with open(grammar_file, "rb") as plist_file:
        grammar = plistlib.load(plist_file)

    return LegacyAdapter(LanguageParser(grammar))


@cache
def new_matlab_adapter() -> NewEngineAdapter:
    """New engine wired to the upstream MATLAB grammar."""
    from .corpus import matlab_spec

    return NewEngineAdapter(matlab_spec.grammar)


@cache
def new_markdown_adapter() -> NewEngineAdapter:
    """New engine wired to the upstream built markdown grammar."""
    from .corpus import markdown_spec

    return NewEngineAdapter(markdown_spec.grammar)


def get_adapter(language: str, engine: str = "legacy") -> LegacyAdapter | NewEngineAdapter:
    """Return an adapter; omitted ``engine`` preserves the legacy harness default."""
    if engine == "new":
        if language == "matlab":
            return new_matlab_adapter()
        if language == "markdown":
            return new_markdown_adapter()
        raise KeyError(f"No new-engine adapter registered for language {language!r}")
    if engine != "legacy":
        raise ValueError(f"Unknown engine {engine!r}")
    if language == "matlab":
        return matlab_adapter()
    if language == "markdown":
        return markdown_adapter()
    raise KeyError(f"No legacy adapter registered for language {language!r}")
