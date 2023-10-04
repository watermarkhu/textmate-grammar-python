import logging
from typing import TYPE_CHECKING, Optional

logging.DEBUG
if TYPE_CHECKING:
    from .parser import GrammarParser


class Logger(object):
    """The logger object for the grammar parsers."""

    def __init__(self, **kwargs):
        self.id = None
        self.max_token_length = 50
        self.content_decimals = 4
        self.scope = "UNKNOWN"
        self.logger = logging.getLogger("textmate_grammar")
        self.logger.addHandler(logging.StreamHandler())

    def configure(self, parser: "GrammarParser", length: int, level: int = logging.CRITICAL):
        """Configures the logger to a specific grammar and content length"""
        self.content_decimals = len(str(length))
        id = parser.token if parser.token else parser.key
        if self.id != id:
            self.id = id
            tokens = gen_all_tokens(parser.grammar)
            self.max_token_length = max((len(token) for token in tokens))
            self.scope = parser.token
        self.logger.setLevel(level)

    def format_message(
        self, message: str, parser: Optional["GrammarParser"] = None, position: Optional[int] = None, verbosity: int = 0
    ):
        "Formats a logging message to the defined format"
        if position:
            msg_pos = "{:{decimals}d}".format(position, decimals=self.content_decimals).replace(" ", ".")
        else:
            msg_pos = "." * self.content_decimals
        if parser:
            parser_id = parser.token if parser.token else parser.key
            msg_id = "." * (self.max_token_length - len(parser_id)) + parser_id
        else:
            msg_id = "." * self.max_token_length

        return f"{self.scope}:{msg_pos}:{msg_id}: {'.'*verbosity}{message}"

    def debug(self, *args, **kwargs):
        if self.logger.getEffectiveLevel() > logging.DEBUG:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.debug(message)

    def info(self, *args, **kwargs):
        if self.logger.getEffectiveLevel() > logging.INFO:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.info(message)

    def warning(self, *args, **kwargs):
        if self.logger.getEffectiveLevel() > logging.WARNING:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.warning(message)

    def error(self, *args, **kwargs):
        if self.logger.getEffectiveLevel() > logging.ERROR:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.error(message)

    def critical(self, *args, **kwargs):
        if self.logger.getEffectiveLevel() > logging.CRITICAL:
            return
        message = self.format_message(*args, **kwargs)
        self.logger.critical(message)


def gen_all_tokens(grammar: dict, items: list = []):
    for key, value in grammar.items():
        if key in ["name", "contentName"]:
            items.append(value)
        elif isinstance(value, list):
            for nested_grammar in (item for item in value if isinstance(item, dict)):
                gen_all_tokens(nested_grammar, items)
        elif isinstance(value, dict):
            gen_all_tokens(value, items)
    return items


LOGGER = Logger()
