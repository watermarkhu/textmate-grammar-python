# %%
from exceptions import IncludedParserNotFound
from elements import ParsedElementBase, ParsedElement, ParsedElementBlock
from typing import Tuple, List
import re


PARSERSTORE = {}


class ParserBase(object):
    pass


class Parser(object):
    def __new__(cls, grammar: dict, **kwargs):
        if "include" in grammar:
            return IncludeParser(grammar)
        else:
            return GrammarParser(grammar, **kwargs)


class IncludeParser(ParserBase):
    def __init__(self, grammar: dict) -> None:
        self.key = grammar["include"][1:]

    def __repr__(self) -> str:
        if self.key in PARSERSTORE:
            return PARSERSTORE[self.key].__repr__()
        else:
            return f"{self.__class__.__name__}:<{self.key}>"

    def __call__(self, *args, **kwargs):
        if self.key in PARSERSTORE:
            return PARSERSTORE[self.key].__call__(*args, **kwargs)
        else:
            raise IncludedParserNotFound(self.key)


class GrammarParser(ParserBase):
    PARSERSTORE = {}

    def __init__(self, grammar: dict, key: str = "") -> None:
        self.grammar = grammar
        self.key = key
        self.token = grammar.get("name", "")
        self.match, self.begin, self.end = None, None, None
        self.captures, self.beginCaptures, self.endCaptures = [], [], []
        self.patterns = []
        self.source = ""

        if key:
            PARSERSTORE[key] = self

        if "match" in grammar:
            self.match = self.compile_regex(grammar["match"])
            self.captures = self._init_captures(grammar, key="captures")
        elif "begin" in grammar and "end" in grammar:
            self.begin = self.compile_regex(grammar["begin"])
            self.end = self.compile_regex(grammar["end"])
            self.beginCaptures = self._init_captures(grammar, key="beginCaptures")
            self.endCaptures = self._init_captures(grammar, key="endCaptures")
        if "patterns" in grammar:
            self.patterns = [Parser(pattern) for pattern in grammar["patterns"]]

    def __repr__(self) -> str:
        repr = f"{self.__class__.__name__}:"
        if self.token or self.key:
            repr += self.token if self.token else f"<{self.key}>"
        else:
            repr += "PATTERN"
        return repr

    def __call__(self, source: str) -> Tuple[bool, str, List[ParsedElementBase]]:
        self.source = source

        if self.match:
            return self.match_captures(source, self.match, self.captures)

        elif self.begin and self.end:
            beginMatched, midSrc, beginElements = self.match_captures(
                source, self.begin, parsers=self.beginCaptures
            )
            if not beginMatched:
                return False, source, []

            midElements = []
            endMatched = False
            while not endMatched:
                for parser in self.patterns:
                    midMatched, ms, me = parser(midSrc)
                    if midMatched:
                        midSrc = ms
                        midElements += me
                        break

                endMatched, endSrc, endElements = self.match_captures(
                    midSrc, self.end, parsers=self.endCaptures
                )
                if not midMatched and not endMatched:
                    raise Exception("Could not close end.")

            return (
                True,
                endSrc,
                ParsedElementBlock(self.token, beginElements, endElements, midElements),
            )

        elif self.patterns:
            for parser in self.patterns:
                patternMatched, patternStr, patternElements = parser(source)
                if patternMatched:
                    return patternMatched, patternStr, patternElements
            else:
                return False, source, []

        return True, "", [ParsedElement(self.token, source)]

    @staticmethod
    def compile_regex(string: str):
        return re.compile(string.replace("\\\\", "\\"))

    @staticmethod
    def _init_captures(grammar: dict, key: str = "captures"):
        if key in grammar:
            indices = [int(key) for key in grammar[key].keys()]
            values = list(grammar[key].values())
            captures = [None] * max(indices)
            for ind, val in zip(indices, values):
                captures[ind - 1] = Parser(val)
        else:
            captures = []
        return captures

    @staticmethod
    def match_captures(
        source: str, regex: re.Pattern, parsers: List[ParserBase] = []
    ) -> str:
        if regex.groups != len(parsers):
            raise Exception("Number of groups do not match supplied regex.")

        matching = regex.match(source)
        if not matching or matching.start() != 0:
            return False, source, []

        if parsers:
            elements = [
                parsed[2][0]
                for parsed in [
                    parser(group) for parser, group in zip(parsers, matching.groups())
                ]
            ]
        else:
            elements = [ParsedElement("other", source[: matching.end()])]

        return True, source[matching.end() :], elements
