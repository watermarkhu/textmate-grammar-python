"""Tests for :mod:`textmate_grammar.engine.oniglib` — the port of vscode-textmate's
``onigLib.ts`` (adapter over onigurumacffi, standing in for ``vscode-oniguruma``).

The load-bearing semantic pinned here: ``\\G`` binds to the scan offset passed per
find call, not to a stored anchor — see oniglib.py and the parity plan.
"""

from __future__ import annotations

import pytest
from onigurumacffi import OnigError

from textmate_grammar.engine import oniglib
from textmate_grammar.engine.oniglib import (
    FindOption,
    IOnigCaptureIndex,
    OnigString,
    disposeOnigString,
)

SCANNER = oniglib.DEFAULT_ONIG_LIB.create_onig_scanner


def capture_tuples(match: oniglib.IOnigMatch) -> tuple[tuple[int, int], ...]:
    return tuple((capture.start, capture.end) for capture in match.capture_indices)


class TestFindNextMatchSync:
    def test_leftmost_beats_earlier_pattern_starting_later(self) -> None:
        # 'b' (index 0) matches at 2; 'ab' (index 1) matches at 1 → leftmost wins
        match = oniglib.OnigScanner(["b", "ab"]).find_next_match_sync("xaby", 0)
        assert match is not None
        assert (match.index, capture_tuples(match)) == (1, ((1, 3),))

    def test_leftmost_over_earlier_pattern_index(self) -> None:
        # both start at 0; smallest offset wins
        match = oniglib.OnigScanner(["z", "az"]).find_next_match_sync("az", 0)
        assert match is not None
        assert (match.index, capture_tuples(match)) == (1, ((0, 2),))

    def test_tie_breaks_to_lowest_pattern_index(self) -> None:
        # 'a' matches at 0 with span (0,1); 'ab' also matches at 0 with span (0,2).
        # vscode-oniguruma keeps the result of the first pattern on equal positions.
        match = oniglib.OnigScanner(["a", "ab"]).find_next_match_sync("ab", 0)
        assert match is not None
        assert (match.index, capture_tuples(match)) == (0, ((0, 1),))

    def test_no_match_returns_none(self) -> None:
        assert SCANNER(["x"]).find_next_match_sync("abc", 0) is None

    def test_scan_start_position_skips_before(self) -> None:
        scanner = SCANNER(["x"])
        match = scanner.find_next_match_sync("xxx", 1)
        assert match is not None
        assert (match.index, capture_tuples(match)) == (0, ((1, 2),))

    def test_accepts_onig_string(self) -> None:
        string = oniglib.DEFAULT_ONIG_LIB.create_onig_string("abcd")
        match = SCANNER(["cd"]).find_next_match_sync(string, 0)
        assert match is not None
        assert capture_tuples(match) == ((2, 4),)
        disposeOnigString(string)  # port of disposeOnigString, a no-op

    def test_unicode_offsets_are_code_points(self) -> None:
        # upstream scans UTF-8 bytes and maps indices back to UTF-16 code units;
        # here the translator is Python's native code-point indexing
        match = SCANNER(["ü"]).find_next_match_sync("füü", 0)
        assert match is not None
        assert capture_tuples(match) == ((1, 2),)

    def test_captures_unmatched_group_is_clamped(self) -> None:
        # oniguruma reports unmatched groups with -1 offsets; vscode-oniguruma
        # clamps those through convertUtf8OffsetToUtf16 to start == end == 0
        match = SCANNER(["(a)(b)?(c)"]).find_next_match_sync("ac", 0)
        assert match is not None
        assert match.capture_indices == (
            IOnigCaptureIndex(start=0, end=2, length=2),  # full match: 'ac'
            IOnigCaptureIndex(start=0, end=1, length=1),  # (a)
            IOnigCaptureIndex(start=0, end=0, length=0),  # (b)? — unmatched
            IOnigCaptureIndex(start=1, end=2, length=1),  # (c)
        )

    def test_captures_empty_group(self) -> None:
        match = SCANNER(["a(b*)"]).find_next_match_sync("az", 0)
        assert match is not None
        assert capture_tuples(match) == ((0, 1), (1, 1))

    def test_invalid_pattern_raises(self) -> None:
        # vscode-oniguruma throws the oniguruma error at scanner creation
        with pytest.raises(OnigError):
            SCANNER(["a(["])


class TestGoAnchorBindsToScanOffset:
    """The critical semantic: a ``\\G`` in a compiled pattern matches exactly at
    the start offset of each ``find_next_match_sync`` call (one compiled pattern,
    many offsets)."""

    def test_same_pattern_matches_at_offset_searches(self) -> None:
        scanner = SCANNER([r"\Gx"])
        for start, expected in ((0, (0, 1)), (1, (1, 2)), (2, (2, 3))):
            match = scanner.find_next_match_sync("xxxz", start)
            assert match is not None, f"expected a match at {start}"
            assert capture_tuples(match) == (expected,)
        assert scanner.find_next_match_sync("xxxz", 3) is None

    def test_go_after_nonmatching_prefix(self) -> None:
        scanner = SCANNER([r"\G\d+"])
        # only from offset 3 on does the scan position sit where '1234' starts
        assert scanner.find_next_match_sync("abc1234", 0) is None
        match = scanner.find_next_match_sync("abc1234", 3)
        assert match is not None
        assert capture_tuples(match) == ((3, 7),)

    def test_not_begin_position_option_fails_go_anchor(self) -> None:
        # FindOption.NotBeginPosition: (start) isn't considered as the begin of
        # the search — \\G fails (onigLib.ts:34-36, getFindOptions for allowG=False)
        scanner = SCANNER([r"\Gx"])
        assert scanner.find_next_match_sync("xx", 0) is not None
        assert (
            scanner.find_next_match_sync("xx", 0, FindOption.NOT_BEGIN_POSITION) is None
        )

    def test_not_end_string_and_not_begin_string_options(self) -> None:
        # ONIG_OPTIONS translated verbatim: \z / \Z fail, \A fails
        scanner = SCANNER([r"ab\z"])
        assert scanner.find_next_match_sync("ab", 0) is not None
        assert scanner.find_next_match_sync("ab", 0, FindOption.NOT_END_STRING) is None
        scanner = SCANNER([r"\Aab"])
        assert scanner.find_next_match_sync("ab", 0) is not None
        assert scanner.find_next_match_sync("ab", 0, FindOption.NOT_BEGIN_STRING) is None


class TestFindBestMatch:
    def test_anchor_binds_to_position_when_allowed(self) -> None:
        scanner = SCANNER([r"\Gx"])
        match = scanner.find_best_match(2, "xxxz", has_anchor=True)
        assert match is not None
        assert capture_tuples(match) == ((2, 3),)

    def test_anchor_fails_when_not_allowed(self) -> None:
        scanner = SCANNER([r"\Gx"])
        assert scanner.find_best_match(2, "xxxz", has_anchor=False) is None

    def test_regular_patterns_ignores_anchor_flag(self) -> None:
        scanner = SCANNER(["x"])
        match = scanner.find_best_match(1, "xxxz", has_anchor=False)
        assert match is not None
        assert capture_tuples(match) == ((1, 2),)

    def test_back_references_flag_is_bookkeeping_only(self) -> None:
        # \\n backreferences are resolved before scanning (regexsource.resolve_back_
        # references), so the flag changes nothing about the scan itself
        scanner = SCANNER(["x"])
        without = scanner.find_best_match(0, "xxz")
        with_flag = scanner.find_best_match(0, "xxz", has_back_references=True)
        assert without == with_flag


class TestOnigLibSurface:
    def test_default_lib_emulates_vscode_oniguruma_wiring(self) -> None:
        # the shell of main.ts: create scanners and strings from one lib object
        onig = oniglib.DEFAULT_ONIG_LIB
        scanner = onig.create_onig_scanner([r"\d+"])
        string = onig.create_onig_string("on 42")
        match = scanner.find_next_match_sync(string, 0)
        assert match is not None
        assert (match.index, capture_tuples(match)) == (0, ((3, 5),))

    def test_scanner_sources_round_trip(self) -> None:
        scanner = oniglib.OnigScanner(["a", "b"])
        assert scanner.sources == ("a", "b")

    def test_onig_string_content(self) -> None:
        assert OnigString("hello").content == "hello"
