from typing import TYPE_CHECKING
from pprint import pprint
from collections import defaultdict
from itertools import groupby

from .handler import POS

if TYPE_CHECKING:
    from .parser import Capture


TOKEN_DICT = dict[POS, list[str]]


class ContentElement(object):
    """The base grammar element object."""

    def __init__(
        self,
        token: str,
        grammar: dict,
        content: str,
        characters: dict[POS, str],
        children: "list[ContentElement | Capture]" = [],
    ) -> None:
        self.token = token
        self.grammar = grammar
        self.content = content
        self.characters = characters
        self.children = children

    def __eq__(self, other):
        if self.grammar == other.grammar and self.characters == other.characters:
            return True
        else:
            return False

    def to_dict(self, verbosity: int = -1, all_content: bool = False, **kwargs) -> dict:
        "Converts the object to dictionary."
        out_dict = {"token": self.token}
        if all_content or not self.children:
            out_dict["content"] = self.content
        if self.children:
            out_dict["children"] = (
                self._list_property_to_dict("children", verbosity=verbosity - 1, all_content=all_content)
                if verbosity
                else self.children
            )
        return out_dict

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
                tokens.append([starting, content, key])
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

    def _token_by_index(self, token_dict: TOKEN_DICT = defaultdict(list)) -> TOKEN_DICT:
        """Recursively tokenize every index between start and close."""
        for pos in self.characters.keys():
            token_dict[pos].append(self.token)

        # Tokenize child elements
        for element in self.children:
            element._token_by_index(token_dict)
        return token_dict

    def _list_property_to_dict(self, prop: str, **kwargs):
        """Makes a dictionary from a property."""
        return [
            item.to_dict(**kwargs) if isinstance(item, ContentElement) else item for item in getattr(self, prop, [])
        ]

    def __repr__(self) -> str:
        content = self.content if len(self.content) < 15 else self.content[:15] + "..."
        return repr(f"{self.token}<<{content}>>({len(self.children)})")


class ContentBlockElement(ContentElement):
    """A parsed element with a begin and a end"""

    def __init__(
        self, begin: "list[ContentElement | Capture]" = [], end: "list[ContentElement | Capture]" = [], **kwargs
    ) -> None:
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

        ordered_keys = [key for key in ["token", "begin", "end", "content", "children"] if key in out_dict]
        ordered_dict = {key: out_dict[key] for key in ordered_keys}
        return ordered_dict

    def _token_by_index(self, token_dict: TOKEN_DICT = defaultdict(list)) -> TOKEN_DICT:
        """Converts the object to a flattened array of tokens."""
        super()._token_by_index(token_dict)
        for element in self.begin:
            element._token_by_index(token_dict)
        for element in self.end:
            element._token_by_index(token_dict)
        return token_dict
