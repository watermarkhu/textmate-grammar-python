from pathlib import Path
import logging
import pytest


from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from . import RegressionTestClass, MODULE_ROOT


test_files = [
    str(MODULE_ROOT.parent / "syntaxes" / "matlab" / (file + ".m"))
    for file in [
        "Account",
        # "AnEnum",
        # "argumentValidation",
        # "CircleArea",
        # "controlFlow",
        # "lineContinuations",
        # "PropertyValidation",
    ]
]


@pytest.mark.parametrize("source", test_files)
class TestMatlabRegression(RegressionTestClass):
    """The regression test class for MATLAB."""

    scope = "source.matlab"

    @classmethod
    def setup_class(cls) -> None:
        cls._parser = LanguageParser(matlab.GRAMMAR, log_level=logging.DEBUG)

    @property
    def parser(self):
        return self._parser

    def test(self, source: Path | str):
        py_tokens = self.parse_python(source)
        node_tokens = self.parse_node(source)
        assert py_tokens == node_tokens
