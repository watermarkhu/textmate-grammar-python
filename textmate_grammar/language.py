from typing import Union, Optional
from pathlib import Path
from io import StringIO, TextIOBase
import logging

from .parser import GrammarParser, PatternsParser, init_parser
from .exceptions import IncompatibleFileType, FileNotFound
from .elements import ContentElement, UnparsedElement
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
        self.injections = {}

        # Initalize grammars in repository
        for repo in gen_repositories(grammar):
            for key, parser_grammar in repo.items():
                self.repository[key] = init_parser(parser_grammar, key=key, language=self)

        # Initialize injections
        injections = grammar.get("injections", {})
        for key, injected_grammar in injections.items():
            self.injections[key] = init_parser(injected_grammar, key=key, language=self)

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

        return self.parse_language(stream, **kwargs)
    
    def parse_language(self, stream: TextIOBase, **kwargs):
        """Parses the current stream with the language scope."""

        stream.seek(0)
        parsed, elements, span = self.parse(stream, find_one=False, top_level=True, **kwargs)

        if parsed:
            stream.seek(0)
            content = stream.read()
            element = ContentElement(
                token=self.token, grammar=self.grammar, content=content, span=span, captures=elements
            )
        else:
            element = None
        return element
    
    # TODO top_level should be default False, but currently unexpected bahavior
    def parse(self, stream, *args, top_level:bool=True, **kwargs):
        """The parse method for grammars for a language pattern"""
        parsed, elements, span = super().parse(stream, *args, injections=True, **kwargs)

        if top_level:

            LOGGER.info("-------------------------------", parser=self)
            LOGGER.info("Start parsing unparsed elements", parser=self)
            LOGGER.info("-------------------------------", parser=self)

            parsed_elements = []
            for element in elements:
                if isinstance(element, UnparsedElement):
                    parsed_elements.extend(element.parse())
                else:
                    parsed_elements.append(element.parse_unparsed())

            if parsed:
                stream.seek(span[1])

            return parsed, parsed_elements, span
        
        else:
            return parsed, elements, span

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
