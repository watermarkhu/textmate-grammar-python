from typing import List, Tuple, TYPE_CHECKING
from pprint import pprint
from collections import defaultdict
from itertools import groupby
from io import TextIOBase

from .read import stream_read_pos
from .logging import LOGGER

if TYPE_CHECKING:
    from .parser import GrammarParser


class ContentElement(object):
    """The base grammar element object."""

    def __init__(
        self,
        token: str,
        grammar: dict,
        content: str,
        span: Tuple[int, int],
        captures: List["ContentElement"] = [],
    ) -> None:
        self.token = token
        self.grammar = grammar
        self.content = content
        self.span = span
        self.captures = captures

    def __eq__(self, other):
        if self.grammar == other.grammar and self.span == other.span:
            return True
        else:
            return False

    def to_dict(self, verbosity: int = -1, all_content: bool = False, parse_unparsed: bool = False, **kwargs) -> dict:
        "Converts the object to dictionary."
        if parse_unparsed:
            self.parse_unparsed()
        out_dict = {"token": self.token}
        if all_content or not self.captures:
            out_dict["content"] = self.content
        if self.captures:
            out_dict["captures"] = (
                self._list_property_to_dict(
                    "captures", verbosity=verbosity - 1, all_content=all_content, parse_unparsed=parse_unparsed
                )
                if verbosity
                else self.captures
            )
        return out_dict
    
    def flatten(self) -> List[Tuple[Tuple[int, int], str, List[str]]]:
        """Converts the object to a flattened array of tokens per index."""
        items_dict = self._token_by_index()
        tokens = []
        for key, group in groupby(sorted(items_dict.items()), lambda x: x[1]):
            group_tokens = list(group)
            start_index = group_tokens[0][0]
            group_length = len(group_tokens)
            span = (start_index, start_index + group_length)
            content_start = start_index - self.span[0]
            content = self.content[content_start:content_start+group_length]
            tokens.append([span, content, key])
        return tokens

    def print(self, flatten: bool = False, verbosity: int = -1, all_content: bool = False, **kwargs) -> None:
        """Prints the current object recursively by converting to dictionary."""
        if flatten:
            output = self.flatten(**kwargs)
        else:
            output = self.to_dict(verbosity=verbosity, all_content=all_content, **kwargs)

        pprint(
            output,
            sort_dicts=False,
            width=kwargs.pop("width", 150),
            **kwargs,
        )

    def parse_unparsed(self, **kwargs) -> "ContentElement":
        """Parses the unparsed elements contained in the current element."""
        self.captures = self._parse_unparsed_elements(self.captures, **kwargs)
        return self
    
    def _token_by_index(self, items_dict: dict = defaultdict(list)) -> dict:
        self.parse_unparsed()
        for ind in range(self.span[0], self.span[1]):
            items_dict[ind].append(self.token)
        for element in self.captures:
            element._token_by_index(items_dict=items_dict)
        return items_dict
    

    def _list_property_to_dict(self, prop: str, **kwargs):
        """Makes a dictionary from a property."""
        return [
            item.to_dict(**kwargs) if isinstance(item, ContentElement) else item for item in getattr(self, prop, [])
        ]

    def __repr__(self) -> str:
        content = self.content if len(self.content) < 15 else self.content[:15] + "..."
        return repr(f"{self.token}<<{content}>>({len(self.captures)})")

    @staticmethod
    def _parse_unparsed_elements(elements: List["ContentElement"], **kwargs):
        """Parses the unparsed elements of the UnparsedElement type of a property."""
        parsed_elements = []
        for element in elements:
            if type(element) is UnparsedElement:
                for unparsed_parsed in element.parse(**kwargs):
                    parsed_elements.append(unparsed_parsed.parse_unparsed(**kwargs))
            else:
                parsed_elements.append(element.parse_unparsed(**kwargs))
        return parsed_elements


class ContentBlockElement(ContentElement):
    """A parsed element with a begin and a end"""

    def __init__(self, begin: List[ContentElement] = [], end: List[ContentElement] = [], **kwargs) -> None:
        super().__init__(**kwargs)
        self.begin = begin
        self.end = end

    def to_dict(self, verbosity: int = -1, **kwargs) -> dict:
        out_dict = super().to_dict(verbosity=verbosity, **kwargs)
        if self.begin:
            out_dict["begin"] = (
                self._list_property_to_dict("begin", verbosity=verbosity - 1, **kwargs) if verbosity else self.begin
            )
        if self.end:
            out_dict["end"] = (
                self._list_property_to_dict("end", verbosity=verbosity - 1, **kwargs) if verbosity else self.end
            )

        ordered_keys = [key for key in ["token", "begin", "end", "content", "captures"] if key in out_dict]
        ordered_dict = {key: out_dict[key] for key in ordered_keys}
        return ordered_dict

    def parse_unparsed(self, **kwargs):
        """Parses the unparsed elements contained in the current element."""
        self.captures = self._parse_unparsed_elements(self.captures, **kwargs)
        self.begin = self._parse_unparsed_elements(self.begin, **kwargs)
        self.end = self._parse_unparsed_elements(self.end, **kwargs)
        return self

    def _token_by_index(self, items_dict: dict = defaultdict(list)) -> dict:
        """Converts the object to a flattened array of tokens."""
        self.parse_unparsed()
        for ind in range(self.span[0], self.span[1]):
            items_dict[ind].append(self.token)
        for element in self.begin:
            element._token_by_index(items_dict=items_dict)
        for element in self.captures:
            element._token_by_index(items_dict=items_dict)
        for element in self.end:
            element._token_by_index(items_dict=items_dict)
        return items_dict

class UnparsedElement(ContentElement):
    """The to-be-parsed Element type.

    If a matched regex pattern includes groups that are to be parsed iteratively, an UnparsedElement is
    created. Unparsed elements are to be parsed at a later moment and allows for faster pattern matching.
    """

    def __init__(self, stream: TextIOBase, parser: "GrammarParser", span: Tuple[int, int], **kwargs):
        super().__init__(f"@{parser.token}", parser.grammar, "", span)
        self.stream = stream
        self.parser = parser
        self.parser_kwargs = kwargs

    def parse(self, verbosity: int = 0) -> List[ContentElement]:
        """Parses the stream stored in the UnparsedElement."""

        LOGGER.debug("UnparsedElement parsing", self.parser, self.span[0])
        self.stream.seek(self.span[0])
        _, elements, _ = self.parser.parse(
            self.stream, boundary=self.span[1], find_one=False, verbosity=verbosity, **self.parser_kwargs
        )

        if len(elements) == 1 and elements[0] == self:
            # UnparsedElement loop, exit loop by creating a standard ContentElement from span
            LOGGER.debug("UnparsedElement loop detected, ContentElement is created.", self.parser, self.span[0])
            element = ContentElement(
                token=self.parser.token,
                grammar=self.grammar,
                content=stream_read_pos(self.stream, self.span[0], self.span[1]),
                span=self.span,
            )
            return [element]
        else:
            captures = self._parse_unparsed_elements(elements)
            if self.parser.token:
                # Put captures into standard element.
                element = ContentElement(
                    token=self.parser.token,
                    grammar=self.grammar,
                    content=stream_read_pos(self.stream, self.span[0], self.span[1]),
                    span=self.span,
                    captures=captures,
                )
                return [element]
            else:
                # Return captures directly since no token exists for current parser
                return captures
