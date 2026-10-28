"""The vscode-textmate v9.3.2 state model and line tokenization engine.

The main loop follows ``grammar/tokenizeString.ts``. Scope names and state are
kept as immutable parent-linked structures, while enter/anchor positions are
line-local mutable bookkeeping exactly as in ``StateStackImpl``.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .matcher import create_matchers, match_scope_identifiers
from .oniglib import DEFAULT_ONIG_LIB, FindOption, IOnigCaptureIndex, IOnigLib, OnigString
from .regexsource import CompiledRule
from .rules import (
    END_RULE_ID,
    WHILE_RULE_ID,
    BeginEndRule,
    BeginWhileRule,
    CaptureRule,
    IRuleFactoryHelper,
    MatchRule,
    Rule,
    RuleFactory,
    RuleRegistry,
    init_grammar,
)

__all__ = (
    "AttributedScopeStack",
    "BalancedBracketSelectors",
    "Grammar",
    "IToken",
    "ITokenizeLineResult",
    "LineTokens",
    "ScopeListElement",
    "ScopeStack",
    "StateStack",
    "StateStackImpl",
    "TokenHandler",
    "create_grammar",
    "createGrammar",
    "getScopeName",
    "getScopeNames",
    "get_scope_name",
    "get_scope_names",
)


class ScopeStack:
    """The ``theme.ts`` linked scope path, in root-first observable order."""

    __slots__ = ("parent", "scope_name")

    def __init__(self, parent: ScopeStack | None, scope_name: str) -> None:
        self.parent = parent
        self.scope_name = scope_name

    @classmethod
    def push_many(cls, path: ScopeStack | None, scope_names: Sequence[str]) -> ScopeStack | None:
        for name in scope_names:
            path = cls(path, name)
        return path

    @classmethod
    def from_segments(cls, *segments: str) -> ScopeStack | None:
        return cls.push_many(None, segments)

    @property
    def scopeName(self) -> str:  # noqa: N802
        return self.scope_name

    @property
    def name(self) -> str:
        return self.scope_name

    def push(self, scope_name: str) -> ScopeStack:
        return ScopeStack(self, scope_name)

    def get_segments(self) -> list[str]:
        return get_scope_names(self)

    def getSegments(self) -> list[str]:  # noqa: N802
        return self.get_segments()

    def get_extension_if_defined(self, base: ScopeStack | None) -> list[str] | None:
        result: list[str] = []
        item: ScopeStack | None = self
        while item is not None and item is not base:
            result.append(item.scope_name)
            item = item.parent
        return list(reversed(result)) if item is base else None

    def extends(self, other: ScopeStack) -> bool:
        item: ScopeStack | None = self
        while item is not None:
            if item is other:
                return True
            item = item.parent
        return False

    def __str__(self) -> str:
        return " ".join(get_scope_names(self))


@dataclass(frozen=True, slots=True, eq=False)
class AttributedScopeStack:
    """Scope path node plus vscode-textmate's inherited token/style attributes."""

    parent: AttributedScopeStack | None
    scope_path: ScopeStack
    token_attributes: int = 0
    font_attributes: Any = None
    style_attributes: Any = None

    @property
    def scopePath(self) -> ScopeStack:  # noqa: N802
        return self.scope_path

    @property
    def tokenAttributes(self) -> int:  # noqa: N802
        return self.token_attributes

    @property
    def fontAttributes(self) -> Any:  # noqa: N802
        return self.font_attributes

    @property
    def styleAttributes(self) -> Any:  # noqa: N802
        return self.style_attributes

    @property
    def scope_name(self) -> str:
        return self.scope_path.scope_name

    @classmethod
    def create_root(cls, scope_name: str) -> AttributedScopeStack:
        return cls(None, ScopeStack(None, scope_name))

    @classmethod
    def from_extension(
        cls,
        name_scopes_list: AttributedScopeStack | None,
        content_name_scopes_list: Sequence[Mapping[str, Any]],
    ) -> AttributedScopeStack | None:
        current = name_scopes_list
        scope_path = name_scopes_list.scope_path if name_scopes_list is not None else None
        for frame in content_name_scopes_list:
            names = frame.get("scopeNames", [])
            scope_path = ScopeStack.push_many(scope_path, names)
            if scope_path is None:
                continue
            current = cls(
                current,
                scope_path,
                int(frame.get("encodedTokenAttributes", 0)),
            )
        return current

    @classmethod
    def fromExtension(  # noqa: N802
        cls,
        name_scopes_list: AttributedScopeStack | None,
        content_name_scopes_list: Sequence[Mapping[str, Any]],
    ) -> AttributedScopeStack | None:
        return cls.from_extension(name_scopes_list, content_name_scopes_list)

    def push_attributed(self, scope_names: str | None, grammar: Grammar) -> AttributedScopeStack:
        if scope_names is None:
            return self
        result = self
        for scope_name in scope_names.split(" "):
            if scope_name:
                result = AttributedScopeStack(
                    result,
                    result.scope_path.push(scope_name),
                    result.token_attributes,
                )
        return result

    def pushAttributed(self, scope_names: str | None, grammar: Grammar) -> AttributedScopeStack:  # noqa: N802
        return self.push_attributed(scope_names, grammar)

    def get_scope_names(self) -> list[str]:
        return self.scope_path.get_segments()

    def getScopeNames(self) -> list[str]:  # noqa: N802
        return self.get_scope_names()

    def get_extension_if_defined(
        self, base: AttributedScopeStack | None
    ) -> list[dict[str, Any]] | None:
        frames: list[dict[str, Any]] = []
        item: AttributedScopeStack | None = self
        while item is not None and item is not base:
            scope_names = item.scope_path.get_extension_if_defined(
                item.parent.scope_path if item.parent is not None else None
            )
            frames.append(
                {"encodedTokenAttributes": item.token_attributes, "scopeNames": scope_names or []}
            )
            item = item.parent
        return list(reversed(frames)) if item is base else None

    def getExtensionIfDefined(
        self, base: AttributedScopeStack | None
    ) -> list[dict[str, Any]] | None:  # noqa: N802
        return self.get_extension_if_defined(base)

    def equals(self, other: AttributedScopeStack | None) -> bool:
        return attributed_scope_stacks_equal(self, other)

    def __str__(self) -> str:
        return " ".join(self.get_scope_names())


def attributed_scope_stacks_equal(
    left: AttributedScopeStack | None, right: AttributedScopeStack | None
) -> bool:
    while left is not right:
        if left is None or right is None:
            return left is right
        if left.scope_name != right.scope_name or left.token_attributes != right.token_attributes:
            return False
        left, right = left.parent, right.parent
    return True


class StateStackImpl:
    """Port of grammar.ts ``StateStackImpl`` (including line-scoped positions)."""

    NULL: StateStackImpl

    def __init__(
        self,
        parent: StateStackImpl | None,
        rule_id: int,
        enter_pos: int,
        anchor_pos: int,
        begin_rule_captured_eol: bool,
        end_rule: str | None,
        name_scopes_list: AttributedScopeStack | None,
        content_name_scopes_list: AttributedScopeStack | None,
    ) -> None:
        self.parent = parent
        self.rule_id = rule_id
        self._enter_pos = enter_pos
        self._anchor_pos = anchor_pos
        self.beginRuleCapturedEOL = begin_rule_captured_eol
        self.endRule = end_rule
        self.nameScopesList = name_scopes_list
        self.contentNameScopesList = content_name_scopes_list
        self.depth: int = parent.depth + 1 if parent is not None else 1

    @property
    def ruleId(self) -> int:  # noqa: N802
        return self.rule_id

    @property
    def begin_rule_captured_eol(self) -> bool:
        return self.beginRuleCapturedEOL

    @property
    def end_rule(self) -> str | None:
        return self.endRule

    @property
    def name_scopes_list(self) -> AttributedScopeStack | None:
        return self.nameScopesList

    @property
    def content_name_scopes_list(self) -> AttributedScopeStack | None:
        return self.contentNameScopesList

    def clone(self) -> StateStackImpl:
        return self

    @staticmethod
    def _structural_equals(left: StateStackImpl | None, right: StateStackImpl | None) -> bool:
        while left is not right:
            if left is None or right is None:
                return left is right
            if (
                left.depth != right.depth
                or left.rule_id != right.rule_id
                or left.endRule != right.endRule
            ):
                return False
            left, right = left.parent, right.parent
        return True

    _structuralEquals = _structural_equals  # noqa: N815

    def structural_equals(self, other: StateStackImpl | None) -> bool:
        return self._structural_equals(self, other)

    def equals(self, other: StateStackImpl | None) -> bool:
        return (
            other is not None
            and self._structural_equals(self, other)
            and attributed_scope_stacks_equal(
                self.contentNameScopesList, other.contentNameScopesList
            )
        )

    def reset(self) -> None:
        item: StateStackImpl | None = self
        while item is not None:
            item._enter_pos = -1
            item._anchor_pos = -1
            item = item.parent

    def pop(self) -> StateStackImpl | None:
        return self.parent

    def safe_pop(self) -> StateStackImpl:
        return self.parent if self.parent is not None else self

    def safePop(self) -> StateStackImpl:  # noqa: N802
        return self.safe_pop()

    def push(
        self,
        rule_id: int,
        enter_pos: int,
        anchor_pos: int,
        begin_rule_captured_eol: bool,
        end_rule: str | None,
        name_scopes_list: AttributedScopeStack | None,
        content_name_scopes_list: AttributedScopeStack | None,
    ) -> StateStackImpl:
        return StateStackImpl(
            self,
            rule_id,
            enter_pos,
            anchor_pos,
            begin_rule_captured_eol,
            end_rule,
            name_scopes_list,
            content_name_scopes_list,
        )

    def get_enter_pos(self) -> int:
        return self._enter_pos

    def getEnterPos(self) -> int:  # noqa: N802
        return self.get_enter_pos()

    def get_anchor_pos(self) -> int:
        return self._anchor_pos

    def getAnchorPos(self) -> int:  # noqa: N802
        return self.get_anchor_pos()

    def get_rule(self, grammar: RuleRegistry) -> Rule:
        return grammar.get_rule(self.rule_id)

    def with_content_name_scopes_list(self, scopes: AttributedScopeStack) -> StateStackImpl:
        if self.contentNameScopesList is scopes:
            return self
        if self.parent is None:
            raise RuntimeError("root stack frame has no parent")
        return self.parent.push(
            self.rule_id,
            self._enter_pos,
            self._anchor_pos,
            self.beginRuleCapturedEOL,
            self.endRule,
            self.nameScopesList,
            scopes,
        )

    def withContentNameScopesList(self, scopes: AttributedScopeStack) -> StateStackImpl:  # noqa: N802
        return self.with_content_name_scopes_list(scopes)

    def with_end_rule(self, end_rule: str) -> StateStackImpl:
        if self.endRule == end_rule:
            return self
        return StateStackImpl(
            self.parent,
            self.rule_id,
            self._enter_pos,
            self._anchor_pos,
            self.beginRuleCapturedEOL,
            end_rule,
            self.nameScopesList,
            self.contentNameScopesList,
        )

    def withEndRule(self, end_rule: str) -> StateStackImpl:  # noqa: N802
        return self.with_end_rule(end_rule)

    def has_same_rule_as(self, other: StateStackImpl) -> bool:
        item: StateStackImpl | None = self
        while item is not None and item._enter_pos == other._enter_pos:
            if item.rule_id == other.rule_id:
                return True
            item = item.parent
        return False

    def hasSameRuleAs(self, other: StateStackImpl) -> bool:  # noqa: N802
        return self.has_same_rule_as(other)

    def to_state_stack_frame(self) -> dict[str, Any]:
        name_extension = (
            self.nameScopesList.get_extension_if_defined(
                self.parent.nameScopesList if self.parent is not None else None
            )
            if self.nameScopesList is not None
            else None
        )
        content_extension = (
            self.contentNameScopesList.get_extension_if_defined(self.nameScopesList)
            if self.contentNameScopesList is not None
            else None
        )
        return {
            "ruleId": self.rule_id,
            "beginRuleCapturedEOL": self.beginRuleCapturedEOL,
            "endRule": self.endRule,
            "nameScopesList": name_extension or [],
            "contentNameScopesList": content_extension or [],
        }

    def toStateStackFrame(self) -> dict[str, Any]:  # noqa: N802
        return self.to_state_stack_frame()

    @classmethod
    def push_frame(cls, parent: StateStackImpl | None, frame: Mapping[str, Any]) -> StateStackImpl:
        name_scopes = AttributedScopeStack.from_extension(
            parent.nameScopesList if parent is not None else None,
            frame.get("nameScopesList", ()),
        )
        if name_scopes is None:
            raise ValueError("state frame must provide a name scope")
        content_scopes = AttributedScopeStack.from_extension(
            name_scopes, frame.get("contentNameScopesList", ())
        )
        return cls(
            parent,
            int(frame["ruleId"]),
            int(frame.get("enterPos", -1)),
            int(frame.get("anchorPos", -1)),
            bool(frame["beginRuleCapturedEOL"]),
            frame.get("endRule"),
            name_scopes,
            content_scopes,
        )

    @classmethod
    def pushFrame(cls, parent: StateStackImpl | None, frame: Mapping[str, Any]) -> StateStackImpl:  # noqa: N802
        return cls.push_frame(parent, frame)

    def to_string(self) -> str:
        frames: list[str] = []
        item: StateStackImpl | None = self
        while item is not None:
            frames.append(f"({item.rule_id}, {item.nameScopesList}, {item.contentNameScopesList})")
            item = item.parent
        return "[" + ",".join(reversed(frames)) + "]"

    def __str__(self) -> str:
        return self.to_string()


StateStackImpl.NULL = StateStackImpl(None, 0, 0, 0, False, None, None, None)
# Transitional public spelling retained while task 5 changes the package API.
StateStack = StateStackImpl
ScopeListElement = ScopeStack


@dataclass(frozen=True, slots=True)
class IToken:
    startIndex: int
    endIndex: int
    scopes: list[str]

    @property
    def start_index(self) -> int:
        return self.startIndex

    @property
    def end_index(self) -> int:
        return self.endIndex


@dataclass(frozen=True, slots=True)
class ITokenizeLineResult:
    tokens: list[IToken]
    ruleStack: StateStackImpl
    stoppedEarly: bool

    @property
    def rule_stack(self) -> StateStackImpl:
        return self.ruleStack

    @property
    def stopped_early(self) -> bool:
        return self.stoppedEarly


class BalancedBracketSelectors:
    """Balanced-bracket selector matcher for the optional binary-token API."""

    def __init__(self, balanced: Sequence[str], unbalanced: Sequence[str]) -> None:
        self.allow_any = "*" in balanced
        self.balanced = [
            matcher.matcher
            for selector in balanced
            if selector != "*"
            for matcher in create_matchers(selector, match_scope_identifiers)
        ]
        self.unbalanced = [
            matcher.matcher
            for selector in unbalanced
            for matcher in create_matchers(selector, match_scope_identifiers)
        ]

    @property
    def matchesAlways(self) -> bool:  # noqa: N802
        return self.allow_any and not self.unbalanced

    @property
    def matchesNever(self) -> bool:  # noqa: N802
        return not self.balanced and not self.allow_any

    def match(self, scopes: list[str]) -> bool:
        return not any(matcher(scopes) for matcher in self.unbalanced) and (
            self.allow_any or any(matcher(scopes) for matcher in self.balanced)
        )


class LineTokens:
    """Minimal ``LineTokens`` implementation for scope-array tokens."""

    def __init__(self, line_text: str) -> None:
        self.line_text = line_text
        self.tokens: list[IToken] = []
        self.last_token_end_index = 0

    def produce_from_scopes(self, scopes: AttributedScopeStack | None, end_index: int) -> None:
        if self.last_token_end_index >= end_index:
            return
        self.tokens.append(
            IToken(self.last_token_end_index, end_index, scopes.get_scope_names() if scopes else [])
        )
        self.last_token_end_index = end_index

    def get_result(self, stack: StateStackImpl, line_length: int) -> list[IToken]:
        if self.tokens and self.tokens[-1].startIndex == line_length - 1:
            self.tokens.pop()
        if not self.tokens:
            self.last_token_end_index = -1
            self.produce_from_scopes(stack.contentNameScopesList, line_length)
            self.tokens[-1] = IToken(0, self.tokens[-1].endIndex, self.tokens[-1].scopes)
        return self.tokens


class TokenHandler:
    def __init__(self, line_text: str) -> None:
        self.line_tokens = LineTokens(line_text)

    def handle(self, scopes: AttributedScopeStack | None, end_index: int) -> None:
        self.line_tokens.produce_from_scopes(scopes, end_index)

    def get_token_result(self, stack: StateStackImpl, line_length: int) -> list[IToken]:
        return self.line_tokens.get_result(stack, line_length)


@dataclass(frozen=True)
class Injection:
    debug_selector: str
    matcher: Callable[[list[str]], bool]
    priority: int
    rule_id: int
    grammar: Mapping[str, Any]


class _DefaultGrammarRepository:
    def __init__(
        self, root: Mapping[str, Any], external: Callable[[str], Mapping[str, Any] | None] | None
    ) -> None:
        self.root = root
        self.external = external

    def lookup(self, scope_name: str) -> Mapping[str, Any] | None:
        if scope_name == self.root.get("scopeName"):
            return self.root
        return self.external(scope_name) if self.external is not None else None

    def injections(self, scope_name: str) -> Sequence[str]:
        del scope_name
        return ()


class Grammar(RuleRegistry, IRuleFactoryHelper):
    """A loaded grammar and its vscode-textmate line tokenizer."""

    def __init__(
        self,
        scope_name: str,
        grammar: Mapping[str, Any],
        initial_language: int = 1,
        embedded_languages: Mapping[str, int] | None = None,
        token_types: Mapping[str, int] | None = None,
        balanced_bracket_selectors: BalancedBracketSelectors | None = None,
        grammar_repository: Any = None,
        onig_lib: IOnigLib = DEFAULT_ONIG_LIB,
        *,
        external_grammar: Callable[[str], Mapping[str, Any] | None] | None = None,
    ) -> None:
        super().__init__(onig_lib)
        self.root_scope_name = scope_name
        self.grammar = init_grammar(dict(grammar))
        self.initial_language = initial_language
        self.embedded_languages = embedded_languages or {}
        self.token_types = token_types or {}
        self.balanced_bracket_selectors = balanced_bracket_selectors
        self.grammar_repository = grammar_repository or _DefaultGrammarRepository(
            grammar, external_grammar
        )
        self._external_grammar_callback = external_grammar
        self._included_grammars: dict[str, Mapping[str, Any]] = {}
        self._root_id = -1
        self._injections: list[Injection] | None = None

    def get_external_grammar(
        self, scope_name: str, repository: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if scope_name in self._included_grammars:
            return self._included_grammars[scope_name]  # type: ignore[return-value]
        raw: Mapping[str, Any] | None = None
        repo = self.grammar_repository
        lookup = getattr(repo, "get_external_grammar", None)
        if callable(lookup):
            raw = lookup(scope_name, repository)
        if raw is None and callable(getattr(repo, "lookup", None)):
            raw = repo.lookup(scope_name)
        if raw is None and self._external_grammar_callback is not None:
            raw = self._external_grammar_callback(scope_name)
        if raw is None:
            return None
        base = repository.get("$base") if repository else None
        initialized = init_grammar(dict(raw), base if isinstance(base, dict) else None)
        self._included_grammars[scope_name] = initialized
        return initialized

    def _collect_injections(self) -> list[Injection]:
        result: list[Injection] = []

        def add_injections(raw_grammar: Mapping[str, Any]) -> None:
            injections = raw_grammar.get("injections")
            if not isinstance(injections, Mapping):
                return
            repo = raw_grammar.get("repository") or {}
            for selector, raw_rule in injections.items():
                if not isinstance(selector, str) or not isinstance(raw_rule, dict):
                    continue
                for matcher in create_matchers(selector, match_scope_identifiers):
                    rule_id = RuleFactory.get_compiled_rule_id(raw_rule, self, repo)
                    result.append(
                        Injection(selector, matcher.matcher, matcher.priority, rule_id, raw_grammar)
                    )

        add_injections(self.grammar)
        repo = self.grammar_repository
        injection_scopes = (
            repo.injections(self.root_scope_name)
            if callable(getattr(repo, "injections", None))
            else ()
        )
        for injection_scope in injection_scopes or ():
            injection_grammar = self.get_external_grammar(injection_scope, None)
            if injection_grammar is not None and injection_grammar.get("injectionSelector"):
                selector = str(injection_grammar["injectionSelector"])
                for matcher in create_matchers(selector, match_scope_identifiers):
                    rule_id = RuleFactory.get_compiled_rule_id(
                        injection_grammar, self, injection_grammar.get("repository") or {}
                    )
                    result.append(
                        Injection(
                            selector, matcher.matcher, matcher.priority, rule_id, injection_grammar
                        )
                    )
        # Python's sort is stable, matching Array.sort's stable ordering in the pinned runtime.
        result.sort(key=lambda injection: injection.priority)
        return result

    def get_injections(self) -> list[Injection]:
        if self._injections is None:
            self._injections = self._collect_injections()
        return self._injections

    def _ensure_root(self) -> None:
        if self._root_id == -1:
            self._root_id = RuleFactory.get_compiled_rule_id(
                self.grammar["repository"]["$self"], self, self.grammar["repository"]
            )
            # Upstream eagerly collects these so injection rules get deterministic ids.
            self.get_injections()

    def tokenize_line(
        self, line_text: str, prev_state: StateStackImpl | None = None, time_limit: int = 0
    ) -> ITokenizeLineResult:
        self._ensure_root()
        is_first_line = prev_state is None or prev_state is StateStackImpl.NULL
        if is_first_line:
            root_rule = self.get_rule(self._root_id)
            root_scope = root_rule.getName(None, None) or "unknown"
            scopes = AttributedScopeStack.create_root(root_scope)
            stack = StateStackImpl(None, self._root_id, -1, -1, False, None, scopes, scopes)
        else:
            assert prev_state is not None
            stack = prev_state
            stack.reset()
        augmented_line = line_text + "\n"
        onig_line = self.create_onig_string(augmented_line)
        handler = TokenHandler(augmented_line)
        final_stack, stopped_early = _tokenize_string(
            self, onig_line, is_first_line, 0, stack, handler, True, time_limit
        )
        onig_line.dispose()
        return ITokenizeLineResult(
            handler.get_token_result(final_stack, len(augmented_line)), final_stack, stopped_early
        )

    def tokenizeLine(
        self, line_text: str, prev_state: StateStackImpl | None = None, time_limit: int = 0
    ) -> ITokenizeLineResult:  # noqa: N802
        return self.tokenize_line(line_text, prev_state, time_limit)

    def dispose(self) -> None:
        for rule in self._rule_id2desc:
            if rule is not None:
                rule.dispose()


def create_grammar(
    scope_name: str,
    grammar: Mapping[str, Any],
    initial_language: int = 1,
    embedded_languages: Mapping[str, int] | None = None,
    token_types: Mapping[str, int] | None = None,
    balanced_bracket_selectors: BalancedBracketSelectors | None = None,
    grammar_repository: Any = None,
    onig_lib: IOnigLib = DEFAULT_ONIG_LIB,
    *,
    external_grammar: Callable[[str], Mapping[str, Any] | None] | None = None,
) -> Grammar:
    """Construct a grammar; ``external_grammar`` is the registry integration seam."""
    return Grammar(
        scope_name,
        grammar,
        initial_language,
        embedded_languages,
        token_types,
        balanced_bracket_selectors,
        grammar_repository,
        onig_lib,
        external_grammar=external_grammar,
    )


createGrammar = create_grammar  # noqa: N816


@dataclass(frozen=True)
class _MatchResult:
    capture_indices: Sequence[IOnigCaptureIndex]
    matched_rule_id: int
    priority_match: bool = False


def _find_options(allow_a: bool, allow_g: bool) -> FindOption:
    options = FindOption.NONE
    if not allow_a:
        options |= FindOption.NOT_BEGIN_STRING
    if not allow_g:
        options |= FindOption.NOT_BEGIN_POSITION
    return options


def _prepare_rule_search(
    rule: Rule, grammar: Grammar, end_source: str | None, is_first_line: bool, allow_g: bool
) -> tuple[CompiledRule, FindOption]:
    # Task 1a's compile_ag path implements anchor variants; do not bind \G with a
    # mutable/stored anchor or bypass RegExpSourceList's anchor cache.
    return rule.compileAG(grammar, end_source, is_first_line, allow_g), FindOption.NONE


def _match_rule(
    grammar: Grammar,
    line: OnigString,
    is_first_line: bool,
    line_pos: int,
    stack: StateStackImpl,
    anchor_position: int,
) -> _MatchResult | None:
    rule = stack.get_rule(grammar)
    scanner, options = _prepare_rule_search(
        rule, grammar, stack.endRule, is_first_line, line_pos == anchor_position
    )
    result = scanner.find_next_match_sync(line, line_pos, options)
    if result is None:
        return None
    return _MatchResult(result.capture_indices, result.rule_id)


def _match_injections(
    injections: Sequence[Injection],
    grammar: Grammar,
    line: OnigString,
    is_first_line: bool,
    line_pos: int,
    stack: StateStackImpl,
    anchor_position: int,
) -> _MatchResult | None:
    best: _MatchResult | None = None
    best_start = float("inf")
    scopes = stack.contentNameScopesList.get_scope_names() if stack.contentNameScopesList else []
    for injection in injections:
        if not injection.matcher(scopes):
            continue
        rule = grammar.get_rule(injection.rule_id)
        scanner, options = _prepare_rule_search(
            rule, grammar, None, is_first_line, line_pos == anchor_position
        )
        result = scanner.find_next_match_sync(line, line_pos, options)
        if result is None:
            continue
        start = result.capture_indices[0].start
        if start >= best_start:
            continue
        best_start = start
        best = _MatchResult(result.capture_indices, result.rule_id, injection.priority == -1)
        if best_start == line_pos:
            break
    return best


def _match_rule_or_injections(
    grammar: Grammar,
    line: OnigString,
    is_first_line: bool,
    line_pos: int,
    stack: StateStackImpl,
    anchor_position: int,
) -> _MatchResult | None:
    normal = _match_rule(grammar, line, is_first_line, line_pos, stack, anchor_position)
    injections = grammar.get_injections()
    if not injections:
        return normal
    injected = _match_injections(
        injections, grammar, line, is_first_line, line_pos, stack, anchor_position
    )
    if injected is None:
        return normal
    if normal is None:
        return injected
    injected_start = injected.capture_indices[0].start
    normal_start = normal.capture_indices[0].start
    return (
        injected
        if injected_start < normal_start
        or (injected.priority_match and injected_start == normal_start)
        else normal
    )


@dataclass
class _WhileCheckResult:
    stack: StateStackImpl
    line_pos: int
    anchor_position: int
    is_first_line: bool


def _check_while_conditions(
    grammar: Grammar,
    line: OnigString,
    is_first_line: bool,
    line_pos: int,
    stack: StateStackImpl,
    handler: TokenHandler,
) -> _WhileCheckResult:
    anchor_position = 0 if stack.beginRuleCapturedEOL else -1
    while_frames: list[tuple[StateStackImpl, BeginWhileRule]] = []
    item: StateStackImpl | None = stack
    while item is not None:
        rule = item.get_rule(grammar)
        if isinstance(rule, BeginWhileRule):
            while_frames.append((item, rule))
        item = item.parent

    for while_frame, rule in reversed(while_frames):
        # BeginWhileRule compiles its separate single-pattern while scanner.
        options = FindOption.NONE
        scanner = rule.compileWhileAG(
            grammar, while_frame.endRule, is_first_line, line_pos == anchor_position
        )
        result = scanner.find_next_match_sync(line, line_pos, options)
        if result is None:
            stack = while_frame.parent or while_frame
            break
        if result.rule_id != WHILE_RULE_ID:
            stack = while_frame.parent or while_frame
            break
        indices = result.capture_indices
        if indices:
            handler.handle(while_frame.contentNameScopesList, indices[0].start)
            _handle_captures(
                grammar, line, is_first_line, while_frame, handler, rule.whileCaptures, indices
            )
            handler.handle(while_frame.contentNameScopesList, indices[0].end)
            anchor_position = indices[0].end
            if indices[0].end > line_pos:
                line_pos = indices[0].end
                is_first_line = False
    return _WhileCheckResult(stack, line_pos, anchor_position, is_first_line)


def _handle_captures(
    grammar: Grammar,
    line: OnigString,
    is_first_line: bool,
    stack: StateStackImpl,
    handler: TokenHandler,
    captures: Sequence[CaptureRule | None],
    indices: Sequence[IOnigCaptureIndex],
) -> None:
    if not captures:
        return
    local: list[tuple[AttributedScopeStack, int]] = []
    max_end = indices[0].end
    for capture_id, capture in enumerate(captures[: len(indices)]):
        if capture is None:
            continue
        index = indices[capture_id]
        if index.length == 0:
            continue
        if index.start > max_end:
            break
        while local and local[-1][1] <= index.start:
            scopes, end = local.pop()
            handler.handle(scopes, end)
        handler.handle(local[-1][0] if local else stack.contentNameScopesList, index.start)
        if capture.retokenize_captured_with_rule_id:
            name = capture.getName(line.content, indices)
            name_scopes = (
                stack.contentNameScopesList or AttributedScopeStack.create_root("unknown")
            ).push_attributed(name, grammar)
            content_name = capture.getContentName(line.content, indices)
            content_scopes = name_scopes.push_attributed(content_name, grammar)
            nested = stack.push(
                capture.retokenize_captured_with_rule_id,
                index.start,
                -1,
                False,
                None,
                name_scopes,
                content_scopes,
            )
            subline = grammar.create_onig_string(line.content[: index.end])
            _tokenize_string(
                grammar,
                subline,
                is_first_line and index.start == 0,
                index.start,
                nested,
                handler,
                False,
                0,
            )
            subline.dispose()
            continue
        scope_name = capture.getName(line.content, indices)
        if scope_name is not None:
            base = local[-1][0] if local else stack.contentNameScopesList
            if base is not None:
                local.append((base.push_attributed(scope_name, grammar), index.end))
    while local:
        scopes, end = local.pop()
        handler.handle(scopes, end)


def _tokenize_string(
    grammar: Grammar,
    line: OnigString,
    is_first_line: bool,
    line_pos: int,
    stack: StateStackImpl,
    handler: TokenHandler,
    check_while_conditions: bool,
    time_limit: int,
) -> tuple[StateStackImpl, bool]:
    line_length = len(line.content)
    anchor_position = -1
    if check_while_conditions:
        while_result = _check_while_conditions(
            grammar, line, is_first_line, line_pos, stack, handler
        )
        stack = while_result.stack
        line_pos = while_result.line_pos
        is_first_line = while_result.is_first_line
        anchor_position = while_result.anchor_position

    start_time = time.monotonic()
    while True:
        if time_limit and (time.monotonic() - start_time) * 1000 > time_limit:
            return stack, True
        match = _match_rule_or_injections(
            grammar, line, is_first_line, line_pos, stack, anchor_position
        )
        if match is None:
            handler.handle(stack.contentNameScopesList, line_length)
            return stack, False

        indices = match.capture_indices
        matched_rule_id = match.matched_rule_id
        has_advanced = bool(indices) and indices[0].end > line_pos
        if matched_rule_id == END_RULE_ID:
            popped_rule = stack.get_rule(grammar)
            if not isinstance(popped_rule, BeginEndRule):
                raise RuntimeError("end rule matched outside a begin/end context")
            handler.handle(stack.contentNameScopesList, indices[0].start)
            stack = stack.with_content_name_scopes_list(stack.nameScopesList)  # type: ignore[arg-type]
            _handle_captures(
                grammar, line, is_first_line, stack, handler, popped_rule.endCaptures, indices
            )
            handler.handle(stack.contentNameScopesList, indices[0].end)
            popped = stack
            stack = stack.parent or stack
            anchor_position = popped.get_anchor_pos()
            if not has_advanced and popped.get_enter_pos() == line_pos:
                stack = popped
                handler.handle(stack.contentNameScopesList, line_length)
                return stack, False
        else:
            rule = grammar.get_rule(matched_rule_id)
            handler.handle(stack.contentNameScopesList, indices[0].start)
            before_push = stack
            scope_name = rule.getName(line.content, indices)
            name_scopes = (
                stack.contentNameScopesList or AttributedScopeStack.create_root("unknown")
            ).push_attributed(scope_name, grammar)
            stack = stack.push(
                matched_rule_id,
                line_pos,
                anchor_position,
                indices[0].end == line_length,
                None,
                name_scopes,
                name_scopes,
            )
            if isinstance(rule, (BeginEndRule, BeginWhileRule)):
                captures = rule.beginCaptures
                _handle_captures(grammar, line, is_first_line, stack, handler, captures, indices)
                handler.handle(stack.contentNameScopesList, indices[0].end)
                anchor_position = indices[0].end
                content_name = rule.getContentName(line.content, indices)
                content_scopes = name_scopes.push_attributed(content_name, grammar)
                stack = stack.with_content_name_scopes_list(content_scopes)
                if isinstance(rule, BeginEndRule) and rule.endHasBackReferences:
                    stack = stack.with_end_rule(
                        rule.getEndWithResolvedBackReferences(line.content, indices)
                    )
                elif isinstance(rule, BeginWhileRule) and rule.whileHasBackReferences:
                    stack = stack.with_end_rule(
                        rule.getWhileWithResolvedBackReferences(line.content, indices)
                    )
                if not has_advanced and before_push.has_same_rule_as(stack):
                    stack = stack.pop() or stack
                    handler.handle(stack.contentNameScopesList, line_length)
                    return stack, False
            else:
                captures = rule.captures if isinstance(rule, MatchRule) else []
                _handle_captures(grammar, line, is_first_line, stack, handler, captures, indices)
                handler.handle(stack.contentNameScopesList, indices[0].end)
                stack = stack.pop() or stack
                if not has_advanced:
                    stack = stack.safe_pop()
                    handler.handle(stack.contentNameScopesList, line_length)
                    return stack, False

        if indices[0].end > line_pos:
            line_pos = indices[0].end
            is_first_line = False


def get_scope_names(chain: Any | None) -> list[str]:
    result: list[str] = []
    item = chain
    while item is not None:
        if isinstance(item, (AttributedScopeStack, ScopeStack)):
            result.append(item.scope_name)
            item = item.parent
        else:
            name = getattr(
                item, "scope_name", getattr(item, "scopeName", getattr(item, "name", None))
            )
            if name is None:
                break
            result.append(name)
            item = getattr(item, "parent", None)
    result.reverse()
    return result


def get_scope_name(chain: Any | None) -> str:
    return " ".join(get_scope_names(chain))


getScopeName = get_scope_name  # noqa: N816
getScopeNames = get_scope_names  # noqa: N816
