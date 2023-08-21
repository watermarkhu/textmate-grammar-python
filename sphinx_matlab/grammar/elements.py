from typing import List, Optional
from pprint import pprint


class ParsedElement(object):
    def __init__(self, token: str, content: str, captures: List["ParsedElement"] = []) -> None:
        self.token = token
        self.content = content
        self.captures = captures

    def to_dict(self, content: bool = True) -> dict:
        outDict = dict(self.__dict__)
        if not content:
            outDict.pop("content")
        outDict = self.list_property_to_dict(outDict, "captures", content)
        return outDict

    def list_property_to_dict(self, outDict: dict, property: str, content: bool):
        if not outDict[property]:
            outDict.pop(property)
        else:
            outDict[property] = [
                item.to_dict(content=content) if isinstance(item, ParsedElement) else item
                for item in getattr(self, property)
            ]
        return outDict

    def print(self, content: bool = True) -> None:
        pprint(self.to_dict(content=content), sort_dicts=False, width=120)

    def __repr__(self) -> str:
        return repr(f"{self.token}<{self.content}>({len(self.captures)})")


class ParsedElementBlock(ParsedElement):
    def __init__(
        self,
        token: str,
        content: str,
        captures: List[ParsedElement] = [],
        begin: List[ParsedElement] = [],
        end: List[ParsedElement] = [],
    ) -> None:
        self.token = token
        self.begin = begin
        self.content = content
        self.end = end
        self.captures = captures

    def to_dict(self, *args, content:bool = True, **kwargs) -> dict:
        outDict = super().to_dict(*args, content=content, **kwargs)
        outDict = self.list_property_to_dict(outDict, "begin", content)
        outDict = self.list_property_to_dict(outDict, "end", content)
        return outDict
