from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from .. import LanguageGrammar

class MarkdownGrammar(LanguageGrammar):

    def __init__(self):

        tmLanguageFile = (
            Path(__file__).parents[3] / "syntaxes" / "markdown" / "markdown.tmLanguage.base.yaml"
        )
        tmLanguageYAML = Path(__file__).parent / "grammar.yaml"


        if tmLanguageFile.exists():
            shutil.copyfile(tmLanguageFile, tmLanguageYAML)

        with open(tmLanguageYAML) as file:
            try:
                self.grammar = yaml.load(file.read(), Loader=yaml.CLoader)
            except ImportError:
                self.grammar = yaml.load(file.read(), Loader=yaml.Loader)
    
    
