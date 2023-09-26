from typing import List, Tuple, Optional, TYPE_CHECKING
from io import TextIOBase
from abc import ABC, abstractmethod
from warnings import warn
import onigurumacffi as re
from .exceptions import IncludedParserNotFound, CannotCloseEnd
from .elements import ContentElement, ContentBlockElement
from .stream import stream_read_pos, stream_read_length, search_stream

if TYPE_CHECKING:
    from .language import LanguageParser


def init_parser(grammar: dict, **kwargs):
    "Initializes the parser based on the grammar."
    if "include" in grammar:
        return grammar["include"]
    elif "match" in grammar:
        return MatchParser(grammar, **kwargs)
    elif "begin" in grammar and "end" in grammar:
        return BeginEndParser(grammar, **kwargs)
    elif "begin" in grammar and "while" in grammar:
        return BeginWhileParser(grammar, **kwargs)
    elif "patterns" in grammar:
        return PatternsParser(grammar, **kwargs)
    else:
        return TokenParser(grammar, **kwargs)


class GrammarParser(ABC):
    def __init__(self, grammar: dict, language: Optional["LanguageParser"] = None, key: str = "") -> None:
        self.grammar = grammar
        self.language = language
        self.key = key
        self.comment = grammar.get("comment", "")
        self.disabled = grammar.get("disabled", False)
        self.initialized = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:<{self.key}>"

    def _init_captures(self, grammar: dict, key: str = "captures") -> dict:
        """Initializes a captures dictionary"""
        captures = {}
        if key in grammar:
            for group_id, pattern in grammar[key].items():
                captures[int(group_id)] = init_parser(pattern, language=self.language)
        return captures

    def _find_include(self, key: str, **kwargs):
        if not self.language:
            raise IncludedParserNotFound(key)

        if key in ["$self", "$base"]:
            return self.language
        elif key[0] == "#":
            return self.language.repository.get(key[1:], None)
        else:
            return self.language._find_include_scopes(key)

    @abstractmethod
    def initialize_repository(self):
        pass

    @abstractmethod
    def parse(
        self,
        stream: TextIOBase,
        boundary: Optional[int] = None,
        anchor: Optional[int] = None,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        pass


class TokenParser(GrammarParser):
    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.token = grammar["name"]
        self.initialized = True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.token}"

    def initialize_repository(self):
        pass

    def parse(
        self,
        stream: TextIOBase,
        boundary: Optional[int],
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        init_pos = stream.tell()
        span = (init_pos, boundary)
        content = stream_read_pos(stream, init_pos, boundary)
        elements = [
            ContentElement(
                token=self.token,
                grammar=self.grammar,
                content=content,
                span=span,
            )
        ]
        stream.seek(boundary)
        return True, elements, span


class MatchParser(GrammarParser):
    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.exp_match = re.compile(grammar["match"])
        self.captures = self._init_captures(grammar, key="captures")
        self.token = grammar.get("name", None)

    def __repr__(self) -> str:
        if self.token:
            return f"{self.__class__.__name__}:{self.token}"
        else:
            identifier = self.key if self.key else "_".join(self.comment.lower().split(" "))
            return f"{self.__class__.__name__}:<{identifier}>"

    def initialize_repository(self):
        self.initialized = True
        for key, value in self.captures.items():
            if not isinstance(value, GrammarParser):
                self.captures[key] = self._find_include(value)
        for parser in self.captures.values():
            if not parser.initialized:
                parser.initialize_repository()

    def parse(
        self,
        stream: TextIOBase,
        boundary: Optional[int] = None,
        anchor: Optional[int] = None,
        ws_only: bool = True,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        span, captures = search_stream(stream, self.exp_match, self.captures, boundary, anchor=anchor, ws_only=ws_only)
        if span is None:
            return False, [], (0, 0)

        if self.token:
            content = stream_read_pos(stream, span[0], span[1])
            elements = [
                ContentElement(
                    token=self.token,
                    grammar=self.grammar,
                    content=content,
                    span=span,
                    captures=captures,
                )
            ]
        else:
            elements = captures

        stream.seek(span[1])

        return True, elements, span


class PatternsParser(GrammarParser):
    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.patterns = [init_parser(pattern, language=self.language) for pattern in grammar.get("patterns", [])]

    def initialize_repository(self):
        self.initialized = True
        self.patterns = [
            parser if isinstance(parser, GrammarParser) else self._find_include(parser) for parser in self.patterns
        ]
        for parser in self.patterns:
            if not parser.initialized:
                parser.initialize_repository()

        pattern_parsers = [parser for parser in self.patterns if type(parser) == PatternsParser]
        for parser in pattern_parsers:
            parser_index = self.patterns.index(parser)
            self.patterns[parser_index : parser_index + 1] = parser.patterns

    def parse(
        self,
        stream: TextIOBase,
        boundary: Optional[int] = None,
        ws_only: bool = True,
        find_one: bool = True,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        init_pos = stream.tell()
        if boundary is None:
            boundary = stream.seek(0, 2)
            stream.seek(init_pos)

        parsed, elements = False, []
        current_pos = init_pos
        while current_pos <= boundary:
            for parser in self.patterns:
                parsed, candidate_elements, span = parser.parse(stream, boundary=boundary, ws_only=ws_only, **kwargs)
                if parsed:
                    if find_one:
                        return True, candidate_elements, span
                    elements.extend(candidate_elements)
                    break
            else:
                for parser in self.patterns:
                    parsed, candidate_elements, span = parser.parse(stream, boundary=boundary, ws_only=False, **kwargs)
                    if parsed:
                        if find_one:
                            return True, candidate_elements, span
                        elements.extend(candidate_elements)
                        break
                else:
                    break
            if stream.tell() == current_pos:
                warn("Recursing detected, exiting...")
                break
            current_pos = stream.tell()

        close_pos = stream.tell()
        return parsed, elements, (init_pos, close_pos)


class BeginEndParser(PatternsParser):
    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        if "contentName" in grammar:
            self.token = grammar["contentName"]
            self.between_content = True
        else:
            self.token = grammar.get("name", None)
            self.between_content = False
        self.apply_end_pattern_last = grammar.get("applyEndPatternLast", False)
        self.exp_begin = re.compile(grammar["begin"])
        self.exp_end = re.compile(grammar["end"])
        self.captures_begin = self._init_captures(grammar, key="beginCaptures")
        self.captures_end = self._init_captures(grammar, key="endCaptures")

    def __repr__(self) -> str:
        if self.token:
            return f"{self.__class__.__name__}:{self.token}"
        else:
            identifier = self.key if self.key else "_".join(self.comment.lower().split(" "))
            return f"{self.__class__.__name__}:<{identifier}>"

    def initialize_repository(self):
        self.initialized = True
        super().initialize_repository()
        for key, value in self.captures_end.items():
            if not isinstance(value, GrammarParser):
                self.captures_end[key] = self._find_include(value)
        for key, value in self.captures_begin.items():
            if not isinstance(value, GrammarParser):
                self.captures_begin[key] = self._find_include(value)
        for parser in self.captures_begin.values():
            if not parser.initialized:
                parser.initialize_repository()
        for parser in self.captures_end.values():
            if not parser.initialized:
                parser.initialize_repository()

    def parse(
        self,
        stream: TextIOBase,
        boundary: Optional[int] = None,
        anchor: Optional[int] = None,
        ws_only: bool = True,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        begin_span, begin_elements = search_stream(
            stream, self.exp_begin, self.captures_begin, boundary, anchor=anchor, ws_only=ws_only
        )
        if not begin_span:
            return False, [], (0, 0)

        init_pos = stream.tell()
        if boundary is None:
            boundary = stream.seek(0, 2)
            stream.seek(init_pos)

        end_elements, mid_elements = [], []

        while stream.tell() <= boundary:
            stream.seek(init_pos)
            parsed = False
            for parser in self.patterns:
                parsed, candidate_mid_elements, candidate_mid_span = parser.parse(
                    stream, boundary=boundary, anchor=begin_span[1], ws_only=True, **kwargs
                )
                if parsed:
                    break
            stream.seek(init_pos)
            end_span, candidate_end_elements = search_stream(
                stream, self.exp_end, self.captures_end, boundary, ws_only=True
            )

            if not parsed and not end_span:
                for parser in self.patterns:
                    parsed, candidate_mid_elements, candidate_mid_span = parser.parse(
                        stream, boundary=boundary, anchor=begin_span[1], ws_only=False, **kwargs
                    )
                    if parsed:
                        break

                stream.seek(init_pos)
                end_span, candidate_end_elements = search_stream(
                    stream, self.exp_end, self.captures_end, boundary, ws_only=False
                )

            if end_span:
                if parsed:
                    if stream_read_length(stream, candidate_mid_span[1] - 1, 1) == "\n":
                        pattern_at_end = end_span[1] in [candidate_mid_span[1] - 1, candidate_mid_span[1]]
                    else:
                        pattern_at_end = end_span[1] == candidate_mid_span[1]

                    if pattern_at_end:
                        empty_span_end = end_span[1] == end_span[0]

                        if empty_span_end:
                            mid_elements.extend(candidate_mid_elements)
                            close_pos = end_span[0] if self.between_content else end_span[1]
                            end_elements = candidate_end_elements
                            break
                        elif not self.apply_end_pattern_last:
                            close_pos = end_span[0] if self.between_content else end_span[1]
                            end_elements = candidate_end_elements
                            break
                        else:
                            mid_elements.extend(candidate_mid_elements)
                            init_pos = candidate_mid_span[1]
                    elif candidate_mid_span[0] < end_span[1]:
                        mid_elements.extend(candidate_mid_elements)
                        init_pos = candidate_mid_span[1]
                    else:
                        close_pos = end_span[0] if self.between_content else end_span[1]
                        end_elements = candidate_end_elements
                        break
                else:
                    close_pos = end_span[0] if self.between_content else end_span[1]
                    end_elements = candidate_end_elements
                    break
            else:
                if parsed:
                    mid_elements.extend(candidate_mid_elements)
                    if stream_read_length(stream, candidate_mid_span[1] - 1, 1) == "\n":
                        init_pos = candidate_mid_span[1] - 1
                    else:
                        init_pos = candidate_mid_span[1]
                else:
                    stream.readline()
                    init_pos = stream.tell()
        else:
            close_pos = boundary

        start = begin_span[1] if self.between_content else begin_span[0]

        if self.token:
            elements = [
                ContentBlockElement(
                    token=self.token,
                    grammar=self.grammar,
                    content=stream_read_pos(stream, start, close_pos),
                    span=(start, close_pos),
                    captures=mid_elements,
                    begin=begin_elements,
                    end=end_elements,
                )
            ]
        else:
            elements = begin_elements + mid_elements + end_elements

        stream.seek(end_span[1])

        return True, elements, (begin_span[0], end_span[1])


class BeginWhileParser(PatternsParser):
    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        if "contentName" in grammar:
            self.token = grammar["contentName"]
            self.between_content = True
        else:
            self.token = grammar.get("name", None)
            self.between_content = False
        self.exp_begin = re.compile(grammar["begin"])
        self.exp_while = re.compile(grammar["while"])
        self.captures_begin = self._init_captures(grammar, key="beginCaptures")
        self.captures_while = self._init_captures(grammar, key="whileCaptures")

    def __repr__(self) -> str:
        if self.token:
            return f"{self.__class__.__name__}:{self.token}"
        else:
            identifier = self.key if self.key else "_".join(self.comment.lower().split(" "))
            return f"{self.__class__.__name__}:<{identifier}>"

    def initialize_repository(self):
        self.initialized = True
        super().initialize_repository()
        for key, value in self.captures_end.items():
            if not isinstance(value, GrammarParser):
                self.captures_end[key] = self._find_include(value)
        for key, value in self.captures_while.items():
            if not isinstance(value, GrammarParser):
                self.captures_while[key] = self._find_include(value)
        for parser in self.captures_begin.values():
            if not parser.initialized:
                parser.initialize_repository()
        for parser in self.captures_while.values():
            if not parser.initialized:
                parser.initialize_repository()

    def parse(
        self,
        stream: TextIOBase,
        *args,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        pass
