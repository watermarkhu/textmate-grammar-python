from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from io import TextIOBase
import onigurumacffi as re
from onigurumacffi import _Pattern as Pattern

from .elements import ContentElement, UnparsedElement
from .read import stream_read_pos
from .logging import LOGGER

if TYPE_CHECKING:
    from .parser import GrammarParser


regex_nextline = re.compile("\n|$")


class ANCHOR(object):
    """Saves the match end location for the next matching if it contains \\G."""

    _pos: int = 0

    @classmethod
    def set(cls, pos: int):
        cls._pos = pos

    @classmethod
    def get(cls):
        return cls._pos


def search_stream(
    stream: TextIOBase,
    regex: Pattern,
    parsers: Dict[int, "GrammarParser"] = {},
    boundary: Optional[int] = None,
    ws_only: bool = True,
    **kwargs,
) -> Tuple[Tuple[int, int], List[ContentElement]]:
    """Matches the stream against a capture group.

    The stream is matched against the input pattern. If there are any capture groups,
    each is then subsequently parsed by the inputted parsers. The number of parsers therefor
    must match the number of capture groups of the expression, or there must be a single parser
    and no capture groups.

    In a grammar that contains a pattern, first a round of search is performed while ws_only is
    set to True, trying to find a match directy from the initial position. If no matches are found,
    a second round is initiated with ws_only set to False, allowing for non-tokenized whitespace
    charaters to be skipped in the matching.
    """

    init_pos = stream.tell()
    if regex._pattern == "\Z":
        # Directly finds and returns the end of line position.
        line = stream.readline()
        end_pos = stream.tell() - 1
        ANCHOR.set(end_pos)
        return (end_pos, end_pos), []
    elif "\G" in regex._pattern:
        # Gets the previous matching end position from ANCHOR.
        init_pos = ANCHOR.get()

    if "(?<" not in regex._pattern:
        # Simple matching without lookback
        line = stream.readline()
        matching = regex.search(line)
        match_shift = init_pos

    else:
        # Find begin of line and search starting from the initial position
        stream.readline()
        line_end_pos = stream.tell()
        pos_on_line = 0

        while stream.tell() == line_end_pos:
            pos_on_line += 1
            if init_pos < pos_on_line:
                pos_on_line -= 1
                break
            stream.seek(init_pos - pos_on_line)
            stream.readline()
        else:
            if pos_on_line:
                pos_on_line -= 1

        stream.seek(init_pos - pos_on_line)
        line = stream.readline()
        matching = regex.search(line, start=pos_on_line)
        match_shift = init_pos - pos_on_line

    # Check that no charaters are skipped in case ws-only is enabled
    if matching:
        leading_string = stream_read_pos(stream, init_pos, match_shift + matching.start())
        if ws_only and leading_string and not leading_string.isspace():
            stream.seek(init_pos)
            return None, []
    else:
        stream.seek(init_pos)
        return None, []
        
    # Get span of current matching, taking into account the lookback operation
    match_span = (match_shift + matching.start(), match_shift + matching.end())

    # Do not allow matching past a boundary positition, if provided
    if boundary and match_span[1] > boundary:
        stream.seek(init_pos)
        return None, []
    
    # Include \n in match span if regex matches on end of line $
    if "$" in regex._pattern and matching.end() + 1 == len(line):
        newline_matching = regex.search(line[:-1])
        if newline_matching and newline_matching.span() == matching.span():
            match_span = (match_shift + matching.start(), match_shift + matching.end() + 1)

    # Set anchor for next matching
    ANCHOR.set(match_span[1])

    if 0 in parsers:
        # No groups, but a parser existed. Create UnparsedElement for the single capture group
        elements = [
            UnparsedElement(
                stream=stream,
                parser=parsers[0],
                span=match_span,
            )
        ]
    elif parsers:
        # Parse each capture group
        elements = []
        for group_id, parser in parsers.items():
            try:
                group = matching.group(group_id)
            except IndexError:
                LOGGER.warning(f"The capture group {group_id} does not exist in regex {regex._pattern}")
                continue
            if not group:
                continue
            span = matching.span(group_id)

            # Create UnparsedElements for each of the capture groups. This will save time in the
            # initial round of pattern matching. Unparsed elements are parsed only when the ancestor
            # element is confirmed in the matching.
            #
            # It is not needed to worry about the ANCHOR. Since the matching end of will always be after
            # the starting positions of its capture groups.
            elements.append(
                UnparsedElement(
                    stream=stream,
                    parser=parser,
                    span=(match_shift + span[0], match_shift + span[1]),
                )
            )

    # No parsers
    else:
        elements = []

    stream.seek(match_span[1])

    return match_span, elements
