from typing import List, Tuple
from pprint import pprint
from io import StringIO


class ParsedElement(object):
    """The base parsed element object."""

    def __init__(
        self,
        token: str,
        grammar: dict,
        content: str,
        span: Tuple[int, int],
        captures: List["ParsedElement"] = [],
    ) -> None:
        self.token = token
        self.grammar = grammar
        self.content = content
        self.span = span
        self.captures = captures

    def to_dict(self, content: bool = True) -> dict:
        "Converts the object to dictionary."
        out_dict = {"token": self.token}
        if content:
            out_dict["content"] = self.content
        if self.captures:
            out_dict["captures"] = self.list_property_to_dict("captures", content)
        return out_dict

    def list_property_to_dict(self, prop: str, content: bool):
        """Makes a dictionary from a property."""
        return [
            item.to_dict(content=content) if isinstance(item, ParsedElement) else item
            for item in getattr(self, prop, [])
        ]

    def print(self, content: bool = True, **kwargs) -> None:
        """Prints the current object recursively by converting to dictionary."""
        pprint(self.to_dict(content=content), sort_dicts=False, width=kwargs.pop("width", 150), **kwargs)

    def __repr__(self) -> str:
        content = self.content if len(self.content) < 15 else self.content[:15] + "..."
        return repr(f"{self.token}<<{content}>>({len(self.captures)})")


class ParsedElementBlock(ParsedElement):
    """A parsed element with a begin and a end"""

    def __init__(self, begin: List[ParsedElement] = [], end: List[ParsedElement] = [], **kwargs) -> None:
        super().__init__(**kwargs)
        self.begin = begin
        self.end = end

    def to_dict(self, *args, content: bool = True, **kwargs) -> dict:
        out_dict = super().to_dict(*args, content=content, **kwargs)
        if self.begin:
            out_dict["begin"] = self.list_property_to_dict("begin", content)
        if self.end:
            out_dict["end"] = self.list_property_to_dict("end", content)

        ordered_keys = [key for key in ["token", "begin", "end", "content", "captures"] if key in out_dict]
        ordered_dict = {key: out_dict[key] for key in ordered_keys}
        return ordered_dict
