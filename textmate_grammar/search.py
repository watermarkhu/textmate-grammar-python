from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from warnings import warn
from io import TextIOBase
import onigurumacffi as re
from onigurumacffi import _Pattern as Pattern

from .elements import ContentElement, UnparsedElement
from .read import stream_read_length, stream_read_pos

if TYPE_CHECKING:
    from .parser import GrammarParser


regex_nextline = re.compile("\n|$")

class ANCHOR(object):
    """Saves the match end location for the next matching if it contains \\G. """
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
        end_pos = stream.tell()
        ANCHOR.set(end_pos)
        return (end_pos, end_pos), []
    elif regex._pattern[:2] == "\G":
        # Gets the previous matching end position from ANCHOR.
        init_pos = ANCHOR.get()

    match_shift = init_pos

    if "(?<" not in regex._pattern:
        # Simple matching without lookback
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
        # Keep performing the search on the current line while looking back one additional 
        # charater per iteration. 
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

    # Get span of current matching, taking into account the lookback operation
    match_span = (match_shift + matching.start(), match_shift + matching.end())

    # Do not allow matching past a boundary positition, if provided
    if boundary and match_span[1] > boundary:
        stream.seek(init_pos)
        return None, []
    
    # Set anchor for next matching
    ANCHOR.set(match_span[1])

    if 0 in parsers:
        # No groups, but a parser existed. Use token of parser to create element
        elements = [
            ContentElement(
                token=parsers[0].token if parsers[0].token else parsers[0].comment,
                grammar=parsers[0].grammar,
                content=stream_read_pos(stream, match_span[0], match_span[1]),
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
                warn(f"The capture group {group_id} does not exist in regex {regex._pattern}")
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
