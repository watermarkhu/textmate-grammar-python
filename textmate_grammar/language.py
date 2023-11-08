from pathlib import Path

from .logging import LOGGER
from .exceptions import IncompatibleFileType
from .parser import GrammarParser, PatternsParser
from .elements import ContentElement
from .handler import ContentHandler, POS


LANGUAGE_PARSERS = {}


class DummyParser(GrammarParser):
    """A dummy parser object"""

    def __init__(self):
        self.key = "DummyLanguage"
        self.initialized = True

    def _initialize_repository(self):
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
        self.injections = []

        # Initalize grammars in repository
        for repo in gen_repositories(grammar):
            for key, parser_grammar in repo.items():
                self.repository[key] = GrammarParser.initialize(parser_grammar, key=key, language=self)

        # Update language parser store
        language_name = grammar.get("scopeName", "myLanguage")
        LANGUAGE_PARSERS[language_name] = self

        self._initialize_repository()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.key}"

    @staticmethod
    def _find_include_scopes(key: str):
        return LANGUAGE_PARSERS.get(key, DummyParser())

    def _initialize_repository(self):
        """When the grammar has patterns, this method should called to initialize its inclusions."""

        # Initialize injections
        injections = self.grammar.get("injections", {})
        for key, injected_grammar in injections.items():
            target_string = key[: key.index("-")].strip()
            if not target_string:
                target_string = self.grammar.get("scopeName", "myLanguage")
            target_language = LANGUAGE_PARSERS[target_string]

            injected_parser = GrammarParser.initialize(
                injected_grammar, key=f"{target_string}.injection", language=target_language
            )
            injected_parser._initialize_repository()

            scope_string = key[key.index("-") :]
            exception_scopes = [s.strip() for s in scope_string.split("-") if s.strip()]
            target_language.injections.append([exception_scopes, injected_parser])

        super()._initialize_repository()

    def parse_file(self, filePath: str | Path, **kwargs) -> ContentElement | None:
        """Parses an entire file with the current grammar"""
        if type(filePath) != Path:
            filePath = Path(filePath)

        if filePath.suffix.split(".")[-1] not in self.file_types:
            raise IncompatibleFileType(extensions=self.file_types)

        handler = ContentHandler.from_path(filePath)

        # Configure logger
        LOGGER.configure(self, height=len(handler.lines), width=max(handler.line_lengths))

        return self._parse_language(handler, **kwargs)

    def parse_string(self, input: str, **kwargs):
        """Parses an input string"""
        handler = ContentHandler(input)
        # Configure logger
        LOGGER.configure(self, height=len(handler.lines), width=max(handler.line_lengths))
        return self._parse_language(handler, **kwargs)

    def _parse_language(self, handler: ContentHandler, **kwargs) -> ContentElement | None:
        """Parses the current stream with the language scope."""

        parsed, elements, _ = self.parse(handler, (0, 0), **kwargs)
        return elements[0] if parsed else None

    def _parse(
        self, handler: ContentHandler, starting: POS, **kwargs
    ) -> tuple[bool, list[ContentElement], tuple[int, int]]:
        kwargs.pop("find_one", None)
        return super()._parse(handler, starting, find_one=False, **kwargs)


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
