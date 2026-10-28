"""Unit tests for the port of vscode-textmate's ``src/matcher.ts``.

The first test matrix is a 1:1 port of the inline cases in vscode-textmate's
``src/tests/matcher.test.ts``; everything after it exercises the pieces the
TypeScript test spread doesn't cover: ``L:``/``R:`` priority prefixes,
``.``-boundary name matching, deep scope chains and the vacuous-truth edge
semantics that fall out of ``matchers.every/some`` on empty lists.
"""

from __future__ import annotations

import pytest

from textmate_grammar.engine.matcher import (
    MatcherWithPriority,
    ScopePath,
    create_matchers,
    match_scope_identifiers,
    match_scope_names,
    scopes_are_matching,
)

# ---------------------------------------------------------------------------
# Inline test cases ported from vscode-textmate src/tests/matcher.test.ts.
# ---------------------------------------------------------------------------

# fmt: off
MATCHER_TEST_CASES = [
    # (expression, input, expected result of `matchers.some(m => m.matcher(input))`)
    ("foo", ["foo"], True),
    ("foo", ["bar"], False),
    ("- foo", ["foo"], False),
    ("- foo", ["bar"], True),
    ("- - foo", ["bar"], False),
    ("bar foo", ["foo"], False),
    ("bar foo", ["bar"], False),
    ("bar foo", ["bar", "foo"], True),
    ("bar - foo", ["bar"], True),
    ("bar - foo", ["foo", "bar"], False),
    ("bar - foo", ["foo"], False),
    ("bar, foo", ["foo"], True),
    ("bar, foo", ["bar"], True),
    ("bar, foo", ["bar", "foo"], True),
    ("bar, -foo", ["bar", "foo"], True),
    ("bar, -foo", ["yo"], True),
    ("bar, -foo", ["foo"], False),
    ("(foo)", ["foo"], True),
    ("(foo - bar)", ["foo"], True),
    ("(foo - bar)", ["foo", "bar"], False),
    ("foo bar - (yo man)", ["foo", "bar"], True),
    ("foo bar - (yo man)", ["foo", "bar", "yo"], True),
    ("foo bar - (yo man)", ["foo", "bar", "yo", "man"], False),
    ("foo bar - (yo | man)", ["foo", "bar", "yo", "man"], False),
    ("foo bar - (yo | man)", ["foo", "bar", "yo"], False),
    ("R:text.html - (comment.block, text.html source)", ["text.html", "bar", "source"], False),
    ("text.html.php - (meta.embedded | meta.tag), L:text.html.php meta.tag, L:source.js.embedded.html",
     ["text.html.php", "bar", "source.js"], True),
]
# fmt: on


def flat_name_matcher(identifiers: list[str], stack_elements: list[str]) -> bool:
    """Port of the nameMatcher in vscode-textmate's matcher.test.ts: equality."""
    last_index = 0
    for identifier in identifiers:
        for index in range(last_index, len(stack_elements)):
            if stack_elements[index] == identifier:
                last_index = index + 1
                break
        else:
            return False
    return True


@pytest.mark.parametrize(("expression", "scopes_input", "expected"), MATCHER_TEST_CASES)
def test_matcher_ts_inline_cases(expression: str, scopes_input: list[str], expected: bool):
    matchers = create_matchers(expression, flat_name_matcher)
    result = any(matcher.matcher(scopes_input) for matcher in matchers)
    assert result == expected


# ---------------------------------------------------------------------------
# Priority prefixes (L: / R:).
# ---------------------------------------------------------------------------


def test_priority_per_branch():
    matchers = create_matchers("R:alpha, L:beta, gamma", flat_name_matcher)
    priorities = [matcher.priority for matcher in matchers]
    assert priorities == [1, -1, 0]


def test_priority_does_not_change_matching():
    matchers = create_matchers("R:foo", flat_name_matcher)
    assert matchers[0].matcher(["foo"]) is True
    assert matchers[0].matcher(["bar"]) is False

    matchers = create_matchers("L:foo - bar", flat_name_matcher)
    assert matchers[0].matcher(["foo"]) is True
    assert matchers[0].matcher(["foo", "bar"]) is False


def test_priority_prefix_is_tokended_as_one_token():
    # `L:`/`R:` must not split into identifiers: the branch becomes exactly one matcher.
    matchers = create_matchers("L:source.python", flat_name_matcher)
    assert isinstance(matchers, list)
    assert [m.priority for m in matchers] == [-1]  # one branch, not `L` + `source.python`
    assert matchers[0].matcher(["source.python"]) is True


def test_unknown_priority_warns_and_still_parses_body(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.warns(UserWarning, match="Unknown priority"):
        matchers = create_matchers("Z: foo", flat_name_matcher)
    assert [m.priority for m in matchers] == [0]
    assert matchers[0].matcher(["foo"]) is True
    assert matchers[0].matcher(["bar"]) is False
    assert capsys.readouterr().out == ""  # nothing is printed to stdout, unlike TS console


def test_implicit_priority_default_is_zero():
    matchers = create_matchers("foo bar - (yo man), baz", flat_name_matcher)
    assert [m.priority for m in matchers] == [0, 0]


# ---------------------------------------------------------------------------
# Vacuous-truth semantics ported from Array.prototype.every/some on [].
# ---------------------------------------------------------------------------


def test_empty_conjunction_is_vacuously_true():
    # matcher.ts: `matchers.every(...)` on an empty conjunction is true, so a
    # priority prefix without a selector body matches everything.
    matchers = create_matchers("R:", flat_name_matcher)
    assert [m.priority for m in matchers] == [1]
    assert matchers[0].matcher([]) is True
    assert matchers[0].matcher(["anything"]) is True


def test_parenthesized_empty_conjunction_is_vacuously_true():
    # matcher.ts: parseConjunction always yields a matcher (`every` on [] is
    # true), so `()` — and any group whose body parses to nothing — is an
    # always-true branch. An empty *alternation* (some on []) is unreachable.
    matchers = create_matchers("()", flat_name_matcher)
    assert matchers[0].matcher(["foo"]) is True


def test_empty_selector_yields_no_matchers():
    assert create_matchers("", flat_name_matcher) == []
    # Only separators/unlexable junk: nothing was ever parsed.
    assert create_matchers(";;;", flat_name_matcher) == []


# ---------------------------------------------------------------------------
# Name matching over flat scope lists (grammar.ts nameMatcher semantics).
# ---------------------------------------------------------------------------


def test_match_scope_identifiers_requires_subsequence_order():
    assert match_scope_identifiers(["bar", "foo"], ["foo", "bar"]) is False
    assert match_scope_identifiers(["foo", "bar"], ["foo", "bar"]) is True
    # Scanning resumes strictly *after* a consumed position, so each identifier
    # needs its own scope occurrence.
    assert match_scope_identifiers(["a", "a"], ["a"]) is False
    assert match_scope_identifiers(["a", "a"], ["a", "a"]) is True


def test_match_scope_identifiers_allows_gaps():
    assert match_scope_identifiers(["a", "c"], ["a", "b", "c"]) is True


def test_match_scope_identifiers_uses_dot_boundaries():
    assert match_scope_identifiers(["meta.tag"], ["meta", "meta.tag"]) is True
    assert match_scope_identifiers(["meta.tag"], ["meta.tag.block"]) is True
    assert match_scope_identifiers(["meta.tag"], ["meta.tagx"]) is False
    assert match_scope_identifiers(["tag"], ["metal"]) is False
    assert match_scope_identifiers(["meta"], ["meta"]) is True


def test_match_scope_identifiers_length_guard():
    assert match_scope_identifiers(["a", "b"], ["a"]) is False
    assert match_scope_identifiers([], ["a"]) is True  # every([]) vacuously true


# ---------------------------------------------------------------------------
# Scope paths: parent-linked chains (protocol consumed from task 3a).
# ---------------------------------------------------------------------------


class ScopeStackElement:
    """Minimal ScopePath stand-in shaped like 3a's state-stack scope list."""

    def __init__(self, name: str, parent: "ScopeStackElement | None" = None) -> None:
        self.name = name
        self.parent = parent


def _push_path(names: list[str]) -> ScopePath | None:
    """Build a chain where consecutive `push`es make the first name the root."""
    path: ScopeStackElement | None = None
    for name in names:
        path = ScopeStackElement(name, path)
    return path


def test_match_scope_names_walks_the_parent_chain():
    # Innermost first when pushing; matched root-first like getScopeNames().
    path = _push_path(["source.python", "meta.function.parameters", "string"])
    assert match_scope_names(["source.python", "string"], path) is True
    assert match_scope_names(["string", "source.python"], path) is False
    assert match_scope_names(["meta.function.parameters"], path) is True


def test_match_scope_names_root_only():
    assert match_scope_names(["source.python"], _push_path(["source.python"])) is True
    assert match_scope_names(["source.python"], None) is False


DEEP_NAMES = ["a", "b", "c", "d", "e", "f", "g", "h"]


def test_match_scope_names_deep_stack():
    path = _push_path(DEEP_NAMES)
    assert match_scope_names(["a", "d", "h"], path) is True
    assert match_scope_names(["h"], path) is True
    assert match_scope_names(["b", "a"], path) is False
    assert match_scope_names(list(reversed(DEEP_NAMES)), path) is False


def test_deep_stack_through_create_matchers():
    path = _push_path(DEEP_NAMES)

    matchers = create_matchers(
        "a d g h", lambda ids, scopes_path: match_scope_names(ids, scopes_path)
    )
    assert matchers[0].priority == 0
    assert matchers[0].matcher(path) is True

    matchers = create_matchers("R:a - b", lambda ids, scopes_path: match_scope_names(ids, scopes_path))
    assert matchers[0].priority == 1
    assert matchers[0].matcher(path) is False  # b occurs in the chain

    other = _push_path(["a", "d"])
    assert matchers[0].matcher(other) is True  # a without b

    matchers = create_matchers("- b c", lambda ids, scopes_path: match_scope_names(ids, scopes_path))
    # A leading '-' negates the *whole* following identifier run: not(b AND c).
    assert matchers[0].matcher(path) is False  # b and c both present
    assert matchers[0].matcher(_push_path(["c"])) is True  # no b
    assert matchers[0].matcher(_push_path(["a"])) is True  # neither b nor c

    # An identifier run before '-' is a plain conjunct; only the neighbors of
    # '-' are negated (matcher.test.ts `bar - foo`).
    matchers = create_matchers(
        "bar - foo, yo", lambda ids, scopes_path: match_scope_names(ids, scopes_path)
    )
    [bar_not_foo, yo] = matchers
    assert bar_not_foo.matcher(_push_path(["bar"])) is True
    assert bar_not_foo.matcher(_push_path(["foo", "bar"])) is False
    assert yo.matcher(_push_path(["yo"])) is True
    assert yo.matcher(_push_path(["bar"])) is False


# ---------------------------------------------------------------------------
# scopes_are_matching boundary cases.
# ---------------------------------------------------------------------------


def test_scopes_are_matching_boundaries():
    assert scopes_are_matching("text.html", "text.html") is True
    assert scopes_are_matching("text.html.php", "text.html") is True
    assert scopes_are_matching("text.htmlx", "text.html") is False
    assert scopes_are_matching("text.html.php", "html") is False
    assert scopes_are_matching("text.html", "text.html.php") is False
    assert scopes_are_matching("", "text") is False
