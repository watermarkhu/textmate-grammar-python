"""Grammar registration and dependency loading from vscode-textmate v9.3.2.

The upstream ``Registry`` and ``SyncRegistry`` create the concrete ``Grammar``
class. That class is not available until task 3b, so the one deliberate seam here
is an injectable ``grammar_factory(location, raw_grammar)``. Its default raises
``NotImplementedError``; the later tokenizer task supplies the real constructor.

Upstream exposes asynchronous methods because its loader returns promises. This
port intentionally uses synchronous callables returning raw grammar mappings (or
``None``); dependency traversal, load caching, registration, and construction
otherwise retain the upstream behavior. ``onig_lib`` is carried in the options
for the eventual Grammar wiring, but is not consumed by this seam yet.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict, cast

from .oniglib import DEFAULT_ONIG_LIB, IOnigLib
from .raw_grammar import LOCATION_KEY, ILocation, IRawGrammar
from .rules import IncludeReferenceKind, init_grammar, parse_include

__all__ = [
    "AbsoluteRuleReference",
    "ExternalReferenceCollector",
    "Registry",
    "RegistryOptions",
    "ScopeDependencyProcessor",
    "SyncRegistry",
    "TopLevelRepositoryRuleReference",
    "TopLevelRuleReference",
    "TokenizerLike",
    "collect_includes",
    "get_grammar_dependencies",
]

RawGrammar = Mapping[str, Any]


class TokenizerLike(Protocol):
    """Minimal interface of a constructed grammar owned by the registry."""

    def dispose(self) -> None:
        """Release tokenizer resources, when present."""
        ...


class RegistryOptions(TypedDict, total=False):
    """Synchronous counterpart of upstream ``RegistryOptions``."""

    onig_lib: IOnigLib
    load_grammar: Callable[[str], IRawGrammar | None]
    get_injections: Callable[[str], Sequence[str] | None]
    onigLib: IOnigLib
    loadGrammar: Callable[[str], IRawGrammar | None]
    getInjections: Callable[[str], Sequence[str] | None]


GrammarFactory = Callable[[ILocation | None, IRawGrammar], TokenizerLike]


def _default_grammar_factory(registry: SyncRegistry, onig_lib: IOnigLib) -> GrammarFactory:
    """Build a tokenizer using the registry as its included-grammar repository."""
    from .tokenize import Grammar

    def create(location: ILocation | None, raw_grammar: IRawGrammar) -> TokenizerLike:
        del location
        return Grammar(
            str(raw_grammar["scopeName"]),
            raw_grammar,
            initial_language=0,
            grammar_repository=registry,
            onig_lib=onig_lib,
        )

    return create


@dataclass(frozen=True)
class TopLevelRuleReference:
    """Reference to an entire grammar, as in grammarDependencies.ts:15-22."""

    scope_name: str

    def to_key(self) -> str:
        return self.scope_name


@dataclass(frozen=True)
class TopLevelRepositoryRuleReference:
    """Reference to one named rule in a grammar's top-level repository."""

    scope_name: str
    rule_name: str

    def to_key(self) -> str:
        return f"{self.scope_name}#{self.rule_name}"


AbsoluteRuleReference = TopLevelRuleReference | TopLevelRepositoryRuleReference


class ExternalReferenceCollector:
    """Deduplicating collector; raw-rule visitation uses identity like JS Set."""

    def __init__(self) -> None:
        self.references: list[AbsoluteRuleReference] = []
        self._seen_reference_keys: set[str] = set()
        self.visited_rule: set[int] = set()

    def add(self, reference: AbsoluteRuleReference) -> None:
        key = reference.to_key()
        if key not in self._seen_reference_keys:
            self._seen_reference_keys.add(key)
            self.references.append(reference)


class ScopeDependencyProcessor:
    """Queue-based port of ``ScopeDependencyProcessor`` (lines 59-103)."""

    def __init__(self, repo: SyncRegistry, initial_scope_name: str) -> None:
        self.repo = repo
        self.initial_scope_name = initial_scope_name
        self.seen_full_scope_requests: set[str] = {initial_scope_name}
        self.seen_partial_scope_requests: set[str] = set()
        self.queue: list[AbsoluteRuleReference] = [TopLevelRuleReference(initial_scope_name)]

    def process_queue(self) -> None:
        current_queue = self.queue
        self.queue = []
        dependencies = ExternalReferenceCollector()
        for reference in current_queue:
            _collect_references_of_reference(
                reference, self.initial_scope_name, self.repo, dependencies
            )

        for dependency in dependencies.references:
            if isinstance(dependency, TopLevelRuleReference):
                if dependency.scope_name in self.seen_full_scope_requests:
                    continue
                self.seen_full_scope_requests.add(dependency.scope_name)
                self.queue.append(dependency)
            else:
                if dependency.scope_name in self.seen_full_scope_requests:
                    continue
                key = dependency.to_key()
                if key in self.seen_partial_scope_requests:
                    continue
                self.seen_partial_scope_requests.add(key)
                self.queue.append(dependency)


def _scope_name(grammar: Mapping[str, Any]) -> str:
    return str(grammar.get("scopeName", ""))


def _collect_references_of_reference(
    reference: AbsoluteRuleReference,
    base_scope_name: str,
    repo: SyncRegistry,
    result: ExternalReferenceCollector,
) -> None:
    self_grammar = repo.lookup(reference.scope_name)
    if self_grammar is None:
        if reference.scope_name == base_scope_name:
            raise ValueError(f"No grammar provided for <{base_scope_name}>")
        return

    base_grammar = repo.lookup(base_scope_name)
    if base_grammar is None:
        raise ValueError(f"No grammar provided for <{base_scope_name}>")

    if isinstance(reference, TopLevelRuleReference):
        _collect_top_level_rule(base_grammar, self_grammar, result)
    else:
        repository = self_grammar.get("repository")
        if isinstance(repository, Mapping):
            rule = repository.get(reference.rule_name)
            if isinstance(rule, Mapping):
                _collect_rules([rule], base_grammar, self_grammar, repository, result)

    for injection in repo.injections(reference.scope_name) or ():
        result.add(TopLevelRuleReference(injection))


def _collect_top_level_rule(
    base_grammar: RawGrammar,
    self_grammar: RawGrammar,
    result: ExternalReferenceCollector,
) -> None:
    repository = self_grammar.get("repository")
    repo_mapping = repository if isinstance(repository, Mapping) else {}
    patterns = self_grammar.get("patterns")
    if isinstance(patterns, list):
        _collect_rules(patterns, base_grammar, self_grammar, repo_mapping, result)
    injections = self_grammar.get("injections")
    if isinstance(injections, Mapping):
        _collect_rules(list(injections.values()), base_grammar, self_grammar, repo_mapping, result)


def _collect_top_level_repository_rule(
    rule_name: str,
    base_grammar: RawGrammar,
    self_grammar: RawGrammar,
    repository: Mapping[str, Any] | None,
    result: ExternalReferenceCollector,
) -> None:
    if repository is None:
        return
    rule = repository.get(rule_name)
    if isinstance(rule, Mapping):
        _collect_rules([rule], base_grammar, self_grammar, repository, result)


def _collect_rules(
    rules: Sequence[Any],
    base_grammar: RawGrammar,
    self_grammar: RawGrammar,
    repository: Mapping[str, Any] | None,
    result: ExternalReferenceCollector,
) -> None:
    for rule in rules:
        if not isinstance(rule, Mapping):
            continue
        identity = id(rule)
        if identity in result.visited_rule:
            continue
        result.visited_rule.add(identity)

        rule_repository = rule.get("repository")
        if isinstance(rule_repository, Mapping):
            pattern_repository: Mapping[str, Any] | None = {
                **(repository or {}),
                **rule_repository,
            }
        else:
            pattern_repository = repository

        patterns = rule.get("patterns")
        if isinstance(patterns, list):
            _collect_rules(patterns, base_grammar, self_grammar, pattern_repository, result)

        include = rule.get("include")
        if not isinstance(include, str) or not include:
            continue
        reference = parse_include(include)

        if reference.kind == IncludeReferenceKind.Base:
            _collect_top_level_rule(base_grammar, base_grammar, result)
        elif reference.kind == IncludeReferenceKind.Self:
            _collect_top_level_rule(base_grammar, self_grammar, result)
        elif reference.kind == IncludeReferenceKind.RelativeReference:
            _collect_top_level_repository_rule(
                reference.ruleName or "",
                base_grammar,
                self_grammar,
                pattern_repository,
                result,
            )
        else:
            scope_name = reference.scopeName or ""
            if scope_name == _scope_name(self_grammar):
                target_grammar = self_grammar
            elif scope_name == _scope_name(base_grammar):
                target_grammar = base_grammar
            else:
                target_grammar = None

            if target_grammar is not None:
                target_repository = pattern_repository
                if reference.kind == IncludeReferenceKind.TopLevelRepositoryReference:
                    _collect_top_level_repository_rule(
                        reference.ruleName or "",
                        base_grammar,
                        target_grammar,
                        target_repository,
                        result,
                    )
                else:
                    _collect_top_level_rule(base_grammar, target_grammar, result)
            elif reference.kind == IncludeReferenceKind.TopLevelRepositoryReference:
                result.add(TopLevelRepositoryRuleReference(scope_name, reference.ruleName or ""))
            else:
                result.add(TopLevelRuleReference(scope_name))


def collect_includes(grammar: IRawGrammar) -> list[AbsoluteRuleReference]:
    """Collect external references from a grammar's own rules and injections.

    The result is an empty-base traversal useful for inspection. Full dependency
    loading should use :func:`get_grammar_dependencies`, which resolves local
    ``$base`` and scope references against the registry like upstream does.
    """
    registry = SyncRegistry()
    registry.register_grammar(grammar)
    collector = ExternalReferenceCollector()
    _collect_top_level_rule(grammar, grammar, collector)
    return collector.references


def get_grammar_dependencies(registry: SyncRegistry, scope_name: str) -> list[str]:
    """Return all reachable full grammar scopes, including injection scopes."""
    processor = ScopeDependencyProcessor(registry, scope_name)
    dependencies: list[str] = []
    while processor.queue:
        dependencies.extend(reference.scope_name for reference in processor.queue)
        processor.process_queue()
    # ScopeDependencyProcessor de-duplicates requests across queue iterations.
    return list(dict.fromkeys(dependencies))


class SyncRegistry:
    """Synchronous equivalent of upstream ``SyncRegistry``."""

    def __init__(self, onig_lib: IOnigLib = DEFAULT_ONIG_LIB) -> None:
        self.onig_lib = onig_lib
        self._grammars: dict[str, TokenizerLike] = {}
        self._raw_grammars: dict[str, IRawGrammar] = {}
        self._injection_grammars: dict[str, list[str]] = {}
        self._external_grammars: dict[tuple[str, int | None], dict[str, Any]] = {}

    def dispose(self) -> None:
        for grammar in self._grammars.values():
            dispose = getattr(grammar, "dispose", None)
            if callable(dispose):
                dispose()

    def register_grammar(
        self, grammar: IRawGrammar, injection_scope_names: Sequence[str] | None = None
    ) -> None:
        scope_name = grammar["scopeName"]
        self._raw_grammars[scope_name] = grammar
        if injection_scope_names is not None:
            self._injection_grammars[scope_name] = list(injection_scope_names)

    def addGrammar(
        self, grammar: IRawGrammar, injection_scope_names: Sequence[str] | None = None
    ) -> None:  # noqa: N802
        self.register_grammar(grammar, injection_scope_names)

    def lookup(self, scope_name: str) -> IRawGrammar | None:
        return self._raw_grammars.get(scope_name)

    def injections(self, target_scope: str) -> list[str] | None:
        return self._injection_grammars.get(target_scope)

    def get_external_grammar(
        self, scope_name: str, repository: Mapping[str, Any] | None = None
    ) -> IRawGrammar | None:
        """Look up and initialize an included grammar, cached by scope and base.

        Upstream caches per concrete ``Grammar`` instance. The registry-level
        substitute keys by the caller's ``$base`` object as well, preventing one
        root grammar's base repository from leaking into another.
        """
        base = repository.get("$base") if repository is not None else None
        cache_key = (scope_name, id(base) if base is not None else None)
        if cache_key in self._external_grammars:
            return cast(IRawGrammar, self._external_grammars[cache_key])
        grammar = self.lookup(scope_name)
        if grammar is None:
            return None
        initialized = init_grammar(
            cast(dict[str, Any], grammar),
            cast(dict[str, Any], base) if isinstance(base, Mapping) else None,
        )
        self._external_grammars[cache_key] = initialized
        return cast(IRawGrammar, initialized)

    def grammar_for_scope_name(
        self,
        scope_name: str,
        grammar_factory: GrammarFactory | None = None,
    ) -> TokenizerLike | None:
        if scope_name not in self._grammars:
            raw_grammar = self._raw_grammars.get(scope_name)
            if raw_grammar is None:
                return None
            location = raw_grammar.get(LOCATION_KEY)
            factory = grammar_factory or _default_grammar_factory(self, self.onig_lib)
            self._grammars[scope_name] = factory(location, raw_grammar)
        return self._grammars[scope_name]

    def grammarForScopeName(self, scope_name: str) -> TokenizerLike | None:  # noqa: N802
        return self.grammar_for_scope_name(scope_name)


class Registry:
    """Registry options, dependency resolution, and lazy grammar construction."""

    def __init__(
        self,
        options: RegistryOptions,
        *,
        grammar_factory: GrammarFactory | None = None,
    ) -> None:
        self._options = options
        onig_lib = options.get("onig_lib", options.get("onigLib", DEFAULT_ONIG_LIB))
        self._sync_registry = SyncRegistry(onig_lib)
        self._using_default_factory = grammar_factory is None
        self._grammar_factory = grammar_factory or _default_grammar_factory(
            self._sync_registry, onig_lib
        )
        self._ensure_grammar_cache: dict[str, bool] = {}

    @property
    def _grammars(self) -> dict[str, TokenizerLike]:
        """Constructed-grammar cache (upstream stores this on SyncRegistry)."""
        return self._sync_registry._grammars

    def dispose(self) -> None:
        self._sync_registry.dispose()

    def register_grammar(
        self, raw_grammar: IRawGrammar, injections: Sequence[str] | None = None
    ) -> None:
        """Register an already parsed raw grammar and optional injection scopes."""
        self._sync_registry.register_grammar(raw_grammar, injections)

    def _load_grammar_to_cache(self, scope_name: str) -> None:
        if scope_name in self._ensure_grammar_cache:
            return
        # Mark first, matching upstream's promise cache and ensuring one call even
        # for missing grammars. Re-entrant loaders are not part of the sync API.
        self._ensure_grammar_cache[scope_name] = True
        loader = self._options.get("load_grammar", self._options.get("loadGrammar"))
        if loader is None:
            return
        grammar = loader(scope_name)
        if grammar is not None:
            get_injections = self._options.get("get_injections", self._options.get("getInjections"))
            injections = get_injections(scope_name) if get_injections is not None else None
            self._sync_registry.register_grammar(grammar, injections)

    def _load_grammar(self, initial_scope_name: str) -> TokenizerLike | None:
        processor = ScopeDependencyProcessor(self._sync_registry, initial_scope_name)
        while processor.queue:
            requests = processor.queue
            for request in requests:
                self._load_grammar_to_cache(request.scope_name)
            processor.process_queue()
        return self._sync_registry.grammar_for_scope_name(initial_scope_name, self._grammar_factory)

    def load_grammar(self, initial_scope_name: str) -> TokenizerLike | None:
        """Load a grammar and every referenced grammar before constructing it."""
        return self._load_grammar(initial_scope_name)

    def loadGrammar(self, initial_scope_name: str) -> TokenizerLike | None:  # noqa: N802
        """vscode-textmate spelling of :meth:`load_grammar`."""
        return self.load_grammar(initial_scope_name)

    def addGrammar(
        self,
        raw_grammar: IRawGrammar,
        injections: Sequence[str] = (),
        initial_language: int = 0,
        embedded_languages: Mapping[str, int] | None = None,
    ) -> TokenizerLike:
        """Register and construct a grammar, matching upstream's convenience method."""
        self.register_grammar(raw_grammar, injections)
        scope_name = str(raw_grammar["scopeName"])
        grammar = self._sync_registry._grammars.get(scope_name)
        if grammar is None and self._using_default_factory:
            from .tokenize import Grammar

            grammar = Grammar(
                scope_name,
                raw_grammar,
                initial_language=initial_language,
                embedded_languages=embedded_languages,
                grammar_repository=self._sync_registry,
                onig_lib=self._sync_registry.onig_lib,
            )
            self._sync_registry._grammars[scope_name] = grammar
        elif grammar is None:
            grammar = self._sync_registry.grammar_for_scope_name(scope_name, self._grammar_factory)
        if grammar is None:
            raise ValueError(f"No grammar provided for <{raw_grammar['scopeName']}>")
        return grammar
