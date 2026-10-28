"""Unit tests for the ``plist.ts`` port (``engine.plist``).

Real-fixture assertions (MATLAB.tmLanguage, markdown.tmGrammar plist) were
verified against the upstream TypeScript parsers (vscode-textmate 9.3.2,
running the actual ``src/plist.ts`` under node). Inline-snippet expectations
were verified the same way, including error messages and offsets.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from textmate_grammar.engine.plist import parse_plist, parse_with_location

ROOT = Path(__file__).parents[3]
MATLAB_TMLANGUAGE = ROOT / "syntaxes/matlab/Matlab.tmbundle/Syntaxes/MATLAB.tmLanguage"
MARKDOWN_TMLANGUAGE = ROOT / "syntaxes/markdown/syntaxes/markdown.tmLanguage"

requires_matlab = pytest.mark.skipif(
    not MATLAB_TMLANGUAGE.exists(), reason="syntaxes submodule not initialized"
)
requires_markdown = pytest.mark.skipif(
    not MARKDOWN_TMLANGUAGE.exists(), reason="syntaxes submodule not initialized"
)


def _parse_fixture(path: Path) -> Any:
    return parse_plist(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Real fixtures: upstream MATLAB.tmbundle plist
# ---------------------------------------------------------------------------


@requires_matlab
class TestMatlabFixture:
    """MATLAB.tmLanguage, parsed from the upstream plist (ts-verified)."""

    @pytest.fixture
    @classmethod
    def grammar(cls) -> Any:
        return _parse_fixture(MATLAB_TMLANGUAGE)

    def test_top_level_keys(self, grammar: Any) -> None:
        assert set(grammar) == {
            "name",
            "fileTypes",
            "keyEquivalent",
            "scopeName",
            "uuid",
            "patterns",
            "injections",
            "repository",
        }
        assert grammar["name"] == "MATLAB"
        assert grammar["fileTypes"] == ["m"]
        assert grammar["keyEquivalent"] == "^~M"
        assert grammar["uuid"] == "007502A4-1DC5-44DD-816E-23F89D65F280"

    def test_scope_name(self, grammar: Any) -> None:
        assert grammar["scopeName"] == "source.matlab"

    def test_top_level_patterns(self, grammar: Any) -> None:
        patterns = grammar["patterns"]
        assert isinstance(patterns, list)
        assert len(patterns) == 3
        assert patterns[0] == {
            "include": "#rules_before_command_dual",
            "comment": "Rules are split into groups so #command_dual can be "
            "excluded in things like (), {}, []",
        }
        assert patterns[1] == {"include": "#command_dual"}
        assert patterns[2] == {"include": "#rules_after_command_dual"}

    def test_injections(self, grammar: Any) -> None:
        injections = grammar["injections"]
        assert isinstance(injections, dict)
        assert list(injections) == [
            "source.matlab -comment -entity -support -string -variable "
            "-interpolation -source.shell"
        ]
        assert injections["source.matlab -comment -entity -support -string "
                          "-variable -interpolation -source.shell"] == {
            "patterns": [{"include": "#readwrite_operations"}]
        }

    def test_repository_keys(self, grammar: Any) -> None:
        repository = grammar["repository"]
        assert isinstance(repository, dict)
        assert len(repository) == 41
        assert "function_call" in repository
        assert "comment_block" in repository
        assert "end_in_parentheses" in repository

    def test_known_repository_rule_function_call(self, grammar: Any) -> None:
        fc = grammar["repository"]["function_call"]
        assert set(fc) == {"comment", "name", "begin", "end", "beginCaptures", "endCaptures", "patterns"}
        assert fc["comment"] == (
            "\n\t\t\t\tFunction call; matrix or array index (subscript)"
            "\n\t\t\t\tWe don't include $self here to avoid matching command "
            "syntax inside (), [], {}\n\t\t\t"
        )
        assert fc["name"] == "meta.function-call.parens.matlab"
        assert fc["begin"] == "([a-zA-Z][a-zA-Z0-9_]*)\\s*(\\()"
        assert fc["end"] == "(\\)|(?<!\\.{3}.*)\\n)"
        assert fc["patterns"] == [
            {"include": "#end_in_parentheses"},
            {"include": "#rules_before_command_dual"},
            {"include": "#rules_after_command_dual"},
        ]

    def test_nested_captures(self, grammar: Any) -> None:
        fc = grammar["repository"]["function_call"]
        begin_captures = fc["beginCaptures"]
        assert set(begin_captures) == {"1", "2"}
        assert begin_captures["1"]["name"] == "entity.name.function.matlab"
        # capture rules may nest patterns, incl. the $self self-reference
        assert begin_captures["1"]["patterns"] == [
            {
                "comment": "Embed MATLAB into function calls to allow keyword "
                "grammar injection.",
                "include": "$self",
            }
        ]
        assert begin_captures["2"]["name"] == "punctuation.section.parens.begin.matlab"
        assert fc["endCaptures"] == {"0": {"name": "punctuation.section.parens.end.matlab"}}


# ---------------------------------------------------------------------------
# Real fixtures: upstream markdown plist grammar
# ---------------------------------------------------------------------------


@requires_markdown
class TestMarkdownFixture:
    """markdown.tmLanguage, parsed from the upstream plist (ts-verified)."""

    @pytest.fixture
    @classmethod
    def grammar(cls) -> Any:
        return _parse_fixture(MARKDOWN_TMLANGUAGE)

    def test_scope_name(self, grammar: Any) -> None:
        assert grammar["scopeName"] == "text.html.markdown"

    def test_patterns_count(self, grammar: Any) -> None:
        assert grammar["patterns"] == [
            {"include": "#frontMatter"},
            {"include": "#block"},
        ]

    def test_repository_keys(self, grammar: Any) -> None:
        assert len(grammar["repository"]) == 87
        assert "block" in grammar["repository"]
        assert "heading" in grammar["repository"]

    def test_block_repository_entry(self, grammar: Any) -> None:
        block = grammar["repository"]["block"]
        assert [rule["include"] for rule in block["patterns"]] == [
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

    def test_integer_value_coercion(self, grammar: Any) -> None:
        # ``<integer>1</integer>`` parses as the JS number 1 (Python float).
        assert grammar["repository"]["bold"]["patterns"][0]["applyEndPatternLast"] == 1


class TestParseWithLocation:
    """``$vscodeTextmateLocation`` embedding (debug path), ts-verified."""

    @requires_markdown
    def test_markdown_locations(self) -> None:
        grammar = parse_with_location(
            MARKDOWN_TMLANGUAGE.read_text(encoding="utf-8"),
            "/path/to/markdown.tmLanguage",
            "$vscodeTextmateLocation",
        )
        assert grammar["$vscodeTextmateLocation"] == {
            "filename": "/path/to/markdown.tmLanguage",
            "line": 4,
            "char": 8,
        }
        assert grammar["repository"]["block"]["$vscodeTextmateLocation"] == {
            "filename": "/path/to/markdown.tmLanguage",
            "line": 30,
            "char": 12,
        }
        assert grammar["repository"]["frontMatter"]["$vscodeTextmateLocation"] == {
            "filename": "/path/to/markdown.tmLanguage",
            "line": 3929,
            "char": 12,
        }

    @requires_matlab
    def test_matlab_location(self) -> None:
        grammar = parse_with_location(
            MATLAB_TMLANGUAGE.read_text(encoding="utf-8"),
            "/p/MATLAB.tmLanguage",
            "$vscodeTextmateLocation",
        )
        assert grammar["repository"]["function_call"]["$vscodeTextmateLocation"] == {
            "filename": "/p/MATLAB.tmLanguage",
            "line": 1691,
            "char": 8,
        }

    def test_no_location_key_without_filename(self) -> None:
        grammar = parse_plist("<dict><key>a</key><dict/></dict>")
        assert "$vscodeTextmateLocation" not in grammar


# ---------------------------------------------------------------------------
# Inline snippets, verified against the TS parser
# ---------------------------------------------------------------------------


class TestValueCoercions:
    def test_string(self) -> None:
        assert parse_plist("<dict><key>a</key><string>b</string></dict>") == {"a": "b"}

    def test_integer(self) -> None:
        assert parse_plist("<dict><key>a</key><integer>-5</integer></dict>") == {"a": -5.0}
        # JS parseInt radix-10 quirks, verified against the TS parser
        assert parse_plist("<dict><key>a</key><integer>0x10</integer></dict>") == {"a": 0.0}
        assert parse_plist("<dict><key>a</key><integer>12.9</integer></dict>") == {"a": 12.0}
        assert parse_plist("<dict><key>a</key><integer>1e5</integer></dict>") == {"a": 1.0}

    def test_real(self) -> None:
        assert parse_plist("<dict><key>a</key><real>10.5</real></dict>") == {"a": 10.5}
        assert parse_plist("<dict><key>a</key><real>1.5e3</real></dict>") == {"a": 1500.0}
        # JS parseFloat, verified: <real>Infinity</real> → Infinity
        assert parse_plist("<real>Infinity</real>") == float("inf")

    def test_real_nan_fails(self) -> None:
        with pytest.raises(ValueError, match=r"Near offset 34: cannot parse float"):
            parse_plist("<dict><key>a</key><real>abc</real></dict>")

    def test_integer_nan_fails(self) -> None:
        with pytest.raises(ValueError, match=r"Near offset 38: cannot parse integer"):
            parse_plist("<dict><key>a</key><integer> </integer></dict>")

    def test_true_false(self) -> None:
        assert parse_plist(
            "<dict><key>a</key><true>ignored</true><key>b</key><false/></dict>"
        ) == {"a": True, "b": False}

    def test_date(self) -> None:
        grammar = parse_plist("<dict><key>a</key><date>2020-01-02T10:00:00Z</date></dict>")
        assert grammar["a"].isoformat() == "2020-01-02T10:00:00+00:00"

    def test_invalid_date_nan(self) -> None:
        grammar = parse_plist("<dict><key>a</key><date>not a date</date></dict>")
        assert math.isnan(grammar["a"])

    def test_data_passthrough(self) -> None:
        assert parse_plist("<dict><key>a</key><data>QUI=</data></dict>") == {"a": "QUI="}
        assert parse_plist("<data>QUI=</data>") == "QUI="


class TestXmlSkipping:
    def test_prolog_comment_doctype(self) -> None:
        content = (
            '<?xml version="1.0"?>\n'
            "<!DOCTYPE plist PUBLIC '-//Apple//DTD PLIST 1.0//EN'>\n"
            "<!-- top-level comment -->\n"
            "<plist version='1.0'>\n<dict>\n<key>a</key><string>b</string>\n</dict>"
        )
        assert parse_plist(content) == {"a": "b"}

    def test_no_cdata_support_quirk(self) -> None:
        # Upstream has no CDATA support: the block is skipped to the next '>'.
        assert parse_plist(
            "<dict><key>a</key><array><![CDATA[skj]]></array></dict>"
        ) == {"a": []}

    def test_bom_skipped(self) -> None:
        with pytest.raises(ValueError, match="Near offset 13: unexpected <key>"):
            parse_plist("﻿<key>a</key>")

    def test_comment_inside_value_stays_literal(self) -> None:
        # Verified quirk: comments are only recognized outside values.
        assert parse_plist("  <dict>  <key>a  </key>  <string>b<!--c--></string> </dict> ") == {
            "a  ": "b<!--c-->"
        }


class TestEntities:
    def test_named_entities(self) -> None:
        assert parse_plist("<dict><key>a</key><string>&amp;&lt;&gt;&quot;&apos;</string></dict>") == {
            "a": '&<>"\''
        }

    def test_numeric_entities(self) -> None:
        assert parse_plist("<dict><key>a</key><string>&#72;</string></dict>") == {"a": "H"}
        assert parse_plist("<dict><key>a</key><string>&#x41;</string></dict>") == {"a": "A"}

    def test_uppercase_hex_not_decoded_quirk(self) -> None:
        # Upstream regex only knows lowercase hex digits.
        assert parse_plist("<dict><key>a</key><string>&#x4A;&amp;&#72;</string></dict>") == {
            "a": "&#x4A;&H"
        }


class TestQuirks:
    def test_closing_tag_prefix_match(self) -> None:
        # ``</dictionary>`` closes a ``<dict>`` (prefix matching).
        assert parse_plist("<dict><key>a</key><string>b</dictionary>") == {"a": "b"}

    def test_unterminated_value_at_eof(self) -> None:
        assert parse_plist('<dict><key>a</key><string>abc') == {"a": "abc"}

    def test_self_closed_dict(self) -> None:
        assert parse_plist("<dict/>") == {}
        assert parse_plist('<plist><dict><key>a</key><string>b</string></plist></dict>') == {
            "a": "b"
        }
        assert parse_plist("<dict/>") == {}
        assert parse_plist("") is None
        # plist.ts (unlike json.ts) never checks for unclosed containers
        assert parse_plist("<dict>") == {}
        assert parse_plist("<dict><key>a</key>") == {}

    def test_self_closed_string_is_empty(self) -> None:
        assert parse_plist("<dict><key>a</key><string/></dict>") == {"a": ""}

    def test_open_tag_attributes_and_whitespace(self) -> None:
        assert parse_plist("<dict><key>a</key>  <string   >b</string></dict>") == {"a": "b"}


class TestErrors:
    @pytest.mark.parametrize(
        ("content", "message"),
        [
            ("</dict><dict></dict>", r"Near offset 7: unexpected </dict> ~~~<dict></dict>~~~"),
            ("<dict><string>x</string></dict>", r"Near offset 24: missing <key> ~~~</dict>"),
            ("<dict><key>a</key><key>b</key></dict>", r"Near offset 30: too many <key> ~~~</dict>"),
            ("hello world", r"Near offset 1: expected < ~~~ello world~~~"),
            ("abc<", r"Near offset 1: expected < ~~~bc<~~~"),
            ("a;", r"Near offset 1: expected < ~~~;~~~"),
            ("<", r"Near offset 1: unexpected end of input ~~~~~~"),
            ("</dict", r"Near offset 6: unexpected </dict> ~~~~~~"),
            ("element/>", r"Near offset 1: expected < ~~~lement/>~~~"),
            (
                "<element/>",
                r"Near offset 10: unexpected opened tag element ~~~~~~",
            ),
            (
                "<dict><key>a</key><bogus/></dict>",
                r"Near offset 26: unexpected opened tag bogus ~~~</dict>~~~",
            ),
            (
                "<dict><key>a</key><array></dict></array>",
                r"Near offset 32: unexpected </dict> ~~~</array>~~~",
            ),
            (
                "<dict><key>a</key><string>b</dict>>",
                r"Near offset 35: expected < ~~~~~~",
            ),
        ],
    )
    def test_error_messages(self, content: str, message: str) -> None:
        with pytest.raises(ValueError, match=r"^" + message):
            parse_plist(content)

    def test_unexpected_opened_tag_no_match(self) -> None:
        with pytest.raises(ValueError, match="unexpected opened tag dictaudrey"):
            parse_plist("<dictaudrey")
