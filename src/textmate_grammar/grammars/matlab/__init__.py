from __future__ import annotations

import plistlib
import re
import yaml

from pathlib import Path

from .. import BasePreProcessor


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
        GRAMMAR = plistlib.load(tmFile, fmt=plistlib.FMT_XML)
    with open(tmLanguageYAML, "w") as ymlFile:
        ymlFile.write(yaml.dump(GRAMMAR, indent=2))
else:
    with open(tmLanguageYAML) as ymlFile:
        try:
            GRAMMAR = yaml.load(ymlFile.read(), Loader=yaml.CLoader)
        except ImportError:
            GRAMMAR = yaml.load(ymlFile.read(), Loader=yaml.Loader)


class RemoveLineContinationsPreProcessor(BasePreProcessor):
    """The pre-processor for the MATLAB language."""

    def process(self, input: str) -> str:
        """Process the input text."""
        output = ""
        for split in input.split("..."):
            matching = re.search(r'\n[\t\f\v ]*', split)
            if matching:
                output += split[matching.span()[1]:]
            else:
                output += split
        return output
