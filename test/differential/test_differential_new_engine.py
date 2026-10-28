"""Differential coverage for the newly ported grammar tokenizer."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from .corpus import CORPUS_LANGUAGES, CorpusEntry, corpus
from .engine_adapter import TokenRecord, get_adapter
from .test_differential import ORACLE_REASON, ORACLE_SCRIPT, compare, oracle_available


@pytest.mark.skipif(not oracle_available(), reason=ORACLE_REASON)
@pytest.mark.parametrize("entry", corpus(), ids=lambda entry: entry.id)
def test_new_engine_tokenization_parity(entry: CorpusEntry, tmp_path: Path) -> None:
    """Compare every corpus file against vscode-textmate using the new engine."""
    oracle_input = tmp_path / f"oracle_{entry.path.name}"
    text = entry.load_text()
    oracle_input.write_text(text, encoding="utf-8", newline="\n")
    spec = CORPUS_LANGUAGES[entry.language]
    process = subprocess.run(
        ["node", str(ORACLE_SCRIPT), str(spec.grammar), str(oracle_input)],
        check=True,
        capture_output=True,
        text=True,
    )
    oracle = []
    oracle_state = None
    for line in process.stdout.splitlines():
        record = json.loads(line)
        if record["type"] == "token":
            oracle.append(
                TokenRecord(
                    record["line"],
                    record["start"],
                    record["end"],
                    tuple(record["scopes"]),
                    record["content"],
                )
            )
        elif record["type"] == "state":
            oracle_state = record["scopes"]
    actual, actual_state = get_adapter(entry.language, engine="new").tokenize_with_state(text)
    compare(oracle, actual)
    assert actual_state == oracle_state
