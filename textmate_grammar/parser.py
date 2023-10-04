from typing import List, Tuple, Optional, TYPE_CHECKING
from io import TextIOBase
from abc import ABC, abstractmethod
import onigurumacffi as re
import logging

from .exceptions import IncludedParserNotFound
from .elements import ContentElement, ContentBlockElement
from .search import ANCHOR, search_stream
from .read import stream_read_length, stream_read_pos
from .logging import LOGGER

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

    """The abstract grammar parser object"""

    def __init__(self, grammar: dict, language: Optional["LanguageParser"] = None, key: str = "") -> None:
        self.grammar = grammar
        self.language = language
        self.key = key
        self.token = grammar.get("name", "")
        self.comment = grammar.get("comment", "")
        self.disabled = grammar.get("disabled", False)
        self.initialized = False
        self.anchored = False
        self.injected_patterns = []

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
        """Find the included grammars and during repository initialization"""
        if not self.language:
            raise IncludedParserNotFound(key)

        if key in ["$self", "$base"]:  # TODO there is a difference between these
            return self.language
        elif key[0] == "#":
            return self.language.repository.get(key[1:], None)
        else:
            return self.language._find_include_scopes(key)

    def initialize_repository(self):
        """When the grammar has patterns, this method should called to initialize its inclusions."""
        pass

    @abstractmethod
    def parse(
        self,
        stream: TextIOBase,
        boundary: Optional[int] = None,
        verbosity: int = 0,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        """The method to parse a stream using the current grammar."""
        pass


class TokenParser(GrammarParser):
    """The parser for grammars for which only the token is provided."""

    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.initialized = True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.token}"

    def parse(
        self,
        stream: TextIOBase,
        boundary: Optional[int],
        verbosity: int = 0,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        """The parse method for grammars for which only the token is provided.

        When no regex patterns are provided. The element is created between the initial and boundary positions.
        """
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
        ANCHOR.set(boundary)
        stream.seek(boundary)
        LOGGER.info(f"{self.__class__.__name__} found < {repr(content)} >", self, init_pos, verbosity)
        return True, elements, span


class MatchParser(GrammarParser):
    """The parser for grammars for which a match pattern is provided."""

    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.exp_match = re.compile(grammar["match"])
        self.captures = self._init_captures(grammar, key="captures")
        if "\G" in grammar["match"]:
            self.anchored = True

    def __repr__(self) -> str:
        if self.token:
            return f"{self.__class__.__name__}:{self.token}"
        else:
            identifier = self.key if self.key else "_".join(self.comment.lower().split(" "))
            return f"{self.__class__.__name__}:<{identifier}>"

    def initialize_repository(self):
        """When the grammar has patterns, this method should called to initialize its inclusions."""
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
        ws_only: bool = True,
        verbosity: int = 0,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        """The parse method for grammars for which a match pattern is provided."""
        init_pos = stream.tell()

        span, captures = search_stream(stream, self.exp_match, self.captures, boundary, ws_only=ws_only)
        if span is None:
            LOGGER.debug(f"{self.__class__.__name__} no match", self, init_pos, verbosity)
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
            LOGGER.info(f"{self.__class__.__name__} found < {repr(content)} >", self, init_pos, verbosity)
        else:
            elements = captures

        stream.seek(span[1])

        return True, elements, span


class PatternsParser(GrammarParser):
    """The parser for grammars for which several patterns are provided."""

    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.patterns = [init_parser(pattern, language=self.language) for pattern in grammar.get("patterns", [])]

    def initialize_repository(self):
        """When the grammar has patterns, this method should called to initialize its inclusions."""
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
        injections: bool = False,
        verbosity: int = 0,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        """The parse method for grammars for which a match pattern is provided."""
        init_pos = stream.tell()

        if boundary is None:
            boundary = stream.seek(0, 2)
            stream.seek(init_pos)

        parsed, elements = False, []
        current_pos = init_pos
        patterns = [parser for parser in self.patterns if not parser.disabled]
        if find_one or injections:
            patterns = patterns + self.injected_patterns

        while current_pos < boundary:
            for parser in patterns:
                # Try to find patterns
                parsed, candidate_elements, span = parser.parse(
                    stream, boundary=boundary, ws_only=ws_only, verbosity=verbosity + 1, **kwargs
                )
                if parsed:
                    if find_one:
                        LOGGER.info(f"{self.__class__.__name__} found single element", self, current_pos, verbosity)
                        return True, candidate_elements, span
                    elements.extend(candidate_elements)
                    break
            else:
                if find_one:
                    break
                # Try again if previously allowed no leading white space charaters, only when multple patterns are to be found
                second_try_patterns = patterns if ws_only else []
                for parser in second_try_patterns:
                    parsed, candidate_elements, span = parser.parse(
                        stream, boundary=boundary, ws_only=False, verbosity=verbosity + 1, **kwargs
                    )
                    if parsed:
                        if find_one:
                            LOGGER.info(f"{self.__class__.__name__} found single element", self, current_pos, verbosity)
                            return True, candidate_elements, span
                        elements.extend(candidate_elements)
                        break
                else:
                    break
            if stream.tell() == current_pos:
                LOGGER.warning(
                    f"{self.__class__.__name__} stream did not move after a search round", self, current_pos, verbosity
                )
                break
            current_pos = stream.tell()

        close_pos = stream.tell()
        return bool(elements), elements, (init_pos, close_pos)


class BeginEndParser(PatternsParser):
    """The parser for grammars for which a begin/end pattern is provided."""

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
        if "\G" in grammar["begin"]:
            self.anchored = True

    def __repr__(self) -> str:
        if self.token:
            return f"{self.__class__.__name__}:{self.token}"
        else:
            identifier = self.key if self.key else "_".join(self.comment.lower().split(" "))
            return f"{self.__class__.__name__}:<{identifier}>"

    def initialize_repository(self):
        """When the grammar has patterns, this method should called to initialize its inclusions."""
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
        ws_only: bool = True,
        verbosity: int = 0,
        **kwargs,
    ) -> Tuple[bool, List[ContentElement], Tuple[int, int]]:
        """The parse method for grammars for which a begin/end pattern is provided."""

        begin_span, begin_elements = search_stream(
            stream, self.exp_begin, self.captures_begin, boundary, ws_only=ws_only
        )
        if not begin_span:
            LOGGER.debug(f"{self.__class__.__name__} no begin match", self, stream.tell(), verbosity)
            return False, [], (0, 0)
        LOGGER.info(f"{self.__class__.__name__} found begin", self, stream.tell(), verbosity)

        # Get initial and boundary positions
        init_pos = stream.tell()
        if boundary is None:
            boundary = stream.seek(0, 2)
            stream.seek(init_pos)

        # Define loop parameters
        end_elements, mid_elements = [], []
        patterns = [parser for parser in self.patterns if not parser.disabled]
        first_run = True

        while init_pos <= boundary:
            stream.seek(init_pos)
            parsed = False

            # Try to find patterns first with no leading whitespace charaters allowed
            for parser in patterns:
                parsed, candidate_mid_elements, candidate_mid_span = parser.parse(
                    stream, boundary=boundary, ws_only=True, verbosity=verbosity + 1, **kwargs
                )
                if parsed:
                    LOGGER.debug(f"{self.__class__.__name__} found pattern (no ws)", self, stream.tell(), verbosity)
                    break

            # Try to find the end pattern with no leading whitespace charaters allowed
            stream.seek(init_pos)
            end_span, candidate_end_elements = search_stream(
                stream, self.exp_end, self.captures_end, boundary, ws_only=True
            )

            if not parsed and not end_span:
                # Try to find the patterns and end pattern allowing for leading whitespace charaters
                for parser in patterns:
                    parsed, candidate_mid_elements, candidate_mid_span = parser.parse(
                        stream, boundary=boundary, ws_only=False, verbosity=verbosity + 1, **kwargs
                    )
                    if parsed:
                        LOGGER.debug(f"{self.__class__.__name__} found pattern (ws)", self, stream.tell(), verbosity)
                        break

                stream.seek(init_pos)
                end_span, candidate_end_elements = search_stream(
                    stream, self.exp_end, self.captures_end, boundary, ws_only=False
                )

            if end_span:
                if parsed:
                    # Check whether the capture pattern has the same closing positions as the end pattern
                    if stream_read_length(stream, candidate_mid_span[1] - 1, 1) == "\n":
                        # If capture pattern ends with \n, both left and right of \n is considered end
                        pattern_at_end = end_span[1] in [candidate_mid_span[1] - 1, candidate_mid_span[1]]
                    else:
                        pattern_at_end = end_span[1] == candidate_mid_span[1]

                    if pattern_at_end:
                        empty_span_end = end_span[1] == end_span[0]
                        if empty_span_end:
                            # Both found capture pattern and end pattern are accepted, break pattern search
                            mid_elements.extend(candidate_mid_elements)
                            close_pos = end_span[0] if self.between_content else end_span[1]
                            end_elements = candidate_end_elements
                            LOGGER.debug(
                                f"{self.__class__.__name__} capture+end: both accepted, break",
                                self,
                                stream.tell(),
                                verbosity,
                            )
                            break
                        elif not self.apply_end_pattern_last:
                            # End pattern prioritized over capture pattern, break pattern search
                            close_pos = end_span[0] if self.between_content else end_span[1]
                            end_elements = candidate_end_elements
                            LOGGER.debug(
                                f"{self.__class__.__name__} capture+end: end prioritized, break",
                                self,
                                stream.tell(),
                                verbosity,
                            )
                            break
                        else:
                            # Capture pattern prioritized over end pattern, continue pattern search
                            mid_elements.extend(candidate_mid_elements)
                            init_pos = candidate_mid_span[1]
                            LOGGER.debug(
                                f"{self.__class__.__name__} capture+end: capture prioritized, continue",
                                self,
                                stream.tell(),
                                verbosity,
                            )

                    elif candidate_mid_span[0] < end_span[1]:
                        # Capture pattern found before end pattern, continue pattern search
                        mid_elements.extend(candidate_mid_elements)
                        init_pos = candidate_mid_span[1]
                        LOGGER.debug(
                            f"{self.__class__.__name__} capture<end: leading capture, continue",
                            self,
                            stream.tell(),
                            verbosity,
                        )
                    else:
                        # End pattern found before capture pattern, break pattern search
                        close_pos = end_span[0] if self.between_content else end_span[1]
                        end_elements = candidate_end_elements
                        LOGGER.debug(
                            f"{self.__class__.__name__} end<capture: leading end, break", self, stream.tell(), verbosity
                        )
                        break
                else:
                    # No capture pattern found, accept end pattern and break pattern search
                    close_pos = end_span[0] if self.between_content else end_span[1]
                    end_elements = candidate_end_elements
                    LOGGER.debug(f"{self.__class__.__name__} end: break", self, stream.tell(), verbosity)
                    break
            else:  # No end pattern found
                if parsed:
                    # Append found capture pattern and find next starting position
                    mid_elements.extend(candidate_mid_elements)

                    if stream_read_length(stream, candidate_mid_span[1] - 1, 1) == "\n":
                        # Capture pattern ends with newline
                        stream.seek(candidate_mid_span[1] - 1)
                        end_span, candidate_end_elements = search_stream(
                            stream, self.exp_end, self.captures_end, boundary, ws_only=True
                        )
                        if end_span and end_span[1] <= candidate_mid_span[1]:
                            # Potential end pattern can be found one character before the end of the
                            # found capture pattern, start next pattern search round here.
                            init_pos = candidate_mid_span[1] - 1
                        else:
                            # Start next pattern search round from the end of the found capture pattenr
                            init_pos = candidate_mid_span[1]

                        LOGGER.debug(
                            f"{self.__class__.__name__} capture: ends with newline, continue",
                            self,
                            stream.tell(),
                            verbosity,
                        )

                    elif stream_read_length(stream, candidate_mid_span[1], 1) == "\n":
                        # Next character after capture pattern is newline
                        stream.seek(candidate_mid_span[1])
                        end_span, candidate_end_elements = search_stream(
                            stream, self.exp_end, self.captures_end, boundary, ws_only=True
                        )
                        if end_span and end_span[1] <= candidate_mid_span[1] + 1:
                            # Potential end pattern can be found directly after the found capture pattern
                            init_pos = candidate_mid_span[1]
                        else:
                            # Skip the newline character in the next pattern search round
                            init_pos = candidate_mid_span[1] + 1

                        LOGGER.debug(
                            f"{self.__class__.__name__} capture: next is newline, continue",
                            self,
                            stream.tell(),
                            verbosity,
                        )
                    else:
                        init_pos = candidate_mid_span[1]
                        LOGGER.debug(f"{self.__class__.__name__} capture: continue", self, stream.tell(), verbosity)
                else:
                    # No capture patterns nor end patterns found. Skip the current line.
                    line = stream.readline()

                    if stream.tell() == init_pos:
                        close_pos = init_pos
                        end_span = (init_pos, init_pos)
                        LOGGER.warning(f"Recursing occuring while skipping < {repr(line)} >", self, init_pos, verbosity)
                        break

                    if not line.isspace():
                        LOGGER.warning(
                            f"No patterns found in line, skipping < {repr(line)} >", self, init_pos, verbosity
                        )
                    init_pos = stream.tell()

            if first_run:
                # Skip all parsers that were anchored to the begin pattern after the first round
                patterns = [parser for parser in patterns if not parser.anchored]
                first_run = False
        else:
            # Did not break out of while loop, set close_pos to boundary
            close_pos = boundary

        start = begin_span[1] if self.between_content else begin_span[0]

        # Construct output elements
        if self.token:
            content = stream_read_pos(stream, start, close_pos)
            elements = [
                ContentBlockElement(
                    token=self.token,
                    grammar=self.grammar,
                    content=content,
                    span=(start, close_pos),
                    captures=mid_elements,
                    begin=begin_elements,
                    end=end_elements,
                )
            ]
            LOGGER.info(f"{self.__class__.__name__} found < {repr(content)} >", self, start, verbosity)
        else:
            elements = begin_elements + mid_elements + end_elements

        stream.seek(end_span[1])

        return True, elements, (begin_span[0], end_span[1])


class BeginWhileParser(PatternsParser):
    """The parser for grammars for which a begin/end pattern is provided."""

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
        """When the grammar has patterns, this method should called to initialize its inclusions."""
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
        """The parse method for grammars for which a begin/while pattern is provided."""
        raise NotImplementedError
