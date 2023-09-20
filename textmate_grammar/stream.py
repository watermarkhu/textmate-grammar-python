from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from io import StringIO
import onigurumacffi as re
from onigurumacffi import _Pattern as Pattern
from .exceptions import ImpossibleSpan
from .elements import ContentElement, UnparsedElement

if TYPE_CHECKING:
    from .parser import GrammarParser


REGEX_LOOKBEHIND_MAX = 20
REGEX_LOOKBEHIND_STEP = 4
regex_nextline = re.compile("\n|$")


def stream_read_pos(stream: StringIO, start_pos: int, close_pos: int) -> str:
    """Reads the stream between the start and end positions."""
    if start_pos > close_pos:
        raise ImpossibleSpan
    stream.seek(start_pos)
    content = stream.read(close_pos - start_pos)
    return content


def stream_endline_pos(stream: StringIO, start_pos: int) -> int:
    """Finds the position of the next endline character or EOS."""
    stream.seek(start_pos)
    content = stream.read()
    new_line_from_start = content.find("\n")
    if new_line_from_start == -1:
        return start_pos + len(content)
    else:
        return start_pos + new_line_from_start


def search_stream(
    regex: Pattern,
    stream: StringIO,
    parsers: Dict[int, "GrammarParser"] = [],
    start_pos: int = 0,
    close_pos: int = -1,
    **kwargs,
) -> Tuple[List[ContentElement], Optional[Tuple[int, int]]]:
    """Matches the stream against a capture group.

    The stream is matched against the input pattern. If there are any capture groups,
    each is then subsequently parsed by the inputted parsers. The number of parsers therefor
    must match the number of capture groups of the expression, or there must be a single parser
    and no capture groups.
    """
    if close_pos == -1:
        close_pos = len(stream.getvalue())
    elif start_pos > close_pos:
        raise ImpossibleSpan

    lookbehind, can_look_behind = 0, True
    do_look_behind = "(?<" in regex._pattern

    while lookbehind <= REGEX_LOOKBEHIND_MAX and can_look_behind:
        if not do_look_behind:
            # Only perform while loop once
            can_look_behind = False

        if (start_pos - lookbehind) < 0:
            # Set to start of stream of lookbehind is maximized
            lookbehind, can_look_behind = start_pos, False

        # Read buffer
        stream.seek(start_pos - lookbehind)
        match_stream_delta = start_pos
        while stream.tell() < close_pos:
            line = stream.readline()
            matching = regex.search(line)
            if matching:
                break
            match_stream_delta += len(line)
        else:
            lookbehind += REGEX_LOOKBEHIND_STEP
            continue

        if matching.end() + match_stream_delta <= close_pos:
            break

        lookbehind += REGEX_LOOKBEHIND_STEP
    else:
        return [], None

    match_span = (match_stream_delta + matching.start(), match_stream_delta + matching.end())

    if match_span[0] < start_pos:
        return [], None

    # No groups, but a parser existed. Use token of parser to create element
    if 0 in parsers:
        elements = [
            ContentElement(
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
            elements.append(
                UnparsedElement(
                    stream,
                    parser,
                    (span[0] + match_stream_delta, span[1] + match_stream_delta),
                )
            )
    # No parsers
    else:
        elements = []

    return elements, match_span
