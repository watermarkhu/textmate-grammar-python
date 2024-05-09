from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import onigurumacffi as re

from .elements import Capture, ContentBlockElement, ContentElement
from .handler import POS, ContentHandler, Pattern
from .utils.exceptions import IncludedParserNotFound
from .utils.logger import LOGGER, track_depth

if TYPE_CHECKING:
    from .parsers.base import LanguageParser


class GrammarParser(ABC):
    """The abstract grammar parser object"""

    @staticmethod
    def initialize(grammar: dict, **kwargs):
        """
        Initializes the parser based on the grammar.

        :param grammar: The grammar to initialize the parser with.
        :param kwargs: Additional keyword arguments.
        :return: The initialized parser.
        """
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

    def __init__(
        self,
        grammar: dict,
        language_parser: LanguageParser | None = None,
        key: str = "",
        is_capture: bool = False,
        **kwargs,
    ) -> None:
        """
        Initialize a Parser object.

        :param grammar: The grammar dictionary.
        :param language: The language parser object. Defaults to None.
        :param key: The key for the parser. Defaults to "".
        :param is_capture: Indicates if the parser is a capture. Defaults to False.
        :param kwargs: Additional keyword arguments.

        :return: None
        """
        self.grammar = grammar
        self.language_parser = language_parser
        self.key = key
        self.token = grammar.get("name", "")
        self.is_capture = is_capture
        self.initialized = False
        self.anchored = False

    @property
    def comment(self) -> str:
        return self.grammar.get("comment", "")

    @property
    def disabled(self) -> bool:
        return self.grammar.get("disabled", False)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:<{self.key}>"

    def _init_captures(self, grammar: dict, key: str = "captures", **kwargs) -> dict:
        """Initializes a captures dictionary"""
        captures = {}
        if key in grammar:
            for group_id, pattern in grammar[key].items():
                captures[int(group_id)] = self.initialize(
                    pattern, language_parser=self.language_parser, is_capture=True
                )
        return captures

    def _find_include(self, key: str, **kwargs) -> GrammarParser:
        """Find the included grammars and during repository initialization"""
        if not self.language_parser:
            raise IncludedParserNotFound(key)

        if key in ["$self", "$base"]:  # TODO there is a difference between these
            return self.language_parser
        elif key[0] == "#":
            return self.language_parser.repository.get(key[1:], None)
        else:
            return self.language_parser._find_include_scopes(key)

    @abstractmethod
    def _parse(
        self,
        handler: ContentHandler,
        starting: POS,
        **kwargs,
    ) -> tuple[bool, list[Capture | ContentElement], tuple[int, int] | None]:
        """The abstract method which all parsers much implement

        The ``_parse`` method is called by ``parse``, which will additionally parse any nested Capture elements.
        The ``_parse`` method should contain all the rules for the extended parser.

        :param handler: The content handler to handle the parsed elements.
        :param starting: The starting position of the parsing.
        :param kwargs: Additional keyword arguments.
        :return: A tuple containing the parsing result, a list of parsed elements, and the ending position of the parsing.
        """
        pass

    def _initialize_repository(self, **kwargs) -> None:
        """Initializes the repository's inclusions.

        When the grammar has patterns, this method should called to initialize its inclusions.
        This should occur after all sub patterns have been initialized.
        """
        return

    def parse(
        self,
        handler: ContentHandler,
        starting: POS = (0, 0),
        boundary: POS | None = None,
        **kwargs,
    ) -> tuple[bool, list[Capture | ContentElement], tuple[int, int] | None]:
        """
        The method to parse a handler using the current grammar.

        :param handler: The ContentHandler object that will handle the parsed content.
        :param starting: The starting position for parsing. Defaults to (0, 0).
        :param boundary: The boundary position for parsing. Defaults to None.
        :param **kwargs: Additional keyword arguments that can be passed to the parser.

        :return: A tuple containing:
            - parsed: A boolean indicating whether the parsing was successful.
            - elements: A list of Capture or ContentElement objects representing the parsed content.
            - span: A tuple containing the starting and ending positions of the parsed content, or None if parsing failed.
        """
        if not self.initialized and self.language_parser is not None:
            self.language_parser._initialize_repository()
        parsed, elements, span = self._parse(handler, starting, boundary=boundary, **kwargs)
        return parsed, elements, span

    def match_and_capture(
        self,
        handler: ContentHandler,
        pattern: Pattern,
        starting: POS,
        boundary: POS,
        parsers: dict[int, GrammarParser] | None = None,
        parent_capture: Capture | None = None,
        **kwargs,
    ) -> tuple[tuple[POS, POS] | None, str, list[Capture | ContentElement]]:
        """Matches a pattern and its capture groups.

        Matches the pattern on the handler between the starting and boundary positions. If a pattern is matched,
        its capture groups are initialized as Capture objects. These are only parsed after the full handler has been
        parsed. This occurs in GrammarParser.parse when calling parse_captures.

        :param handler: The content handler to match the pattern on.
        :param pattern: The pattern to match.
        :param starting: The starting position for the match.
        :param boundary: The boundary position for the match.
        :param parsers: A dictionary of parsers.
        :param parent_capture: The parent capture object.
        :param kwargs: Additional keyword arguments.
        :return: A tuple containing the span of the match, the matched string, and a list of capture objects or content elements.
        """
        if parsers is None:
            parsers = {}
        matching, span = handler.search(pattern, starting=starting, boundary=boundary, **kwargs)

        if matching:
            if parsers:
                capture = Capture(
                    handler,
                    pattern,
                    matching,
                    parsers,
                    starting,
                    boundary,
                    key=self.key,
                    **kwargs,
                )
                if parent_capture is not None and capture == parent_capture:
                    return None, "", []
                else:
                    return span, matching.group(), [capture]
            else:
                return span, matching.group(), []
        else:
            return None, "", []


class TokenParser(GrammarParser):
    """The parser for grammars for which only the token is provided."""

    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.initialized = True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.token}"

    @track_depth
    def _parse(
        self,
        handler: ContentHandler,
        starting: POS,
        boundary: POS,
        **kwargs,
    ) -> tuple[bool, list[Capture | ContentElement], tuple[POS, POS] | None]:
        """The parse method for grammars for which only the token is provided.

        When no regex patterns are provided. The element is created between the initial and boundary positions.
        """
        content = handler.read_pos(starting, boundary)
        elements: list[Capture | ContentElement] = [
            ContentElement(
                token=self.token,
                grammar=self.grammar,
                content=content,
                characters=handler.chars(starting, boundary),
            )
        ]
        handler.anchor = boundary[1]
        LOGGER.info(
            f"{self.__class__.__name__} found < {repr(content)} >",
            self,
            starting,
            kwargs.get("depth", 0),
        )
        return True, elements, (starting, boundary)


class MatchParser(GrammarParser):
    """The parser for grammars for which a match pattern is provided."""

    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.exp_match = re.compile(grammar["match"])
        self.parsers = self._init_captures(grammar, key="captures")
        if "\\G" in grammar["match"]:
            self.anchored = True

    def __repr__(self) -> str:
        if self.token:
            return f"{self.__class__.__name__}:{self.token}"
        else:
            identifier = self.key if self.key else "_".join(self.comment.lower().split(" "))
            return f"{self.__class__.__name__}:<{identifier}>"

    def _initialize_repository(self, **kwargs) -> None:
        """When the grammar has patterns, this method should called to initialize its inclusions."""
        self.initialized = True
        for key, value in self.parsers.items():
            if not isinstance(value, GrammarParser):
                self.parsers[key] = self._find_include(value)
        for parser in self.parsers.values():
            if not parser.initialized:
                parser._initialize_repository()

    @track_depth
    def _parse(
        self,
        handler: ContentHandler,
        starting: POS,
        boundary: POS,
        **kwargs,
    ) -> tuple[bool, list[Capture | ContentElement], tuple[POS, POS] | None]:
        """The parse method for grammars for which a match pattern is provided."""

        span, content, captures = self.match_and_capture(
            handler,
            pattern=self.exp_match,
            starting=starting,
            boundary=boundary,
            parsers=self.parsers,
            **kwargs,
        )

        if span is None:
            LOGGER.debug(
                f"{self.__class__.__name__} no match",
                self,
                starting,
                kwargs.get("depth", 0),
            )
            return False, [], None

        LOGGER.info(
            f"{self.__class__.__name__} found < {repr(content)} >",
            self,
            starting,
            kwargs.get("depth", 0),
        )

        if self.token:
            elements: list[Capture | ContentElement] = [
                ContentElement(
                    token=self.token,
                    grammar=self.grammar,
                    content=content,
                    characters=handler.chars(*span),
                    children=captures,
                )
            ]
        else:
            elements = captures

        return True, elements, span


class ParserHasPatterns(GrammarParser, ABC):
    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        self.patterns = [
            self.initialize(pattern, language_parser=self.language_parser)
            for pattern in grammar.get("patterns", [])
        ]

    def _initialize_repository(self):
        """When the grammar has patterns, this method should called to initialize its inclusions."""
        self.initialized = True
        self.patterns = [
            parser if isinstance(parser, GrammarParser) else self._find_include(parser)
            for parser in self.patterns
        ]
        for parser in self.patterns:
            if not parser.initialized:
                parser._initialize_repository()

        # Copy patterns from included pattern parsers
        pattern_parsers = [parser for parser in self.patterns if isinstance(parser, PatternsParser)]
        for parser in pattern_parsers:
            parser_index = self.patterns.index(parser)
            self.patterns[parser_index : parser_index + 1] = parser.patterns

        # Injection grammars
        for exception_scopes, injection_pattern in self.language_parser.injections:
            if self.token:
                if self.token.split(".")[0] not in exception_scopes:
                    self.patterns.append(injection_pattern)
            elif self.is_capture:
                self.patterns.append(injection_pattern)


class PatternsParser(ParserHasPatterns):
    """The parser for grammars for which several patterns are provided."""

    @track_depth
    def _parse(
        self,
        handler: ContentHandler,
        starting: POS,
        boundary: POS | None = None,
        greedy: bool = False,
        find_one: bool = True,
        **kwargs,
    ) -> tuple[bool, list[Capture | ContentElement], tuple[POS, POS]]:
        """The parse method for grammars for which a match pattern is provided."""

        if boundary is None:
            boundary = (len(handler.lines) - 1, handler.line_lengths[-1])

        parsed = False
        elements: list[Capture | ContentElement] = []
        patterns = [parser for parser in self.patterns if not parser.disabled]

        current = (starting[0], starting[1])

        while current < boundary:
            for parser in patterns:
                # Try to find patterns
                parsed, captures, span = parser._parse(
                    handler,
                    current,
                    boundary=boundary,
                    greedy=greedy,
                    **kwargs,
                )
                if parsed:
                    if find_one:
                        LOGGER.info(
                            f"{self.__class__.__name__} found single element",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )
                        return True, captures, span
                    elements.extend(captures)
                    current = span[1]
                    break
            else:
                if find_one:
                    break

            if not parsed and not greedy:
                # Try again if previously allowed no leading white space charaters, only when multple patterns are to be found
                options_span, options_elements = {}, {}
                for parser in patterns:
                    parsed, captures, span = parser._parse(
                        handler,
                        current,
                        boundary=boundary,
                        greedy=True,
                        **kwargs,
                    )
                    if parsed:
                        options_span[parser] = span
                        options_elements[parser] = captures
                        LOGGER.debug(
                            f"{self.__class__.__name__} found pattern choice",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )

                if options_span:
                    parser = sorted(
                        options_span,
                        key=lambda parser: (
                            *options_span[parser][0],
                            patterns.index(parser),
                        ),
                    )[0]
                    current = options_span[parser][1]
                    elements.extend(options_elements[parser])
                    LOGGER.info(
                        f"{self.__class__.__name__} chosen pattern of {parser}",
                        self,
                        current,
                        kwargs.get("depth", 0),
                    )
                elif self != self.language_parser:
                    break
                else:
                    remainder = handler.read_line(current)
                    if not remainder.isspace():
                        LOGGER.warning(
                            f"{self.__class__.__name__} remainder of line not parsed: {remainder}",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )
                    if current[0] + 1 <= len(handler.lines):
                        current = (current[0] + 1, 0)
                    else:
                        LOGGER.debug(
                            f"{self.__class__.__name__} EOF encountered",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )
                        break

            if current == starting:
                LOGGER.warning(
                    f"{self.__class__.__name__} handler did not move after a search round",
                    self,
                    starting,
                    kwargs.get("depth", 0),
                )
                break

            line_length = handler.line_lengths[current[0]]
            if current[1] in [line_length, line_length - 1]:
                try:
                    empty_lines = next(
                        i for i, v in enumerate(handler.line_lengths[current[0] + 1 :]) if v > 1
                    )
                    current = (current[0] + 1 + empty_lines, 0)
                except StopIteration:
                    break

        if self.token:
            elements = [
                ContentElement(
                    token=self.token,
                    grammar=self.grammar,
                    content=handler.read_pos(starting, boundary),
                    characters=handler.chars(starting, boundary),
                    children=elements,
                )
            ]

        return bool(elements), elements, (starting, current)


class BeginEndParser(ParserHasPatterns):
    """The parser for grammars for which a begin/end pattern is provided."""

    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        if "contentName" in grammar:
            self.token = grammar["contentName"]
            self.between_content = True
        else:
            self.token = grammar.get("name")
            self.between_content = False
        self.apply_end_pattern_last = grammar.get("applyEndPatternLast", False)
        self.exp_begin = re.compile(grammar["begin"])
        self.exp_end = re.compile(grammar["end"])
        self.parsers_begin = self._init_captures(grammar, key="beginCaptures")
        self.parsers_end = self._init_captures(grammar, key="endCaptures")
        if "\\G" in grammar["begin"]:
            self.anchored = True

    def __repr__(self) -> str:
        if self.token:
            return f"{self.__class__.__name__}:{self.token}"
        else:
            identifier = self.key if self.key else "_".join(self.comment.lower().split(" "))
            return f"{self.__class__.__name__}:<{identifier}>"

    def _initialize_repository(self, **kwargs) -> None:
        """When the grammar has patterns, this method should called to initialize its inclusions."""
        self.initialized = True
        super()._initialize_repository()
        for key, value in self.parsers_end.items():
            if not isinstance(value, GrammarParser):
                self.parsers_end[key] = self._find_include(value)
        for key, value in self.parsers_begin.items():
            if not isinstance(value, GrammarParser):
                self.parsers_begin[key] = self._find_include(value)
        for parser in self.parsers_begin.values():
            if not parser.initialized:
                parser._initialize_repository()
        for parser in self.parsers_end.values():
            if not parser.initialized:
                parser._initialize_repository()

    @track_depth
    def _parse(
        self,
        handler: ContentHandler,
        starting: POS,
        boundary: POS,
        greedy: bool = False,
        **kwargs,
    ) -> tuple[bool, list[Capture | ContentElement], tuple[POS, POS] | None]:
        """The parse method for grammars for which a begin/end pattern is provided."""

        begin_span, _, begin_elements = self.match_and_capture(
            handler,
            self.exp_begin,
            starting,
            boundary=boundary,
            parsers=self.parsers_begin,
            greedy=greedy,
            **kwargs,
        )

        if not begin_span:
            LOGGER.debug(
                f"{self.__class__.__name__} no begin match",
                self,
                starting,
                kwargs.get("depth", 0),
            )
            return False, [], None
        LOGGER.info(
            f"{self.__class__.__name__} found begin",
            self,
            starting,
            kwargs.get("depth", 0),
        )

        # Get initial and boundary positions
        current = begin_span[1]
        if boundary is None:
            boundary = (len(handler.lines) - 1, handler.line_lengths[-1])

        # Define loop parameters
        end_elements: list[Capture | ContentElement] = []
        mid_elements: list[Capture | ContentElement] = []
        patterns = [parser for parser in self.patterns if not parser.disabled]
        first_run = True

        while current <= boundary:
            parsed = False

            # Create boolean that is enabled when a parser is recursively called. In this its end pattern should
            # be applied last, otherwise the same span will be recognzed as the end pattern by the upper level parser
            apply_end_pattern_last = False

            # Try to find patterns first with no leading whitespace charaters allowed
            for parser in patterns:
                parsed, capture_elements, capture_span = parser._parse(
                    handler, current, boundary=boundary, greedy=False, **kwargs
                )
                if parsed:
                    if parser == self:
                        apply_end_pattern_last = True
                    LOGGER.debug(
                        f"{self.__class__.__name__} found pattern (no ws)",
                        self,
                        current,
                        kwargs.get("depth", 0),
                    )
                    break

            # Try to find the end pattern with no leading whitespace charaters allowed
            end_span, _, end_elements = self.match_and_capture(
                handler,
                self.exp_end,
                current,
                boundary=boundary,
                parsers=self.parsers_end,
                greedy=False,
                **kwargs,
            )

            if not parsed and not end_span:
                # Try to find the patterns and end pattern allowing for leading whitespace charaters

                LOGGER.info(
                    f"{self.__class__.__name__} getting all pattern options",
                    self,
                    current,
                    kwargs.get("depth", 0),
                )

                options_span, options_elements = {}, {}
                for parser in patterns:
                    parsed, capture_elements, capture_span = parser._parse(
                        handler,
                        current,
                        boundary=boundary,
                        greedy=True,
                        **kwargs,
                    )
                    if parsed:
                        options_span[parser] = capture_span
                        options_elements[parser] = capture_elements
                        LOGGER.debug(
                            f"{self.__class__.__name__} found pattern choice",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )

                if options_span:
                    parsed = True
                    parser = sorted(
                        options_span,
                        key=lambda parser: (
                            *options_span[parser][0],
                            patterns.index(parser),
                        ),
                    )[0]
                    capture_span = options_span[parser]
                    capture_elements = options_elements[parser]

                    if parser == self:
                        apply_end_pattern_last = True

                    LOGGER.info(
                        f"{self.__class__.__name__} chosen pattern of {parser}",
                        self,
                        current,
                        kwargs.get("depth", 0),
                    )

                end_span, end_content, end_elements = self.match_and_capture(
                    handler,
                    self.exp_end,
                    current,
                    boundary=boundary,
                    parsers=self.parsers_end,
                    greedy=True,
                    **kwargs,
                )

            if end_span:
                if parsed:
                    # Check whether the capture pattern has the same closing positions as the end pattern
                    capture_before_end = handler.prev(capture_span[1])
                    if handler.read(capture_before_end, skip_newline=False) == "\n":
                        # If capture pattern ends with \n, both left and right of \n is considered end
                        pattern_at_end = end_span[1] in [
                            capture_before_end,
                            capture_span[1],
                        ]
                    else:
                        pattern_at_end = end_span[1] == capture_span[1]

                    end_before_pattern = end_span[0] <= capture_span[0]
                    empty_span_end = end_span[1] == end_span[0]

                    if pattern_at_end and (end_before_pattern or empty_span_end):
                        if empty_span_end:
                            # Both found capture pattern and end pattern are accepted, break pattern search
                            LOGGER.debug(
                                f"{self.__class__.__name__} capture+end: both accepted, break",
                                self,
                                current,
                                kwargs.get("depth", 0),
                            )
                            mid_elements.extend(capture_elements)
                            closing = end_span[0] if self.between_content else end_span[1]
                            break
                        elif not self.apply_end_pattern_last and not apply_end_pattern_last:
                            # End pattern prioritized over capture pattern, break pattern search
                            LOGGER.debug(
                                f"{self.__class__.__name__} capture+end: end prioritized, break",
                                self,
                                current,
                                kwargs.get("depth", 0),
                            )
                            closing = end_span[0] if self.between_content else end_span[1]
                            break
                        else:
                            # Capture pattern prioritized over end pattern, continue pattern search
                            LOGGER.debug(
                                f"{self.__class__.__name__} capture+end: capture prioritized, continue",
                                self,
                                current,
                                kwargs.get("depth", 0),
                            )
                            mid_elements.extend(capture_elements)
                            current = capture_span[1]

                    elif capture_span[0] < end_span[0]:
                        # Capture pattern found before end pattern, continue pattern search
                        LOGGER.debug(
                            f"{self.__class__.__name__} capture<end: leading capture, continue",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )
                        mid_elements.extend(capture_elements)
                        current = capture_span[1]
                    else:
                        # End pattern found before capture pattern, break pattern search
                        LOGGER.debug(
                            f"{self.__class__.__name__} end<capture: leading end, break",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )
                        closing = end_span[0] if self.between_content else end_span[1]
                        break
                else:
                    # No capture pattern found, accept end pattern and break pattern search
                    LOGGER.debug(
                        f"{self.__class__.__name__} end: break",
                        self,
                        current,
                        kwargs.get("depth", 0),
                    )
                    closing = end_span[0] if self.between_content else end_span[1]
                    break
            else:  # No end pattern found
                if parsed:
                    # Append found capture pattern and find next starting position
                    mid_elements.extend(capture_elements)

                    if handler.read(capture_span[1], skip_newline=False) == "\n":
                        # Next character after capture pattern is newline

                        LOGGER.debug(
                            f"{self.__class__.__name__} capture: next is newline, continue",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )

                        end_span, _, _ = self.match_and_capture(
                            handler,
                            self.exp_end,
                            capture_span[1],
                            boundary=boundary,
                            parsers=self.parsers_end,
                            allow_leading_all=False,
                            **kwargs,
                        )

                        if end_span and end_span[1] <= handler.next(capture_span[1]):
                            # Potential end pattern can be found directly after the found capture pattern
                            current = capture_span[1]
                        else:
                            # Skip the newline character in the next pattern search round
                            current = handler.next(capture_span[1])
                    else:
                        LOGGER.debug(
                            f"{self.__class__.__name__} capture: continue",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )
                        current = capture_span[1]
                else:
                    # No capture patterns nor end patterns found. Skip the current line.
                    line = handler.read_line(current)

                    if line and not line.isspace():
                        LOGGER.warning(
                            f"No patterns found in line, skipping < {repr(line)} >",
                            self,
                            current,
                            kwargs.get("depth", 0),
                        )
                    current = handler.next((current[0], handler.line_lengths[current[0]]))

            if apply_end_pattern_last:
                current = handler.next(current)

            if first_run:
                # Skip all parsers that were anchored to the begin pattern after the first round
                patterns = [parser for parser in patterns if not parser.anchored]
                first_run = False
        else:
            # Did not break out of while loop, set closing to boundary
            closing = boundary
            end_span = ((0, 0), boundary)

        start = begin_span[1] if self.between_content else begin_span[0]

        content = handler.read_pos(start, closing)
        LOGGER.info(
            f"{self.__class__.__name__} found < {repr(content)} >",
            self,
            start,
            kwargs.get("depth", 0),
        )

        # Construct output elements
        if self.token:
            elements: list[Capture | ContentElement] = [
                ContentBlockElement(
                    token=self.token,
                    grammar=self.grammar,
                    content=content,
                    characters=handler.chars(start, closing),
                    children=mid_elements,
                    begin=begin_elements,
                    end=end_elements,
                )
            ]
        else:
            elements = begin_elements + mid_elements + end_elements

        return True, elements, (begin_span[0], end_span[1])


class BeginWhileParser(PatternsParser):
    """The parser for grammars for which a begin/end pattern is provided."""

    def __init__(self, grammar: dict, **kwargs) -> None:
        super().__init__(grammar, **kwargs)
        if "contentName" in grammar:
            self.token = grammar["contentName"]
            self.between_content = True
        else:
            self.token = grammar.get("name")
            self.between_content = False
        self.exp_begin = re.compile(grammar["begin"])
        self.exp_while = re.compile(grammar["while"])
        self.parsers_begin = self._init_captures(grammar, key="beginCaptures")
        self.parsers_while = self._init_captures(grammar, key="whileCaptures")

    def __repr__(self) -> str:
        if self.token:
            return f"{self.__class__.__name__}:{self.token}"
        else:
            identifier = self.key if self.key else "_".join(self.comment.lower().split(" "))
            return f"{self.__class__.__name__}:<{identifier}>"

    def _initialize_repository(self):
        """When the grammar has patterns, this method should called to initialize its inclusions."""
        self.initialized = True
        super()._initialize_repository()
        for key, value in self.parsers_end.items():
            if not isinstance(value, GrammarParser):
                self.parsers_end[key] = self._find_include(value)
        for key, value in self.parsers_while.items():
            if not isinstance(value, GrammarParser):
                self.parsers_while[key] = self._find_include(value)
        for parser in self.parsers_begin.values():
            if not parser.initialized:
                parser._initialize_repository()
        for parser in self.parsers_while.values():
            if not parser.initialized:
                parser._initialize_repository()

    def _parse(
        self,
        handler: ContentHandler,
        starting: POS,
        **kwargs,
    ):
        """The parse method for grammars for which a begin/while pattern is provided."""
        raise NotImplementedError
