from onigurumacffi import _Pattern as Pattern, _Match as Match

from .logging import LOGGER
from .exceptions import FileNotFound, ImpossibleSpan


POS = tuple[int, int]


class ContentHandler(object):

    """The handler object targetted for parsing.
    
    To parse a string or file, it needs to be loaded into the ContentHandler object. 
    The handler will take care of all read actions on the input stream, where the contents
    are index by a tuple (line_number, line_position). Additionally, the handler contains the
    search method to match a search span against a input oniguruma regex pattern.
    """

    def __init__(self, source: str) -> None:
        self.source = source
        self.lines = [line + "\n" for line in source.split("\n")]
        self.line_lengths = [len(line) for line in self.lines]
        self.anchor: int = 0

    @classmethod
    def from_path(cls, file_path: str):
        """Loads a file from a path"""

        if not file_path.exists():
            raise FileNotFound(str(file_path))

        # Open file and replace Windows/Mac line endings
        with open(file_path, "r") as file:
            content = file.read()
        content = content.replace("\r\n", "\n")
        content = content.replace("\r", "\n")

        return cls(content)

    def _check_pos(self, pos: POS):
        if pos[0] > len(self.lines) or pos[1] > self.line_lengths[pos[0]]:
            raise ImpossibleSpan

    def next(self, pos: POS, step: int = 1) -> POS:
        """Returns the next position on the current handler"""
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
        """Returns the previous position on the current handler."""
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
        """Returns the range of positions between start and close"""
        indices = []
        if start[0] == close[0]:
            for lp in range(start[1], close[1]):
                indices.append((start[0], lp))
        else:
            for lp in range(start[1], self.line_lengths[start[0]]):
                indices.append((start[0], lp))
            for ln in range(start[0]+1, close[0]):
                for lp in range(self.line_lengths[ln]):
                    indices.append((ln, lp))
            for lp in range(close[1]):
                indices.append((close[0], lp))
        return indices
    
    def chars(self, start: POS, close: POS) -> dict[POS: str]:
        """Returns the source per position"""
        indices = self.range(start, close)
        return {pos: self.read(pos) for pos in indices}

    def read_pos(self, start_pos: POS, close_pos: POS, skip_newline: bool = True) -> str:
        """Reads the content between the start and end positions."""

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
        line = self.lines[pos[0]]
        return line[pos[1]:]

    def read(self, start_pos: POS, length: int = 1, skip_newline: bool = True) -> str:
        """Reads the content from start for a length"""
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
        leading_chars: int = 0,
        **kwargs,
    ) -> (Match | None, tuple[POS, POS] | None):
        """Matches the stream against a capture group.

        The stream is matched against the input pattern. If there are any capture groups,
        each is then subsequently parsed by the inputted parsers. The number of parsers therefor
        must match the number of capture groups of the expression, or there must be a single parser
        and no capture groups.

        leading_chars:
        - 0: none allowed
        - 1: whitespace characters allowed
        - 2: any character allowed
        """

        if pattern._pattern in ["\\z", "\\Z"]:
            leading_chars = 2

        # Get line from starting (and boundary) positions
        if boundary and starting[0] == boundary[0]:
            line = self.lines[starting[0]][:boundary[1]]
        else:
            line = self.lines[starting[0]]

        # Gets the previous matching end position from anchor in case of \G.
        init_pos = self.anchor if "\\G" in pattern._pattern else starting[1]

        # Find begin of line and search starting from the initial position
        matching = pattern.search(line, start=init_pos)

        # Check that no charaters are skipped in case ws-only is enabled
        if matching:
            leading_string = line[init_pos : matching.start()]
            if leading_string and not (leading_chars == 2 or (leading_chars == 1 and leading_string.isspace())):
                return None, None
        else:
            return None, None

        # Get span of current matching, taking into account the lookback operation
        start_pos = (starting[0], matching.start())
        close_pos = (starting[0], matching.end())

        # Do not allow matching past a boundary positition, if provided
        if boundary and close_pos > boundary:
            return None, None

        if leading_string and not leading_string.isspace() and leading_chars == 2:
            LOGGER.warning(f"skipping < {leading_string} >", position=start_pos, depth=kwargs.get("depth", 0))

        # Include \n in match span if pattern matches on end of line $
        if "$" in pattern._pattern and matching.end() + 1 == self.line_lengths[starting[0]]:
            newline_matching = pattern.search(line[:-1])
            if newline_matching and newline_matching.span() == matching.span():
                close_pos = (starting[0], matching.end() + 1)

        # Set anchor for next matching
        self.anchor = matching.end()

        return matching, (start_pos, close_pos)
