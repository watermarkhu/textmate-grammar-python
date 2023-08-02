# %%
from .exceptions import IncludedParserNotFound, CannotCloseEnd, RegexGroupsMismatch
from .elements import ParsedElementBase, ParsedElement, ParsedElementBlock
from typing import Tuple, List, Union
import re


PARSEROUTPUT = Tuple[bool, str, List[ParsedElementBase]]


class GrammarParser(object):
    PARSERSTORE = {}
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

        self.source, self.parentSource = "", ""
        self.sourceStrIdx = 0

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

    def parse(self, source: str, parentSource: str = "", **kwargs) -> PARSEROUTPUT:
        self.source = source
        self.parentSource = parentSource

        if self.match:
            matched, remainder, elements = self.match_captures(
                source, self.match, self.captures, **kwargs
            )
            if matched:
                return (
                    True,
                    remainder,
                    [ParsedElement(token=self.token, content=elements)],
                )
            else:
                return False, source, ""

        elif self.begin and self.end:
            beginMatched, midSrc, beginElements = self.match_captures(
                source, self.begin, parsers=self.beginCaptures, **kwargs
            )
            if not beginMatched:
                return False, source, ""

            if self.patterns:
                # Search for pattens between begin and end
                midElements, endMatched = [], False
                parsers = [self.get_parser(callId) for callId in self.patterns]
                while not endMatched:
                    midMatched = False
                    for parser in parsers:
                        midMatched, ms, me = parser.parse(midSrc, parentSource=source)
                        if midMatched:
                            midSrc = ms
                            midElements += me
                            break

                    if midMatched:
                        endMatched, endSrc, endElements = self.match_captures(
                            midSrc, self.end, parsers=self.endCaptures, **kwargs
                        )
                    else:
                        endMatched, endSrc, endElements = self.match_captures(
                            midSrc,
                            self.end,
                            parsers=self.endCaptures,
                            endSearch=True,
                            **kwargs,
                        )
                        if not endMatched:
                            return False, source, ""

                        midElements = [
                            ParsedElement(
                                token=self.token, content=midSrc[: -len(endSrc)]
                            )
                        ]

                begin, end, mid = beginElements, endElements, midElements
            else:
                # Search for end and all in between is content
                endMatched, endSrc, endElements = self.match_captures(
                    midSrc, self.end, parsers=self.endCaptures, endSearch=True, **kwargs
                )
                if not endMatched:
                    return False, source, ""
                
                midElements = [
                    ParsedElement(
                        token=self.token, content=midSrc[: -len(endSrc)]
                    )
                ]

                begin, end, mid = beginElements, midElements, endElements

            if self.contentToken:
                if len(mid) == 1:
                    elements = [
                        ParsedElement(token=self.contentToken, content=mid[0].content)
                    ]
                else:
                    elements = [
                        ParsedElementBlock(
                            token=self.contentToken, begin=begin, end=end, content=mid
                        )
                    ]
            elif self.token:
                elements = [
                    ParsedElementBlock(
                        token=self.token, begin=begin, end=end, content=mid
                    )
                ]
            else:
                elements = mid
            return (True, endSrc, elements)

        elif self.patterns:
            elements = []
            parsers = [self.get_parser(callId) for callId in self.patterns]
            while True:
                for parser in parsers:
                    patternMatched, patternSrc, patternElements = parser.parse(
                        source, parentSource=parentSource
                    )
                    if patternMatched:
                        source = patternSrc
                        elements += patternElements
                        break
                else:
                    break
            if elements:
                if self.token:
                    return (
                        True,
                        patternSrc,
                        [ParsedElement(token=self.token, content=elements)],
                    )
                else:
                    return True, patternSrc, elements
            else:
                return False, source, ""

        if source:
            return True, "", [ParsedElement(token=self.token, content=source)]
        else:
            return True, "", ""

    def match_captures(
        self,
        source: str,
        regex: re.Pattern,
        parsers: List["GrammarParser"] = [],
        endSearch: bool = False,
        fullMatch: bool = False,
        **kwargs,
    ) -> PARSEROUTPUT:
        """Matches the source string against a capture group.

        The source string is matched against the input pattern. If there are any capture groups,
        each is then subsequently parsed by the inputted parsers. The number of parsers therefor
        must match the number of capture groups of the expression, or there must be a single parser
        and no capture groups.
        """
        if not (
            (regex.groups == 0 and len(parsers) == 1) or (regex.groups == len(parsers))
        ):
            raise RegexGroupsMismatch

        if regex.pattern[:3] == "(?<":
            matching = regex.search(self.parentSource)
            if not matching:
                return False, source, ""

            parentIdx = len(self.parentSource) - len(source)
            matchStartIdx = matching.start() - parentIdx
            matchEndIdx = matching.end() - parentIdx
            if matchStartIdx < 0:
                raise Exception("FIX THIS")

            if fullMatch and (matchEndIdx - matchStartIdx) != len(source):
                return False, source, ""

        else:
            matching = regex.fullmatch(source) if fullMatch else regex.search(source)
            if not matching:
                return False, source, ""
            matchStartIdx = matching.start()
            matchEndIdx = matching.end()

            if not endSearch:
                source[:matchEndIdx]

        if (regex.groups == len(parsers)) and parsers:
            elements = []
            for parser, group in zip(parsers, matching.groups("")):
                groupMatched, _, parsed_elements = parser.parse(group, fullMatch=True)
                if not groupMatched:
                    return False, source, ""
                elements += parsed_elements
            if not elements:
                elements = ""
        elif regex.groups == 0 and len(parsers) == 1:
            elements = [
                ParsedElement(token=parsers[0].token, content=source[:matchEndIdx])
            ]
        else:
            elements = source[:matchEndIdx]

        self.sourceStrIdx += matchEndIdx

        return True, source[matchEndIdx:], elements


# %%
