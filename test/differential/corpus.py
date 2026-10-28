"""Corpus definition for the differential tests.

This module is the single place where the tested (grammar, corpus file) pairs are declared so
that the corpus can be grown (task 6 of ``plan/vscode-textmate-parity.md``) with minimal changes
to the harness. Entries are grouped per language, each language defining the grammar file both
sides compare against; the new engine is selected explicitly by the differential test.
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
DIFFERENTIAL_FIXTURE_ROOT = TEST_DIFFERENTIAL_ROOT / "corpus"

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

python_spec = LanguageSpec(
    language="python",
    scope="source.python",
    grammar=DIFFERENTIAL_FIXTURE_ROOT / "grammars" / "python.tmLanguage.json",
)

typescript_spec = LanguageSpec(
    language="typescript",
    scope="source.ts",
    grammar=DIFFERENTIAL_FIXTURE_ROOT / "grammars" / "TypeScript.tmLanguage",
)

CORPUS_LANGUAGES: dict[str, LanguageSpec] = {
    matlab_spec.language: matlab_spec,
    markdown_spec.language: markdown_spec,
    python_spec.language: python_spec,
    typescript_spec.language: typescript_spec,
}


@dataclass(frozen=True)
class CorpusEntry:
    """One (language, source file) corpus item."""

    language: str
    path: Path
    preserve_newlines: bool = False

    @property
    def id(self) -> str:
        return f"{self.language}/{self.path.stem}"

    def load_text(self) -> str:
        """The exact text both engines of the harness tokenize for this entry.

        Most fixtures normalize ``\\r\\n`` and ``\\r`` to ``\\n`` because the legacy MATLAB
        ``ContentHandler`` does so. The CRLF smoke fixture opts out with ``preserve_newlines``
        so both the oracle and new engine see the original ``\\r`` characters.
        """
        if self.preserve_newlines:
            return self.path.read_bytes().decode("utf-8")
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
        CorpusEntry("matlab", REPOSITORY_ROOT / "test" / "regression" / "matlab" / "test_multiple_inheritance_ml.m")
    )
    return entries


def markdown_corpus() -> list[CorpusEntry]:
    """Small markdown samples from the upstream markdown submodule's colorize fixtures."""
    return [
        CorpusEntry("markdown", MARKDOWN_FIXTURE_ROOT / "header-inline.md"),
        CorpusEntry("markdown", MARKDOWN_FIXTURE_ROOT / "code-block.md"),
        CorpusEntry("markdown", MARKDOWN_FIXTURE_ROOT / "table-alignment.md"),
    ]


def legacy_corpus() -> tuple[CorpusEntry, ...]:
    """Original MATLAB and markdown samples retained for the legacy baseline suite."""
    return tuple(sorted(matlab_corpus() + markdown_corpus(), key=lambda entry: entry.id))


def fixture_corpus(language: str) -> list[CorpusEntry]:
    """Files in the self-contained differential fixture directory for ``language``."""
    return [
        CorpusEntry(language, path, preserve_newlines=path.name == "crlf_unicode.m")
        for path in sorted((DIFFERENTIAL_FIXTURE_ROOT / language).glob("*"))
        if path.is_file()
    ]


@functools.lru_cache(maxsize=1)
def corpus() -> tuple[CorpusEntry, ...]:
    """All corpus entries the differential tests run over, in a stable order."""
    entries = [entry for spec in CORPUS_LANGUAGES.values() for entry in _lang_corpus(spec.language)]
    return tuple(sorted(entries, key=lambda entry: entry.id))


def _lang_corpus(language: str) -> list[CorpusEntry]:
    if language == "matlab":
        return matlab_corpus() + fixture_corpus("matlab")
    if language == "markdown":
        return markdown_corpus() + fixture_corpus("markdown")
    if language in {"python", "typescript"}:
        return fixture_corpus(language)
    raise KeyError(f"No corpus registered for language {language!r}")
