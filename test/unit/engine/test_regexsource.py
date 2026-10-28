"""Tests for :mod:`textmate_grammar.engine.regexsource` — port of vscode-textmate's
``RegExpSource``, ``RegExpSourceList`` and ``CompiledRule`` (rule.ts) plus the
``RegexSource``/``escapeRegExpCharacters`` utils they lean on (utils.ts).

vscode-textmate has no dedicated RegExpSource unit test file upstream — this suite is
hand-written against rule.ts semantics; the comments keep the behavior pinned to the
reference implementation's logic.
"""

from __future__ import annotations

import pytest

from textmate_grammar.engine.oniglib import DEFAULT_ONIG_LIB, IOnigCaptureIndex
from textmate_grammar.engine.regexsource import (
    CompiledRule,
    RegExpSource,
    RegExpSourceList,
    RegexSource,
    escapeRegExpCharacters,
)

SENTINEL = "\uffff"  # the neutralized-anchor character rule.ts:666-714 writes


def captures(*spans: tuple[int, int]) -> list[IOnigCaptureIndex]:
    return [IOnigCaptureIndex(start, end, end - start) for start, end in spans]


class TestEscapeRegExpCharacters:
    def test_leaves_common_text_alone(self) -> None:
        assert escapeRegExpCharacters("abc 123") == "abc 123"

    def test_escapes_regex_specials(self) -> None:
        assert escapeRegExpCharacters("a.b(c[d])") == r"a\.b\(c\[d\]\)"
        assert escapeRegExpCharacters("$*") == r"\$\*"

class TestConstructor:
    def test_plain_source_stays_verbatim(self) -> None:
        source = RegExpSource(r"abc[^a-z]\+", 1)
        assert source.source == r"abc[^a-z]\+"
        assert source.has_anchor is False
        assert source.has_back_references is False
        assert source.rule_id == 1

    def test_empty_source(self) -> None:
        # rule.ts:590 — the truthy check branches; '' is handled by the else
        source = RegExpSource("", 1)
        assert source.source == ""
        assert source.has_anchor is False

    def test_trailing_backslash_is_harmless(self) -> None:
        # rule.ts:600-613 — a backslash without a following character can't be read
        source = RegExpSource("abc\\", 1)
        assert source.source == "abc\\"
        assert source.has_anchor is False

    def test_z_is_reworked_to_lookaround(self) -> None:
        # rule.ts:603-606 — `\z` → `$(?!\n)(?<!\n)`
        source = RegExpSource(r"a\zb", 1)
        assert source.source == r"a$(?!\n)(?<!\n)b"

    def test_z_rework_is_escaped_char_aware(self) -> None:
        # '\z' only triggers when the backslash is a real escape start; a plain
        # 'z' stays
        assert RegExpSource(r"xyz", 1).source == r"xyz"
        assert RegExpSource(r"\nz", 1).source == r"\nz"
        # ... and `\\z` (escaped backslash + literal 'z') is not reworked either,
        # because the walk consumes escape pairs as one unit (rule.ts:601-611)
        assert RegExpSource(r"\\z", 1).source == r"\\z"

    def test_multiple_z_reworks(self) -> None:
        source = RegExpSource(r"a\zb\zc", 1)
        assert source.source == r"a$(?!\n)(?<!\n)b$(?!\n)(?<!\n)c"

    def test_z_rework_keeps_earlier_anchors(self) -> None:
        # the \z rewrite must not lose the \G escape that preceded it
        source = RegExpSource(r"\G\z", 1)
        assert source.has_anchor is True
        assert source.source == r"\G$(?!\n)(?<!\n)"


class TestAnchorDetection:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (r"\Aabc", True),
            (r"\Gabc", True),
            (r"a\Ab\Gc", True),
            ("abc", False),
            # a letter 'A'/'G' is not an anchor
            (r"AG", False),
            (r"\nA", False),
        ],
    )
    def test_has_anchor(self, raw: str, expected: bool) -> None:
        assert RegExpSource(raw, 1).has_anchor is expected

    def test_anchor_after_escaped_backslash(self) -> None:
        # `\\G` = escaped backslash + 'G': the walk consumes the pair, then reads
        # 'G' as a plain char — not an anchor
        assert RegExpSource(r"\\G", 1).has_anchor is False
        # ... which consumes the escape pair → the source is unchanged too
        assert RegExpSource(r"\\G", 1).source == r"\\G"

    def test_anchors_in_char_class_are_flagged_like_upstream(self) -> None:
        # rule.ts:600-613 has no character-class awareness: `[\G]` contains an
        # escaped 'G' and is flagged. Enshrined here on purpose as upstream behavior.
        assert RegExpSource(r"[\G]", 1).has_anchor is True

    def test_caret_in_char_class_is_not_an_anchor(self) -> None:
        # the task-card sharp edge: '^' is never the anchor marker; anchors are
        # only the escape pairs \A / \G (rule.ts:607-609)
        assert RegExpSource(r"[a^b]", 1).has_anchor is False
        assert RegExpSource(r"^abc", 1).has_anchor is False
        assert RegExpSource(r"[^]", 1).has_anchor is False


class TestBackReferencesDetection:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (r"abc\1", True),
            (r"abc\12", True),
            (r"a\0b", True),
            ("abc", False),
            (r"\n", False),  # \n is an escaped 'n'
            (r"\\1", True),  # upstream quirk: the trailing \1 pair is detected
        ],
    )
    def test_has_back_references(self, raw: str, expected: bool) -> None:
        assert RegExpSource(raw, 1).has_back_references is expected


class TestResolveBackReferences:
    def test_substitutes_captured_text(self) -> None:
        # capture 0 is the full-match span; \1 addresses the (begin) group echoed
        source = RegExpSource(r"^a\1b$", 1)
        assert source.resolve_back_references("0123456789", captures((0, 3), (5, 7))) == r"^a56b$"

    def test_escapes_capture_content(self) -> None:
        # rule.ts:662 — escapeRegExpCharacters over the captured text
        source = RegExpSource(r"\1", 1)
        assert source.resolve_back_references("x.*y", captures((0, 1), (1, 3))) == r"\.\*"

    def test_out_of_range_backreference_is_empty(self) -> None:
        # rule.ts:662 — capturedValues[...] || '' on missing captures
        source = RegExpSource(r"a\3b", 1)
        assert source.resolve_back_references("abcdefgh", captures((0, 2))) == "ab"

    def test_multi_digit_backreference(self) -> None:
        # rule.ts:661 — parseInt(g1, 10): '12' refers to capture 12, not '1' then '2';
        # the index counts over the capture list that includes group 0
        spans = [(0, 1), *[(i, i + 1) for i in range(1, 13)]]  # captures 0..12
        source = RegExpSource(r"\12", 1)
        assert source.resolve_back_references("abcdefghijklmnop", captures(*spans)) == "m"

    def test_unmatched_group_is_empty(self) -> None:
        # unmatched groups arrive clamped to (0,0) from the oniglib adapter and
        # slice to '' exactly like upstream's lineText.substring(0, 0)
        source = RegExpSource(r"x\1y", 1)
        assert source.resolve_back_references("abc", captures((0, 0), (0, 0))) == "xy"


class TestAnchorCache:
    def test_all_four_variants(self) -> None:
        # the backslash of an anchor pair stays; only its escape target ('A'/'G')
        # is rewritten to the sentinel in the variants where it is not allowed
        source = RegExpSource(r"\A\Gabc", 1)
        assert source.resolve_anchors(False, False) == "\\" + SENTINEL + "\\" + SENTINEL + "abc"
        assert source.resolve_anchors(False, True) == "\\" + SENTINEL + r"\Gabc"
        assert source.resolve_anchors(True, False) == r"\A" + "\\" + SENTINEL + "abc"
        assert source.resolve_anchors(True, True) == r"\A\Gabc"

    def test_keeping_verbatim_when_allowed(self) -> None:
        source = RegExpSource(r"\Gafter", 1)
        assert source.resolve_anchors(True, True).startswith("\\G")
        assert source.resolve_anchors(False, True).startswith("\\G")
        # ... but the not-allowed variant neutralizes exactly the 'G' character
        assert source.resolve_anchors(False, False) == "\\" + SENTINEL + "after"
        assert source.resolve_anchors(True, False) == "\\" + SENTINEL + "after"

    def test_other_escapes_were_untouched(self) -> None:
        source = RegExpSource(r"\G\n\t\A", 1)
        # only the escape targets 'A'/'G' become the sentinel; '\n' and '\t' stay
        assert source.resolve_anchors(False, False) == "\\" + SENTINEL + r"\n\t" + "\\" + SENTINEL
    def test_non_anchored_source_is_verbatim(self) -> None:
        # rule.ts:717-719 — resolveAnchors short-circuits without a cache
        source = RegExpSource("ab\\nc", 1)
        assert source.resolve_anchors(False, False) == "ab\\nc"
        assert source.resolve_anchors(True, True) == "ab\\nc"

    def test_clone(self) -> None:
        source = RegExpSource(r"\Gz", 1)
        clone = source.clone()
        assert (clone.source, clone.rule_id, clone.has_anchor) == (r"\Gz", 1, True)
        assert clone.resolve_anchors(False, False) == "\\" + SENTINEL + "z"

    def test_set_source_rebuilds_cache(self) -> None:
        source = RegExpSource(r"\A", 1)
        assert source.resolve_anchors(False, False) == "\\" + SENTINEL
        # identical source: no-op (rule.ts:646-648)
        source.set_source(r"\A")
        source.set_source(r"\G")
        assert source.source == r"\G"
        assert source.resolve_anchors(False, False) == "\\" + SENTINEL
        # has_anchor is only recomputed at construction (rule.ts:645-654)
        source = RegExpSource("plain", 1)
        source.set_source(r"\Gnow")
        assert source.source == r"\Gnow"


class TestRegexSource:
    def test_has_captures(self) -> None:
        assert RegexSource.hasCaptures(None) is False
        assert RegexSource.hasCaptures("") is False
        assert RegexSource.hasCaptures("$1") is True
        assert RegexSource.hasCaptures("${2:/downcase}") is True
        assert RegexSource.hasCaptures("$n") is False

    def test_replace_captures_simple(self) -> None:
        # $n addresses into the capture list; index 0 is the full-match span
        assert (
            RegexSource.replaceCaptures("main.$1", "abc.def.ghi", captures((0, 11), (4, 7)))
            == "main.def"
        )

    def test_replace_captures_commands(self) -> None:
        caps = captures((0, 3), (4, 7))
        assert RegexSource.replaceCaptures("${1:/upcase} x", "abc def", caps) == "DEF x"
        assert RegexSource.replaceCaptures("${1:/downcase} x", "DEF def", caps) == "def x"

    def test_replace_captures_missing_reference_stays(self) -> None:
        # utils.ts:83-97 — no capture at $4 → '$4' stays verbatim
        assert RegexSource.replaceCaptures("$4a", "abc", captures((0, 3))) == "$4a"

    def test_replace_captures_strips_leading_dots(self) -> None:
        # utils.ts:86-88
        assert RegexSource.replaceCaptures("$0", "..foo", captures((0, 5))) == "foo"

    def test_replace_captures_unmatched_is_empty(self) -> None:
        # unmatched groups arrive clamped to (0,0) and slice to ''
        assert RegexSource.replaceCaptures("x$1", "abc", captures((0, 3), (0, 0))) == "x"


class TestCompiledRule:
    def test_rules_resolve_back_from_pattern_index(self) -> None:
        compiled = CompiledRule(DEFAULT_ONIG_LIB, ["x", "y", "z"], [3, 7, 9])
        match = compiled.find_next_match_sync("aye", 0)
        assert match is not None
        assert (match.rule_id, match.capture_indices) == (
            7,
            (IOnigCaptureIndex(start=1, end=2, length=1),),
        )
        # a start after every match position: no result
        assert compiled.find_next_match_sync("aye", 2) is None

    def test_debug_representation(self) -> None:
        compiled = CompiledRule(DEFAULT_ONIG_LIB, ["xy", "z"], [4, 5])
        assert str(compiled) == "   - 4: xy\n   - 5: z"

    def test_dispose_shuts_scanning_down(self) -> None:
        compiled = CompiledRule(DEFAULT_ONIG_LIB, ["x"], [1])
        compiled.dispose()
        with pytest.raises(RuntimeError):
            compiled.find_next_match_sync("x", 0)


class TestRegExpSourceList:
    def test_push_unshift_and_len(self) -> None:
        pattern_list = RegExpSourceList()
        first, second = RegExpSource("a", 1), RegExpSource("b", 2)
        pattern_list.push(second)
        pattern_list.unshift(first)
        assert len(pattern_list) == 2
        # unshift puts its item in front (rule.ts:795-798): the compiled pattern
        # order is ['a', 'b'] even though 'b' was added first
        compiled = pattern_list.compile(DEFAULT_ONIG_LIB)
        leftmost = compiled.find_next_match_sync("ab", 0)
        assert leftmost is not None
        assert leftmost.rule_id == 1
        shifted = compiled.find_next_match_sync("ab", 1)
        assert shifted is not None
        assert shifted.rule_id == 2

    def test_compile_is_cached(self) -> None:
        pattern_list = RegExpSourceList()
        pattern_list.push(RegExpSource("a", 1))
        compiled = pattern_list.compile(DEFAULT_ONIG_LIB)
        assert pattern_list.compile(DEFAULT_ONIG_LIB) is compiled

    def test_without_anchors_compile_ag_shares_the_plain_compile(self) -> None:
        # rule.ts:821-822 — non-anchored lists always return the cached compile
        pattern_list = RegExpSourceList()
        pattern_list.push(RegExpSource("xa", 1))
        compiled = pattern_list.compile(DEFAULT_ONIG_LIB)
        for allow_a in (False, True):
            for allow_g in (False, True):
                assert pattern_list.compile_ag(DEFAULT_ONIG_LIB, allow_a, allow_g) is compiled

    def test_anchored_lists_get_one_variant_per_combination(self) -> None:
        pattern_list = RegExpSourceList()
        pattern_list.push(RegExpSource(r"\Gx", 1))
        pattern_list.push(RegExpSource(r"y\Ay", 2))
        plain = pattern_list.compile_ag(DEFAULT_ONIG_LIB, True, True)
        assert plain is pattern_list.compile_ag(DEFAULT_ONIG_LIB, True, True)
        no_go = pattern_list.compile_ag(DEFAULT_ONIG_LIB, True, False)
        no_a = pattern_list.compile_ag(DEFAULT_ONIG_LIB, False, False)
        assert len({id(plain), id(no_go), id(no_a)}) == 3

    def test_compiled_variant_changes_the_match(self) -> None:
        # the same anchored pattern compiled under allowed vs. disallowed anchors:
        # with \G allowed the scan matches at the passed offset, without it it can't
        pattern_list = RegExpSourceList()
        pattern_list.push(RegExpSource(r"\Gx", 1))
        go_allowed = pattern_list.compile_ag(DEFAULT_ONIG_LIB, True, True)
        go_denied = pattern_list.compile_ag(DEFAULT_ONIG_LIB, False, False)
        assert go_allowed.find_next_match_sync("xxx", 2) is not None
        assert go_denied.find_next_match_sync("xxx", 2) is None
        # the plain compile keeps \G allowed and is a separate cached scan target
        plain = pattern_list.compile(DEFAULT_ONIG_LIB)
        assert plain.find_next_match_sync("xxx", 1) is not None

    def test_set_source_busts_the_cache(self) -> None:
        # rule.ts:804-810
        pattern_list = RegExpSourceList()
        pattern_list.push(RegExpSource("a", 1))
        compiled = pattern_list.compile(DEFAULT_ONIG_LIB)
        pattern_list.set_source(0, "a")  # same source: no cache bust
        assert pattern_list.compile(DEFAULT_ONIG_LIB) is compiled
        pattern_list.set_source(0, "b")
        assert pattern_list.compile(DEFAULT_ONIG_LIB) is not compiled
