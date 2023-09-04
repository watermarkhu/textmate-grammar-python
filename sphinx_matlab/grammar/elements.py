from typing import List, Tuple
from pprint import pprint
from io import StringIO


class ParsedElement(object):
    def __init__(
        self, token: str, grammar: dict, stream: StringIO, span: Tuple[int, int], captures: List["ParsedElement"] = [], 
    ) -> None:
        self.token = token
        self.grammar = grammar
        self.stream = stream
        self.span = span
        self.captures = captures
    
    @property
    def content(self):
        self.stream.seek(self.span[0])
        return self.stream.read(self.span[1] - self.span[0])

    def to_dict(self, content: bool = True) -> dict:
        outDict = dict(token=self.token)
        if content:
            outDict["content"] = self.content
        if self.captures:
            outDict["captures"] = self.list_property_to_dict("captures", content)
        return outDict

    def list_property_to_dict(self, property: str, content: bool):
        return [
            item.to_dict(content=content) if isinstance(item, ParsedElement) else item
            for item in getattr(self, property, [])
        ]

    def print(self, content: bool = True, **kwargs) -> None:
        pprint(self.to_dict(content=content), sort_dicts=False, width=kwargs.pop('width', 150), **kwargs)

    def __repr__(self) -> str:
        content = self.content if len(self.content) < 15 else self.content[:15] + "..."
        return repr(f"{self.token}<<{content}>>({len(self.captures)})")


class ParsedElementBlock(ParsedElement):
    def __init__(
        self,
        begin: List[ParsedElement] = [],
        end: List[ParsedElement] = [],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.begin = begin
        self.end = end
        

    def to_dict(self, *args, content: bool = True, **kwargs) -> dict:
        outDict = super().to_dict(*args, content=content, **kwargs)
        if self.begin:
            outDict["begin"] = self.list_property_to_dict("begin", content)
        if self.end:
            outDict["end"] = self.list_property_to_dict("end", content)

        orderedKeys = [key for key in ["token", "begin", "end", "content", "captures"] if key in outDict]
        orderedDict = {key: outDict[key] for key in orderedKeys}
        return orderedDict
