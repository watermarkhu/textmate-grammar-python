from typing import Optional
from .parser import GrammarParser, PatternsParser, init_parser


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


def gen_repositories(grammar, key="repository"):
    """Recursively gets all repositories from a grammar dictionary"""
    if hasattr(grammar,'items'):
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