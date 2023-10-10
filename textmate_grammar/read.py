from io import TextIOBase
from .exceptions import ImpossibleSpan


def stream_read_pos(stream: TextIOBase, start_pos: int, close_pos: int) -> str:
    """Reads the stream between the start and end positions."""
    return stream_read_length(stream, start_pos, close_pos - start_pos)


def stream_read_length(stream: TextIOBase, start_pos: int, length: int, skip_newline:bool = True) -> str:
    """Reads the stream from start for a length"""
    if length < 0:
        raise ImpossibleSpan
    init_pos = stream.tell()
    stream.seek(start_pos)
    content = stream.read(length)
    stream.seek(init_pos)
    return content[:-1] if skip_newline and content and content[-1] == "\n" else content

