from typing import List, Tuple, Optional, TYPE_CHECKING
from io import TextIOBase
from abc import ABC, abstractmethod
import onigurumacffi as re
from .exceptions import IncludedParserNotFound, CannotCloseEnd
from .elements import ContentElement, ContentBlockElement
from .stream import stream_read_pos, search_stream

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
    ) -> Tuple[bool, List[ContentElement]]:
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
            return False, [], None

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
        find_one: bool = True,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        init_pos = stream.tell()
        if boundary is None:
            boundary = stream.seek(0, 2)
            stream.seek(init_pos)

        elements = []

        while stream.tell() <= boundary:
            for parser in self.patterns:
                parsed, candidate_elements, candidate_span = parser.parse(stream, boundary=boundary, **kwargs)
                if parsed:
                    if find_one:
                        return True, candidate_elements, candidate_span
                    elements.extend(candidate_elements)
                    break
            else:
                break

        return parsed, elements, (init_pos, stream.tell())


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
            return False, [], None

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
                    if candidate_mid_span[1] == end_span[1]:
                        if end_span[0] == end_span[1]:
                            mid_elements.extend(candidate_mid_elements)
                            close = end_span[0] if self.between_content else end_span[1]
                            end_elements = candidate_end_elements
                            break
                        elif not self.apply_end_pattern_last:
                            close = end_span[0] if self.between_content else end_span[1]
                            end_elements = candidate_end_elements
                            break
                        else:
                            mid_elements.extend(candidate_mid_elements)
                            init_pos = candidate_mid_span[1]
                    elif candidate_mid_span[0] > end_span[1]:
                        close = end_span[0] if self.between_content else end_span[1]
                        end_elements = candidate_end_elements
                        break
                    else:
                        mid_elements.extend(candidate_mid_elements)
                        init_pos = candidate_mid_span[1]
                else:
                    close = end_span[0] if self.between_content else end_span[1]
                    end_elements = candidate_end_elements
                    break
            else:
                if parsed:
                    mid_elements.extend(candidate_mid_elements)
                    init_pos = candidate_mid_span[1]
                else:
                    stream.readline()
                    init_pos = stream.tell()
        else:
            close = boundary

        start = begin_span[1] if self.between_content else begin_span[0]

        if self.token:
            elements = [
                ContentBlockElement(
                    token=self.token,
                    grammar=self.grammar,
                    content=stream_read_pos(stream, start, close),
                    span=(start, close),
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
    ) -> Tuple[bool, List[ContentElement]]:
        pass


# class GrammarParser(object):
#     "The parser object for a single TMLanguage grammar scope."

#     def __init__(self, grammar: dict, key: str = "", language: Optional["LanguageParser"] = None, **kwargs) -> None:
#         self.grammar = grammar
#         self.language = language
#         self.key = key
#         self.token = grammar.get("name", "")
#         self.content_token = grammar.get("contentName", "")
#         self.comment = grammar.get("comment", "")
#         self.exp_match, self.exp_begin, self.exp_end = None, None, None
#         self.captures, self.captures_begin, self.captures_end = {}, {}, {}
#         self.patterns = []
#         self.last_parse = None

#         if "match" in grammar:
#             self.exp_match = re.compile(grammar["match"])
#             self.captures = self._init_captures(grammar, key="captures")
#         elif "begin" in grammar and "end" in grammar:
#             self.exp_begin = re.compile(grammar["begin"])
#             self.exp_end = re.compile(grammar["end"])
#             self.captures_begin = self._init_captures(grammar, key="beginCaptures")
#             self.captures_end = self._init_captures(grammar, key="endCaptures")
#         if "patterns" in grammar:
#             self.patterns = [self._set_parser(pattern) for pattern in grammar["patterns"]]

#     def __call__(self, *args, **kwargs):
#         return self.parse(*args, **kwargs)

#     def __repr__(self) -> str:
#         repr = f"{self.__class__.__name__}:"
#         if self.token or self.key:
#             repr += self.token if self.token else f"<{self.key}>"
#         else:
#             repr += "PATTERN"
#         return repr

#     def _init_captures(self, grammar: dict, key: str = "captures") -> dict:
#         captures = {}
#         if key in grammar:
#             for group_id, pattern in grammar[key].items():
#                 captures[int(group_id)] = self._set_parser(pattern)
#         return captures

#     def _set_parser(self, grammar: dict, **kwargs):
#         "Sets the parser based on the grammar. If $self then the language grammar is used."
#         if "include" in grammar:
#             return grammar["include"]
#         else:
#             return GrammarParser(grammar, language=self.language, **kwargs)

#     @classmethod
#     def get_parser(cls, call_id: Union[str, "GrammarParser"]):
#         "Gets the parser from the PARSERSTORE, updates the call_id with the parser itself in the store."
#         if isinstance(call_id, str):
#             if call_id in cls.PARSERSTORE:
#                 call_id = cls.PARSERSTORE[call_id]
#             else:
#                 raise IncludedParserNotFound(call_id)
#         return call_id

#     def parse(
#         self,
#         stream: TextIOBase,
#         start_pos: int = 0,
#         close_pos: Optional[int] = None,
#         **kwargs,
#     ) -> List[ContentElement]:
#         """Parse the input stream using the current parser."""
#         if close_pos:
#             if start_pos >= close_pos:
#                 return []
#         else:
#             close_pos = len(stream.getvalue())

#         stream.seek(start_pos)

#         if self.exp_match:
#             captures, span = search_stream(
#                 self.exp_match,
#                 stream,
#                 parsers=self.captures,
#                 start_pos=start_pos,
#                 close_pos=close_pos,
#                 **kwargs,
#             )
#             if span is None:
#                 return []
#             content = stream_read_pos(stream, span[0], span[1])
#             elements = [
#                 ContentElement(
#                     token=self.token,
#                     grammar=self.grammar,
#                     content=content,
#                     span=span,
#                     captures=captures,
#                 )
#             ]

#         elif self.exp_begin and self.exp_end:
#             # Find begin
#             captured_begin, begin_span = search_stream(
#                 self.exp_begin,
#                 stream,
#                 parsers=self.captures_begin,
#                 start_pos=start_pos,
#                 close_pos=close_pos,
#                 **kwargs,
#             )
#             if begin_span is None:
#                 return []
#             (begin_start, begin_close) = begin_span
#             if close_pos and begin_close > close_pos:
#                 return []

#             pattern_result = self.parse_patterns(
#                 stream,
#                 start_pos=begin_close,
#                 close_pos=close_pos,
#                 **kwargs,
#             )
#             if not pattern_result:
#                 return []
#             captured_elements, captured_end, (end_start, end_close) = pattern_result

#             token = self.content_token if self.content_token else self.token
#             start, close = (begin_close, end_start) if self.content_token else (begin_start, end_close)

#             elements = [
#                 ContentBlockElement(
#                     token=token,
#                     grammar=self.grammar,
#                     content=stream_read_pos(stream, start, close),
#                     span=(start, close),
#                     captures=captured_elements,
#                     begin=captured_begin,
#                     end=captured_end,
#                 )
#             ]

#         elif self.patterns:
#             captured_elements, _, _ = self.parse_patterns(
#                 stream,
#                 start_pos=start_pos,
#                 close_pos=close_pos,
#                 **kwargs,
#             )

#             if captured_elements:
#                 if isinstance(self, LanguageParser) or not self.token:
#                     elements = captured_elements
#                 else:
#                     content = stream_read_pos(stream, start_pos, close_pos)
#                     elements = [
#                         ContentElement(
#                             token=self.token,
#                             grammar=self.grammar,
#                             content=content,
#                             span=(start_pos, close_pos),
#                             captures=captured_elements,
#                         )
#                     ]

#             else:
#                 return []

#         else:
#             if close_pos is not None:
#                 content = stream_read_pos(stream, start_pos, close_pos)
#                 elements = [
#                     ContentElement(
#                         token=self.token,
#                         grammar=self.grammar,
#                         content=content,
#                         span=(start_pos, close_pos),
#                     )
#                 ]
#             else:
#                 raise CannotCloseEnd(stream.read())

#         return elements

# def parse_patterns(
#     self,
#     stream,
#     start_pos: int,
#     close_pos: int,
#     **kwargs,
# ):
#     "Parse a number of patterns"
#     # get parsers and create lookup store
#     if start_pos >= close_pos:
#         return None

#     parsers = [self.get_parser(call_id) for call_id in self.patterns]
#     elements_on_pos = defaultdict(list)
#     elements_per_parser = defaultdict(dict)
#     captured_elements, captured_end = [], []
#     pattern_start = start_pos
#     end_start, end_close, next_newline_pos = -1, -1, -1

#     while pattern_start < close_pos:
#         # keep doing until closing position is reached

#         if self.exp_end:

#             if (end_start == end_close and pattern_start > end_start) or (
#                 end_start != end_close and pattern_start >= end_start
#             ):
#                 # search for end when necessary
#                 captured_end, end_span = search_stream(
#                     self.exp_end,
#                     stream,
#                     parsers=self.captures_end,
#                     start_pos=pattern_start,
#                     **kwargs,
#                 )
#                 if end_span is None:
#                     return None
#                 (end_start, end_close) = end_span
#                 # parsers = [self.get_parser(call_id) for call_id in self.patterns]

#         if pattern_start > next_newline_pos:
#             next_newline_pos = stream_endline_pos(stream, pattern_start)

#         # Clear positional elements store for passed positions
#         passed_pos = [pos for pos in elements_on_pos.keys() if pos < pattern_start]
#         for pos in passed_pos:
#             elements_on_pos.pop(pos)

#         # invalid_parsers = []
#         for parser in parsers:
#             # Loop over parsers
#             parser_elements = elements_per_parser[parser]

#             # Clear poisitional element store per parser for passed positions
#             passed_pos = [pos for pos in parser_elements.keys() if pos < pattern_start]
#             for pos in passed_pos:
#                 parser_elements.pop(pos)

#             if not parser_elements:
#                 # Perform search of none in element store of parser
#                 elements = parser.parse(
#                     stream,
#                     start_pos=pattern_start,
#                     close_pos=end_close if self.exp_end else next_newline_pos,
#                     **kwargs,
#                 )
#                 for element in elements:
#                     # Add found elements to element stores
#                     elements_on_pos[element.span[0]].append(element)
#                     parser_elements[element.span[0]] = element

#                 # if not elements:
#                 #     # None found, this parser is invalid (for the current search scope)
#                 #     invalid_parsers.append(parser)

#         # No more elements current or future positions within current scope
#         element_on_pos_final_pos = end_start if self.exp_end else close_pos
#         if not any((pos <= element_on_pos_final_pos for pos in elements_on_pos.keys())):
#             break

#         # for parser in invalid_parsers:
#         #     # Remove parser from list for the current scope
#         #     parsers.remove(parser)

#         if pattern_start in elements_on_pos:
#             # Use the element from the current position
#             elements = elements_on_pos.pop(pattern_start)
#             element = sorted(elements, key=lambda element: element.span[1], reverse=True)[0]
#             captured_elements.append(element)
#             # Get the next pattern search starting position from the element
#             if isinstance(element, ContentBlockElement) and element.exp_end:
#                 pattern_start = element.exp_end[-1].span[1]
#             else:
#                 pattern_start = element.span[1]
#         else:
#             # Get the next pattern search starting position from the element store
#             next_element_start = min(elements_on_pos.keys())
#             if next_element_start <= element_on_pos_final_pos:
#                 pattern_start = next_element_start
#             else:
#                 break

#     return (captured_elements, captured_end, end_span) if self.exp_end else (captured_elements, None, None)
