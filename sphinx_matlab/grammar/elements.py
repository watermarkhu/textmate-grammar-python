from typing import List, Optional
from pprint import pprint


class ParsedElement(object):
    def __init__(self, token: str, content: str, captures: List["ParsedElement"] = []) -> None:
        self.token = token
        self.content = content
        self.captures = captures

    def to_dict(self, allContent: bool = False) -> dict:
        outDict = dict(self.__dict__)
        if not outDict["captures"]:
            outDict.pop("captures")
        else:
            if not allContent:
                outDict.pop("content")
            outDict["captures"] = [
                item.to_dict() if isinstance(item, ParsedElement) else item for item in self.captures
            ]
        return outDict

    def print(self, allContent: bool = False) -> None:
        pprint(self.to_dict(allContent=allContent), sort_dicts=False, width=120)

    def __repr__(self) -> str:
        return repr(f"{self.token}<{self.content}>({len(self.captures)})")


class ParsedElementBlock(ParsedElement):
    def __init__(
        self,
        token: str,
        content: str,
        captures: List[ParsedElement] = [],
        begin: Optional[ParsedElement] = None,
        end: Optional[ParsedElement] = None,
    ) -> None:
        self.token = token
        self.begin = begin
        self.content = content
        self.end = end
        self.captures = captures

    def to_dict(self, *args, **kwargs) -> dict:
        outDict = super().to_dict(*args, **kwargs)
        for attr in ["begin", "end"]:
            if getattr(self, attr) is None:
                outDict.pop(attr)
            else:
                outDict[attr] = getattr(self, attr).to_dict()
        return outDict
