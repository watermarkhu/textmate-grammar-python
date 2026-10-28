"""Tests for Registry loading and dependency traversal (vscode-textmate v9.3.2)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from textmate_grammar.engine.raw_grammar import parse_raw_grammar
from textmate_grammar.engine.registry import (
    Registry,
    SyncRegistry,
    TopLevelRuleReference,
    collect_includes,
    get_grammar_dependencies,
)
from textmate_grammar.engine.rules import init_grammar


def parsed(scope_name: str, patterns: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    source = json.dumps({"scopeName": scope_name, "patterns": patterns, **extra})
    return parse_raw_grammar(source, "fixture.json")


GRAMMAR_A = parsed("source.a", [{"include": "source.b"}])
GRAMMAR_B = parsed(
    "source.b",
    [{"include": "source.a"}],
    repository={"part": {"include": "source.a"}},
    injections={"L:source.a": {"include": "source.a#part"}},
)


class DummyGrammar:
    def __init__(self, scope_name: str) -> None:
        self.scope_name = scope_name
        self.disposed = False

    def dispose(self) -> None:
        self.disposed = True


def test_dependency_graph_includes_cross_scope_injections_and_cycles() -> None:
    registry = SyncRegistry()
    registry.register_grammar(GRAMMAR_A, ["source.b"])
    registry.register_grammar(GRAMMAR_B)

    # A -> B by include and injection; B -> A and B#part -> A are cycles.
    assert get_grammar_dependencies(registry, "source.a") == ["source.a", "source.b"]
    assert collect_includes(GRAMMAR_A) == [TopLevelRuleReference("source.b")]
    assert [reference.to_key() for reference in collect_includes(GRAMMAR_B)] == [
        "source.a",
        "source.a#part",
    ]


def test_registry_loads_and_caches_dependency_grammars_once() -> None:
    calls: list[str] = []
    factories: list[tuple[object, str]] = []
    sources = {
        "source.a": json.dumps(GRAMMAR_A),
        "source.b": json.dumps(GRAMMAR_B),
    }

    def load_grammar(scope_name: str) -> dict[str, Any] | None:
        calls.append(scope_name)
        source = sources.get(scope_name)
        return parse_raw_grammar(source, "fixture.json") if source is not None else None

    def factory(location: object, grammar: dict[str, Any]) -> DummyGrammar:
        factories.append((location, grammar["scopeName"]))
        return DummyGrammar(grammar["scopeName"])

    registry = Registry(
        {
            "load_grammar": load_grammar,
            "get_injections": lambda scope: ["source.b"] if scope == "source.a" else [],
        },
        grammar_factory=factory,
    )

    grammar = registry.load_grammar("source.a")
    assert isinstance(grammar, DummyGrammar)
    assert grammar.scope_name == "source.a"
    assert calls.count("source.a") == 1
    assert calls.count("source.b") == 1
    assert set(calls) == {"source.a", "source.b"}
    assert factories == [(None, "source.a")]
    assert registry._grammars["source.a"] is grammar

    # A second request reuses the constructed grammar and loader cache.
    assert registry.load_grammar("source.a") is grammar
    assert calls.count("source.a") == calls.count("source.b") == 1


def test_external_grammar_lookup_initializes_and_caches_with_base_repository() -> None:
    registry = SyncRegistry()
    registry.register_grammar(GRAMMAR_A)
    registry.register_grammar(GRAMMAR_B)
    base = init_grammar(GRAMMAR_A)
    caller_repository = {"$base": base["repository"]["$base"]}

    included = registry.get_external_grammar("source.b", caller_repository)
    assert included is not None
    assert included["repository"]["$self"]["name"] == "source.b"
    assert included["repository"]["$base"] is caller_repository["$base"]
    assert registry.get_external_grammar("source.b", caller_repository) is included

    other_base = init_grammar(GRAMMAR_A)["repository"]["$self"]
    other = registry.get_external_grammar("source.b", {"$base": other_base})
    assert other is not included
    assert other is not None
    assert other["repository"]["$base"] is other_base


def test_default_factory_is_the_explicit_3b_seam() -> None:
    registry = Registry({"load_grammar": lambda _: GRAMMAR_A})
    with pytest.raises(NotImplementedError, match="Grammar construction is not landed"):
        registry.load_grammar("source.a")


def test_dispose_releases_cached_tokenizers() -> None:
    grammar = DummyGrammar("source.a")
    registry = SyncRegistry()
    registry.register_grammar(GRAMMAR_A)
    registry._grammars["source.a"] = grammar

    registry.dispose()

    assert grammar.disposed
