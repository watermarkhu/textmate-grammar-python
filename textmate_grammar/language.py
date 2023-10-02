from typing import List, Union, Tuple, Optional
from pathlib import Path
from io import StringIO
from .parser import GrammarParser, PatternsParser, init_parser
from .exceptions import IncompatibleFileType, FileNotFound, FileNotParsed
from .elements import ContentElement


LANGUAGE_PARSERS = {}


class DummyParser(GrammarParser):
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
        self.name = grammar.get("name", "")
        self.uuid = grammar.get("uuid", "")
        self.file_types = grammar.get("fileTypes", [])
        self.token = grammar.get("scopeName", "myScope")

        self.repository = {}
        for repo in gen_repositories(grammar):
            for key, rules in repo.items():
                self.repository[key] = init_parser(rules, key=key, language=self)

        super().__init__(grammar, key=grammar.get("name", "myLanguage"), language=self, **kwargs)

        LANGUAGE_PARSERS[grammar.get("scopeName", "myScope")] = self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.key}"

    @staticmethod
    def _find_include_scopes(key: str):
        return LANGUAGE_PARSERS.get(key, DummyParser())

    def parse_file(
        self, filePath: Union[str, Path], **kwargs
    ) -> Optional[ContentElement]:
        if type(filePath) != Path:
            filePath = Path(filePath)

        if filePath.suffix.split('.')[-1] not in self.file_types:
            raise IncompatibleFileType(extensions=self.file_types)

        if not filePath.exists():
            raise FileNotFound(str(filePath))
        
        with open(filePath, "r") as file:
            content = file.read()
        content = content.replace("\r\n", "\n")
        content = content.replace("\r", "\n")
        stream = StringIO(content)

        parsed, elements, _ = self.parse(stream, find_one=False, **kwargs)
        elements = [element.parse_unparsed() for element in elements]

        return parsed, elements



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
