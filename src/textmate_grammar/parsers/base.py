from __future__ import annotations

from pathlib import Path

from ..elements import Capture, ContentElement
from ..handler import POS, ContentHandler
from ..parser import GrammarParser, PatternsParser
from ..utils.cache import TextmateCache, init_cache
from ..utils.exceptions import IncompatibleFileType
from ..utils.logger import LOGGER

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
        """
        Initialize a Language object.

        :param grammar: The grammar definition for the language.
        :type grammar: dict
        :param pre_processor: A pre-processor to use on the input string of the parser
        :type pre_processor: BasePreProcessor
        :param kwargs: Additional keyword arguments.

        :ivar name: The name of the language.
        :ivar uuid: The UUID of the language.
        :ivar file_types: The file types associated with the language.
        :ivar token: The scope name of the language.
        :ivar repository: The repository of grammar rules for the language.
        :ivar injections: The list of injection rules for the language.
        :ivar _cache: The cache object for the language.
        """

        super().__init__(
            grammar, key=grammar.get("name", "myLanguage"), language_parser=self, **kwargs
        )

        self.name = grammar.get("name", "")
        self.uuid = grammar.get("uuid", "")
        self.file_types = grammar.get("fileTypes", [])
        self.token = grammar.get("scopeName", "myScope")
        self.repository = {}
        self.injections: list[dict] = []
        self._cache: TextmateCache = init_cache()

        # Initialize grammars in repository
        for repo in _gen_repositories(grammar):
            for key, parser_grammar in repo.items():
                self.repository[key] = GrammarParser.initialize(
                    parser_grammar, key=key, language_parser=self
                )

        # Update language parser store
        language_name = grammar.get("scopeName", "myLanguage")
        LANGUAGE_PARSERS[language_name] = self

        self._initialize_repository()

    def pre_process(self, input: str) -> str:
        """
        Pre-processes the input string before parsing.

        This method can be overloaded in language specific parsers with custom pre-processing logic.
        """
        return input

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
                injected_grammar,
                key=f"{target_string}.injection",
                language_parser=target_language,
            )
            injected_parser._initialize_repository()

            scope_string = key[key.index("-") :]
            exception_scopes = [s.strip() for s in scope_string.split("-") if s.strip()]
            target_language.injections.append([exception_scopes, injected_parser])

        super()._initialize_repository()

    def parse_file(self, filePath: str | Path, **kwargs) -> ContentElement | None:
        """
        Parses an entire file with the current grammar.

        :param filePath: The path to the file to be parsed.
        :param kwargs: Additional keyword arguments to be passed to the parser.
        :return: The parsed element if successful, None otherwise.
        """
        if not isinstance(filePath, Path):
            filePath = Path(filePath).resolve()

        if filePath.suffix.split(".")[-1] not in self.file_types:
            raise IncompatibleFileType(extensions=self.file_types)

        if self._cache.cache_valid(filePath):
            element = self._cache.load(filePath)
        else:
            handler = ContentHandler.from_path(filePath, pre_processor=self.pre_process, **kwargs)
            if handler.content == "":
                return None

            # Configure logger
            LOGGER.configure(self, height=len(handler.lines), width=max(handler.line_lengths))
            element = self._parse_language(handler, **kwargs)  # type: ignore

            if element is not None:
                self._cache.save(filePath, element)
        return element

    def parse_string(self, input: str, **kwargs) -> ContentElement | None:
        """
        Parses an input string.

        :param input: The input string to be parsed.
        :param kwargs: Additional keyword arguments.
        :return: The result of parsing the input string.
        """
        handler = ContentHandler(input, pre_processor=self.pre_process, **kwargs)

        # Configure logger
        LOGGER.configure(self, height=len(handler.lines), width=max(handler.line_lengths))

        element = self._parse_language(handler, **kwargs)

        return element

    def _parse_language(self, handler: ContentHandler, **kwargs) -> ContentElement | None:
        """Parses the current stream with the language scope."""

        parsed, elements, _ = self.parse(handler, (0, 0), **kwargs)

        if parsed:
            element = elements[0]
            element._dispatch(nested=True)  # type: ignore
        else:
            element = None
        return element  # type: ignore

    def _parse(
        self, handler: ContentHandler, starting: POS, **kwargs
    ) -> tuple[bool, list[Capture | ContentElement], tuple[int, int]]:
        kwargs.pop("find_one", None)
        return super()._parse(handler, starting, find_one=False, **kwargs)


def _gen_repositories(grammar, key="repository"):
    """Recursively gets all repositories from a grammar dictionary"""
    if hasattr(grammar, "items"):
        for k, v in grammar.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in _gen_repositories(v, key):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in _gen_repositories(d, key):
                        yield result
