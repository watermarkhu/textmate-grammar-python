from typing import Union, Optional
from pathlib import Path
from io import StringIO
import logging

from .parser import GrammarParser, PatternsParser, init_parser
from .exceptions import IncompatibleFileType, FileNotFound
from .elements import ContentElement
from .logging import LOGGER

LANGUAGE_PARSERS = {}


class DummyParser(GrammarParser):
    """A dummy parser object"""

    def __init__(self):
        self.key = "DummyLanguage"
        self.initialized = True

    def initialize_repository(self):
        pass

    def parse(self, *args, **kwargs):
        pass


class LanguageParser(PatternsParser):
    """The parser of a language grammar."""

    def __init__(self, grammar: dict, **kwargs):
        super().__init__(grammar, key=grammar.get("name", "myLanguage"), language=self, **kwargs)

        self.name = grammar.get("name", "")
        self.uuid = grammar.get("uuid", "")
        self.file_types = grammar.get("fileTypes", [])
        self.token = grammar.get("scopeName", "myScope")
        self.repository = {}

        # Initalize grammars in repository
        for repo in gen_repositories(grammar):
            for key, rules in repo.items():
                self.repository[key] = init_parser(rules, key=key, language=self)

        # Update language parser store
        LANGUAGE_PARSERS[grammar.get("scopeName", "myScope")] = self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.key}"

    @staticmethod
    def _find_include_scopes(key: str):
        return LANGUAGE_PARSERS.get(key, DummyParser())

    def parse_file(
        self, filePath: Union[str, Path], log_level: int = logging.CRITICAL, **kwargs
    ) -> Optional[ContentElement]:
        """Parses an entire file with the current grammar"""
        if type(filePath) != Path:
            filePath = Path(filePath)

        if filePath.suffix.split(".")[-1] not in self.file_types:
            raise IncompatibleFileType(extensions=self.file_types)

        if not filePath.exists():
            raise FileNotFound(str(filePath))

        # Open file and replace Windows/Mac line endings
        with open(filePath, "r") as file:
            content = file.read()
        content = content.replace("\r\n", "\n")
        content = content.replace("\r", "\n")

        # Configure logger
        LOGGER.configure(self, length=len(content), level=log_level)

        # Parse the content as a stream
        stream = StringIO(content)
        parsed, elements, _ = self.parse(stream, find_one=False, **kwargs)

        if parsed:
            # Parse all unparsed elements
            elements = [element.parse_unparsed() for element in elements]
            element = ContentElement(
                token=self.token, grammar=self.grammar, content=content, span=(0, len(content)), captures=elements
            )
        else:
            element = None

        return element


def gen_repositories(grammar, key="repository"):
    """Recursively gets all repositories from a grammar dictionary"""
    if hasattr(grammar, "items"):
        for k, v in grammar.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_repositories(v, key):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_repositories(d, key):
                        yield result
