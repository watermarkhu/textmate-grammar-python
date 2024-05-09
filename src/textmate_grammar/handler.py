from __future__ import annotations

from pathlib import Path
from typing import Callable

from onigurumacffi import _Match as Match
from onigurumacffi import _Pattern as Pattern
from onigurumacffi import compile

from .utils.exceptions import FileNotFound, ImpossibleSpan
from .utils.logger import LOGGER

POS = tuple[int, int]


def _dummy_pre_processor(input: str) -> str:
    return input


class ContentHandler:
    """The handler object targetted for parsing.

    To parse a string or file, it needs to be loaded into the ContentHandler object.
    The handler will take care of all read actions on the input stream, where the contents
    are index by a tuple (line_number, line_position). Additionally, the handler contains the
    search method to match a search span against a input oniguruma regex pattern.
    """

    notLookForwardEOL = compile(r"(?<!\(\?=[^\(]*)\$")

    def __init__(
        self, content: str, pre_processor: Callable[[str], str] = _dummy_pre_processor
    ) -> None:
        """
        Initialize a new instance of the Handler class.

        :param content: The source code to be processed.
        :type content: str
        :param pre_processor: A pre-processor to use on the input string of the parser
        :type pre_processor: BasePreProcessor

        :ivar content: The source code to be processed.
        :ivar lines: A list of lines in the source code, with a newline character at the end of each line.
        :ivar line_lengths: A list of lengths of each line in the source code.
        :ivar anchor: The current position in the source code.
        """
        prepared_content = pre_processor(content.replace("\r\n", "\n").replace("\r", "\n"))

        self.content = prepared_content
        self.lines = [line + "\n" for line in prepared_content.split("\n")]
        self.line_lengths = [len(line) for line in self.lines]
        self.anchor: int = 0

    @classmethod
    def from_path(cls, file_path: Path, **kwargs) -> ContentHandler:
        """Loads a file from a path"""

        if not file_path.exists():
            raise FileNotFound(str(file_path))

        # Open file and replace Windows/Mac line endings
        with open(file_path) as file:
            content = file.read()

        return cls(content, **kwargs)

    def _check_pos(self, pos: POS):
        if pos[0] > len(self.lines) or pos[1] > self.line_lengths[pos[0]]:
            raise ImpossibleSpan

    def next(self, pos: POS, step: int = 1) -> POS:
        """Returns the next position on the current handler.

        :param pos: The current position as a tuple (line, column).
        :param step: The number of steps to move forward. Defaults to 1.
        :return: The next position as a tuple (line, column).
        """
        if step > 1:
            pos = self.next(pos, step=step - 1)
        if pos[1] == self.line_lengths[pos[0]]:
            if pos[0] == len(self.lines):
                return pos
            else:
                return (pos[0] + 1, 0)
        else:
            return (pos[0], pos[1] + 1)

    def prev(self, pos: POS, step: int = 1) -> POS:
        """Returns the previous position on the current handler.

        :param pos: The current position as a tuple (line, column).
        :param step: The number of steps to go back. Defaults to 1.
        :return: The previous position as a tuple (line, column).
        """
        if step > 1:
            pos = self.prev(pos, step=step - 1)
        if pos[1] == 0:
            if pos[0] == 0:
                return (0, 0)
            else:
                return (pos[0] - 1, self.line_lengths[pos[0] - 1])
        else:
            return (pos[0], pos[1] - 1)

    def range(self, start: POS, close: POS) -> list[POS]:
        """
        Returns a list of positions between the start and close positions.

        :param start: The starting position.
        :param close: The closing position.
        :return: A list of positions between the start and close positions.
        """
        indices = []
        if start[0] == close[0]:
            for lp in range(start[1], close[1]):
                indices.append((start[0], lp))
        else:
            for lp in range(start[1], self.line_lengths[start[0]]):
                indices.append((start[0], lp))
            for ln in range(start[0] + 1, close[0]):
                for lp in range(self.line_lengths[ln]):
                    indices.append((ln, lp))
            for lp in range(close[1]):
                indices.append((close[0], lp))
        return indices

    def chars(self, start: POS, close: POS) -> dict[POS, str]:
        """
        Returns a dictionary mapping each position within the given range to the corresponding source character.

        :param start: The starting position of the range.
        :param close: The closing position of the range.
        :return: A dictionary mapping each position within the range to the corresponding source character.
        """
        indices = self.range(start, close)
        return {pos: self.read(pos) for pos in indices}

    def read_pos(self, start_pos: POS, close_pos: POS, skip_newline: bool = True) -> str:
        """Reads the content between the start and end positions.

        :param start_pos: The starting position of the content.
        :param close_pos: The closing position of the content.
        :param skip_newline: Whether to skip the newline character at the end of the content.
        :return: The content between the start and end positions.
        :raises ImpossibleSpan: If the start position is greater than the close position.
        """
        self._check_pos(start_pos)
        self._check_pos(close_pos)
        if start_pos > close_pos:
            raise ImpossibleSpan

        if start_pos[0] == close_pos[0]:
            readout = self.lines[start_pos[0]][start_pos[1] : close_pos[1]]
        else:
            readout = ""
            for ln in range(start_pos[0], close_pos[0] + 1):
                if ln == start_pos[0]:
                    readout += self.lines[ln][start_pos[1] :]
                elif ln == close_pos[0]:
                    readout += self.lines[ln][: close_pos[1]]
                else:
                    readout += self.lines[ln]

        if skip_newline and readout and readout[-1] == "\n":
            readout = readout[:-1]

        return readout

    def read_line(self, pos: POS) -> str:
        """
        Reads a line from the specified position and returns it.

        :param pos: The position of the line to read. The first element is the line number (0-based),
                and the second element is the starting position within the line.
        :return: The line starting from the specified position.
        """
        line = self.lines[pos[0]]
        return line[pos[1] :]

    def read(self, start_pos: POS, length: int = 1, skip_newline: bool = True) -> str:
        """Reads the content from start for a length.

        :param start_pos: The starting position to read from.
        :param length: The number of characters to read. Defaults to 1.
        :param skip_newline: Whether to skip the newline character at the end of the read content. Defaults to True.
        :return: The content read from the specified position.
        :raises ImpossibleSpan: If the length is negative.
        """
        self._check_pos(start_pos)
        if length < 0:
            raise ImpossibleSpan

        remainder = self.line_lengths[start_pos[0]] - start_pos[1]

        if length <= remainder:
            readout = self.lines[start_pos[0]][start_pos[1] : (start_pos[1] + length)]
        else:
            readout = self.lines[start_pos[0]][start_pos[1] :]
            unread_length = length - remainder
            ln = start_pos[0] + 1
            if ln >= len(self.lines):
                return ""

            while unread_length > self.line_lengths[ln]:
                readout += self.lines[ln]
                unread_length -= self.line_lengths[ln]
                ln += 1
            else:
                readout += self.lines[ln][:unread_length]

        if skip_newline and readout[-1] == "\n":
            readout = readout[:-1]

        return readout

    def search(
        self,
        pattern: Pattern,
        starting: POS,
        boundary: POS | None = None,
        greedy: bool = False,
        **kwargs,
    ) -> tuple[Match | None, tuple[POS, POS] | None]:
        """Matches the stream against a capture group.

        :param pattern: The regular expression pattern to match against the stream.
        :param starting: The starting position in the stream.
        :param boundary: The boundary position in the stream. Defaults to None.
        :param greedy: Determines if the matching should be greedy or not. Defaults to False.
        :param kwargs: Additional keyword arguments.

        :return: A tuple containing the matching result and the span of the match.

        .. note::
            - The stream is matched against the input pattern. If there are any capture groups,
              each is then subsequently parsed by the inputted parsers. The number of parsers therefore
              must match the number of capture groups of the expression, or there must be a single parser
              and no capture groups.
            - The `greedy` parameter determines if the matching should be greedy or not. If set to True,
              the matching will try to consume as much of the stream as possible. If set to False,
              the matching will stop at the first match found.
            - The `boundary` parameter can be used to specify a boundary position in the stream. If provided,
              the matching will not go beyond this boundary position.
            - The `leading_chars` parameter can be used to specify the type of leading characters allowed, with:
                - `0`: none allowed
                - `1`: whitespace characters allowed
                - `2`: any character allowed.
        """

        if pattern._pattern in ["\\z", "\\Z"]:
            greedy = True

        # Get line from starting (and boundary) positions
        if boundary and starting[0] == boundary[0]:
            line = self.lines[starting[0]][: boundary[1]]
        else:
            line = self.lines[starting[0]]

        # Gets the previous matching end position from anchor in case of \G.
        init_pos = self.anchor if "\\G" in pattern._pattern else starting[1]

        # Find begin of line and search starting from the initial position
        matching = pattern.search(line, start=init_pos)

        # Check that no charaters are skipped in case ws-only is enabled
        if matching:
            leading_string = line[init_pos : matching.start()]
            if leading_string and not (greedy or (not greedy and leading_string.isspace())):
                return None, None
        else:
            return None, None

        # Get span of current matching, taking into account the lookback operation
        start_pos = (starting[0], matching.start())
        close_pos = (starting[0], matching.end())

        # Do not allow matching past a boundary positition, if provided
        if boundary and close_pos > boundary:
            return None, None

        if leading_string and not leading_string.isspace() and greedy:
            LOGGER.warning(
                f"skipping < {leading_string} >",
                position=start_pos,
                depth=kwargs.get("depth", 0),
            )

        # Include \n in match span if pattern matches on end of line $
        if (
            self.notLookForwardEOL.search(pattern._pattern)
            and matching.end() + 1 == self.line_lengths[starting[0]]
        ):
            newline_matching = pattern.search(line[:-1])
            if newline_matching and newline_matching.span() == matching.span():
                close_pos = (starting[0], matching.end() + 1)

        # Set anchor for next matching
        self.anchor = matching.end()

        return matching, (start_pos, close_pos)
