from typing import Tuple, Dict, List, Union, Optional
from io import StringIO, SEEK_END
from collections import defaultdict
import onigurumacffi as re
from onigurumacffi import _Pattern as Pattern
from .exceptions import IncludedParserNotFound, CannotCloseEnd, ImpossibleSpan
from .elements import ParsedElement, ParsedElementBlock


regex_nextline = re.compile("\n|$")
REGEX_LOOKBEHIND_MAX = 100
REGEX_LOOKBEHIND_STEP = 5


def stream_read_pos(stream: StringIO, start_pos: int, close_pos: int) -> str:
    "Reads the stream between the start and end positions."
    if start_pos > close_pos:
        raise ImpossibleSpan
    stream.seek(start_pos)
    content = stream.read(close_pos - start_pos)
    return content


def search_stream(
    regex: Pattern,
    stream: StringIO,
    parsers: Dict[int, "GrammarParser"] = [],
    start_pos: int = 0,
    close_pos: Optional[int] = None,
    **kwargs,
) -> Tuple[List[ParsedElement], Optional[Tuple[int, int]]]:
    """Matches the stream against a capture group.

    The stream is matched against the input pattern. If there are any capture groups,
    each is then subsequently parsed by the inputted parsers. The number of parsers therefor
    must match the number of capture groups of the expression, or there must be a single parser
    and no capture groups.
    """
    if close_pos and start_pos > close_pos:
        raise ImpossibleSpan

    lookbehind, can_look_behind = 0, True
    do_look_behind = "(?<" in regex._pattern

    while lookbehind <= REGEX_LOOKBEHIND_MAX and can_look_behind:
        if not do_look_behind:  # Only perform while loop once
            can_look_behind = False
        if (start_pos - lookbehind) < 0:  # Set to start of stream of lookbehind is maximized
            lookbehind, can_look_behind = start_pos, False

        stream.seek(start_pos - lookbehind)
        if close_pos:
            line_pos = 0
            read_length = close_pos - start_pos + 1 + lookbehind
            buffer = stream.read(read_length)
            lines = [line + "\n" for line in buffer.split("\n")]  # Add newline as tmlanguage expects it.
            for line in lines:
                matching = regex.search(line)
                if matching:
                    break  # Find first match encountered per line
                line_pos += len(line)
            else:
                lookbehind += REGEX_LOOKBEHIND_STEP
                continue
            match_stream_delta = line_pos + start_pos - lookbehind
        else:
            line = stream.readline()
            matching = regex.search(line)
            if not matching:
                lookbehind += REGEX_LOOKBEHIND_STEP
                continue
            match_stream_delta = start_pos + lookbehind

        if matching is not None:
            break
    else:
        return [], None

    match_span = (match_stream_delta + matching.start(), match_stream_delta + matching.end())
    close_pos = match_stream_delta + matching.end()

    if match_span[0] < start_pos:
        return [], None

    # No groups, but a parser existed. Use token of parser to create element
    if 0 in parsers:
        elements = [
            ParsedElement(
                token=parsers[0].token if parsers[0].token else parsers[0].comment,
                grammar=parsers[0].grammar,
                content=stream_read_pos(stream, match_span[0], match_span[1]),
                span=match_span,
            )
        ]
    # Parse each capture group
    elif parsers:
        elements = []
        for group_id, parser in parsers.items():
            group = matching.group(group_id)
            if not group:
                continue
            span = matching.span(group_id)
            parsed_elements = parser.parse(
                stream,
                start_pos=span[0] + match_stream_delta,
                close_pos=span[1] + match_stream_delta,
                **kwargs,
            )
            elements += parsed_elements
        if not elements:
            return [], match_span
    # No parsers
    else:
        elements = []

    return elements, match_span


class GrammarParser(object):
    "The parser object for a single TMLanguage grammar scope."
    PARSERSTORE = {}

    def __init__(
        self, grammar: dict, key: str = "", parent: Optional["GrammarParser"] = None, **kwargs
    ) -> None:
        self.grammar = grammar
        self.parent = parent
        self.key = key
        self.token = grammar.get("name", "")
        self.content_token = grammar.get("contentName", "")
        self.comment = grammar.get("comment", "")
        self.match, self.begin, self.end = None, None, None
        self.captures, self.captures_begin, self.captures_end = {}, {}, {}
        self.patterns = []
        self.last_parse = None

        if key:
            self.PARSERSTORE[key] = self

        if "match" in grammar:
            self.match = re.compile(grammar["match"])
            self.captures = self.__init_captures(grammar, key="captures")
        elif "begin" in grammar and "end" in grammar:
            self.begin = re.compile(grammar["begin"])
            self.end = re.compile(grammar["end"])
            self.captures_begin = self.__init_captures(grammar, key="beginCaptures")
            self.captures_end = self.__init_captures(grammar, key="endCaptures")
        if "patterns" in grammar:
            self.patterns = [self.set_parser(pattern) for pattern in grammar["patterns"]]

    def __init_captures(self, grammar: dict, key: str = "captures") -> dict:
        captures = {}
        if key in grammar:
            for group_id, pattern in grammar[key].items():
                captures[int(group_id)] = self.set_parser(pattern)
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
        "Sets the parser based on the grammar. If $self then the parent grammar is used."
        if "include" in grammar:
            if grammar["include"] == "$self":
                return self.parent
            else:
                return grammar["include"][1:]
        else:
            return GrammarParser(grammar, parent=self.parent, **kwargs)

    @classmethod
    def get_parser(cls, call_id: Union[str, "GrammarParser"]):
        "Gets the parser from the PARSERSTORE, updates the call_id with the parser itself in the store."
        if isinstance(call_id, str):
            if call_id in cls.PARSERSTORE:
                call_id = cls.PARSERSTORE[call_id]
            else:
                raise IncludedParserNotFound(call_id)
        return call_id

    def parse(
        self,
        stream: StringIO,
        start_pos: int = 0,
        close_pos: Optional[int] = None,
        call_stack: List["GrammarParser"] = [],
        **kwargs,
    ) -> List[ParsedElement]:
        """Parse the input stream using the current parser."""
        if close_pos:
            if start_pos >= close_pos:
                return []
        else:
            close_pos = len(stream.getvalue())

        if (stream, start_pos, close_pos) == self.last_parse and self in call_stack:
            # Prevent the same parser being called recursively
            return []
        current_call_stack = [parser for parser in call_stack] + [self]

        self.last_parse = (stream, start_pos, close_pos)
        stream.seek(start_pos)

        if self.match:
            captures, span = search_stream(
                self.match,
                stream,
                parsers=self.captures,
                start_pos=start_pos,
                close_pos=close_pos,
                call_stack=current_call_stack,
                **kwargs,
            )
            if span is None:
                return []
            content = stream_read_pos(stream, span[0], span[1])
            elements = [
                ParsedElement(
                    token=self.token if self.token else self.key,
                    grammar=self.grammar,
                    content=content,
                    span=span,
                    captures=captures,
                )
            ]

        elif self.begin and self.end:
            # Find begin
            captured_begin, begin_span = search_stream(
                self.begin,
                stream,
                parsers=self.captures_begin,
                start_pos=start_pos,
                close_pos=close_pos,
                call_stack=current_call_stack,
                **kwargs,
            )
            if begin_span is None:
                return []
            (begin_start, begin_close) = begin_span
            if close_pos and begin_close > close_pos:
                return []

            pattern_result = self.parse_patterns(
                stream, start_pos=begin_close, close_pos=close_pos, search_end=True, call_stack=current_call_stack
            )
            if not pattern_result:
                return []
            captured_elements, captured_end, (end_start, end_close) = pattern_result

            token = self.content_token if self.content_token else self.token if self.token else self.key
            start, close = (begin_close, end_start) if self.content_token else (begin_start, end_close)

            elements = [
                ParsedElementBlock(
                    token=token,
                    grammar=self.grammar,
                    content=stream_read_pos(stream, start, close),
                    span=(start, close),
                    captures=captured_elements,
                    begin=captured_begin if captured_begin else None,
                    end=captured_end if captured_end else None,
                )
            ]

        elif self.patterns:
            captured_elements, _, _ = self.parse_patterns(
                stream, start_pos=start_pos, close_pos=close_pos, call_stack=current_call_stack
            )

            if captured_elements:
                if self.token:
                    content = stream_read_pos(stream, start_pos, close_pos)
                    elements = [
                        ParsedElement(
                            token=self.token,
                            grammar=self.grammar,
                            content=content,
                            span=(start_pos, close_pos),
                            captures=captured_elements,
                        )
                    ]
                else:
                    elements = captured_elements
            else:
                return []

        else:
            if close_pos is not None:
                content = stream_read_pos(stream, start_pos, close_pos)
                elements = [
                    ParsedElement(
                        token=self.token if self.token else self.key,
                        grammar=self.grammar,
                        content=content,
                        span=(start_pos, close_pos),
                    )
                ]
            else:
                raise CannotCloseEnd(stream.read())

        return elements

    def parse_patterns(
        self,
        stream,
        start_pos: int,
        close_pos: int,
        search_end: bool = False,
        **kwargs,
    ):
        "Parse a number of patterns"
        # Get parsers and create lookup store
        parsers = [self.get_parser(call_id) for call_id in self.patterns]
        elements_on_pos = defaultdict(list)
        elements_per_parser = defaultdict(list)
        null_search_close = {}
        captured_elements, captured_end = [], []
        pattern_start = start_pos

        if search_end:
            captured_end, end_span = search_stream(
                self.end,
                stream,
                parsers=self.captures_end,
                start_pos=pattern_start,
                close_pos=close_pos,
                onlyLeadingWhiteSpace=False,
                **kwargs,
            )
            if end_span is None:
                return None
            (end_start, _) = end_span

        while pattern_start < close_pos:
 
            elements_per_parser_round = defaultdict(list)
            for parser in parsers:  # Find match per parser
                skipped_index = next(
                    (
                        index
                        for index, element in enumerate(elements_per_parser[parser])
                        if element.span[0] >= pattern_start
                    ),
                    len(elements_per_parser[parser]),
                )
                if skipped_index:
                    elements_per_parser[parser] = elements_per_parser[parser][skipped_index:]

                if not elements_per_parser[parser] and null_search_close.get(parser, None) != close_pos:
                    elements = parser.parse(stream, start_pos=pattern_start, close_pos=close_pos, **kwargs)
                    if elements:
                        elements_per_parser_round[parser].extend(elements)
                        for element in elements:
                            elements_on_pos[element.span[0]].append(element)
                    else:
                        null_search_close[parser] = close_pos

            if elements_per_parser_round:
                for parser, elements in elements_per_parser_round.items():
                    elements_per_parser[parser].extend(elements)
            elif not any((pos >= pattern_start for pos in elements_on_pos.keys())):
                break

            if pattern_start in elements_on_pos:
                elements = elements_on_pos[pattern_start]
                element = sorted(elements, key=lambda element: element.span[1], reverse=True)[0]
                captured_elements.append(element)
                if type(element) is ParsedElementBlock and element.end:
                    pattern_start = element.end[-1].span[1]
                else:
                    pattern_start = element.span[1]
            else:
                pattern_start += 1

            if search_end:
                if pattern_start == end_start:
                    break
                elif pattern_start > end_start:
                    captured_end, end_span = search_stream(
                        self.end,
                        stream,
                        parsers=self.captures_end,
                        start_pos=pattern_start,
                        close_pos=close_pos,
                        onlyLeadingWhiteSpace=False,
                        **kwargs,
                    )
                    if end_span is None:
                        return None
                    (end_start, _) = end_span

        return (captured_elements, captured_end, end_span) if search_end else (captured_elements, None, None)


class LanguageParser(GrammarParser):
    def __init__(self, grammar: dict, **kwargs):
        self.uuid = grammar["uuid"]
        self.file_types = grammar["fileTypes"]

        for key, value in grammar["repository"].items():
            GrammarParser(value, key=key, parent=self, **kwargs)

        super().__init__(grammar, key=grammar["scopeName"], **kwargs)
