# %%
from exceptions import IncludedParserNotFound
from elements import ParsedElementBase, ParsedElement, ParsedElementBlock
from typing import Tuple, List
import re


PARSEROUTPUT = Tuple[bool, str, List[ParsedElementBase]]
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
    regex_replacements = {"\\\\": "\\", "\\G": ""}

    def __init__(self, grammar: dict, key: str = "") -> None:
        self.grammar = grammar
        self.key = key
        self.token = grammar.get("name", "")
        self.contentToken = grammar.get("contentName", "")
        self.comment = grammar.get("comment", "")
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

    def __call__(self, source: str) -> PARSEROUTPUT:
        self.source = source

        if self.match:
            matched, remainder, elements = self.match_captures(source, self.match, self.captures)
            if matched:
                return True, remainder, [ParsedElement(token=self.token, content=elements)]
            else:
                return False, source, []

        elif self.begin and self.end:
            beginMatched, midSrc, beginElements = self.match_captures(
                source, self.begin, parsers=self.beginCaptures
            )
            if not beginMatched:
                return False, source, []

            if self.patterns:
                # Search for pattens between begin and end
                midElements, endMatched = [], False
                while not endMatched:
                    midMatched = False
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

                begin, end, mid = beginElements, endElements, midElements
            else:
                # Search for end and all in between is content
                endMatched, endSrc, endElements = self.match_captures(
                    midSrc, self.end, parsers=self.endCaptures, useSearch=True
                )
                if not endMatched:
                    raise Exception("Could not close end.")
                begin, end, mid = beginElements, [], endElements

            if self.contentToken:
                if len(mid) == 1:
                    elements = [ParsedElement(token=self.contentToken, content=mid[0].content)]
                else:
                    elements = [
                        ParsedElementBlock(token=self.contentToken, begin=begin, end=end, content=mid)
                    ]
            elif self.token:
                elements = [ParsedElementBlock(token=self.token, begin=begin, end=end, content=mid)]
            else:
                elements = mid
            return (True, endSrc, elements)

        elif self.patterns:
            elements = []
            while True:
                for parser in self.patterns:
                    patternMatched, patternSrc, patternElements = parser(source)
                    if patternMatched:
                        source = patternSrc
                        elements += patternElements
                        break
                else:
                    break
            if elements:
                if self.token:
                    return True, patternSrc, [ParsedElement(token=self.token, content=elements)]
                else:
                    return True, patternSrc, elements
            else:
                return False, source, []

        if source:
            return True, "", [ParsedElement(token=self.token, content=source)]
        else:
            return True, "", []

    @staticmethod
    def compile_regex(string: str):
        for orig, repl in GrammarParser.regex_replacements.items():
            string = string.replace(orig, repl)

        return re.compile(string)

    @staticmethod
    def _init_captures(grammar: dict, key: str = "captures"):
        if key in grammar:
            indices = [int(key) for key in grammar[key].keys()]
            values = list(grammar[key].values())

            if indices == [0]:
                captures = [Parser(values[0])]
            else:
                captures = [None] * max(indices)
                for ind, val in zip(indices, values):
                    captures[ind - 1] = Parser(val)
        else:
            captures = []
        return captures

    @staticmethod
    def match_captures(
        source: str,
        regex: re.Pattern,
        parsers: List[ParserBase] = [],
        useSearch: bool = False,
    ) -> PARSEROUTPUT:
        if not (regex.groups == 0 and len(parsers) == 1) and regex.groups != len(parsers):
            raise Exception("Number of groups do not match supplied regex.")

        matching = regex.search(source) if useSearch else regex.match(source)

        if not matching:
            return False, source, []

        if regex.groups != 0 and parsers:
            elements = []
            for parser, group in zip(parsers, matching.groups()):
                _, _, parsed_elements = parser(group)
                elements += parsed_elements
        else:
            elements = source[: matching.end()]

        return True, source[matching.end() :], elements
