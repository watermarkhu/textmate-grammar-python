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
        """
        Initialize a new instance of the Element class.

        Args:
            handler (ContentHandler): The content handler for the element.
            pattern (Pattern): The pattern used for matching.
            matching (Match): The match object.
            parsers (dict[int, GrammarParser]): A dictionary of grammar parsers.
            starting (tuple[int, int]): The starting position of the element.
            boundary (tuple[int, int]): The boundary position of the element.
            key (str, optional): The key for the element. Defaults to "".
            **kwargs: Additional keyword arguments.

        Returns:
            None
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

        Returns:
            A list of Capture or ContentElement objects representing the parsed elements.
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
    return elements


def _str_to_list(input: str | list[str]) -> list[str]:
    if isinstance(input, str):
        return [input] if input else []
    else:
        return input


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
        """
        Initialize a new instance of the Element class.

        Args:
            token (str): The token associated with the element.
            grammar (dict): The grammar associated with the element.
            content (str): The content associated with the element.
            characters (dict[POS, str]): The characters associated with the element.
            children (list[Capture | ContentElement] | None, optional): The children associated with the element. Defaults to None.
        """
        if children is None:
            children = []
        self.token = token
        self.grammar = grammar
        self.content = content
        self.characters = characters
        self._children_captures = children
        self._dispatched: bool = False

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

        Args:
            nested (bool): Indicates whether the dispatch is nested within another dispatch.

        Returns:
            None
        """
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

    def find(
        self,
        tokens: str | list[str],
        start_tokens: str | list[str] = "",
        hide_tokens: str | list[str] = "",
        stop_tokens: str | list[str] = "",
        depth: int = -1,
        attribute: str = "_subelements",
        stack: list[str] | None = None,
    ) -> Generator[tuple[ContentElement, list[str]], None, None]:
        """
        Find content elements based on the given criteria.

        The find method will return a generator that globs though the element-tree, searching for the next
        subelement that matches the given token.

        Args:
            tokens: The tokens to search for. Can be a single token or a list of tokens.
            start_tokens: The tokens that mark the start of the search. Can be a single token or a list of tokens.
            hide_tokens: The tokens to hide from the search results. Can be a single token or a list of tokens.
            stop_tokens: The tokens that mark the end of the search. Can be a single token or a list of tokens.
            depth: The maximum depth to search. Defaults to -1 (unlimited depth).
            attribute: The attribute name to access the subelements. Defaults to "_subelements".
            stack: The stack of tokens encountered during the search. Defaults to None.

        Yields:
            A tuple containing the found content element and the stack of tokens encountered.

        Raises:
            ValueError: If the input tokens and stop_tokens are not disjoint.

        Returns:
            None: If no matching content elements are found.
        """
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
                    nested_generator = child.find(
                        tokens,
                        start_tokens=start_tokens,
                        hide_tokens=hide_tokens,
                        stop_tokens=stop_tokens,
                        depth=depth - 1,
                        stack=[e for e in stack],
                    )
                    yield from nested_generator
        return None

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

        Args:
            tokens (str | list[str]): The tokens to search for.
            start_tokens (str | list[str], optional): The tokens that must appear before the found tokens. Defaults to "".
            hide_tokens (str | list[str], optional): The tokens that should be hidden from the search. Defaults to "".
            stop_tokens (str | list[str], optional): The tokens that, if found, should stop the search. Defaults to "".
            depth (int, optional): The maximum depth to search. Defaults to -1 (unlimited depth).
            attribute (str, optional): The attribute to search within. Defaults to "_subelements".

        Returns:
            list[tuple[ContentElement, list[str]]]: A list of tuples containing the content element and the found tokens.
        """
        return list(
            self.find(
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

        Args:
            depth (int, optional): The depth of the conversion. Defaults to -1.
            all_content (bool, optional): Whether to include all content or only the top-level content. Defaults to False.

        Returns:
            dict: The converted dictionary representation of the object.
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

        Returns:
            A list of tuples representing the flattened tokens. Each tuple contains:
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
        Prints the current object recursively by converting it to a dictionary or a flattend array.

        Args:
            flatten (bool, optional): If True, flattens the object before printing. Defaults to False.
            depth (int, optional): The maximum depth to print. Defaults to -1 (unlimited depth).
            all_content (bool, optional): If True, includes all content in the printout. Defaults to False.
            **kwargs: Additional keyword arguments to be passed to the pprint function.

        Returns:
            None
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

        Args:
            token_dict (TOKEN_DICT | None): A dictionary to store the tokens. If None, a new dictionary is created.

        Returns:
            TOKEN_DICT: A dictionary containing the tokens for each index.

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
        begin: list[Capture | ContentElement] | None = None,
        end: list[Capture | ContentElement] | None = None,
        **kwargs,
    ) -> None:
        """
        Initialize a new instance of the Element class.

        Args:
            begin (list[Capture | ContentElement] | None): A list of Capture or ContentElement objects representing the beginning captures of the element. Defaults to None.
            end (list[Capture | ContentElement] | None): A list of Capture or ContentElement objects representing the ending captures of the element. Defaults to None.
            **kwargs: Additional keyword arguments to be passed to the parent class constructor.

        Returns:
            None
        """
        if end is None:
            end = []
        if begin is None:
            begin = []
        super().__init__(**kwargs)
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

        Returns:
            list[ContentElement]: The list of begin elements.
        """
        if not self._dispatched:
            self._dispatch()
        return self._begin

    @property
    def end(self) -> list[ContentElement]:
        """
        Returns the end elements.

        If the elements have not been dispatched yet, this method will dispatch them before returning.

        Returns:
            list[ContentElement]: A list of end elements.
        """
        if not self._dispatched:
            self._dispatch()
        return self._end

    def _dispatch(self, nested: bool = False):
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

        Args:
            depth (int, optional): The depth of the conversion. Defaults to -1.
            all_content (bool, optional): Whether to include all content. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: The dictionary representation of the element.
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
