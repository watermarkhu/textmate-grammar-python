from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from io import TextIOBase
import onigurumacffi as re
from onigurumacffi import _Pattern as Pattern
from .exceptions import ImpossibleSpan
from .elements import ContentElement, UnparsedElement

if TYPE_CHECKING:
    from .parser import GrammarParser


REGEX_LOOKBEHIND_MAX = 20
REGEX_LOOKBEHIND_STEP = 4
regex_nextline = re.compile("\n|$")


def stream_read_pos(stream: TextIOBase, start_pos: int, close_pos: int) -> str:
    """Reads the stream between the start and end positions."""

    return stream_read_length(stream, start_pos, close_pos - start_pos)


def stream_read_length(stream: TextIOBase, start_pos: int, length: int) -> str:
    """Reads the stream from start for a length"""
    if length < 0:
        raise ImpossibleSpan
    init_pos = stream.tell()
    stream.seek(start_pos)
    content = stream.read(length)
    stream.seek(init_pos)
    return content


def search_stream(
    stream: TextIOBase,
    regex: Pattern,
    parsers: Dict[int, "GrammarParser"] = {},
    boundary: Optional[int] = None,
    anchor: Optional[int] = None,
    ws_only: bool = True,
    **kwargs,
) -> Tuple[Tuple[int, int], List[ContentElement]]:
    """Matches the stream against a capture group.

    The stream is matched against the input pattern. If there are any capture groups,
    each is then subsequently parsed by the inputted parsers. The number of parsers therefor
    must match the number of capture groups of the expression, or there must be a single parser
    and no capture groups.
    """

    init_pos = stream.tell()
    if regex._pattern == "\Z":
        line = stream.readline()
        end_pos = stream.tell()
        return (end_pos, end_pos), []
    elif regex._pattern[:2] == "\G":
        if anchor is None:
            raise SyntaxError
        if init_pos != anchor:
            return None, []

    match_shift = init_pos

    if "(?<" not in regex._pattern:
        line = stream.readline()
        matching = regex.search(line)
        if not matching or (
            ws_only
            and matching.start()
            and not stream_read_length(stream, init_pos, matching.start()).isspace()
        ):
            stream.seek(init_pos)
            return None, []
    else:
        stream.readline()
        line_end_pos = stream.tell()
        look_behind_shift = 0

        while stream.tell() == line_end_pos and match_shift >= 0:
            stream.seek(match_shift)
            line = stream.readline()
            matching = regex.search(line)

            if (
                not matching
                or matching.start() < look_behind_shift
                or (
                    ws_only
                    and matching.start() > look_behind_shift
                    and not stream_read_length(stream, init_pos, matching.start() - look_behind_shift).isspace()
                )
            ):
                look_behind_shift += 1
                match_shift = init_pos - look_behind_shift
            else:
                break
        else:
            stream.seek(init_pos)
            return None, []

    match_span = (match_shift + matching.start(), match_shift + matching.end())

    if boundary and match_span[1] > boundary:
        stream.seek(init_pos)
        return None, []

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
                    (match_shift + span[0], match_shift + span[1]),
                )
            )

    # No parsers
    else:
        elements = []

    stream.seek(match_span[1])

    return match_span, elements
