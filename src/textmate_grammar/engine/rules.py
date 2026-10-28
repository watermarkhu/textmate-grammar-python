"""Port of the ``Rule`` classes, ``RuleRegistry`` and the rule factory from
vscode-textmate's ``src/rule.ts`` (version 9.3.2, the pinned reference clone).

Ported from rule.ts: ``endRuleId``/``whileRuleId`` (rule.ts:17-20), the ``Rule`` base
class (rule.ts:43-89), ``CaptureRule`` (rule.ts:96-120), ``MatchRule``
(rule.ts:122-164), ``IncludeOnlyRule`` (rule.ts:166-207), ``BeginEndRule``
(rule.ts:209-288), ``BeginWhileRule`` (rule.ts:290-379) and the ``RuleFactory``
(rule.ts:381-573) — i.e. ``createCaptureRule``, ``getCompiledRuleId``,
``_compileCaptures`` and ``_compilePatterns``. The registry lives in ``Grammar``
upstream: ``registerRule``/``getRule`` are grammar.ts:245-254; the class
:class:`RuleRegistry` here extracts exactly that behaviour.

``parse_include`` ports ``parseInclude`` and ``IncludeReferenceKind`` from
``src/grammar/grammarDependencies.ts`` (grammarDependencies.ts:247-295) — the
minimal piece the rule factory needs for include resolution. ``init_grammar`` ports
``initGrammar`` (grammar.ts:410-421), which installs the ``$self``/``$base``
repository hooks.

Semantics are 1:1 with the reference; naming is pythonic where it can be (upstream
member names are kept when the python port is simply "same words"), and every
non-obvious piece carries a comment referencing the ported lines of rule.ts /
grammar.ts / grammarDependencies.ts.
"""

from __future__ import annotations

import copy
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, TypeVar

from .oniglib import IOnigCaptureIndex
from .regexsource import (
    CompiledRule,
    RegExpSource,
    RegExpSourceList,
    RegexSource,
)

T = TypeVar("T", bound="Rule")

__all__: tuple[str, ...] = (
    "BeginEndRule",
    "BeginWhileRule",
    "CaptureRule",
    "CompilePatternsResult",
    "END_RULE_ID",
    "IncludeOnlyRule",
    "IncludeReference",
    "IncludeReferenceKind",
    "IRuleFactoryHelper",
    "IRuleRegistry",
    "MatchRule",
    "Rule",
    "RuleFactory",
    "RuleRegistry",
    "WHILE_RULE_ID",
    "create_rule",
    "init_grammar",
    "parse_include",
)

# rule.ts:17-20 — special rule ids signaling that the end (`-1`) / while (`-2`)
# regexp of the enclosing begin rule matched; negative so real registry ids
# (allocated from 1, grammar.ts:246) cannot collide.
END_RULE_ID: int = -1
WHILE_RULE_ID = -2

IRawRuleDict = dict[str, Any]
IRawRepositoryDict = dict[str, IRawRuleDict]
IRawGrammarDict = dict[str, Any]

# rawGrammar.ts ILocatable — where a rule came from in its tmLanguage file, as
# carried under a rule's ``$vscodeTextmateLocation`` key: ``{"filename", "line"}``.
ILocation = dict[str, Any] | None

#: rule.ts:98 — ``retokenizeCapturedWithRuleId`` of 0: the capture content is not
#: retokenized with a nested rule.
_NO_RETOKENIZE = 0


def _basename(path: str) -> str:
    """Port of utils.ts ``basename`` (utils.ts:46-55), used for debug names only."""
    return os.path.basename(path.replace("\\", "/"))


class IRuleRegistry:
    """Port of ``IRuleRegistry`` (rule.ts:31-34): numeric rule registration and
    lookup by id."""

    def get_rule(self, rule_id: int) -> Rule:
        """Port of ``getRule(ruleId)`` (rule.ts:32)."""
        raise NotImplementedError

    def register_rule(self, factory: Callable[[int], T]) -> T:
        """Port of ``registerRule(factory)`` (rule.ts:33): the factory is invoked
        immediately with the freshly allocated id."""
        raise NotImplementedError


class IGrammarRegistry:
    """Port of ``IGrammarRegistry`` (rule.ts:36-38): resolves scope-name includes
    against grammars looked up by scope name. The concrete implementation arrives
    with the registry layer (task 4b); here it is only the hook shape."""

    def get_external_grammar(
        self, scope_name: str, repository: IRawRepositoryDict | None
    ) -> IRawGrammarDict | None:
        """Port of ``getExternalGrammar(scopeName, repository)`` (rule.ts:37)."""
        raise NotImplementedError


class IRuleFactoryHelper(IRuleRegistry, IGrammarRegistry):
    """Port of ``IRuleFactoryHelper`` (rule.ts:40-41). Upstream ``Grammar``
    additionally implements ``IOnigLib`` (grammar.ts:98), so the helper doubles as
    the onig-lib argument of the compile calls; the two ``createOnig*`` members
    come from ``Grammar.createOnigScanner``/``createOnigString``
    (grammar.ts:177-181)."""

    def create_onig_scanner(self, sources: Sequence[str]) -> Any:
        """Port of ``createOnigScanner`` (grammar.ts:177-179)."""
        raise NotImplementedError

    def create_onig_string(self, string: str) -> Any:
        """Port of ``createOnigString`` (grammar.ts:180-181)."""
        raise NotImplementedError


class RuleRegistry(IRuleFactoryHelper):
    """Port of the rule-id <-> Rule bookkeeping that lives in ``Grammar``
    (grammar.ts:100, 127-128, 245-254): monotonically increasing numeric ids
    starting at 1, with the rule objects stored under their id. Serves as the
    concrete :class:`IRuleFactoryHelper` for :class:`RuleFactory` users and, later
    (task 3), as the registry component of ``Grammar``.

    Note: upstream v9.3.2 has no standalone ``RuleRegistry`` class and no scope-name
    interning; the class here is simply the extracted ``Grammar`` behaviour.
    """

    def __init__(self, onig_lib: Any = None) -> None:
        # grammar.ts:126-128 — the id counter and the id -> rule table; index 0
        # stays unused (no rule has id 0).
        self._last_rule_id = 0
        self._rule_id2desc: list[Rule | None] = [None]
        # grammar.ts:119 — the oniguruma lib Grammar delegates scanner/string
        # creation to (an unwired helper creates nothing until needed).
        self._onig_lib = onig_lib

    def register_rule(self, factory: Callable[[int], T]) -> T:
        """Port of ``Grammar.registerRule`` (grammar.ts:245-250)."""
        self._last_rule_id += 1
        rule_id = self._last_rule_id
        # ids are strictly sequential; grow to the id first so a factory that
        # recursively registers rules (captures compile inside this call) keeps
        # the table aligned
        self._rule_id2desc.append(None)
        rule = factory(rule_id)
        self._rule_id2desc[rule_id] = rule
        return rule

    def get_rule(self, rule_id: int) -> Rule:
        """Port of ``Grammar.getRule`` (grammar.ts:252-254). May return the
        (python) ``None`` of a not-yet-registered rule while its factory is still
        running — upstream yields ``undefined`` there, and the only reader that
        can act on it treats non-``None`` like ``undefined`` (see
        ``RuleFactory.compile_patterns``)."""
        return self._rule_id2desc[rule_id]  # type: ignore[return-value]

    def get_external_grammar(
        self, scope_name: str, repository: IRawRepositoryDict | None
    ) -> IRawGrammarDict | None:
        """Port of ``Grammar.getExternalGrammar`` (grammar.ts:256-274): scope-name
        includes resolve through the grammar repository; without a registry layer
        behind this helper there is nothing to resolve (task 4b provides it)."""
        return None

    def _ensure_onig_lib(self) -> Any:
        if self._onig_lib is None:
            from .oniglib import DEFAULT_ONIG_LIB

            self._onig_lib = DEFAULT_ONIG_LIB
        return self._onig_lib

    def create_onig_scanner(self, sources: Sequence[str]) -> Any:
        """Port of ``Grammar.createOnigScanner`` (grammar.ts:177-179)."""
        return self._ensure_onig_lib().create_onig_scanner(sources)

    def create_onig_string(self, string: str) -> Any:
        """Port of ``Grammar.createOnigString`` (grammar.ts:180-181)."""
        return self._ensure_onig_lib().create_onig_string(string)


class Rule:
    """Port of the abstract ``Rule`` (rule.ts:43-89): identity, ``name``/
    ``contentName`` with capture expansion, and the pattern collection / compile
    contract the tokenization loop drives."""

    def __init__(
        self,
        location: ILocation,
        id: int,  # noqa: A002 — mirrors the upstream member name
        name: str | None,
        contentName: str | None,  # noqa: N803 — upstream member name
    ) -> None:
        # rule.ts:45-46 — Python identifiers cannot carry `$`, so the upstream
        # member ``$location`` becomes ``location``
        self.location = location
        self.id = id
        # rule.ts:57-60 — falsy names become None, and whether a name contains
        # capture references ($1 / ${1:/downcase}) is detected once here
        self._name = name or None
        self._name_is_capturing = RegexSource.hasCaptures(self._name)
        self._contentName = contentName or None
        self._contentName_is_capturing = RegexSource.hasCaptures(self._contentName)

    @property
    def debugName(self) -> str:  # noqa: N802
        """Port of ``Rule.debugName`` (rule.ts:65-68)."""
        location = (
            f"{_basename(self.location['filename'])}:{self.location['line']}"
            if self.location
            else "unknown"
        )
        return f"{type(self).__name__}#{self.id} @ {location}"

    def getName(  # noqa: N802
        self, lineText: str | None, captureIndices: Sequence[IOnigCaptureIndex] | None
    ) -> str | None:
        """Port of ``Rule.getName`` (rule.ts:70-75): expands capture references in
        the name against the matched text; non-capturing names pass through."""
        if (
            not self._name_is_capturing
            or self._name is None
            or lineText is None
            or captureIndices is None
        ):
            return self._name
        return RegexSource.replaceCaptures(self._name, lineText, captureIndices)

    def getContentName(  # noqa: N802
        self, lineText: str, captureIndices: Sequence[IOnigCaptureIndex]
    ) -> str | None:
        """Port of ``Rule.getContentName`` (rule.ts:77-82)."""
        if not self._contentName_is_capturing or self._contentName is None:
            return self._contentName
        return RegexSource.replaceCaptures(self._contentName, lineText, captureIndices)

    def dispose(self) -> None:
        """Port of ``Rule.dispose`` (rule.ts:63); the base rule holds nothing.

        Subclasses override to drop their compiled-pattern caches (kept for
        parity; garbage collection makes it a cache-buster only)."""
        return

    def collectPatterns(self, grammar: IRuleRegistry, out: RegExpSourceList) -> None:  # noqa: N802
        """Port of ``Rule.collectPatterns`` (rule.ts:84) — abstract."""
        raise NotImplementedError

    def compile(self, grammar: IRuleFactoryHelper, endRegexSource: str | None) -> CompiledRule:  # noqa: N802
        """Port of ``Rule.compile`` (rule.ts:86) — abstract."""
        raise NotImplementedError

    def compileAG(  # noqa: N802
        self, grammar: IRuleFactoryHelper, endRegexSource: str | None, allowA: bool, allowG: bool
    ) -> CompiledRule:
        """Port of ``Rule.compileAG`` (rule.ts:88) — abstract."""
        raise NotImplementedError


@dataclass(frozen=True)
class CompilePatternsResult:
    """Port of ``ICompilePatternsResult`` (rule.ts:91-94): the ordered rule ids of
    a pattern list plus upstream's flag recording that entries were dropped
    (include targets that could not be resolved)."""

    patterns: tuple[int, ...]
    hasMissingPatterns: bool  # noqa: N815 — upstream field name


class CaptureRule(Rule):
    """Port of ``CaptureRule`` (rule.ts:96-120) — one entry of a ``captures`` map.

    ``retokenizeCapturedWithRuleId`` is 0 (no nested rule) unless the capture
    declares ``patterns``, in which case it is the id of the rule compiled from
    them (rule.ts:476-480)."""

    def __init__(
        self,
        location: ILocation,
        id: int,  # noqa: A002
        name: str | None,
        contentName: str | None,  # noqa: N803
        retokenizeCapturedWithRuleId: int,  # noqa: N803
    ) -> None:
        super().__init__(location, id, name, contentName)
        self.retokenize_captured_with_rule_id = retokenizeCapturedWithRuleId

    def collectPatterns(self, grammar: IRuleRegistry, out: RegExpSourceList) -> None:  # noqa: N802
        # rule.ts:109-111 — capture rules never appear in a pattern list
        raise RuntimeError("Not supported!")

    def compile(self, grammar: IRuleFactoryHelper, endRegexSource: str | None) -> CompiledRule:  # noqa: N802
        # rule.ts:113-115
        raise RuntimeError("Not supported!")

    def compileAG(  # noqa: N802
        self, grammar: IRuleFactoryHelper, endRegexSource: str | None, allowA: bool, allowG: bool
    ) -> CompiledRule:
        # rule.ts:117-119
        raise RuntimeError("Not supported!")


class MatchRule(Rule):
    """Port of ``MatchRule`` (rule.ts:122-164): a single ``match`` pattern with
    optional captures."""

    def __init__(
        self,
        location: ILocation,
        id: int,  # noqa: A002
        name: str | None,
        match: str,
        captures: list[CaptureRule | None],
    ) -> None:
        super().__init__(location, id, name, None)
        # rule.ts:129 — the match pattern carries this rule's id
        self._match = RegExpSource(match, self.id)
        self.captures = captures
        self._cachedCompiledPatterns: RegExpSourceList | None = None

    def dispose(self) -> None:
        # rule.ts:134-139 — bust the compiled cache
        self._cachedCompiledPatterns = None

    @property
    def debugMatchRegExp(self) -> str:  # noqa: N802
        """Port of ``debugMatchRegExp`` (rule.ts:141-143)."""
        return self._match.source

    def collectPatterns(self, grammar: IRuleRegistry, out: RegExpSourceList) -> None:  # noqa: N802
        # rule.ts:145-147
        out.push(self._match)

    def _get_cached_compiled_patterns(self, grammar: IRuleRegistry) -> RegExpSourceList:
        """Port of ``_getCachedCompiledPatterns`` (rule.ts:157-163)."""
        if self._cachedCompiledPatterns is None:
            self._cachedCompiledPatterns = RegExpSourceList()
            self.collectPatterns(grammar, self._cachedCompiledPatterns)
        return self._cachedCompiledPatterns

    def compile(self, grammar: IRuleFactoryHelper, endRegexSource: str | None) -> CompiledRule:  # noqa: N802
        # rule.ts:149-151 — `endRegexSource` is unused for match rules
        return self._get_cached_compiled_patterns(grammar).compile(grammar)

    def compileAG(  # noqa: N802
        self, grammar: IRuleFactoryHelper, endRegexSource: str | None, allowA: bool, allowG: bool
    ) -> CompiledRule:
        # rule.ts:153-155
        return self._get_cached_compiled_patterns(grammar).compile_ag(grammar, allowA, allowG)


class IncludeOnlyRule(Rule):
    """Port of ``IncludeOnlyRule`` (rule.ts:166-207): a rule made purely of
    ``include`` references whose own (possibly missing) patterns are collected at
    compile time."""

    def __init__(
        self,
        location: ILocation,
        id: int,  # noqa: A002
        name: str | None,
        contentName: str | None,  # noqa: N803
        patterns: CompilePatternsResult,
    ) -> None:
        super().__init__(location, id, name, contentName)
        self.patterns = patterns.patterns
        self.hasMissingPatterns = patterns.hasMissingPatterns
        self._cachedCompiledPatterns: RegExpSourceList | None = None

    def dispose(self) -> None:
        # rule.ts:178-182
        self._cachedCompiledPatterns = None

    def collectPatterns(self, grammar: IRuleRegistry, out: RegExpSourceList) -> None:  # noqa: N802
        # rule.ts:185-190 — flatten each referenced rule's patterns, in order
        for pattern in self.patterns:
            rule = grammar.get_rule(pattern)
            rule.collectPatterns(grammar, out)

    def _get_cached_compiled_patterns(self, grammar: IRuleRegistry) -> RegExpSourceList:
        """Port of ``_getCachedCompiledPatterns`` (rule.ts:200-206)."""
        if self._cachedCompiledPatterns is None:
            self._cachedCompiledPatterns = RegExpSourceList()
            self.collectPatterns(grammar, self._cachedCompiledPatterns)
        return self._cachedCompiledPatterns

    def compile(self, grammar: IRuleFactoryHelper, endRegexSource: str | None) -> CompiledRule:  # noqa: N802
        # rule.ts:192-194
        return self._get_cached_compiled_patterns(grammar).compile(grammar)

    def compileAG(  # noqa: N802
        self, grammar: IRuleFactoryHelper, endRegexSource: str | None, allowA: bool, allowG: bool
    ) -> CompiledRule:
        # rule.ts:196-198
        return self._get_cached_compiled_patterns(grammar).compile_ag(grammar, allowA, allowG)


class BeginEndRule(Rule):
    """Port of ``BeginEndRule`` (rule.ts:209-288): ``begin``/``end`` with captures
    on both, contained ``patterns`` and ``applyEndPatternLast`` placement."""

    def __init__(
        self,
        location: ILocation,
        id: int,  # noqa: A002
        name: str | None,
        contentName: str | None,  # noqa: N803
        begin: str,
        beginCaptures: list[CaptureRule | None],  # noqa: N803
        end: str | None,
        endCaptures: list[CaptureRule | None],  # noqa: N803
        applyEndPatternLast: bool | None,  # noqa: N803
        patterns: CompilePatternsResult,
    ) -> None:
        super().__init__(location, id, name, contentName)
        # rule.ts:222 — the begin pattern carries this rule's id
        self._begin = RegExpSource(begin, self.id)
        self.beginCaptures = beginCaptures
        # rule.ts:224 — the end pattern carries endRuleId (-1); a missing end
        # becomes the empty source (see grammar.ts turn-of-line handling)
        self._end = RegExpSource(end if end else "", END_RULE_ID)
        # rule.ts:225 — backreferences in the end get substituted against the
        # begin match's captures before use
        self.endHasBackReferences = self._end.has_back_references
        self.endCaptures = endCaptures
        # rule.ts:227 — missing/undefined means False
        self.applyEndPatternLast = applyEndPatternLast or False
        self.patterns = patterns.patterns
        self.hasMissingPatterns = patterns.hasMissingPatterns
        self._cachedCompiledPatterns: RegExpSourceList | None = None

    def dispose(self) -> None:
        # rule.ts:233-238
        self._cachedCompiledPatterns = None

    @property
    def debugBeginRegExp(self) -> str:  # noqa: N802
        """Port of ``debugBeginRegExp`` (rule.ts:240-242)."""
        return self._begin.source

    @property
    def debugEndRegExp(self) -> str:  # noqa: N802
        """Port of ``debugEndRegExp`` (rule.ts:244-246)."""
        return self._end.source

    def getEndWithResolvedBackReferences(  # noqa: N802
        self, lineText: str, captureIndices: Sequence[IOnigCaptureIndex]
    ) -> str:
        """Port of ``getEndWithResolvedBackReferences`` (rule.ts:248-250): the end
        pattern with backreferences substituted from the begin match."""
        return self._end.resolve_back_references(lineText, captureIndices)

    def collectPatterns(self, grammar: IRuleRegistry, out: RegExpSourceList) -> None:  # noqa: N802
        # rule.ts:252-254
        out.push(self._begin)

    def _get_cached_compiled_patterns(
        self, grammar: IRuleRegistry, endRegexSource: str
    ) -> RegExpSourceList:
        """Port of ``_getCachedCompiledPatterns`` (rule.ts:264-287): the contained
        patterns' sources, with the end source placed first (or last under
        ``applyEndPatternLast``) and backreferencing ends swapped for the caller's
        resolved ``endRegexSource`` (it changes per match, hence the setSource)."""
        if self._cachedCompiledPatterns is None:
            self._cachedCompiledPatterns = RegExpSourceList()

            for pattern in self.patterns:
                rule = grammar.get_rule(pattern)
                rule.collectPatterns(grammar, self._cachedCompiledPatterns)

            # rule.ts:273-277 — a cloned end carries the same rule id; cloning is
            # needed because set_source below rewrites the shared source
            if self.applyEndPatternLast:
                self._cachedCompiledPatterns.push(
                    self._end.clone() if self._end.has_back_references else self._end
                )
            else:
                self._cachedCompiledPatterns.unshift(
                    self._end.clone() if self._end.has_back_references else self._end
                )

        # rule.ts:279-285 — with backreferences, the end source differs per call
        if self._end.has_back_references:
            if self.applyEndPatternLast:
                self._cachedCompiledPatterns.set_source(
                    len(self._cachedCompiledPatterns) - 1, endRegexSource
                )
            else:
                self._cachedCompiledPatterns.set_source(0, endRegexSource)

        return self._cachedCompiledPatterns

    def compile(self, grammar: IRuleFactoryHelper, endRegexSource: str | None) -> CompiledRule:  # noqa: N802
        # rule.ts:256-258
        return self._get_cached_compiled_patterns(grammar, endRegexSource or "").compile(grammar)

    def compileAG(  # noqa: N802
        self, grammar: IRuleFactoryHelper, endRegexSource: str | None, allowA: bool, allowG: bool
    ) -> CompiledRule:
        # rule.ts:260-262
        return self._get_cached_compiled_patterns(grammar, endRegexSource or "").compile_ag(
            grammar, allowA, allowG
        )


class BeginWhileRule(Rule):
    """Port of ``BeginWhileRule`` (rule.ts:290-379): ``begin`` plus a ``while``
    condition checked at the start of every line (rule id ``whileRuleId`` = -2),
    with the contained ``patterns`` compiled as for ``BeginEndRule``."""

    def __init__(
        self,
        location: ILocation,
        id: int,  # noqa: A002
        name: str | None,
        contentName: str | None,  # noqa: N803
        begin: str,
        beginCaptures: list[CaptureRule | None],  # noqa: N803
        while_: str,
        whileCaptures: list[CaptureRule | None],  # noqa: N803
        patterns: CompilePatternsResult,
    ) -> None:
        super().__init__(location, id, name, contentName)
        # rule.ts:303 — the begin pattern carries this rule's id
        self._begin = RegExpSource(begin, self.id)
        self.beginCaptures = beginCaptures
        self.whileCaptures = whileCaptures
        # rule.ts:306 — the while pattern carries whileRuleId (-2)
        self._while = RegExpSource(while_, WHILE_RULE_ID)
        # rule.ts:307
        self.whileHasBackReferences = self._while.has_back_references
        self.patterns = patterns.patterns
        self.hasMissingPatterns = patterns.hasMissingPatterns
        self._cachedCompiledPatterns: RegExpSourceList | None = None
        self._cachedCompiledWhilePatterns: RegExpSourceList | None = None

    def dispose(self) -> None:
        # rule.ts:314-323 — both caches
        self._cachedCompiledPatterns = None
        self._cachedCompiledWhilePatterns = None

    @property
    def debugBeginRegExp(self) -> str:  # noqa: N802
        """Port of ``debugBeginRegExp`` (rule.ts:325-327)."""
        return self._begin.source

    @property
    def debugWhileRegExp(self) -> str:  # noqa: N802
        """Port of ``debugWhileRegExp`` (rule.ts:329-331)."""
        return self._while.source

    def getWhileWithResolvedBackReferences(  # noqa: N802
        self, lineText: str, captureIndices: Sequence[IOnigCaptureIndex]
    ) -> str:
        """Port of ``getWhileWithResolvedBackReferences`` (rule.ts:333-335): the
        while pattern with backreferences substituted from the begin match."""
        return self._while.resolve_back_references(lineText, captureIndices)

    def collectPatterns(self, grammar: IRuleRegistry, out: RegExpSourceList) -> None:  # noqa: N802
        # rule.ts:337-339
        out.push(self._begin)

    def _get_cached_compiled_patterns(self, grammar: IRuleRegistry) -> RegExpSourceList:
        """Port of ``_getCachedCompiledPatterns`` (rule.ts:349-359): only the
        contained patterns — unlike ``BeginEndRule`` there is no end source."""
        if self._cachedCompiledPatterns is None:
            self._cachedCompiledPatterns = RegExpSourceList()

            for pattern in self.patterns:
                rule = grammar.get_rule(pattern)
                rule.collectPatterns(grammar, self._cachedCompiledPatterns)

        return self._cachedCompiledPatterns

    def compile(self, grammar: IRuleFactoryHelper, endRegexSource: str | None) -> CompiledRule:  # noqa: N802
        # rule.ts:341-343
        return self._get_cached_compiled_patterns(grammar).compile(grammar)

    def compileAG(  # noqa: N802
        self, grammar: IRuleFactoryHelper, endRegexSource: str | None, allowA: bool, allowG: bool
    ) -> CompiledRule:
        # rule.ts:345-347
        return self._get_cached_compiled_patterns(grammar).compile_ag(grammar, allowA, allowG)

    def _get_cached_compiled_while_patterns(
        self, grammar: IRuleRegistry, endRegexSource: str | None
    ) -> RegExpSourceList:
        """Port of ``_getCachedCompiledWhilePatterns`` (rule.ts:369-378): a
        single-item list with the while source, swapped for the resolved source
        when it has backreferences."""
        if self._cachedCompiledWhilePatterns is None:
            self._cachedCompiledWhilePatterns = RegExpSourceList()
            self._cachedCompiledWhilePatterns.push(
                self._while.clone() if self._while.has_back_references else self._while
            )
        if self._while.has_back_references:
            self._cachedCompiledWhilePatterns.set_source(
                0, endRegexSource if endRegexSource else ""
            )
        return self._cachedCompiledWhilePatterns

    def compileWhile(self, grammar: IRuleFactoryHelper, endRegexSource: str | None) -> CompiledRule:  # noqa: N802
        """Port of ``compileWhile`` (rule.ts:361-363)."""
        return self._get_cached_compiled_while_patterns(grammar, endRegexSource).compile(grammar)

    def compileWhileAG(  # noqa: N802
        self, grammar: IRuleFactoryHelper, endRegexSource: str | None, allowA: bool, allowG: bool
    ) -> CompiledRule:
        """Port of ``compileWhileAG`` (rule.ts:365-367)."""
        return self._get_cached_compiled_while_patterns(grammar, endRegexSource).compile_ag(
            grammar, allowA, allowG
        )


class IncludeReferenceKind(IntEnum):
    """Port of ``IncludeReferenceKind`` (grammarDependencies.ts:247-253)."""

    Base = 0
    Self = 1
    RelativeReference = 2
    TopLevelReference = 3
    TopLevelRepositoryReference = 4


@dataclass(frozen=True)
class IncludeReference:
    """Port of the ``IncludeReference`` union (grammarDependencies.ts:240-276);
    fields beyond ``kind`` are set per kind (``scope_name``/``rule_name``)."""

    kind: IncludeReferenceKind
    scopeName: str | None = None  # noqa: N815 — upstream field name
    ruleName: str | None = None  # noqa: N815 — upstream field name


def parse_include(include: str) -> IncludeReference:
    """Port of ``parseInclude`` (grammarDependencies.ts:278-295): ``$base`` /
    ``$self``, ``#rule`` (relative), ``scope`` (top level), ``scope#rule``
    (top-level repository reference). Note: this is the shared include parser; the
    full grammarDependency machinery (task 4b) should import it from here."""
    if include == "$base":
        return IncludeReference(IncludeReferenceKind.Base)
    if include == "$self":
        return IncludeReference(IncludeReferenceKind.Self)

    index_of_sharp = include.find("#")
    if index_of_sharp == -1:
        return IncludeReference(IncludeReferenceKind.TopLevelReference, scopeName=include)
    if index_of_sharp == 0:
        return IncludeReference(IncludeReferenceKind.RelativeReference, ruleName=include[1:])
    return IncludeReference(
        IncludeReferenceKind.TopLevelRepositoryReference,
        scopeName=include[:index_of_sharp],
        ruleName=include[index_of_sharp + 1 :],
    )


def init_grammar(grammar: IRawGrammarDict, base: IRawRuleDict | None = None) -> IRawGrammarDict:
    """Port of ``initGrammar`` (grammar.ts:410-421): deep-copies the raw grammar
    and installs the ``$self`` and ``$base`` repository entries the include
    resolution relies on (``$self`` = the top-level patterns, ``$base`` = the
    caller-provided base grammar's self entry or the grammar's own)."""

    grammar = copy.deepcopy(grammar)

    # grammar.ts:413
    repository = grammar.get("repository") or {}
    grammar["repository"] = repository

    # grammar.ts:414-418
    location = grammar.get("$vscodeTextmateLocation")
    repository["$self"] = {
        "$vscodeTextmateLocation": location,
        "patterns": grammar.get("patterns"),
        "name": grammar.get("scopeName"),
    }

    # grammar.ts:419
    repository["$base"] = base if base is not None else repository["$self"]

    return grammar


class RuleFactory:
    """Port of ``RuleFactory`` (rule.ts:381-573)."""

    @staticmethod
    def create_capture_rule(  # noqa: N802
        helper: IRuleFactoryHelper,
        location: ILocation,
        name: str | None,
        contentName: str | None,  # noqa: N803
        retokenizeCapturedWithRuleId: int,  # noqa: N803
    ) -> CaptureRule:
        """Port of ``createCaptureRule`` (rule.ts:383-387): registers the capture
        rule under a fresh id."""
        return helper.register_rule(
            lambda id: CaptureRule(location, id, name, contentName, retokenizeCapturedWithRuleId)  # noqa: B008
        )

    @staticmethod
    def get_compiled_rule_id(  # noqa: N802
        desc: IRawRuleDict, helper: IRuleFactoryHelper, repository: IRawRepositoryDict
    ) -> int:
        """Port of ``getCompiledRuleId`` (rule.ts:389-447): the dispatch on the raw
        rule's shape, memoized on the rule dict via its internal ``id`` field.

        Note on recursion: upstream writes ``desc.id = id`` *inside* the factory
        callback, which is invoked synchronously by ``registerRule`` — so the id is
        stored before any nested ``getCompiledRuleId`` runs, exactly as here.
        """

        # rule.ts:390 — a previously compiled desc keeps its id; the callback sets
        # desc['id'] = id first thing (rule.ts:391-392) so re-entrancy sees it
        if not desc.get("id"):
            helper.register_rule(_RuleFactoryCallback(desc, helper, repository))

        return desc["id"]

    @staticmethod
    def compile_captures(  # noqa: N802
        captures: IRawRuleDict | None, helper: IRuleFactoryHelper, repository: IRawRepositoryDict
    ) -> list[CaptureRule | None]:
        """Port of ``_compileCaptures`` (rule.ts:449-485): builds the
        ``(CaptureRule | None)[]`` indexed by capture group number 1..n."""
        result: list[CaptureRule | None] = []

        if captures:
            # rule.ts:454-461 — find the maximum capture id (keys "1", "2", ...)
            maximum_capture_id = 0
            for capture_id in captures:
                if capture_id == "$vscodeTextmateLocation":
                    continue
                numeric_capture_id = int(capture_id)
                if numeric_capture_id > maximum_capture_id:
                    maximum_capture_id = numeric_capture_id

            # rule.ts:466-468 — initialize the result with nones
            result = [None] * (maximum_capture_id + 1)

            # rule.ts:471-481 — fill out result; a capture group declaring
            # `patterns` retokenizes its content with a fresh nested rule
            for capture_id in captures:
                if capture_id == "$vscodeTextmateLocation":
                    continue
                numeric_capture_id = int(capture_id)
                capture = captures[capture_id]
                retokenize_captured_with_rule_id = _NO_RETOKENIZE
                if capture.get("patterns"):
                    retokenize_captured_with_rule_id = RuleFactory.get_compiled_rule_id(
                        capture, helper, repository
                    )
                result[numeric_capture_id] = RuleFactory.create_capture_rule(
                    helper,
                    capture.get("$vscodeTextmateLocation"),
                    capture.get("name"),
                    capture.get("contentName"),
                    retokenize_captured_with_rule_id,
                )

        return result

    @staticmethod
    def compile_patterns(  # noqa: N802
        patterns: list[IRawRuleDict] | None,
        helper: IRuleFactoryHelper,
        repository: IRawRepositoryDict,
    ) -> CompilePatternsResult:
        """Port of ``_compilePatterns`` (rule.ts:487-572): compiles the raw pattern
        list to rule ids, preserving order, resolving ``include`` entries and
        dropping rules whose include chain resolves to nothing instantiated."""
        result: list[int] = []

        if patterns:
            for pattern in patterns:
                # rule.ts:493 — -1 signals "entry dropped"
                rule_id: int = -1

                if pattern.get("include"):
                    reference = parse_include(pattern["include"])

                    # rule.ts:499-542
                    if reference.kind in (
                        IncludeReferenceKind.Base,
                        IncludeReferenceKind.Self,
                    ):
                        # rule.ts:502 — look up the raw repository rule; the
                        # grammar must have $self/$base installed (init_grammar).
                        # int(...[-1]) keeps the type narrow: a missing entry is a
                        # programming error upstream too (it would throw)
                        included = repository[pattern["include"]]
                        rule_id = RuleFactory.get_compiled_rule_id(included, helper, repository)
                    elif reference.kind == IncludeReferenceKind.RelativeReference:
                        # rule.ts:507-513 — local include found in `repository`
                        local_included_rule = repository.get(reference.ruleName or "")
                        if local_included_rule:
                            rule_id = RuleFactory.get_compiled_rule_id(
                                local_included_rule, helper, repository
                            )
                        # else: dropped (upstream logs a warning; the id stays -1)
                    else:
                        # rule.ts:517-541 — external include (scope name), with or
                        # without a `#repository` rule name; resolved through the
                        # IRuleFactoryHelper hook (task 4b implements it)
                        external_grammar_name = reference.scopeName
                        external_grammar_include = (
                            reference.ruleName
                            if reference.kind == IncludeReferenceKind.TopLevelRepositoryReference
                            else None
                        )

                        external_grammar = helper.get_external_grammar(
                            external_grammar_name or "", repository
                        )

                        if external_grammar:
                            if external_grammar_include:
                                external_included_rule = (
                                    external_grammar.get("repository") or {}
                                ).get(external_grammar_include)
                                if external_included_rule:
                                    rule_id = RuleFactory.get_compiled_rule_id(
                                        external_included_rule,
                                        helper,
                                        external_grammar.get("repository") or {},
                                    )
                            else:
                                # rule.ts:536 — the external grammar's top rule
                                external_repository = external_grammar.get("repository") or {}
                                self_rule = external_repository.get("$self")
                                if self_rule is not None:
                                    rule_id = RuleFactory.get_compiled_rule_id(
                                        self_rule, helper, external_repository
                                    )
                        # else: dropped (upstream logs a warning; the id stays -1)
                else:
                    # rule.ts:544 — an inline (anonymous) pattern compiles itself
                    rule_id = RuleFactory.get_compiled_rule_id(pattern, helper, repository)

                if rule_id != -1:
                    # rule.ts:548-562 — skip rules that are pattern-less skeletons
                    # whose pattern lists all had missing include targets
                    rule = helper.get_rule(rule_id)

                    skip_rule = False

                    if isinstance(rule, (IncludeOnlyRule, BeginEndRule, BeginWhileRule)) and (
                        rule.hasMissingPatterns and len(rule.patterns) == 0
                    ):
                        skip_rule = True

                    if skip_rule:
                        continue

                    result.append(rule_id)

        # rule.ts:568-571 — order preserved; a shorter output means patterns went
        # missing (rule.ts:570)
        return CompilePatternsResult(
            patterns=tuple(result),
            hasMissingPatterns=len(patterns) != len(result) if patterns else False,
        )


def create_rule(
    desc: IRawRuleDict, helper: IRuleFactoryHelper, repository: IRawRepositoryDict
) -> int:
    """Mirror of ``RuleFactory.getCompiledRuleId`` (task-card spelling); prefer
    :meth:`RuleFactory.get_compiled_rule_id`."""
    return RuleFactory.get_compiled_rule_id(desc, helper, repository)


class _RuleFactoryCallback:
    """The `(id) => { ... }` factories of ``getCompiledRuleId`` (rule.ts:391-443),
    kept as a small class so the dispatch reads like upstream. The callback stores
    the allocated id on the raw desc *first* (rule.ts:391-392) so behaviour is
    identical under recursion."""

    def __init__(
        self, desc: IRawRuleDict, helper: IRuleFactoryHelper, repository: IRawRepositoryDict
    ) -> None:
        self._desc = desc
        self._helper = helper
        self._repository = repository

    def __call__(self, id: int) -> Rule:  # noqa: A002
        desc = self._desc
        helper = self._helper
        repository = self._repository

        # rule.ts:392 — memoize on the desc (consumed by the guard in
        # getCompiledRuleId once the callback returns)
        desc["id"] = id

        # rule.ts:394-402 — match rule
        if desc.get("match"):
            return MatchRule(
                desc.get("$vscodeTextmateLocation"),
                desc["id"],
                desc.get("name"),
                desc["match"],
                RuleFactory.compile_captures(desc.get("captures"), helper, repository),
            )

        # rule.ts:404-419 — begin is undefined: include-only rule; a local
        # `repository` section extends the parent's for the patterns below it
        if "begin" not in desc or desc["begin"] is None:
            if desc.get("repository"):
                repository = {**repository, **desc["repository"]}
            patterns = desc.get("patterns")
            if patterns is None and desc.get("include"):
                # rule.ts:409-411 — a bare `include` becomes the pattern list
                patterns = [{"include": desc["include"]}]
            return IncludeOnlyRule(
                desc.get("$vscodeTextmateLocation"),
                desc["id"],
                desc.get("name"),
                desc.get("contentName"),
                RuleFactory.compile_patterns(patterns, helper, repository),
            )

        # rule.ts:421-431 — begin + while: BeginWhileRule; captures fall back to
        # the rule-level `captures` when the specific ones are missing
        if desc.get("while"):
            return BeginWhileRule(
                desc.get("$vscodeTextmateLocation"),
                desc["id"],
                desc.get("name"),
                desc.get("contentName"),
                desc["begin"],
                RuleFactory.compile_captures(
                    desc.get("beginCaptures") or desc.get("captures"), helper, repository
                ),
                desc["while"],
                RuleFactory.compile_captures(
                    desc.get("whileCaptures") or desc.get("captures"), helper, repository
                ),
                RuleFactory.compile_patterns(desc.get("patterns"), helper, repository),
            )

        # rule.ts:433-442 — begin + end: BeginEndRule
        return BeginEndRule(
            desc.get("$vscodeTextmateLocation"),
            desc["id"],
            desc.get("name"),
            desc.get("contentName"),
            desc["begin"],
            RuleFactory.compile_captures(
                desc.get("beginCaptures") or desc.get("captures"), helper, repository
            ),
            desc.get("end"),
            RuleFactory.compile_captures(
                desc.get("endCaptures") or desc.get("captures"), helper, repository
            ),
            desc.get("applyEndPatternLast"),
            RuleFactory.compile_patterns(desc.get("patterns"), helper, repository),
        )
