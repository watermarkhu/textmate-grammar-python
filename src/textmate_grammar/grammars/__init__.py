from abc import ABC


class LanguageGrammar(ABC):
    """
    Base class for language grammars.
    """

    def __init__(self):
        self.grammar = {}

    def __call__(self) -> dict:
        """
        Returns the grammar as a dictionary.
        """
        return self.grammar

    def pre_process(self, input: str) -> str:
        """
        Pre-processes the input string before parsing.
        """
        return input
