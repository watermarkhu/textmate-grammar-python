from __future__ import annotations

import plistlib
import re
import yaml

from pathlib import Path

from .. import LanguageGrammar


class MatlabGrammar(LanguageGrammar):
    """
    Represents a grammar for the MATLAB language.
    """

    def __init__(self, remove_line_continuations: bool = False):
        """
        Initializes a new instance of the MatlabGrammar class.

        Args:
            remove_line_continuations (bool, optional): Whether to remove line continuations. Defaults to False.
        """

        self._rlc = remove_line_continuations

        tmLanguageFile = (
            Path(__file__).parents[3]
            / "syntaxes"
            / "matlab"
            / "Matlab.tmbundle"
            / "Syntaxes"
            / "MATLAB.tmLanguage"
        )
        tmLanguageYAML = Path(__file__).parent / "grammar.yaml"

        if tmLanguageFile.exists():
            with open(tmLanguageFile, "rb") as tmFile:
                self.grammar = plistlib.load(tmFile, fmt=plistlib.FMT_XML)
            with open(tmLanguageYAML, "w") as ymlFile:
                ymlFile.write(yaml.dump(self.grammar, indent=2))
        else:
            with open(tmLanguageYAML) as ymlFile:
                try:
                    self.grammar = yaml.load(ymlFile.read(), Loader=yaml.CLoader)
                except ImportError:
                    self.grammar = yaml.load(ymlFile.read(), Loader=yaml.Loader)


    def pre_process(self, input: str) -> str:
        """
        Pre-processes the input text.
        """
        if self._rlc:
            input = self._remove_line_continuations(input)
        return input


    def _remove_line_continuations(self, input: str) -> str:
        """
        Removes line continuations from the input text.
        """
        output = ""
        for split in input.split("..."):
            matching = re.search(r'\n[\t\f\v ]*', split)
            if matching:
                output += split[matching.span()[1]:]
            else:
                output += split
        return output
