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


def get_adapter(language: str) -> LegacyAdapter:
    """Return the :class:`LegacyAdapter` for a corpus language id."""
    if language == "matlab":
        return matlab_adapter()
    if language == "markdown":
        return markdown_adapter()
    raise KeyError(f"No legacy adapter registered for language {language!r}")
