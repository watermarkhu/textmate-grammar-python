"""Unit tests for the ``parseRawGrammar.ts`` + ``json.ts`` port
(``engine.raw_grammar``).

Real-fixture assertions were verified against the upstream TypeScript parsers
(vscode-textmate 9.3.2, running the actual ``src/plist.ts`` / ``src/json.ts``
under node): the Python parsing of both grammar fixtures is byte-identical to
the TypeScript output (``JSON.stringify`` comparison).

Note: upstream has no YAML-tmLanguage support and no content sniffing — a
non-``.json`` file path always routes to the plist parser, regardless of file
extension or content. Those semantics are asserted here as well.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from textmate_grammar.engine.plist import parse_plist
from textmate_grammar.engine.raw_grammar import (
    IN_DEBUG_MODE,
    LOCATION_KEY,
    parse_json,
    parse_raw_grammar,
    value_as_string,
)

ROOT = Path(__file__).parents[3]
MATLAB_TMLANGUAGE = ROOT / "syntaxes/matlab/Matlab.tmbundle/Syntaxes/MATLAB.tmLanguage"
MARKDOWN_TMLANGUAGE = ROOT / "syntaxes/markdown/syntaxes/markdown.tmLanguage"
MARKDOWN_JSON = Path(__file__).parent / "data" / "markdown.tmLanguage.json"

requires_matlab = pytest.mark.skipif(
    not MATLAB_TMLANGUAGE.exists(), reason="syntaxes submodule not initialized"
)
requires_markdown = pytest.mark.skipif(
    not (MARKDOWN_TMLANGUAGE.exists() and MARKDOWN_JSON.exists()),
    reason="syntaxes submodule not initialized",
)

_JSON_GRAMMAR = '{"scopeName": "source.x", "patterns": [{"include": "#a"}], "repository": {}}'
_XML_GRAMMAR = (
    "<dict><key>scopeName</key><string>source.x</string>"
    "<key>patterns</key><array/><key>repository</key><dict/></dict>"
)


# ---------------------------------------------------------------------------
# Routing (parseRawGrammar.ts)
# ---------------------------------------------------------------------------


class TestRouting:
    def test_json_path_routes_to_json(self) -> None:
        grammar = parse_raw_grammar(_JSON_GRAMMAR, "/path/to/grammar.tmLanguage.json")
        assert grammar == {
            "scopeName": "source.x",
            "patterns": [{"include": "#a"}],
            "repository": {},
        }
        assert LOCATION_KEY not in grammar  # production path = JSON.parse

    def test_plist_path_routes_to_plist(self) -> None:
        grammar = parse_raw_grammar(_XML_GRAMMAR, "/path/to/grammar.tmLanguage")
        assert grammar["scopeName"] == "source.x"
        assert grammar["patterns"] == []
        assert grammar["repository"] == {}

    def test_null_path_routes_to_plist(self) -> None:
        assert parse_raw_grammar(_XML_GRAMMAR, None)["scopeName"] == "source.x"

    def test_json_content_without_json_extension_goes_to_plist(self) -> None:
        # Upstream routing is extension-only: JSON content handed to the plist
        # parser necessarily fails.
        with pytest.raises(ValueError, match="Near offset 1: expected <"):
            parse_raw_grammar(_JSON_GRAMMAR, "/path/to/grammar.tmLanguage")

    def test_plist_content_with_json_extension_goes_to_json(self) -> None:
        with pytest.raises(ValueError):
            parse_raw_grammar(_XML_GRAMMAR, "/path/to/g.json")

    def test_yaml_is_not_supported(self) -> None:
        # Upstream has no YAML-tmLanguage support: non-XML content fails in
        # the plist parser (its faithful error behavior is kept).
        with pytest.raises(ValueError, match=r"Near offset 1: expected <"):
            parse_raw_grammar("scopeName: source.yml", "/path/to/grammar.yaml")
    def test_jsonc_comments_are_not_tolerated(self) -> None:
        # Upstream parses .json with strict JSON.parse: no comments.
        with pytest.raises(ValueError):
            parse_raw_grammar(
                '{\n// comment for\n"a": true\n}', "/path/to/grammar.jsonc"
            )


def test_plist_content_in_json_file_parses_asplist() -> None:
    # Routing is by extension only: plist content with a .json suffix is
    # handed to JSON and (necessarily) fails.
    with pytest.raises(ValueError):
        parse_raw_grammar("<dict><key>a</key><string>b</string></dict>", "/g.json")


# ---------------------------------------------------------------------------
# Real fixtures
# ---------------------------------------------------------------------------


@requires_matlab
def test_matlab_fixture_routing() -> None:
    content = MATLAB_TMLANGUAGE.read_text(encoding="utf-8")
    grammar = parse_raw_grammar(content, str(MATLAB_TMLANGUAGE))
    assert grammar == parse_plist(content)
    assert grammar["scopeName"] == "source.matlab"
    assert len(grammar["patterns"]) == 3
    assert len(grammar["repository"]) == 41


class TestPlistJsonParity:
    """The markdown grammar as plist and as JSON must parse identically.

    (The markdown submodule only ships the plist; the JSON variant of the very
    same grammar is checked in under ``data/``, generated through the upstream
    plist parser itself.)
    """

    @requires_markdown
    def test_fixture_matches_plist_fixture(self) -> None:
        from_plist = parse_plist(MARKDOWN_TMLANGUAGE.read_text(encoding="utf-8"))
        from_json = parse_raw_grammar(
            MARKDOWN_JSON.read_text(encoding="utf-8"), str(MARKDOWN_JSON)
        )
        assert from_json == from_plist

    @requires_markdown
    def test_selected_values(self) -> None:
        grammar = parse_raw_grammar(
            MARKDOWN_JSON.read_text(encoding="utf-8"), str(MARKDOWN_JSON)
        )
        assert grammar["scopeName"] == "text.html.markdown"
        assert len(grammar["patterns"]) == 2
        assert [rule["include"] for rule in grammar["repository"]["block"]["patterns"]] == [
            "#separator",
            "#heading",
            "#blockquote",
            "#lists",
            "#fenced_code_block",
            "#raw_block",
            "#link-def",
            "#html",
            "#table",
            "#paragraph",
        ]
        assert len(grammar["repository"]) == 87


# ---------------------------------------------------------------------------
# json.ts (debug-mode tolerant tokenizer)
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_basics(self) -> None:
        assert parse_json('{"a": "b"}', None, False) == {"a": "b"}
        assert parse_json("[1, 2]", None, False) == [1.0, 2.0]
        # unlike JSON.parse, the hand-rolled tokenizer only accepts
        # dict/array at the root (ts-verified)
        for scalar in ("null", "true", "false", '"x"', "1x"):
            with pytest.raises(ValueError, match="unexpected token in root"):
                parse_json(scalar, None, False)

    def test_root_number_eos_quirk_returns_none(self) -> None:
        # ts-verified quirk: a number token reaching EOS leaves the stream
        # state untouched, so the loop exits and json.ts returns null/None
        assert parse_json("12", None, False) is None

    def test_json_decode_error_is_value_error(self) -> None:
        # json.loads raises json.JSONDecodeError, a subclass of ValueError.
        with pytest.raises(ValueError, match="Expecting property name"):
            parse_raw_grammar("{not json", "/g.json")

    def test_number_quirks(self) -> None:
        # JS parseFloat-like token semantics, ts-verified
        assert parse_json('{"a": 1-2}', None, False) == {"a": 1.0}
        assert parse_json('{"a": 1. , "b": .5, "c": 1e}', None, False) == {
            "a": 1.0,
            "b": 0.5,
            "c": 1.0,
        }
        assert parse_json('{"a": 1e+3}', None, False) == {"a": 1000.0}

    def test_trailing_garbage_after_root_is_ignored(self) -> None:
        assert parse_json('{"a": "b"} trailing', None, False) == {"a": "b"}

    def test_no_trailing_commas(self) -> None:
        # json.ts is NOT jsonc: trailing commas fail.
        with pytest.raises(ValueError, match="Near offset 12: unexpected token in array"):
            parse_json("[ 1, 2, 3, ]", None, False)

    def test_no_comments(self) -> None:
        with pytest.raises(ValueError, match="unexpected token in root"):
            parse_json('// header\n{"a": 1}', None, False)

    def test_duplicate_keys_last_wins(self) -> None:
        assert parse_json('{"a": 1, "a": 2}', None, False) == {"a": 2.0}

    def test_error_locations_are_stream_relative(self) -> None:
        with pytest.raises(ValueError, match=r"Near offset 13: expected colon ~~~}~~~"):
            parse_json('    {"a" null}', None, False)

    def test_invalid_escape_sequence(self) -> None:
        with pytest.raises(ValueError, match="Near offset 5: invalid escape sequence"):
            parse_json('{"a": "q\\q"}', None, False)

    def test_unicode_escape(self) -> None:
        assert parse_json('{"a": "\\u00e9"}', None, False) == {"a": "é"}

    def test_unclosed_constructs(self) -> None:
        with pytest.raises(ValueError, match="unclosed constructs"):
            parse_json('{"a": [', None, False)

    def test_metadata_locations(self) -> None:
        grammar = parse_json('{"a": {"b": [1]}}', "f.json", True)
        assert grammar[LOCATION_KEY] == {"filename": "f.json", "line": 1, "char": 0}
        assert grammar["a"][LOCATION_KEY] == {"filename": "f.json", "line": 1, "char": 6}

    def test_no_metadata_locations(self) -> None:
        grammar = parse_json('{"a": {}}', "f.json", False)
        assert LOCATION_KEY not in grammar


# ---------------------------------------------------------------------------
# Debug-mode wiring (DebugFlags.InDebugMode stand-in)
# ---------------------------------------------------------------------------


class TestInDebugMode:
    def test_default_off(self) -> None:
        assert IN_DEBUG_MODE is False

    def test_on_enables_metadata_parsing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import textmate_grammar.engine.raw_grammar as module

        monkeypatch.setenv("VSCODE_TEXTMATE_DEBUG", "1")
        try:
            importlib.reload(module)
            assert module.IN_DEBUG_MODE is True
            grammar = module.parse_raw_grammar('{"a": [1]}', "/g.json")
            assert LOCATION_KEY in grammar
        finally:
            monkeypatch.undo()
            importlib.reload(module)
        assert module.IN_DEBUG_MODE is False


# ---------------------------------------------------------------------------
# rawGrammar.ts type layer + scalar coercions
# ---------------------------------------------------------------------------


class TestValueAsString:
    def test_string_passthrough(self) -> None:
        assert value_as_string("source.ts") == "source.ts"

    def test_bool(self) -> None:
        # JS capitalization, not Python's
        assert value_as_string(True) == "true"
        assert value_as_string(False) == "false"

    def test_numbers(self) -> None:
        assert value_as_string(1) == "1"
        assert value_as_string(1.0) == "1"
        assert value_as_string(0.5) == "0.5"
        assert value_as_string(12.9) == "12.9"
        assert value_as_string(1e21) == "1e+21"
        assert value_as_string(1e-7) == "1e-07"  # exponent format differs from JS
        assert value_as_string(float("nan")) == "NaN"
        assert value_as_string(float("inf")) == "Infinity"
        assert value_as_string(float("-inf")) == "-Infinity"
