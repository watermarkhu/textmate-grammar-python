"""Tests for the state and scope primitives ported from grammar.ts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from textmate_grammar.engine.matcher import match_scope_names
from textmate_grammar.engine.rules import RuleRegistry
from textmate_grammar.engine.tokenize import (
    ScopeListElement,
    StateStack,
    get_scope_name,
    get_scope_names,
)


def test_state_stack_push_pop_and_parent_chain() -> None:
    grammar = RuleRegistry()
    root = StateStack(grammar, "source.python", 1)
    function = root.push(grammar, "meta.function", 2)
    string = function.push(grammar, "string.quoted", 3)

    assert root.depth == 1
    assert function.depth == 2
    assert string.depth == 3
    assert string.parent is function
    assert string.pop() is function
    assert function.pop() is root
    assert root.pop() is None
    assert string.rule_id == 3
    assert string.ruleId == 3
    assert string.grammar is grammar


def test_state_stack_is_immutable_and_preserves_upstream_identity_rules() -> None:
    grammar = RuleRegistry()
    root = StateStack(grammar, "source.python", 1)

    assert root.clone() is root
    assert root.push(grammar, "source.python", 1) is not root
    assert root.equals(StateStack(grammar, "source.python", 1))
    assert not root.equals(StateStack(RuleRegistry(), "source.python", 1))
    with pytest.raises(FrozenInstanceError):
        root.scope_name = "source.other"  # type: ignore[misc]


def test_scope_list_merge_reuses_identical_path_and_splits_different_path() -> None:
    first = ScopeListElement.from_scope_names(["source.python", "meta.function"])
    identical = ScopeListElement.from_scope_names(["source.python", "meta.function"])
    different = ScopeListElement.from_scope_names(["source.python", "string"])

    assert first is not None
    assert identical is not None
    assert different is not None
    assert ScopeListElement.merge(first, identical) is first
    assert ScopeListElement.merge(first, different) is None
    assert ScopeListElement.merge(first, first) is first


def test_scope_names_are_enumerated_root_first() -> None:
    scopes = ScopeListElement.from_scope_names(
        ["source.python", "meta.function", "string.quoted"]
    )

    assert get_scope_names(scopes) == ["source.python", "meta.function", "string.quoted"]
    assert get_scope_name(scopes) == "source.python meta.function string.quoted"
    assert get_scope_names(None) == []
    assert get_scope_name(None) == ""


def test_state_stack_frames_implement_matchers_scope_path_protocol() -> None:
    grammar = RuleRegistry()
    scopes = StateStack(grammar, "source.python", 1)
    scopes = scopes.push(grammar, "meta.function.parameters", 2)
    scopes = scopes.push(grammar, "string.quoted", 3)

    assert match_scope_names(["source.python", "string"], scopes)
    assert not match_scope_names(["string", "source.python"], scopes)
    assert get_scope_names(scopes) == [
        "source.python",
        "meta.function.parameters",
        "string.quoted",
    ]
