# %%
from .exceptions import IncludedParserNotFound, CannotCloseEnd, RegexGroupsMismatch
from .elements import ParsedElementBase, ParsedElement, ParsedElementBlock, CONTENT_TYPE
from typing import Tuple, List, Union, Optional
from io import StringIO, SEEK_END
import re


class GrammarParser(object):
    PARSERSTORE = {}
    regex_max_lookback = 10
    regex_replacements = {"\\\\": "\\", "\\G": ""}

    def __init__(self, grammar: dict, key: str = "", **kwargs) -> None:
        self.grammar = grammar
        self.key = key
        self.token = grammar.get("name", "")
        self.contentToken = grammar.get("contentName", "")
        self.comment = grammar.get("comment", "")
        self.match, self.begin, self.end = None, None, None
        self.captures, self.beginCaptures, self.endCaptures = [], [], []
        self.patterns = []

        if key:
            self.PARSERSTORE[key] = self

        if "match" in grammar:
            self.match = self.compile_regex(grammar["match"])
            self.captures = self.__init_captures(grammar, key="captures")
        elif "begin" in grammar and "end" in grammar:
            self.begin = self.compile_regex(grammar["begin"])
            self.end = self.compile_regex(grammar["end"])
            self.beginCaptures = self.__init_captures(grammar, key="beginCaptures")
            self.endCaptures = self.__init_captures(grammar, key="endCaptures")
        if "patterns" in grammar:
            self.patterns = [self.set_parser(pattern) for pattern in grammar["patterns"]]

    def __init_captures(self, grammar: dict, key: str = "captures"):
        if key in grammar:
            indices = [int(key) for key in grammar[key].keys()]
            values = list(grammar[key].values())

            if indices == [0]:
                captures = [self.set_parser(values[0])]
            else:
                captures = [None] * max(indices)
                for ind, val in zip(indices, values):
                    captures[ind - 1] = self.set_parser(val)
        else:
            captures = []
        return captures

    def __call__(self, *args, **kwargs):
        return self.parse(*args, **kwargs)

    def __repr__(self) -> str:
        repr = f"{self.__class__.__name__}:"
        if self.token or self.key:
            repr += self.token if self.token else f"<{self.key}>"
        else:
            repr += "PATTERN"
        return repr

    def set_parser(self, grammar: dict, **kwargs):
        if "include" in grammar:
            if grammar["include"] == "$self":
                return self
            else:
                return grammar["include"][1:]
        else:
            return GrammarParser(grammar, **kwargs)

    @classmethod
    def get_parser(cls, callId: Union[str, "GrammarParser"]):
        if isinstance(callId, str):
            if callId in cls.PARSERSTORE:
                callId = cls.PARSERSTORE[callId]
            else:
                raise IncludedParserNotFound(callId)
        return callId

    @classmethod
    def compile_regex(cls, string: str):
        for orig, repl in cls.regex_replacements.items():
            string = string.replace(orig, repl)
        return re.compile(string)

    @staticmethod
    def stream_end_pos(stream: StringIO) -> int:
        pos = stream.tell()
        endPos = stream.seek(0, SEEK_END)
        stream.seek(pos)
        return endPos

    @staticmethod
    def stream_read_pos(stream: StringIO, start: int, end: int) -> str:
        stream.seek(start)
        content = stream.read(end - start)
        stream.seek(end)
        return content

    def parse(
        self, stream: StringIO, startEnd: Optional[Tuple[int, int]] = None, **kwargs
    ) -> Tuple[bool, CONTENT_TYPE]:
        if self.match:
            (parsed, elements, _) = self.search(self.match, stream, parsers=self.captures, **kwargs)
            if parsed:
                elements = [ParsedElement(token=self.token, content=elements)]
            else:
                return False, [""]

        elif self.begin and self.end:
            # Find begin
            (beginMatched, beginElements, _) = self.search(
                self.begin, stream, parsers=self.beginCaptures, **kwargs
            )
            if not beginMatched:
                return False, [""]
            midStartPos = stream.tell()

            # Find end
            (endMatched, endElements, midEndPos) = self.search(
                self.end,
                stream,
                parsers=self.endCaptures,
                endSearch=True,
                **kwargs,
            )
            endStartPos = stream.tell()
            if not endMatched:
                return False, [""]

            if startEnd and startEnd == (midStartPos, midEndPos):
                return True, [self.stream_read_pos(stream, midStartPos, midEndPos)]
                # raise Warning("Recursion detected")

            elif self.patterns:
                # Search for pattens between begin and end
                midElements = []
                parsers = [self.get_parser(callId) for callId in self.patterns]
                stream.seek(midStartPos)

                while stream.tell() != midEndPos:
                    for parser in parsers:
                        midMatched, elements = parser.parse(
                            stream, startEnd=(midStartPos, midEndPos), **kwargs
                        )
                        if midMatched:
                            midElements += elements
                            break
                    else:
                        return False, [""]
            else:
                # Search for end and all in between is content
                midElements = [
                    ParsedElement(
                        token=self.token, content=self.stream_read_pos(stream, midStartPos, midEndPos)
                    )
                ]
            stream.seek(endStartPos)

            if self.contentToken:
                if len(midElements) == 1:
                    elements = [ParsedElement(token=self.contentToken, content=midElements[0].content)]
                else:
                    elements = [
                        ParsedElementBlock(
                            token=self.contentToken, begin=beginElements, end=endElements, content=midElements
                        )
                    ]
            elif self.token:
                elements = [
                    ParsedElementBlock(
                        token=self.token, begin=beginElements, end=endElements, content=midElements
                    )
                ]
            else:
                elements = midElements

        elif self.patterns:
            elements = []
            parsers = [self.get_parser(callId) for callId in self.patterns]
            endPos = self.stream_end_pos(stream)

            while stream.tell() != endPos:
                for parser in parsers:
                    patternMatched, patternElements = parser.parse(stream, **kwargs)
                    if patternMatched:
                        elements += patternElements
                        break
                else:
                    break

            if elements:
                if self.token:
                    elements = [ParsedElement(token=self.token, content=elements)]
            else:
                elements = [""]
        else:
            content = stream.read()
            if "\n" in content:
                raise Exception("Something has gone wrong")
            elements = [ParsedElement(token=self.token, content=content)]

        return True, elements

    def search(
        self,
        regex: re.Pattern,
        stream: StringIO,
        parsers: List["GrammarParser"] = [],
        endSearch: bool = False,
        **kwargs,
    ) -> Tuple[bool, CONTENT_TYPE, Optional[int]]:
        """Matches the stream against a capture group.

        The stream is matched against the input pattern. If there are any capture groups,
        each is then subsequently parsed by the inputted parsers. The number of parsers therefor
        must match the number of capture groups of the expression, or there must be a single parser
        and no capture groups.
        """
        if not ((regex.groups == 0 and len(parsers) == 1) or (regex.groups == len(parsers))):
            raise RegexGroupsMismatch

        initPos = stream.tell()
        lineSearch = True

        if regex.pattern[:3] == "(?<":
            lookback = 1
            while lookback <= self.regex_max_lookback and (initPos - lookback) >= 0:
                stream.seek(initPos - lookback)
                string, lineSearch = stream.read(), False
                matching = regex.search(string)
                if matching:
                    break
                else:
                    lookback += 1
                    stream.seek(initPos)
            else:
                stream.seek(initPos)
                return False, [""], None
        else:
            lookback = 0
            string = stream.readline()
            matching = regex.search(string)
            if not matching:
                stream.seek(initPos)
                string, lineSearch = stream.read(), False
                matching = regex.search(string)
                if not matching:
                    stream.seek(initPos)
                    return False, [""], None

        matchStartIdx, matchEndIdx = matching.start(), matching.end()

        if not endSearch and any(char != " " for char in string[lookback:matchStartIdx]):
            stream.seek(initPos)
            return False, [""], None

        matchingString = string[matchStartIdx:matchEndIdx]

        if (regex.groups == len(parsers)) and parsers:
            elements = []
            for parser, group in zip(parsers, matching.groups("")):
                substream = StringIO(group)
                groupMatched, parsed_elements = parser.parse(substream)
                if not groupMatched or substream.read() != "":
                    stream.seek(initPos)
                    return False, [""], None
                elements += parsed_elements
            if not elements:
                elements = [""]
        elif regex.groups == 0 and len(parsers) == 1:
            elements = [ParsedElement(token=parsers[0].token, content=matchingString)]
        else:
            elements = matchingString

        startPos, endPos = matchStartIdx - lookback, matchEndIdx - lookback
        if lineSearch:
            startPos += initPos
            endPos += initPos

        if len(string) > matchEndIdx and string[matchEndIdx] == "\n":
            endPos += 1
        stream.seek(endPos)
        return True, elements, startPos


# %%
