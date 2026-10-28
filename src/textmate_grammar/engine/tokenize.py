"""State and scope-stack primitives for the vscode-textmate tokenizer.

This module is the state/scope half of ``grammar.ts``.  The line-tokenization
loop is intentionally owned by the following port task and is not implemented
here.  The pinned v9.3.2 source represents these concepts as ``StateStackImpl``
and ``AttributedScopeStack``; this module keeps the smaller scope-name-only
shape required by the engine's matcher and upcoming tokenizer loop.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

__all__ = (
    "ScopeListElement",
    "StateStack",
    "getScopeName",
    "getScopeNames",
    "get_scope_name",
    "get_scope_names",
)


@dataclass(frozen=True, slots=True, eq=False)
class ScopeListElement:
    """One immutable scope name in a parent-linked scope path.

    ``merge`` is the token-output coalescing check: if two independently built
    paths contain the same root-first names, it returns the left path so callers
    can keep sharing its identity; otherwise it returns ``None`` and the output
    spans must remain separate.  Scope-list construction itself always creates
    a node for each pushed name, as upstream ``ScopeStack.push`` does.
    """

    scope_name: str
    parent: ScopeListElement | None = None

    @property
    def name(self) -> str:
        """Alias for the ``ScopePath`` protocol consumed by the matcher."""
        return self.scope_name

    @property
    def scopeName(self) -> str:  # noqa: N802 - mirrors the upstream field
        """Upstream-spelled alias for ``scope_name``."""
        return self.scope_name

    def push(self, scope_name: str) -> ScopeListElement:
        """Return a new path node, retaining this path as its parent."""
        return ScopeListElement(scope_name, self)

    @classmethod
    def from_scope_names(cls, scope_names: Iterable[str]) -> ScopeListElement | None:
        """Build a path from root-first names, returning its innermost node."""
        result: ScopeListElement | None = None
        for scope_name in scope_names:
            result = cls(scope_name, result)
        return result

    @staticmethod
    def merge(
        left: ScopeListElement | None, right: ScopeListElement | None
    ) -> ScopeListElement | None:
        """Return ``left`` when both paths have identical scope names.

        This preserves the existing path object for equal-scope token runs,
        regardless of whether the two paths were independently allocated. A
        differing path returns ``None``, signalling that output tokens split.
        """
        if left is right:
            return left
        if get_scope_names(left) != get_scope_names(right):
            return None
        return left

    def get_scope_names(self) -> list[str]:
        """Return this path's names in root-first order."""
        return get_scope_names(self)

    def __str__(self) -> str:
        return " ".join(get_scope_names(self))


@dataclass(frozen=True, slots=True, eq=False)
class StateStack:
    """Immutable parent-linked tokenizer state frame.

    A frame records the grammar/rule context and its associated scope name.
    ``name`` and ``parent`` intentionally satisfy ``matcher.ScopePath`` so the
    frame chain can be passed directly to :func:`matcher.match_scope_names`.
    Pushes always allocate a new state frame (matching upstream
    ``StateStackImpl.push``); :meth:`clone` returns the same immutable object.
    """

    grammar: Any
    scope_name: str
    rule_id: int
    parent: StateStack | None = None
    depth: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "depth", self.parent.depth + 1 if self.parent is not None else 1)

    @property
    def name(self) -> str:
        """Alias for the ``ScopePath`` protocol consumed by the matcher."""
        return self.scope_name

    @property
    def ruleId(self) -> int:  # noqa: N802 - mirrors the upstream field
        """Upstream-spelled alias for ``rule_id``."""
        return self.rule_id

    def push(self, grammar: Any, scope_name: str, rule_id: int) -> StateStack:
        """Create a new frame with the supplied grammar, scope and rule id."""
        return StateStack(grammar, scope_name, rule_id, self)

    def pop(self) -> StateStack | None:
        """Return the parent frame; popping the root returns ``None``."""
        return self.parent

    def clone(self) -> StateStack:
        """Return this immutable state object unchanged."""
        return self

    def equals(self, other: StateStack | None) -> bool:
        """Compare frame chains structurally, using grammar object identity."""
        left: StateStack | None = self
        right = other
        while left is not right:
            if left is None or right is None:
                return left is right
            if (
                left.depth != right.depth
                or left.grammar is not right.grammar
                or left.rule_id != right.rule_id
                or left.scope_name != right.scope_name
            ):
                return False
            left = left.parent
            right = right.parent
        return True

    def get_rule(self) -> Any:
        """Resolve this frame's rule through its grammar context."""
        return self.grammar.get_rule(self.rule_id)

    def get_scope_names(self) -> list[str]:
        """Return the state frame scopes in root-first order."""
        return get_scope_names(self)

    def __str__(self) -> str:
        return " ".join(get_scope_names(self))


def get_scope_names(chain: Any | None) -> list[str]:
    """Return a linked chain's scope names in root-first order.

    Both :class:`StateStack` and :class:`ScopeListElement` implement the
    ``name``/``parent`` protocol. ``None`` corresponds to an empty path.
    """
    result: list[str] = []
    item = chain
    while item is not None:
        result.append(item.name)
        item = item.parent
    result.reverse()
    return result


def get_scope_name(chain: Any | None) -> str:
    """Return a scope chain as the space-separated TextMate scope string."""
    return " ".join(get_scope_names(chain))


# Keep the grammar.ts helper spellings available at the port boundary; the
# snake_case forms above are the preferred names for Python callers.
getScopeName = get_scope_name  # noqa: N816
getScopeNames = get_scope_names  # noqa: N816
