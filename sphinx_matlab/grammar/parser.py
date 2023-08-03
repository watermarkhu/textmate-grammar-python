# %%
from .exceptions import IncludedParserNotFound, CannotCloseEnd, RegexGroupsMismatch
from .elements import ParsedElement, ParsedElementBlock, CONTENT_TYPE
from typing import Tuple, Dict, Union, Optional
from io import StringIO, SEEK_END
import regex as re


class GrammarParser(object):
    PARSERSTORE = {}
    regex_lookback_max = 100
    regex_lookback_step = 5
    regex_replacements = {"\\\\": "\\"}

    def __init__(self, grammar: dict, key: str = "", **kwargs) -> None:
        self.grammar = grammar
        self.key = key
        self.token = grammar.get("name", "")
        self.contentToken = grammar.get("contentName", "")
        self.comment = grammar.get("comment", "")
        self.match, self.begin, self.end = None, None, None
        self.captures, self.beginCaptures, self.endCaptures = {}, {}, {}
        self.patterns = []
        self.matchedPos = []

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
            self.patterns = [
                self.set_parser(pattern) for pattern in grammar["patterns"]
            ]

    def __init_captures(self, grammar: dict, key: str = "captures") -> dict:
        captures = {}
        if key in grammar:
            for groupId, pattern in grammar[key].items():
                captures[int(groupId)] = self.set_parser(pattern)
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
        closePos = stream.seek(0, SEEK_END)
        stream.seek(pos)
        return closePos

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
            (parsed, elements, _) = self.search(
                self.match, stream, parsers=self.captures, **kwargs
            )
            if parsed:
                elements = [ParsedElement(token=self.token, content=elements)]
            else:
                return False, [""]

        elif self.begin and self.end:
            # Find begin
            (beginMatched, beginElements, _) = self.search(
                self.begin,
                stream,
                parsers=self.beginCaptures,
                readSize=startEnd[1] - startEnd[0] + 1 if startEnd else -1,
                **kwargs,
            )
            if not beginMatched:
                return False, [""]
            midStartPos = stream.tell()

            # Find end
            (endMatched, endElements, midClosePos) = self.search(
                self.end,
                stream,
                parsers=self.endCaptures,
                readSize=startEnd[1] - midStartPos + 1 if startEnd else -1,
                **kwargs,
            )
            endStartPos = stream.tell()
            if not endMatched:
                return False, [""]

            if startEnd and startEnd == (midStartPos, midClosePos):
                return True, [self.stream_read_pos(stream, midStartPos, midClosePos)]
                # raise Warning("Recursion detected")

            elif self.patterns:
                # Search for pattens between begin and end
                midElements = []
                parsers = [self.get_parser(callId) for callId in self.patterns]
                stream.seek(midStartPos)
                patternStartPos = midStartPos

                while stream.tell() < midClosePos:
                    for parser in parsers:
                        midMatched, elements = parser.parse(
                            stream, startEnd=(patternStartPos, midClosePos), **kwargs
                        )
                        if midMatched:
                            patternStartPos = stream.tell()
                            midElements += elements
                            break
                    else:
                        return False, [""]
            else:
                # Search for end and all in between is content
                midElements = [
                    ParsedElement(
                        token=self.token,
                        content=self.stream_read_pos(stream, midStartPos, midClosePos),
                    )
                ]
            stream.seek(endStartPos)

            if self.contentToken:
                if len(midElements) == 1:
                    elements = [
                        ParsedElement(
                            token=self.contentToken, content=midElements[0].content
                        )
                    ]
                else:
                    elements = [
                        ParsedElementBlock(
                            token=self.contentToken,
                            begin=beginElements,
                            end=endElements,
                            content=midElements,
                        )
                    ]
            elif self.token:
                elements = [
                    ParsedElementBlock(
                        token=self.token,
                        begin=beginElements,
                        end=endElements,
                        content=midElements,
                    )
                ]
            else:
                elements = midElements

        elif self.patterns:
            elements = []
            parsers = [self.get_parser(callId) for callId in self.patterns]
            closePos = self.stream_end_pos(stream)

            while stream.tell() != closePos:
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
                return False, [""]
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
        parsers: Dict[int, "GrammarParser"] = [],
        readSize: Optional[int] = None,
        **kwargs,
    ) -> Tuple[bool, CONTENT_TYPE, Optional[int]]:
        """Matches the stream against a capture group.

        The stream is matched against the input pattern. If there are any capture groups,
        each is then subsequently parsed by the inputted parsers. The number of parsers therefor
        must match the number of capture groups of the expression, or there must be a single parser
        and no capture groups.
        """

        initPos = stream.tell()
        lookback, streamCanLookback = 0, True
        performLookback = "(?<" in regex.pattern

        while lookback <= self.regex_lookback_max and streamCanLookback:
            if (initPos - lookback) < 0:
                lookback, streamCanLookback = initPos, False
            if not performLookback:
                streamCanLookback = False

            if readSize:
                linePos = 0
                stream.seek(initPos - lookback)
                lines = [
                    line + "\n" for line in stream.read(readSize + lookback).split("\n")
                ]  # Add newline as tmlanguage expects it.
                for lineNumber, line in enumerate(lines):
                    matching = regex.search(line)
                    if matching:
                        break  # Find first match encountered per line
                    linePos += len(line)
                else:
                    stream.seek(initPos)
                    lookback += self.regex_lookback_step
                    continue
                startPos = linePos + initPos - lookback + matching.start()
                closePos = linePos + initPos - lookback + matching.end()
                if matching.end() == len(line) and lineNumber < (len(lines) - 1):
                    closePos += 1  # Let closePos not land on newline character
            else:
                stream.seek(initPos - lookback)
                line = stream.readline()
                matching = regex.search(line)
                if not matching or any(
                    char != " " for char in line[: matching.start()]
                ):  # If not matching or leading characters are not whitespace
                    stream.seek(initPos)
                    lookback += self.regex_lookback_step
                    continue
                startPos = matching.start() + initPos + lookback
                closePos = matching.end() + initPos + lookback
                if matching.end() < len(line) and line[matching.end()] == "\n":
                    closePos += 1  # Let closePos not land on newline character

            if matching is not None:
                break
        else:
            return False, [""], None
        
        if any(startPos in range(ms+1, me-1) for (ms, me) in self.matchedPos):
            # Matching start position is already in a matching
            stream.seek(initPos)
            return  False, [""], None

        stream.seek(startPos)
        matchedString = stream.read(closePos - startPos)

        # Parse each capture group
        if (regex.groups != 0) and parsers:
            elements = []
            for groupId, group in enumerate(matching.groups("")):
                # Create new stream since group must match fully
                if groupId in parsers:
                    parser = parsers[groupId]
                else:
                    continue
                substream = StringIO(group)
                groupMatched, parsed_elements = parser.parse(substream)
                if not groupMatched or substream.read() != "":
                    stream.seek(initPos)
                    return False, [""], None
                elements += parsed_elements
            if not elements:
                elements = [""]
        # No groups, but a parser existed. Use token of parser to create element
        elif regex.groups == 0 and len(parsers) == 1:
            elements = [ParsedElement(token=parsers[0].token, content=matchedString)]
        # No parsers
        else:
            elements = matchedString

        self.matchedPos.append((startPos, closePos))
        stream.seek(closePos)
        return True, elements, startPos
