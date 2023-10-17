from typing import Union, Optional
from pathlib import Path
import logging

from .parser import GrammarParser, PatternsParser
from .exceptions import IncompatibleFileType
from .elements import ContentElement
from .logging import LOGGER
from .handler import ContentHandler, POS


LANGUAGE_PARSERS = {}


class DummyParser(GrammarParser):
    """A dummy parser object"""

    def __init__(self):
        self.key = "DummyLanguage"
        self.initialized = True

    def initialize_repository(self):
        pass

    def _parse(self, *args, **kwargs):
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
        self.injections = {}

        # Initalize grammars in repository
        for repo in gen_repositories(grammar):
            for key, parser_grammar in repo.items():
                self.repository[key] = GrammarParser.initialize(parser_grammar, key=key, language=self)

        # Initialize injections
        injections = grammar.get("injections", {})
        for key, injected_grammar in injections.items():
            self.injections[key] = GrammarParser.initialize(injected_grammar, key=key, language=self)

        # Update language parser store
        LANGUAGE_PARSERS[grammar.get("scopeName", "myScope")] = self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.key}"

    @staticmethod
    def _find_include_scopes(key: str):
        return LANGUAGE_PARSERS.get(key, DummyParser())

    def initialize_repository(self):
        """When the grammar has patterns, this method should called to initialize its inclusions."""
        super().initialize_repository()

        for key, injected_parser in self.injections.items():
            injected_parser.initialize_repository()
            parser_to_inject = self._find_include(key.split(" ")[0])  # TODO this is a hack
            parser_to_inject.injected_patterns.append(injected_parser)

    def parse_file(self, filePath: str | Path, log_level: int = logging.CRITICAL, **kwargs) -> ContentElement | None:
        """Parses an entire file with the current grammar"""
        if type(filePath) != Path:
            filePath = Path(filePath)

        if filePath.suffix.split(".")[-1] not in self.file_types:
            raise IncompatibleFileType(extensions=self.file_types)

        handler = ContentHandler.from_path(filePath)

        # Configure logger
        LOGGER.configure(self, height=len(handler.lines), width=max(handler.line_lengths), level=log_level)

        return self.parse_language(handler, **kwargs)

    def parse_language(self, handler: ContentHandler, **kwargs) -> ContentElement | None:
        """Parses the current stream with the language scope."""

        parsed, elements, span = self.parse(handler, (0, 0), **kwargs)

        if parsed:
            element = ContentElement(
                token=self.token, grammar=self.grammar, content=handler.source, indices=handler.range(*span), captures=elements
            )
        else:
            element = None
        return element

    def _parse(
        self, handler: ContentHandler, starting: POS, find_one: bool = False, **kwargs
    ) -> tuple[bool, list[ContentElement], tuple[int, int]]:
        return super()._parse(handler, starting, find_one=find_one, injections=True, **kwargs)


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
