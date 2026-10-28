"""Tests for vscode-textmate state/scope structures and the grammar loop."""

from __future__ import annotations

from textmate_grammar.engine.matcher import match_scope_names
from textmate_grammar.engine.tokenize import (
    AttributedScopeStack,
    ScopeStack,
    StateStackImpl,
    create_grammar,
    get_scope_name,
    get_scope_names,
)


def _root_state() -> StateStackImpl:
    scopes = AttributedScopeStack.create_root("source.python")
    return StateStackImpl(None, 1, -1, -1, False, None, scopes, scopes)


def test_scope_stack_root_first_and_matcher_compatible() -> None:
    scopes = ScopeStack(None, "source.python").push("meta.function").push("string.quoted")
    assert get_scope_names(scopes) == ["source.python", "meta.function", "string.quoted"]
    assert get_scope_name(scopes) == "source.python meta.function string.quoted"
    assert match_scope_names(["source.python", "string"], scopes)
    assert not match_scope_names(["string", "source.python"], scopes)
    assert ScopeStack(None, "one").get_extension_if_defined(None) == ["one"]


def test_attributed_scope_stack_push_and_equality() -> None:
    root = AttributedScopeStack.create_root("source.python")
    child = root.push_attributed("meta.function string.quoted", None)  # type: ignore[arg-type]
    equivalent = AttributedScopeStack.create_root("source.python").push_attributed(
        "meta.function string.quoted", None  # type: ignore[arg-type]
    )
    assert child.get_scope_names() == ["source.python", "meta.function", "string.quoted"]
    assert child.parent is not None and child.parent.parent is root
    assert child.equals(equivalent)
    assert child.get_extension_if_defined(root) == [
        {"encodedTokenAttributes": 0, "scopeNames": ["meta.function"]},
        {"encodedTokenAttributes": 0, "scopeNames": ["string.quoted"]},
    ]


def test_state_stack_structural_and_scope_equality_and_line_positions() -> None:
    root = _root_state()
    frame = root.push(4, 3, 1, True, "end", root.contentNameScopesList, root.contentNameScopesList)
    same = _root_state().push(4, 99, 77, True, "end", root.contentNameScopesList, root.contentNameScopesList)
    assert frame.depth == 2
    assert frame.pop() is root
    assert frame.clone() is frame
    assert frame.structural_equals(same)
    assert frame.equals(same)
    assert frame.get_enter_pos() == 3
    assert frame.get_anchor_pos() == 1
    restored = StateStackImpl.push_frame(root, frame.to_state_stack_frame())
    assert restored.rule_id == frame.rule_id
    assert restored.nameScopesList is not None
    assert restored.nameScopesList.get_scope_names() == frame.nameScopesList.get_scope_names()
    frame.reset()
    assert frame.get_enter_pos() == -1
    assert frame.get_anchor_pos() == -1
    assert root.get_enter_pos() == -1
    assert root.safe_pop() is root


def test_tokenize_match_and_multiline_begin_end() -> None:
    raw = {
        "scopeName": "source.test",
        "patterns": [
            {"match": "\\bword\\b", "name": "keyword.word"},
            {
                "begin": '"',
                "end": '"',
                "name": "string.quoted",
                "patterns": [{"match": "\\\\.", "name": "constant.character.escape"}],
            },
        ],
    }
    grammar = create_grammar("source.test", raw)
    first = grammar.tokenize_line('word "open')
    assert [(t.startIndex, t.endIndex, t.scopes) for t in first.tokens] == [
        (0, 4, ["source.test", "keyword.word"]),
        (4, 5, ["source.test"]),
        (5, 6, ["source.test", "string.quoted"]),
        (6, 11, ["source.test", "string.quoted"]),
    ]
    second = grammar.tokenize_line('close"', first.ruleStack)
    assert [token.scopes for token in second.tokens] == [
        ["source.test", "string.quoted"],
        ["source.test", "string.quoted"],
    ]
    assert second.ruleStack.depth == 1


def test_tokenize_line_adds_and_hides_virtual_newline_for_plain_line() -> None:
    grammar = create_grammar(
        "source.test",
        {"scopeName": "source.test", "patterns": [{"match": "x", "name": "constant.x"}]},
    )
    result = grammar.tokenize_line("x")
    assert [(token.startIndex, token.endIndex, token.scopes) for token in result.tokens] == [
        (0, 1, ["source.test", "constant.x"])
    ]
