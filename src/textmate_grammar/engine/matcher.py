"""Port of vscode-textmate's ``src/matcher.ts``.

Scope selectors such as
``text.html.php - (meta.embedded | meta.tag), L:text.html.php meta.tag`` are
parsed into small composable predicate functions evaluated against a scope
path. The semantics are intentionally 1:1 with the TypeScript source; comments
throughout this module reference the corresponding sections of ``matcher.ts``
(and of ``grammar.ts``/``theme.ts`` where matcher.ts delegates the name-matching
logic).

Note on ordering: the only ordering information ``matcher.ts`` itself produces
is the ``L:`` (priority -1) / ``R:`` (priority 1) selector prefix, surfaced as
:attr:`MatcherWithPriority.priority`. Sorting injections by that priority
happens in ``grammar.ts`` (task 3b); specificity ordering of theme rules lives
in ``theme.ts`` and is out of this plan's scope.
"""

from __future__ import annotations

import re
import warnings
from collections.abc import Callable
from typing import Any, Literal, NamedTuple, Protocol, TypeGuard, TypeVar

T = TypeVar("T")

#: matcher.ts: ``export interface Matcher<T> { (matcherInput: T): boolean; }``
Matcher = Callable[[T], bool]

#: matcher.ts ``createMatchers``: ``matchesName: (names, matcherInput) => boolean``
MatchesName = Callable[[list[str], T], bool]

#: The parsed ``L:``/``R:`` selector prefix. ``0`` is the default; ``-1`` for
#: ``L:`` and ``1`` for ``R:`` (same values as grammar.ts ``Injection.priority``).
Priority = Literal[-1, 0, 1]

# matcher.ts newTokenizer: JS ``\w`` is ASCII-only, hence ``re.ASCII``. The
# ``[LR]:`` alternative must win over identifiers so a priority run lexes as one
# token; the identifier alternative may not start with ``-`` (exclusion marker);
# the last alternative matches the structural tokens ``, | - ( )``.
_TOKEN_PATTERN = re.compile(r"(?:[LR]:|[\w\.:][\w\.:\-]*|[,|\-()])", re.ASCII)

# matcher.ts isIdentifier: ``!!token && !!token.match(/[\w\.:]+/)`` — ``match``
# is unanchored (=> re.search) and ``\w`` is ASCII (=> re.ASCII).
_IDENTIFIER_PATTERN = re.compile(r"[\w\.:]+", re.ASCII)


class MatcherWithPriority(NamedTuple):
    """matcher.ts ``interface MatcherWithPriority<T> { matcher; priority }``.

    ``matcher`` is a predicate over whatever input the caller evaluates against
    (grammar.ts uses the flat scope-name list of the current token); ``priority``
    is the parsed ``L:``/``R:`` prefix.
    """

    matcher: Callable[[Any], bool]
    priority: Priority


class ScopePath(Protocol):
    """The parent-linked scope chain matchers are evaluated against.

    A scope path is a linked chain of scope names: the node a caller holds is
    the *innermost* scope, ``.name`` its scope name and ``.parent`` points
    towards the shallower scope; the root scope has ``parent = None``.
    Materialized root-first this equals ``theme.ts``' ``ScopeStack.getSegments()``
    (i.e. ``grammar.ts``' ``getScopeNames()``). Minimal on purpose; the state
    stack built in task 3a satisfies this protocol structurally.
    """

    name: str
    parent: ScopePath | None


def create_matchers(selector: str, matches_name: MatchesName[T]) -> list[MatcherWithPriority]:
    """Port of matcher.ts ``createMatchers``.

    Parses ``selector`` into its comma-separated branches and returns one
    ``MatcherWithPriority`` per branch. Callers treat the branch matchers as
    alternatives (matcher.ts consumers use ``matchers.some(...)``). Only
    ``priority`` carries ordering information; the matchers are pure predicates.
    """
    results: list[MatcherWithPriority] = []
    next_token = _new_tokenizer(selector)
    token: str | None = next_token()

    # matcher.ts declares parseOperand/parseConjunction/parseInnerExpression as
    # (hoisted) closures over `token`; Python needs them defined before the loop.
    def parse_operand() -> Matcher[T] | None:
        nonlocal token
        if token == "-":
            # matcher.ts parseOperand '-' branch: exclusion of the negated operand.
            token = next_token()
            expression_to_negate = parse_operand()
            return _negate(expression_to_negate)
        if token == "(":
            # matcher.ts parseOperand '(' branch: parenthesized group.
            token = next_token()
            expression_in_parents = parse_inner_expression()
            if token == ")":
                token = next_token()
            return expression_in_parents
        if _is_identifier(token):
            # matcher.ts: consecutive identifiers are conjuncts — `bar foo`
            # requires both to occur in order in the name list.
            identifiers: list[str] = []
            while _is_identifier(token):
                identifiers.append(token)
                token = next_token()
            return lambda matcher_input: matches_name(identifiers, matcher_input)
        return None  # `-`, `(`, `|`, `,`, `)` or end of selector terminate parsing

    def parse_conjunction() -> Matcher[T]:
        matchers: list[Matcher[T]] = []
        matcher = parse_operand()
        while matcher is not None:
            matchers.append(matcher)
            matcher = parse_operand()
        # matcher.ts: matchers.every(...) — vacuously true for an empty
        # conjunction (e.g. a priority prefix with no selector body).
        return lambda matcher_input: all(m(matcher_input) for m in matchers)

    def parse_inner_expression() -> Matcher[T]:
        nonlocal token
        matchers: list[Matcher[T]] = []
        matcher = parse_conjunction()
        while matcher is not None:
            matchers.append(matcher)
            if token == "|" or token == ",":
                # matcher.ts: `|` separates alternatives; nested commas count as
                # alternation separators inside a group too.
                while token == "|" or token == ",":
                    token = next_token()
            else:
                break
            matcher = parse_conjunction()
        # matcher.ts: matchers.some(...) — vacuously false for an empty
        # alternation.
        return lambda matcher_input: any(m(matcher_input) for m in matchers)

    while token is not None:
        priority: Priority = 0
        if len(token) == 2 and token[1] == ":":
            # matcher.ts: an ``R:``-prefixed branch gets priority 1, ``L:`` gets
            # -1; an unknown two-character prefix is reported and skipped while
            # its body still parses.
            if token[0] == "R":
                priority = 1
            elif token[0] == "L":
                priority = -1
            else:
                # matcher.ts prints to the console here; a warning keeps the
                # signal visible without aborting tokenization.
                warnings.warn(
                    f"Unknown priority {token} in scope selector", stacklevel=2
                )
            token = next_token()
        matcher = parse_conjunction()
        results.append(MatcherWithPriority(matcher, priority))
        if token != ",":
            break
        token = next_token()

    return results


def _negate(expression: Matcher[T] | None) -> Matcher[T]:
    """matcher.ts: ``matcherInput => !!e && !e(matcherInput)``."""

    def negated(matcher_input: T) -> bool:
        return expression is not None and not expression(matcher_input)

    return negated


def scopes_are_matching(scope_name: str, selector_scope: str) -> bool:
    """Port of grammar.ts ``scopesAreMatching`` (matcher.ts delegates to it).

    True when the stack scope ``scope_name`` equals ``selector_scope`` or
    extends it at a ``.`` boundary: ``text.html`` matches ``text.html.php``
    but not ``text.htmlx``.
    """
    if not scope_name:
        return False
    if scope_name == selector_scope:
        return True
    length = len(selector_scope)
    return (
        len(scope_name) > length
        and scope_name[:length] == selector_scope
        and scope_name[length] == "."
    )


def match_scope_identifiers(identifiers: list[str], scopes: list[str]) -> bool:
    """Port of grammar.ts ``nameMatcher``, the ``matches_name`` matcher.ts is fed.

    Every identifier must occur as a subsequence of ``scopes``, scanning
    strictly left to right: identifier order matters and each identifier
    consumes its position (repeated identifiers need repeated scopes). A stack
    scope matches an identifier via :func:`scopes_are_matching`.
    """
    if len(scopes) < len(identifiers):
        return False
    last_index = 0
    for identifier in identifiers:
        for index in range(last_index, len(scopes)):
            if scopes_are_matching(scopes[index], identifier):
                last_index = index + 1
                break
        else:
            return False
    return True


def match_scope_names(identifiers: list[str], scopes_path: ScopePath | None) -> bool:
    """Name matcher over a :class:`ScopePath` parent chain.

    Equivalent to grammar.ts ``nameMatcher`` fed ``getScopeNames()``: the chain
    is collected from the innermost node through the parents and then reversed
    to root-first order (theme.ts ``ScopeStack.getSegments()``).
    """
    names: list[str] = []
    item = scopes_path
    while item is not None:
        names.append(item.name)
        item = item.parent
    names.reverse()
    return match_scope_identifiers(identifiers, names)


def _is_identifier(token: str | None) -> TypeGuard[str]:
    """matcher.ts ``isIdentifier``: non-empty token with word/``.``/``:`` chars."""
    return token is not None and _IDENTIFIER_PATTERN.search(token) is not None


def _new_tokenizer(selector: str) -> Callable[[], str | None]:
    """Port of matcher.ts ``newTokenizer`` (a successive ``regex.exec`` loop)."""
    tokens = _TOKEN_PATTERN.findall(selector)
    index = 0

    def next_token() -> str | None:
        nonlocal index
        if index < len(tokens):
            token = tokens[index]
            index += 1
            return token
        return None

    return next_token
