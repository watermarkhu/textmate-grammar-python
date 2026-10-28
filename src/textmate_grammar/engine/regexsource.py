"""Port of the ``RegExpSource`` machinery from vscode-textmate's ``src/rule.ts``.

This module ports from ``rule.ts`` (version 9.3.2, the pinned reference clone):
``IRegExpSourceAnchorCache`` (rule.ts:575-580), ``RegExpSource`` (rule.ts:582-735),
``RegExpSourceList`` (rule.ts:744-856) and ``CompiledRule`` (rule.ts:858-894), plus
the two regex-source helpers they depend on from ``src/utils.ts``:
``escapeRegExpCharacters`` (utils.ts:159-161) and the ``RegexSource`` class
(utils.ts:66-115, ``$n``/``${n:/command}`` capture expansion used for scope names).

Semantics are 1:1 with the reference; naming is pythonic and every non-obvious
piece carries a comment referencing the ported lines of rule.ts / utils.ts.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .oniglib import FindOption, IOnigCaptureIndex, IOnigLib, OnigString

__all__: tuple[str, ...] = (
    "AnchorCache",
    "CompiledRule",
    "IFindNextMatchResult",
    "RegExpSource",
    "RegExpSourceList",
    "RegexSource",
    "escapeRegExpCharacters",
)

# rule.ts:10-11
_HAS_BACK_REFERENCES = re.compile(r"\\(\d+)")
_BACK_REFERENCING_END = re.compile(r"\\(\d+)")

# utils.ts:160 — characters that are special in regular expressions
_ESCAPE_REGEXP_CHARACTERS = re.compile(r"[\\|([{}\])\].?*+^$]")

# utils.ts:66 — occurrences of $n and ${n:/command} captures in scope names
_CAPTURING_REGEX_SOURCE = re.compile(r"\$(\d+)|\$\{(\d+):\/(downcase|upcase)\}")


def escapeRegExpCharacters(value: str) -> str:
    """Port of utils.ts ``escapeRegExpCharacters`` (utils.ts:159-161) — escapes the
    characters that are special in regular expressions in the given string."""
    return _ESCAPE_REGEXP_CHARACTERS.sub(lambda match: "\\" + match[0], value)


class RegexSource:
    """Port of utils.ts's static ``RegexSource`` class (utils.ts:66-115): expands
    ``$n`` and ``${n:/downcase|upcase}`` captures in scope names against the text
    a pattern captured."""

    @staticmethod
    def hasCaptures(regex_source: str | None) -> bool:
        """Port of ``RegexSource.hasCaptures`` (utils.ts:68-75)."""
        if regex_source is None:
            return False
        return _CAPTURING_REGEX_SOURCE.search(regex_source) is not None

    @staticmethod
    def replaceCaptures(
        regex_source: str,
        capture_source: str,
        capture_indices: Sequence[IOnigCaptureIndex],
    ) -> str:
        """Port of ``RegexSource.replaceCaptures`` (utils.ts:77-115): replaces each
        ``$n``/``${n:/command}`` occurrence with the content capture ``n`` covers in
        ``capture_source``, applying the optional case command. References to
        captures that don't exist are left verbatim. Unmatched captures (oniguruma
        ``-1`` offsets) contribute '' via the empty substring slice.
        """

        def _replace(match: re.Match[str]) -> str:
            # utils.ts:81 — parseInt(index || commandIndex, 10): the index group of
            # ``$n``, or the one of ``${n:/...}``
            index = match[1] or match[2]
            if index is None:  # unreachable: both alternatives carry a digit group
                return match[0]
            target = int(index)
            # utils.ts:83-88 — a reference to an undefined capture leaves the match
            # text unchanged (JS out-of-bounds → undefined → falsy)
            if target < len(capture_indices) and capture_indices[target]:
                result = capture_source[capture_indices[target].start : capture_indices[target].end]
                # utils.ts:86-88 — remove leading dots that would make the selector invalid
                while result[:1] == ".":
                    result = result[1:]
                # utils.ts:89-97
                if match[3] == "downcase":
                    return result.lower()
                if match[3] == "upcase":
                    return result.upper()
                return result
            return match[0]

        return _CAPTURING_REGEX_SOURCE.sub(_replace, regex_source)


@dataclass(frozen=True)
class AnchorCache:
    """Port of ``IRegExpSourceAnchorCache`` (rule.ts:575-580): the four resolved
    variants of a source with anchors, named after which anchors remain allowed.
    ``A1`` = ``\\A`` kept, ``G1`` = ``\\G`` kept; disallowed anchors were rewritten
    to the U+FFFF sentinel, which can virtually never occur in scanned text."""

    a0_g0: str
    a0_g1: str
    a1_g0: str
    a1_g1: str


class RegExpSource:
    """Port of rule.ts's ``RegExpSource`` (rule.ts:582-735): a pattern source from
    the grammar, preprocessed on construction (``\\z`` workaround), detecting
    whether it uses anchors (``\\A``/``\\G``) or ``\\n`` backreferences and able to
    resolve the anchor variants via its anchor cache."""

    source: str
    rule_id: int
    has_anchor: bool
    has_back_references: bool

    def __init__(self, reg_exp_source: str, rule_id: int) -> None:
        """Port of the constructor (rule.ts:590-639).

        Walks the source once: ``\\z`` (oniguruma-only, kept in tmlanguage sources)
        is rewritten to a JS-compatible equivalent and occurrences of ``\\A``/``\\G``
        mark the source as anchored. Note that escaped anchors inside character
        classes are flagged too — upstream does the same (rule.ts:600-613).
        """
        if reg_exp_source:
            length = len(reg_exp_source)
            last_pushed_pos = 0
            output: list[str] = []

            has_anchor = False
            pos = 0
            while pos < length:
                ch = reg_exp_source[pos]
                # rule.ts:600-613 — only an escape target of a backslash is of
                # interest; a trailing backslash is just passed through
                if ch == "\\" and pos + 1 < length:
                    next_ch = reg_exp_source[pos + 1]
                    if next_ch == "z":
                        # rule.ts:603-606 — ``\z`` → ``$(?!\n)(?<!\n)``
                        output.append(reg_exp_source[last_pushed_pos:pos])
                        output.append("$(?!\\n)(?<!\\n)")
                        last_pushed_pos = pos + 2
                    elif next_ch == "A" or next_ch == "G":
                        # rule.ts:607-609 — anchored; the escaped char is skipped
                        # by shared pos increment of the escape pair below
                        has_anchor = True
                    pos += 2
                    continue
                pos += 1

            self.has_anchor = has_anchor
            if last_pushed_pos == 0:
                # rule.ts:616-618 — no \z hit: the source stays as-is
                self.source = reg_exp_source
            else:
                output.append(reg_exp_source[last_pushed_pos:length])
                self.source = "".join(output)
        else:
            self.has_anchor = False
            self.source = reg_exp_source

        self.rule_id = rule_id
        # rule.ts:636 — detected on the (possibly rewritten) source
        self.has_back_references = bool(_HAS_BACK_REFERENCES.search(self.source))

        # rule.ts:629-633 — precompute the anchor variants once
        self._anchor_cache: AnchorCache | None = (
            self._build_anchor_cache() if self.has_anchor else None
        )

    def clone(self) -> RegExpSource:
        """Port of ``RegExpSource.clone`` (rule.ts:641-643)."""
        return RegExpSource(self.source, self.rule_id)

    def set_source(self, new_source: str) -> None:
        """Port of ``RegExpSource.setSource`` (rule.ts:645-654): rebuilds the anchor
        cache from the new source — but only picks up ``has_anchor`` changes on the
        *next* construction (upstream keeps the old flag here too)."""
        if self.source == new_source:
            return
        self.source = new_source
        if self.has_anchor:
            self._anchor_cache = self._build_anchor_cache()

    def resolve_back_references(
        self, line_text: str, capture_indices: Sequence[IOnigCaptureIndex]
    ) -> str:
        """Port of ``RegExpSource.resolveBackReferences`` (rule.ts:656-664):
        substitutes ``\\n``-style backreferences in the source with the
        regexp-escaped content of capture ``n`` from the (begin) match, e.g. for
        end patterns echoing the begun content. Unmatched or out-of-range captures
        substitute '' — upstream ``capturedValues[...] || ''`` (rule.ts:662)."""
        captured_values = [line_text[capture.start : capture.end] for capture in capture_indices]

        def _replace(match: re.Match[str]) -> str:
            # rule.ts:661-662 —
            # return escapeRegExpCharacters(capturedValues[parseInt(g1, 10)] || '')
            index = int(match[1])
            value = captured_values[index] if index < len(captured_values) else ""
            return escapeRegExpCharacters(value)

        return _BACK_REFERENCING_END.sub(_replace, self.source)

    def _build_anchor_cache(self) -> AnchorCache:
        """Port of ``RegExpSource._buildAnchorCache`` (rule.ts:666-714): builds the
        four source variants in one pass; ``\\A``/``\\G`` pairs stay verbatim in the
        variants where their anchor is allowed, otherwise the escape target is
        rewritten to the U+FFFF sentinel."""
        source = self.source
        length = len(source)

        a0_g0_result: list[str] = []
        a0_g1_result: list[str] = []
        a1_g0_result: list[str] = []
        a1_g1_result: list[str] = []

        pos = 0
        while pos < length:
            ch = source[pos]
            a0_g0_result.append(ch)
            a0_g1_result.append(ch)
            a1_g0_result.append(ch)
            a1_g1_result.append(ch)

            # rule.ts:684-705 — backslash followed by the anchor escape pair
            if ch == "\\" and pos + 1 < length:
                next_ch = source[pos + 1]
                if next_ch == "A":
                    a0_g0_result.append("\uffff")
                    a0_g1_result.append("\uffff")
                    a1_g0_result.append("A")
                    a1_g1_result.append("A")
                elif next_ch == "G":
                    a0_g0_result.append("\uffff")
                    a0_g1_result.append("G")
                    a1_g0_result.append("\uffff")
                    a1_g1_result.append("G")
                else:
                    for result in (a0_g0_result, a0_g1_result, a1_g0_result, a1_g1_result):
                        result.append(next_ch)
                # rule.ts:703 — escape pairs are consumed as one unit
                pos += 2
            else:
                pos += 1

        return AnchorCache(
            a0_g0="".join(a0_g0_result),
            a0_g1="".join(a0_g1_result),
            a1_g0="".join(a1_g0_result),
            a1_g1="".join(a1_g1_result),
        )

    def resolve_anchors(self, allow_a: bool, allow_g: bool) -> str:
        """Port of ``RegExpSource.resolveAnchors`` (rule.ts:716-734): the source
        variant with the disallowed anchors neutralized; non-anchored sources are
        returned verbatim (rule.ts:717-719)."""
        if not self.has_anchor or self._anchor_cache is None:
            return self.source
        if allow_a:
            return self._anchor_cache.a1_g1 if allow_g else self._anchor_cache.a1_g0
        return self._anchor_cache.a0_g1 if allow_g else self._anchor_cache.a0_g0


@dataclass(frozen=True)
class IFindNextMatchResult:
    """Port of ``IFindNextMatchResult`` (rule.ts:896-899): the matched pattern's
    rule id and its capture indices."""

    rule_id: int
    capture_indices: tuple[IOnigCaptureIndex, ...]


class CompiledRule:
    """Port of rule.ts's ``CompiledRule`` (rule.ts:858-894): a set of pattern
    sources compiled once into an :class:`OnigScanner`, resolving matches back to
    the rule ids the patterns belong to."""

    def __init__(self, onig_lib: IOnigLib, reg_exps: Sequence[str], rules: Sequence[int]) -> None:
        # rule.ts:861-863 — one scanner for the whole pattern list
        self._reg_exps = list(reg_exps)
        self._rules = list(rules)
        self._scanner = onig_lib.create_onig_scanner(list(reg_exps))

    def dispose(self) -> None:
        """Port of ``CompiledRule.dispose`` (rule.ts:865-869)."""
        self._scanner.dispose()

    def __str__(self) -> str:
        # rule.ts:871-877 — the debug representation of the compiled pattern set
        return "\n".join(
            f"   - {rule}: {reg_exp}"
            for rule, reg_exp in zip(self._rules, self._reg_exps, strict=True)
        )

    def find_next_match_sync(
        self,
        string: str | OnigString,
        start_position: int,
        options: FindOption = FindOption.NONE,
    ) -> IFindNextMatchResult | None:
        """Port of ``CompiledRule.findNextMatchSync`` (rule.ts:879-893): scans and
        maps the matched pattern index back to ``IFindNextMatchResult``."""
        result = self._scanner.find_next_match_sync(string, start_position, options)
        if result is None:
            return None
        return IFindNextMatchResult(
            rule_id=self._rules[result.index],
            capture_indices=result.capture_indices,
        )


class RegExpSourceList:
    """Port of rule.ts's ``RegExpSourceList`` (rule.ts:744-856): a growing list of
    :class:`RegExpSource` items compiled lazily into :class:`CompiledRule` objects.

    For lists with anchors, the compiled scanners are cached in ``_anchor_cache``
    — upstream carries the four ``A0_G0``..``A1_G1`` fields (rule.ts:737-742,
    751-760); they are keyed here by ``(allow_a, allow_g)``.
    """

    def __init__(self) -> None:
        # rule.ts:751-761 — no items, no anchors, nothing compiled yet
        self._items: list[RegExpSource] = []
        self._has_anchors = False
        self._cached: CompiledRule | None = None
        self._anchor_cache: dict[tuple[bool, bool], CompiledRule | None] = {
            (False, False): None,
            (False, True): None,
            (True, False): None,
            (True, True): None,
        }

    def __len__(self) -> int:
        return len(self._items)

    def push(self, item: RegExpSource) -> None:
        """Port of ``RegExpSourceList.push`` (rule.ts:790-793)."""
        self._items.append(item)
        self._has_anchors = self._has_anchors or item.has_anchor

    def unshift(self, item: RegExpSource) -> None:
        """Port of ``RegExpSourceList.unshift`` (rule.ts:795-798)."""
        self._items.insert(0, item)
        self._has_anchors = self._has_anchors or item.has_anchor

    def set_source(self, index: int, new_source: str) -> None:
        """Port of ``RegExpSourceList.setSource`` (rule.ts:804-810): busts the
        caches when the source of an item actually changes."""
        if self._items[index].source != new_source:
            self._dispose_caches()
            self._items[index].set_source(new_source)

    def _dispose_caches(self) -> None:
        """Port of ``RegExpSourceList._disposeCaches`` (rule.ts:767-788): drops the
        compiled scanners so the next compile rebuilds everything."""
        if self._cached is not None:
            self._cached.dispose()
            self._cached = None
        for (allow_a, allow_g), compiled in self._anchor_cache.items():
            if compiled is not None:
                compiled.dispose()
                self._anchor_cache[(allow_a, allow_g)] = None

    def compile(self, onig_lib: IOnigLib) -> CompiledRule:
        """Port of ``RegExpSourceList.compile`` (rule.ts:812-818): compiles the
        plain sources once and caches them."""
        if self._cached is None:
            reg_exps = [item.source for item in self._items]
            self._cached = CompiledRule(onig_lib, reg_exps, [item.rule_id for item in self._items])
        return self._cached

    def compile_ag(self, onig_lib: IOnigLib, allow_a: bool, allow_g: bool) -> CompiledRule:
        """Port of ``RegExpSourceList.compileAG`` (rule.ts:820-850): non-anchored
        lists share the plain compile (rule.ts:821-822); anchored lists get one
        cached compiled variant per allowed anchor combination."""
        if not self._has_anchors:
            return self.compile(onig_lib)
        compiled = self._anchor_cache[(allow_a, allow_g)]
        if compiled is None:
            compiled = self._resolve_anchors(onig_lib, allow_a, allow_g)
            self._anchor_cache[(allow_a, allow_g)] = compiled
        return compiled

    def _resolve_anchors(self, onig_lib: IOnigLib, allow_a: bool, allow_g: bool) -> CompiledRule:
        """Port of ``RegExpSourceList._resolveAnchors`` (rule.ts:852-855)."""
        reg_exps = [item.resolve_anchors(allow_a, allow_g) for item in self._items]
        return CompiledRule(onig_lib, reg_exps, [item.rule_id for item in self._items])
