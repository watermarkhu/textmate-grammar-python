from typing import List, Union


class ParsedElementBase(object):
    pass


CONTENT_TYPE = Union[str, List[ParsedElementBase]]


class ParsedElement(ParsedElementBase):
    def __init__(self, token: str, content: CONTENT_TYPE) -> None:
        self.token = token
        self.content = content

    def __repr__(self) -> str:
        contentRepr = self.content if isinstance(self.content, str) else len(self.content)
        return repr(f"{self.token}({contentRepr})")

    def to_dict(self) -> dict:
        outDict = dict(self.__dict__)
        if not isinstance(self.content, str):
            outDict["content"] = [
                item.to_dict() if isinstance(item, ParsedElementBase) else item for item in self.content
            ]
        return outDict


class ParsedElementBlock(ParsedElementBase):
    def __init__(
        self,
        token: str,
        begin: CONTENT_TYPE,
        end: CONTENT_TYPE,
        content: CONTENT_TYPE,
    ) -> None:
        self.token = token
        self.begin = begin
        self.end = end
        self.content = content

    def __repr__(self) -> str:
        return repr(f"{self.token}({len(self.content)})")

    def to_dict(self) -> dict:
        outDict = dict(self.__dict__)
        for key in ["begin", "end", "content"]:
            if not isinstance(getattr(self, key), str):
                outDict[key] = [
                    item.to_dict() if isinstance(item, ParsedElementBase) else item
                    for item in getattr(self, key)
                ]
        return outDict
