"""MATLAB language intents exercised through the token-stream API."""

from __future__ import annotations

import pytest

from textmate_grammar.parsers.matlab import matlab_grammar, tokenize_matlab


@pytest.mark.parametrize(
    ("source", "expected_scope"),
    [
        ("@(x) x + 1", "meta.function.anonymous.matlab"),
        ("% a comment", "comment.line.percentage.matlab"),
        ("true false", "constant.language.boolean.matlab"),
        ("if true\nend", "keyword.control.if.matlab"),
        ("global value; persistent cache;", "storage.modifier.matlab"),
        ("import java.util.*", "keyword.other.import.matlab"),
        ("x = 1 ...\n    + 2;", "meta.continuation.line.matlab"),
        ("x = 1.25e-3;", "constant.numeric.decimal.matlab"),
        ("x = a + b .* c == d;", "keyword.operator.arithmetic.matlab"),
        ("arguments\n    x (1,1) double\nend", "constant.numeric.decimal.matlab"),
        ("f(a, b);", "punctuation.separator.comma.matlab"),
        ("value = value + 1;", "variable.other.readwrite.matlab"),
        ('s = "hello";', "string.quoted.double.matlab"),
        ("x = A';", "keyword.operator.transpose.matlab"),
        ("arguments (Input)\n    x (1,1) double\nend", "meta.function-call.parens.matlab"),
        ("value = other;", "keyword.operator.assignment.matlab"),
    ],
    ids=[
        "anonymous-function",
        "comment",
        "constants",
        "control-statements",
        "global-persistent",
        "imports",
        "line-continuation",
        "numbers",
        "operators",
        "validation-arguments",
        "punctuation",
        "read-write",
        "strings",
        "transpose",
        "validators",
        "variables",
    ],
)
def test_matlab_features_produce_expected_scope_paths(source: str, expected_scope: str) -> None:
    """Keep the former language-parser intent as assertions over IToken scopes."""
    line_tokens = tokenize_matlab(source)
    tokens = [token for line in line_tokens for token in line]
    assert tokens
    assert all(token.scopes[0] == "source.matlab" for token in tokens)
    assert any(expected_scope in token.scopes for token in tokens)


def test_matlab_grammar_is_cached_and_tokenize_matlab_accepts_a_source_path(tmp_path) -> None:
    source_path = tmp_path / "sample.m"
    source_path.write_text("value = 2;", encoding="utf-8")

    assert matlab_grammar() is matlab_grammar()
    tokens = [token for line in tokenize_matlab(source_path) for token in line]
    assert any("constant.numeric.decimal.matlab" in token.scopes for token in tokens)
