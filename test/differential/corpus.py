"""Corpus definition for the differential tests.

This module is the single place where the tested (grammar, corpus file) pairs are declared so
that the corpus can be grown (task 6 of ``plan/vscode-textmate-parity.md``) without touching
the harness itself. Entries are grouped per language, each language defining the grammar file
both sides compare against and the legacy :class:`~test.differential.engine_adapter`
adapter used for the python side.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path

TEST_DIFFERENTIAL_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = TEST_DIFFERENTIAL_ROOT.parents[1]
SYNTAXES_ROOT = REPOSITORY_ROOT / "syntaxes"
MATLAB_TEST_ROOT = SYNTAXES_ROOT / "matlab" / "test"
MARKDOWN_FIXTURE_ROOT = SYNTAXES_ROOT / "markdown" / "test" / "colorize-fixtures"

# The syntaxes/matlab/*.m corpus of test/regression/test_matlab.py's explicit file list (the
# test-directory files are globbed by matlab_corpus below).
REGRESSION_MATLAB_STEMS = [
    "Account",
    "AnEnum",
    "argumentValidation",
    "CircleArea",
    "controlFlow",
    "lineContinuations",
    "PropertyValidation",
]


@dataclass(frozen=True)
class LanguageSpec:
    """The grammar program and the adapter used for one corpus language.

    :ivar language: identifier of the corpus language (adapter lookup key).
    :ivar grammar: path to the grammar file passed to the oracle.
    :ivar scope: the grammar's scope name.
    """

    language: str
    scope: str
    grammar: Path


matlab_spec = LanguageSpec(
    language="matlab",
    scope="source.matlab",
    grammar=(SYNTAXES_ROOT / "matlab" / "Matlab.tmbundle" / "Syntaxes" / "MATLAB.tmLanguage"),
)

# NOTE: the upstream markdown grammar (built from the placeholder-templated
# markdown.tmLanguage.base.yaml) is loaded on both sides; see engine_adapter.markdown_adapter().
markdown_spec = LanguageSpec(
    language="markdown",
    scope="text.html.markdown",
    grammar=(SYNTAXES_ROOT / "markdown" / "syntaxes" / "markdown.tmLanguage"),
)

CORPUS_LANGUAGES: dict[str, LanguageSpec] = {
    matlab_spec.language: matlab_spec,
    markdown_spec.language: markdown_spec,
}


@dataclass(frozen=True)
class CorpusEntry:
    """One (language, source file) corpus item."""

    language: str
    path: Path

    @property
    def id(self) -> str:
        return f"{self.language}/{self.path.stem}"

    def load_text(self) -> str:
        """The exact text both engines of the harness tokenize for this entry.

        The legacy engine ingests files through ``ContentHandler``, which normalizes ``\\r\\n``
        and ``\\r`` to ``\\n`` line separators, while ``oracle.js`` splits on ``\\n`` and would
        otherwise keep ``\\r`` inside the line content (and thus in the token content). Loading
        the corpus text through this method hands identical text to both sides; it is the only
        place corpus input normalization happens.
        """
        return self.path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def matlab_corpus() -> list[CorpusEntry]:
    """The matlab .m corpus, the same files the regression tests already compare."""
    entries = [
        CorpusEntry("matlab", SYNTAXES_ROOT / "matlab" / f"{stem}.m")
        for stem in REGRESSION_MATLAB_STEMS
    ] + [
        CorpusEntry("matlab", path)
        for path in sorted(MATLAB_TEST_ROOT.glob("*.m"))
    ]
    entries.append(
        # Originally part of the retired test/regression suite; retained in the
        # differential corpus after that suite was removed.
        CorpusEntry("matlab", TEST_DIFFERENTIAL_ROOT / "corpus" / "matlab" / "test_multiple_inheritance_ml.m")
    )
    return entries


def markdown_corpus() -> list[CorpusEntry]:
    """Small markdown samples from the upstream markdown submodule's colorize fixtures."""
    return [
        CorpusEntry("markdown", MARKDOWN_FIXTURE_ROOT / "header-inline.md"),
        CorpusEntry("markdown", MARKDOWN_FIXTURE_ROOT / "code-block.md"),
        CorpusEntry("markdown", MARKDOWN_FIXTURE_ROOT / "table-alignment.md"),
    ]


@functools.lru_cache(maxsize=1)
def corpus() -> tuple[CorpusEntry, ...]:
    """All corpus entries the differential tests run over, in a stable order."""
    entries = [entry for spec in CORPUS_LANGUAGES.values() for entry in _lang_corpus(spec.language)]
    return tuple(sorted(entries, key=lambda entry: entry.id))


def _lang_corpus(language: str) -> list[CorpusEntry]:
    if language == "matlab":
        return matlab_corpus()
    if language == "markdown":
        return markdown_corpus()
    raise KeyError(f"No corpus registered for language {language!r}")
