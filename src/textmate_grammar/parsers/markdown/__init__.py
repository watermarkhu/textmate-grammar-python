from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from ..base import LanguageParser


class MarkdownParser(LanguageParser):
    def __init__(self, **kwargs):
        tmLanguageFile = (
            Path(__file__).parents[3] / "syntaxes" / "markdown" / "markdown.tmLanguage.base.yaml"
        )
        tmLanguageYAML = Path(__file__).parent / "grammar.yaml"

        if tmLanguageFile.exists():
            shutil.copyfile(tmLanguageFile, tmLanguageYAML)

        with open(tmLanguageYAML) as file:
            try:
                grammar = yaml.load(file.read(), Loader=yaml.CLoader)
            except ImportError:
                grammar = yaml.load(file.read(), Loader=yaml.Loader)

        super().__init__(grammar, **kwargs)
