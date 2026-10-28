"""Differential tests: the legacy python tokenizer vs the vscode-textmate node oracle.

For every corpus entry (see ``corpus.py``; task 6 grows it), the node oracle
(``node oracle.js <grammar-file> <text-file>``) and the legacy engine adapter are run, and
their token records are compared exactly. On a mismatch the test fails with the first
divergent token, its stream index, both records and their +/-3 surrounding records.

The comparison happens on *merged* token streams: the legacy engine's ``flatten()`` merges
consecutive character positions within a line that carry identical scope names, while the raw
vscode-textmate ``tokenizeLine`` result may emit several adjacent tokens (capture boundaries)
with identical scope lists. Merging both sides on the (line, scope list) criterion makes the
streams directly comparable and still exposes every real token-boundary or scope difference.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from .corpus import CORPUS_LANGUAGES, corpus
from .engine_adapter import TokenRecord, get_adapter

TEST_ROOT = Path(__file__).resolve().parent
ORACLE_SCRIPT = TEST_ROOT / "oracle.js"
ORACLE_NODE_MODULES = TEST_ROOT / "node_root" / "node_modules"

CONTEXT = 3  # records of context shown before and after the first divergent token

if TYPE_CHECKING:
    from .corpus import CorpusEntry


def oracle_available() -> bool:
    """Whether the oracle can run: node on PATH and node_root dependencies installed.

    CI wiring (task 0c) installs these; a locally missing setup skips the tests rather than
    erroring them.
    """
    return shutil.which("node") is not None and ORACLE_NODE_MODULES.is_dir()


ORACLE_REASON = (
    "node oracle not runnable: 'node' is not on PATH or test/differential/node_root/node_modules"
    " is missing (npm install in test/differential/node_root); CI wiring is task 0c"
)


def run_oracle(entry: CorpusEntry, oracle_input: Path) -> list[TokenRecord]:
    """Run the oracle on the (already unified) corpus text ``oracle_input`` for ``entry``."""
    spec = CORPUS_LANGUAGES[entry.language]
    process = subprocess.run(
        ["node", str(ORACLE_SCRIPT), str(spec.grammar), str(oracle_input)],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(f"oracle failed (exit={process.returncode}):\n{process.stderr}")

    records: list[TokenRecord] = []
    for line in process.stdout.splitlines():
        record = json.loads(line)
        if record["type"] == "token":
            records.append(
                TokenRecord(record["line"], record["start"], record["end"], tuple(record["scopes"]), record["content"])
            )
    return records


def merge_records(records: list[TokenRecord]) -> list[TokenRecord]:
    """Merge consecutive same-scope records within a line; drop empty-content records.

    Mirrors the legacy engine's ``flatten()`` semantics: characters carrying identical scope
    names inside a line belong to a single token. Merging requires contiguity so that a
    coverage gap on either side is reported as a divergence instead of being hidden.
    """
    merged: list[TokenRecord] = []
    for record in records:
        if not record.content:
            continue
        previous = merged[-1] if merged else None
        if (
            previous is not None
            and previous.line == record.line
            and previous.scopes == record.scopes
            and previous.end == record.start
        ):
            merged[-1] = TokenRecord(
                previous.line, previous.start, record.end, previous.scopes, previous.content + record.content
            )
        else:
            merged.append(record)
    return merged


def format_record(record: TokenRecord | None) -> str:
    """One-line representation of a token record (or its absence)."""
    return "None" if record is None else repr(record)


def _divergence_message(oracle: list[TokenRecord], adapter: list[TokenRecord]) -> str:
    """The failure message for the first divergent token between both streams."""
    i = 0
    length = max(len(oracle), len(adapter))
    while i < length and (oracle[i] if i < len(oracle) else None) == (adapter[i] if i < len(adapter) else None):
        i += 1

    header = (
        f"Token streams diverge: {len(oracle)} oracle records vs {len(adapter)} adapter records."
        if len(oracle) != len(adapter)
        else "Token streams diverge."
    )
    message = [
        header,
        f"First divergent token: index {i}",
        f"  oracle : {format_record(oracle[i] if i < len(oracle) else None)}",
        f"  adapter: {format_record(adapter[i] if i < len(adapter) else None)}",
    ]
    for j in range(max(0, i - CONTEXT), min(length, i + CONTEXT + 1)):
        if j == i:
            continue
        message.append(f"  [{j}] oracle : {format_record(oracle[j] if j < len(oracle) else None)}")
        message.append(f"  [{j}] adapter: {format_record(adapter[j] if j < len(adapter) else None)}")
    return "\n".join(message)


def compare(oracle: list[TokenRecord], adapter: list[TokenRecord]) -> None:
    """Compare the merged token streams exactly; fail on the first divergent token."""
    merged_oracle = merge_records(oracle)
    merged_adapter = merge_records(adapter)

    if merged_oracle != merged_adapter:
        pytest.fail(_divergence_message(merged_oracle, merged_adapter), pytrace=False)


@pytest.mark.skipif(not oracle_available(), reason=ORACLE_REASON)
@pytest.mark.parametrize("entry", corpus(), ids=lambda entry: entry.id)
class TestDifferential:
    """Token-stream parity per (grammar, corpus file) pair."""

    def test_tokenization_parity(self, entry: CorpusEntry, tmp_path: Path) -> None:
        """The legacy engine and the node oracle produce identical token records."""
        # Both engines must tokenize identical text: the test feeds the oracle a copy of the
        # corpus entry's unified text (see CorpusEntry.load_text for the normalization).
        oracle_input = tmp_path / f"oracle_{entry.path.name}"
        oracle_input.write_text(entry.load_text(), encoding="utf-8", newline="\n")

        oracle = run_oracle(entry, oracle_input)

        text = entry.load_text()
        try:
            legacy_adapter = get_adapter(entry.language)
            records = legacy_adapter.tokenize(text)
        except Exception as error:
            pytest.fail(
                f"The legacy engine could not tokenize {entry.id}: "
                f"{error.__class__.__name__}: {error}"
                "\nThis is baseline debt against the vscode-textmate oracle"
                f" (oracle produced {len(oracle)} tokens; first ones: "
                f"{[repr(record) for record in oracle[:5]]})",
                pytrace=False,
            )
        compare(oracle, records)
