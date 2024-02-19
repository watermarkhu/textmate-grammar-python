from __future__ import annotations

from abc import ABC
from collections import defaultdict
from itertools import groupby
from pprint import pprint
from typing import TYPE_CHECKING, Generator

from .handler import POS, ContentHandler, Match, Pattern
from .logger import LOGGER

if TYPE_CHECKING:
    from .parser import GrammarParser


TOKEN_DICT = dict[POS, list[str]]


class Capture:
    """A captured matching group.

    After mathing, any pattern can have a number of capture groups for which subsequent parsers can be defined.
    The Capture object stores this subsequent parse to be dispatched at a later moment.
    """

    def __init__(
        self,
        handler: ContentHandler,
        pattern: Pattern,
        matching: Match,
        parsers: dict[int, GrammarParser],
        starting: tuple[int, int],
        boundary: tuple[int, int],
        key: str = "",
        **kwargs,
    ) -> None:
        self.handler = handler
        self.pattern = pattern
        self.matching = matching
        self.parsers = parsers
        self.starting = starting
        self.boundary = boundary
        self.key = key
        self.kwargs = kwargs

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Capture):
            return bool(
                self.key == other.key
                and self.starting == other.starting
                and self.matching.group() == other.matching.group()
            )
        else:
            return False

    def __repr__(self) -> str:
        return f"@capture<{self.key}>"

    def dispatch(self) -> list[Capture | ContentElement]:
        """Dispatches the remaining parse of the capture group."""
        elements = []
        for group_id, parser in self.parsers.items():
            if group_id > self.pattern.number_of_captures():
                LOGGER.warning(
                    f"The capture group {group_id} does not exist in pattern {self.pattern._pattern}"
                )
                continue

            group_span = self.matching.span(group_id)

            # Empty group
            if group_span[0] == group_span[1]:
                continue

            group_starting = (self.starting[0], group_span[0])
            group_boundary = (self.starting[0], group_span[1])

            if (
                parser == self
                and group_starting == self.starting
                and group_boundary == self.boundary
            ):
                LOGGER.warning("Parser loop detected, continuing...", self, self.starting)
                continue

            # Dispatch the parse
            self.kwargs.pop("greedy", None)
            parsed, captured_elements, _ = parser._parse(
                self.handler,
                starting=group_starting,
                boundary=group_boundary,
                find_one=self.kwargs.pop("find_one", False),
                parent_capture=self,
                **self.kwargs,
            )

            if parsed:
                elements.extend(captured_elements)

        return elements


def dispatch_list(
    pending_elements: list[Capture | ContentElement], parent: ContentElement | None = None
) -> list[ContentElement]:
    """Dispatches all captured parsers in the list."""
    elements = []
    for item in pending_elements:
        if isinstance(item, Capture):
            captured_elements: list[ContentElement] = dispatch_list(item.dispatch())
            elements.extend(captured_elements)
        elif item != parent:
            elements.append(item)
    return elements


class ContentElement:
    """The base grammar element object."""

    def __init__(
        self,
        token: str,
        grammar: dict,
        content: str,
        characters: dict[POS, str],
        children: list[Capture | ContentElement] | None = None,
    ) -> None:
        if children is None:
            children = []
        self.token = token
        self.grammar = grammar
        self.content = content
        self.characters = characters
        self._children_pending = children
        self._children_dispached: list[ContentElement] = []
        self._dispatched_children: bool = False

    @property
    def _subelements(self) -> list[ContentElement]:
        return self.children

    @property
    def children(self) -> list[ContentElement]:
        "Children elements"
        if self._children_pending:
            if not self._dispatched_children:
                self._children_dispached = dispatch_list(self._children_pending, parent=self)
                self._dispatched_children = True
            return self._children_dispached
        else:
            return []

    def __eq__(self, other):
        if not isinstance(other, ContentElement):
            return False
        return bool(self.grammar == other.grammar and self.characters == other.characters)

    def to_dict(self, verbosity: int = -1, all_content: bool = False, **kwargs) -> dict:
        "Converts the object to dictionary."
        out_dict = {"token": self.token}
        if all_content or not self.children:
            out_dict["content"] = self.content
        if self.children:
            out_dict["children"] = (
                self._list_property_to_dict(
                    "children", verbosity=verbosity - 1, all_content=all_content
                )
                if verbosity
                else self.children
            )
        return out_dict

    def find(
        self,
        tokens: str | list[str],
        stop_tokens: str | list[str] = "",
        verbosity: int = -1,
        stack: list[str] | None = None,
        attribute: str = "_subelements",
    ) -> Generator[tuple[ContentElement, list[str]], None, None]:
        """Find the next subelement that match the input token(s).

        The find method will return a generator that globs though the element-tree, searching for the next
        subelement that matches the given token.
        """
        if isinstance(tokens, str):
            tokens = [tokens]
        if isinstance(stop_tokens, str):
            stop_tokens = [stop_tokens] if stop_tokens else []
        if not set(tokens).isdisjoint(set(stop_tokens)):
            raise ValueError("Input tokens and stop_tokens must be disjoint")

        if stack is None:
            stack = []
        stack += [self.token]

        if verbosity:
            verbosity -= 1
            children: list[ContentElement] = getattr(self, attribute, self._subelements)
            for child in children:
                if stop_tokens and (
                    child.token in stop_tokens
                    or (stop_tokens == ["*"] and child.token not in tokens)
                ):
                    return None

                if child.token in tokens or tokens == ["*"]:
                    yield child, [e for e in stack]
                if verbosity:
                    nested_generator = child.find(
                        tokens, verbosity=verbosity - 1, stack=[e for e in stack]
                    )
                    yield from nested_generator
        return None

    def findall(
        self,
        tokens: str | list[str],
        stop_tokens: str | list[str] = "",
        verbosity: int = -1,
        attribute: str = "_subelements",
    ) -> list[tuple[ContentElement, list[str]]]:
        """Returns subelements that match the input token(s)."""
        return list(
            self.find(tokens, stop_tokens=stop_tokens, verbosity=verbosity, attribute=attribute)
        )

    def flatten(self) -> list[tuple[tuple[int, int], str, list[str]]]:
        """Converts the object to a flattened array of tokens per index."""
        token_dict = self._token_by_index(defaultdict(list))
        tokens = []
        for (_, key), group in groupby(sorted(token_dict.items()), lambda x: (x[0][0], x[1])):
            group_tokens = list(group)
            starting = group_tokens[0][0]
            content = ""
            for pos, _ in group_tokens:
                content += self.characters[pos]
            if content:
                tokens.append((starting, content, key))
        return tokens

    def print(
        self,
        flatten: bool = False,
        verbosity: int = -1,
        all_content: bool = False,
        **kwargs,
    ) -> None:
        """Prints the current object recursively by converting to dictionary."""
        if flatten:
            pprint(
                self.flatten(**kwargs),
                sort_dicts=False,
                width=kwargs.pop("width", 150),
                **kwargs,
            )
        else:
            pprint(
                self.to_dict(verbosity=verbosity, all_content=all_content, **kwargs),
                sort_dicts=False,
                width=kwargs.pop("width", 150),
                **kwargs,
            )

    def _token_by_index(self, token_dict: TOKEN_DICT | None = None) -> TOKEN_DICT:
        """Recursively tokenize every index between start and close."""
        if token_dict is None:
            token_dict = defaultdict(list)
        for pos in self.characters:
            token_dict[pos].append(self.token)

        # Tokenize child elements
        for element in self.children:
            element._token_by_index(token_dict)
        return token_dict

    def _list_property_to_dict(self, prop: str, **kwargs):
        """Makes a dictionary from a property."""
        return [
            item.to_dict(**kwargs) if isinstance(item, ContentElement) else item
            for item in getattr(self, prop, [])
        ]

    def __repr__(self) -> str:
        content = self.content if len(self.content) < 15 else self.content[:15] + "..."
        return repr(f"{self.token}<<{content}>>({len(self.children)})")


class ContentBlockElement(ContentElement):
    """A parsed element with a begin and a end"""

    def __init__(
        self,
        begin: list[Capture | ContentElement] | None = None,
        end: list[Capture | ContentElement] | None = None,
        **kwargs,
    ) -> None:
        if end is None:
            end = []
        if begin is None:
            begin = []
        super().__init__(**kwargs)
        self._begin_pending = begin
        self._end_pending = end
        self._begin_dispached: list[ContentElement] = []
        self._end_dispached: list[ContentElement] = []
        self._dispatched_begin: bool = False
        self._dispatched_end: bool = False

    @property
    def _subelements(self) -> list[ContentElement]:
        return self.begin + self.children + self.end

    @property
    def begin(self) -> list[ContentElement]:
        "Begin elements"
        if self._begin_pending:
            if not self._dispatched_begin:
                self._begin_dispached = dispatch_list(self._begin_pending, parent=self)
                self._dispatched_begin = True
            return self._begin_dispached
        else:
            return []

    @property
    def end(self) -> list[ContentElement]:
        "End elements"
        if self._end_pending:
            if not self._dispatched_end:
                self._end_dispached = dispatch_list(self._end_pending, parent=self)
                self._dispatched_end = True
            return self._end_dispached
        else:
            return []

    def to_dict(self, verbosity: int = -1, all_content: bool = False, **kwargs) -> dict:
        out_dict = super().to_dict(verbosity=verbosity, all_content=all_content, **kwargs)
        if self.begin:
            out_dict["begin"] = (
                self._list_property_to_dict("begin", verbosity=verbosity - 1, **kwargs)
                if verbosity
                else self.begin
            )
        if self.end:
            out_dict["end"] = (
                self._list_property_to_dict("end", verbosity=verbosity - 1, **kwargs)
                if verbosity
                else self.end
            )

        ordered_keys = [
            key for key in ["token", "begin", "end", "content", "children"] if key in out_dict
        ]
        ordered_dict = {key: out_dict[key] for key in ordered_keys}
        return ordered_dict

    def _token_by_index(self, token_dict: TOKEN_DICT | None = None) -> TOKEN_DICT:
        """Converts the object to a flattened array of tokens."""
        if token_dict is None:
            token_dict = defaultdict(list)
        super()._token_by_index(token_dict)
        for element in self.begin:
            element._token_by_index(token_dict)
        for element in self.end:
            element._token_by_index(token_dict)
        return token_dict
