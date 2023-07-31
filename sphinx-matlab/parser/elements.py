from typing import List


class ParsedElementBase(object):
    pass


class ParsedElement(object):
    def __init__(self, token: str, content: str) -> None:
        self.token = token
        self.content = content

    def __repr__(self) -> str:
        return repr(f"{self.token}('{self.content}')")

    def to_dict(self) -> dict:
        return self.__dict__


class ParsedElementBlock(object):
    def __init__(
        self,
        token: str,
        begin: List[ParsedElement],
        end: List[ParsedElement],
        content: List[ParsedElementBase],
    ) -> None:
        self.token = token
        self.begin = begin
        self.end = end
        self.content = content

    def __repr__(self) -> str:
        return repr(f"{self.token}({len(self.content)})")

    def to_dict(self) -> dict:
        outDict = self.__dict__
        for key in ["begin", "end", "content"]:
            outDict[key] = [element.to_dict() for element in outDict[key]]
        return outDict
