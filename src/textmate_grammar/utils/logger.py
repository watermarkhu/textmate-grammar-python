from __future__ import annotations

import logging
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parser import GrammarParser


MAX_LENGTH = 79


def track_depth(func):
    """Simple decorator to track recusion depth."""

    @wraps(func)
    def wrapper(*args, depth: int = -1, **kwargs):
        return func(*args, depth=depth + 1, **kwargs)

    return wrapper


class LogFormatter(logging.Formatter):
    """
    A custom log formatter that formats log records with color-coded messages.
    """

    green = "\x1b[32;32m"
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_string = "%(name)s:%(message)s"

    FORMATS = {
        logging.DEBUG: green + format_string + reset,
        logging.INFO: grey + format_string + reset,
        logging.WARNING: yellow + format_string + reset,
        logging.ERROR: red + format_string + reset,
        logging.CRITICAL: bold_red + format_string + reset,
    }

    def format(self, record):
        """
        Formats the log record with the color-coded format based on the log level.

        :param record: The log record to be formatted.
        :return: The formatted log message.
        """
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class Logger:
    """
    The logger object for the grammar parsers.
    """

    long_msg_div = "\x1b[1;32m ... \x1b[0m"

    def __init__(self, **kwargs) -> None:
        self.id = None
        self.max_token_length = 50
        self.line_decimals = 3
        self.position_decimals = 3
        self.scope = "UNKNOWN"
        self.logger = logging.getLogger("textmate_grammar")
        channel = logging.StreamHandler()
        channel.setFormatter(LogFormatter())
        self.logger.addHandler(channel)

    def configure(self, parser: GrammarParser, height: int, width: int, **kwargs) -> None:
        """Configures the logger to a specific grammar and content length"""
        self.line_decimals = len(str(height))
        self.position_decimals = len(str(width))
        id = parser.token if parser.token else parser.key
        if self.id != id:
            self.id = id
            tokens = _gen_all_tokens(parser.grammar)
            self.max_token_length = max(len(token) for token in tokens)
            self.scope = parser.token

    def format_message(
        self,
        message: str,
        parser: GrammarParser | None = None,
        position: tuple[int, int] | None = None,
        depth: int = 0,
    ) -> str:
        """
        Formats a logging message to the defined format.

        :param message: The logging message to be formatted.
        :param parser: The GrammarParser object associated with the message. Defaults to None.
        :param position: The position tuple (line, column) associated with the message. Defaults to None.
        :param depth: The depth of the message in the logging hierarchy. Defaults to 0.
        :return: The formatted logging message.
        """
        if position:
            msg_pos = "{:{ll}d}-{:{lp}d}".format(
                *position, ll=self.line_decimals, lp=self.position_decimals
            ).replace(" ", "0")
        else:
            msg_pos = "." * (self.line_decimals + self.position_decimals + 1)

        if parser:
            parser_id = parser.token if parser.token else parser.key
            msg_id = (
                "." * (self.max_token_length - len(parser_id)) + parser_id[: self.max_token_length]
            )
        else:
            msg_id = "." * self.max_token_length

        vb_message = f"{'|'*(depth-1)}{'-'*bool(depth)}{message}"

        if len(vb_message) > MAX_LENGTH:
            half_length = min([(MAX_LENGTH - 6) // 2, (len(vb_message) - 6) // 2])
            vb_message = vb_message[:half_length] + self.long_msg_div + vb_message[-half_length:]

        return f"{self.scope}:{msg_pos}:{msg_id}: {vb_message}"

    def debug(self, *args, **kwargs) -> None:
        if self.logger.getEffectiveLevel() > logging.DEBUG:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.debug(message)

    def info(self, *args, **kwargs) -> None:
        if self.logger.getEffectiveLevel() > logging.INFO:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.info(message)

    def warning(self, *args, **kwargs) -> None:
        if self.logger.getEffectiveLevel() > logging.WARNING:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.warning(message)

    def error(self, *args, **kwargs) -> None:
        if self.logger.getEffectiveLevel() > logging.ERROR:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.error(message)

    def critical(self, *args, **kwargs) -> None:
        if self.logger.getEffectiveLevel() > logging.CRITICAL:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.critical(message)


def _gen_all_tokens(grammar: dict, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    for key, value in grammar.items():
        if key in ["name", "contentName"]:
            items.append(value)
        elif isinstance(value, list):
            for nested_grammar in (item for item in value if isinstance(item, dict)):
                _gen_all_tokens(nested_grammar, items)
        elif isinstance(value, dict):
            _gen_all_tokens(value, items)
    return items


LOGGER = Logger()
