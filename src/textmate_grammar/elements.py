from __future__ import annotations

from abc import ABC
from collections import defaultdict
from itertools import groupby
from pprint import pprint
from typing import TYPE_CHECKING, Generator

from .handler import POS, ContentHandler, Match, Pattern
from .utils.logger import LOGGER

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
    ):
        """
        Initialize a new instance of the Element class.

        :param handler: The content handler for the element.
        :param pattern: The pattern used for matching.
        :param matching: The match object.
        :param parsers: A dictionary of grammar parsers.
        :param starting: The starting position of the element.
        :param boundary: The boundary position of the element.
        :param key: The key for the element. Defaults to "".
        :param **kwargs: Additional keyword arguments.
        :returns: None
        """
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
        """Dispatches the remaining parse of the capture group.

        This method iterates over the defined parsers for the capture group and dispatches the remaining parse
        based on the captured elements. It returns a list of captured elements or captures.

        :return: A list of Capture or ContentElement objects representing the parsed elements.
        """
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


def _dispatch_list(
    pending_elements: list[Capture | ContentElement], parent: ContentElement | None = None
) -> list[ContentElement]:
    """Dispatches all captured parsers in the list."""
    elements = []
    for item in pending_elements:
        if isinstance(item, Capture):
            captured_elements: list[ContentElement] = _dispatch_list(item.dispatch())
            elements.extend(captured_elements)
        elif item != parent:
            elements.append(item)
    for element in elements:
        element.parent = parent
    return elements


def _str_to_list(input: str | list[str]) -> list[str]:
    if isinstance(input, str):
        return [input] if input else []
    else:
        return input


class ContentElement:
    """The parsed grammar element."""

    def __init__(
        self,
        token: str,
        grammar: dict,
        content: str,
        characters: dict[POS, str],
        children: list[Capture | ContentElement] | None = None,
    ) -> None:
        """
        Initialize a new instance of the Element class.

        :param token: The token associated with the element.
        :param grammar: The grammar associated with the element.
        :param content: The content associated with the element.
        :param characters: The characters associated with the element.
        :param children: The children associated with the element. Defaults to None.
        """
        if children is None:
            children = []
        self.token = token
        self.grammar = grammar
        self.content = content
        self.characters = characters
        self._children_captures = children
        self._dispatched: bool = False
        self.parent: ContentElement | None = None

    @property
    def _subelements(self) -> list[ContentElement]:
        return self.children

    @property
    def children(self) -> list[ContentElement]:
        """
        Returns a list of children elements.

        If the elements have not been dispatched yet, this method will dispatch them before returning.

        :return: A list of ContentElement objects representing the children elements.
        """
        if not self._dispatched:
            self._dispatch()
        return self._children

    def _dispatch(self, nested: bool = False):
        """
        Dispatches the content element and its children.

        :param nested: Indicates whether the dispatch is nested within another dispatch.
        :type nested: bool
        :return: None
        """
        if self._dispatched:
            return
        self._dispatched = True
        self._children: list[ContentElement] = _dispatch_list(self._children_captures, parent=self)
        self._children_captures = []
        if nested:
            for child in self._children:
                child._dispatch(True)

    def __eq__(self, other):
        if not isinstance(other, ContentElement):
            return False
        return bool(self.grammar == other.grammar and self.characters == other.characters)

    def _find(
        self,
        tokens: str | list[str],
        start_tokens: str | list[str] = "",
        hide_tokens: str | list[str] = "",
        stop_tokens: str | list[str] = "",
        depth: int = -1,
        attribute: str = "_subelements",
        stack: list[str] | None = None,
    ) -> Generator[tuple[ContentElement, list[str]], None, None]:
        tokens = _str_to_list(tokens)
        start_tokens = _str_to_list(start_tokens)
        hide_tokens = _str_to_list(hide_tokens)
        stop_tokens = _str_to_list(stop_tokens)

        if not set(tokens).isdisjoint(set(stop_tokens)):
            raise ValueError("Input tokens and stop_tokens must be disjoint")

        if stack is None:
            stack = []
        stack += [self.token]

        start_found = not start_tokens

        if depth:
            depth -= 1
            children: list[ContentElement] = getattr(self, attribute, self._subelements)
            for child in children:
                if stop_tokens and (
                    child.token in stop_tokens
                    or (stop_tokens == ["*"] and child.token not in tokens)
                ):
                    return None

                if not start_found and child.token in start_tokens:
                    start_found = True
                    start_tokens = []

                if (
                    start_found
                    and (child.token in tokens or tokens == ["*"])
                    and child.token not in hide_tokens
                ):
                    yield child, [e for e in stack]
                if depth:
                    nested_generator = child._find(
                        tokens,
                        start_tokens=start_tokens,
                        hide_tokens=hide_tokens,
                        stop_tokens=stop_tokens,
                        depth=depth - 1,
                        stack=[e for e in stack],
                    )
                    yield from nested_generator
        return None

    def find(
        self,
        tokens: str | list[str],
        start_tokens: str | list[str] = "",
        hide_tokens: str | list[str] = "",
        stop_tokens: str | list[str] = "",
        depth: int = -1,
        attribute: str = "_subelements",
    ) -> Generator[tuple[ContentElement, list[str]], None, None]:
        """
        Find content elements based on the given criteria.

        The find method will return a generator that globs though the element-tree, searching for the next
        subelement that matches the given token.

        :param tokens: The tokens to search for. Can be a single token or a list of tokens.
        :param start_tokens: The tokens that mark the start of the search. Can be a single token or a list of tokens.
        :param hide_tokens: The tokens to hide from the search results. Can be a single token or a list of tokens.
        :param stop_tokens: The tokens that mark the end of the search. Can be a single token or a list of tokens.
        :param depth: The maximum depth to search. Defaults to -1 (unlimited depth).
        :param attribute: The attribute name to access the subelements. Defaults to "_subelements".

        :yield: A tuple containing the found content element and the stack of tokens encountered.

        :raises ValueError: If the input tokens and stop_tokens are not disjoint.

        :return: None if no matching content elements are found.
        """
        return self._find(
            tokens,
            start_tokens=start_tokens,
            hide_tokens=hide_tokens,
            stop_tokens=stop_tokens,
            depth=depth,
            attribute=attribute,
        )

    def findall(
        self,
        tokens: str | list[str],
        start_tokens: str | list[str] = "",
        hide_tokens: str | list[str] = "",
        stop_tokens: str | list[str] = "",
        depth: int = -1,
        attribute: str = "_subelements",
    ) -> list[tuple[ContentElement, list[str]]]:
        """
        Find all occurrences of the specified tokens within the content element.

        :param tokens: The tokens to search for.
        :param start_tokens: The tokens that must appear before the found tokens. Defaults to "".
        :param hide_tokens: The tokens that should be hidden from the search. Defaults to "".
        :param stop_tokens: The tokens that, if found, should stop the search. Defaults to "".
        :param depth: The maximum depth to search. Defaults to -1 (unlimited depth).
        :param attribute: The attribute to search within. Defaults to "_subelements".

        :return: A list of tuples containing the content element and the found tokens.
        """
        return list(
            self._find(
                tokens,
                start_tokens=start_tokens,
                hide_tokens=hide_tokens,
                stop_tokens=stop_tokens,
                depth=depth,
                attribute=attribute,
            )
        )

    def to_dict(self, depth: int = -1, all_content: bool = False, **kwargs) -> dict:
        """
        Converts the object to a dictionary.

        :param depth: The depth of the conversion. Defaults to -1.
        :param all_content: Whether to include all content or only the top-level content. Defaults to False.

        :return: The converted dictionary representation of the object.
        """
        out_dict = {"token": self.token}
        if all_content or not self.children:
            out_dict["content"] = self.content
        if self.children:
            out_dict["children"] = (
                self._list_property_to_dict("children", depth=depth - 1, all_content=all_content)
                if depth
                else self.children
            )
        return out_dict

    def flatten(self) -> list[tuple[tuple[int, int], str, list[str]]]:
        """
        Converts the object to a flattened array of tokens per index, similarly to vscode-textmate.

        :return: A list of tuples representing the flattened tokens. Each tuple contains:
             - A tuple representing the starting and ending index of the token.
             - The content of the token.
             - A list of keys associated with the token.
        """
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
        depth: int = -1,
        all_content: bool = False,
        **kwargs,
    ) -> None:
        """
        Prints the current object recursively by converting it to a dictionary or a flattened array.

        :param flatten: If True, flattens the object before printing. Defaults to False.
        :param depth: The maximum depth to print. Defaults to -1 (unlimited depth).
        :param all_content: If True, includes all content in the printout. Defaults to False.
        :param **kwargs: Additional keyword arguments to be passed to the pprint function.

        :return: None
        """
        if flatten:
            pprint(
                self.flatten(**kwargs),
                sort_dicts=False,
                width=kwargs.pop("width", 150),
                **kwargs,
            )
        else:
            pprint(
                self.to_dict(depth=depth, all_content=all_content, **kwargs),
                sort_dicts=False,
                width=kwargs.pop("width", 150),
                **kwargs,
            )

    def _token_by_index(self, token_dict: TOKEN_DICT | None = None) -> TOKEN_DICT:
        """Recursively tokenize every index between start and close.

        This method recursively tokenizes every index between the start and close positions of the element.
        It populates a dictionary, `token_dict`, with the tokens corresponding to each index.

        :param token_dict: A dictionary to store the tokens. If None, a new dictionary is created.
        :type token_dict: dict | None
        :return: A dictionary containing the tokens for each index.
        :rtype: dict
        """
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
        *args,
        begin: list[Capture | ContentElement] | None = None,
        end: list[Capture | ContentElement] | None = None,
        **kwargs,
    ) -> None:
        """
        Initialize a new instance of the Element class.

        :param begin: A list of Capture or ContentElement objects representing the beginning captures of the element. Defaults to None.
        :param end: A list of Capture or ContentElement objects representing the ending captures of the element. Defaults to None.
        :param **kwargs: Additional keyword arguments to be passed to the parent class constructor.

        :return: None
        """
        if end is None:
            end = []
        if begin is None:
            begin = []
        super().__init__(*args, **kwargs)
        self._begin_captures = begin
        self._end_captures = end

    @property
    def _subelements(self) -> list[ContentElement]:
        return self.begin + self.children + self.end

    @property
    def begin(self) -> list[ContentElement]:
        """
        Returns the list of begin elements.

        If the elements have not been dispatched yet, this method will dispatch them before returning.

        :return: The list of begin elements.
        """
        if not self._dispatched:
            self._dispatch()
        return self._begin

    @property
    def end(self) -> list[ContentElement]:
        """
        Returns the end elements.

        If the elements have not been dispatched yet, this method will dispatch them before returning.

        :return: A list of end elements.
        """
        if not self._dispatched:
            self._dispatch()
        return self._end

    def _dispatch(self, nested: bool = False):
        if self._dispatched:
            return
        super()._dispatch(nested)
        self._begin: list[ContentElement] = _dispatch_list(self._begin_captures, parent=self)
        self._end: list[ContentElement] = _dispatch_list(self._end_captures, parent=self)
        self._begin_captures, self._end_captures = [], []
        if nested:
            for item in self._begin:
                item._dispatch(True)
            for item in self._end:
                item._dispatch(True)

    def to_dict(self, depth: int = -1, all_content: bool = False, **kwargs) -> dict:
        """
        Converts the element to a dictionary representation.

        :param depth: The depth of the conversion. Defaults to -1.
        :param all_content: Whether to include all content. Defaults to False.
        :param **kwargs: Additional keyword arguments.

        :return: The dictionary representation of the element.
        """
        out_dict = super().to_dict(depth=depth, all_content=all_content, **kwargs)
        if self.begin:
            out_dict["begin"] = (
                self._list_property_to_dict("begin", depth=depth - 1, **kwargs)
                if depth
                else self.begin
            )
        if self.end:
            out_dict["end"] = (
                self._list_property_to_dict("end", depth=depth - 1, **kwargs) if depth else self.end
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
