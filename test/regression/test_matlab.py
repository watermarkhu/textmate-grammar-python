from pathlib import Path
import logging
import pytest

from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from . import RegressionTestClass, MODULE_ROOT

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = LanguageParser(matlab.GRAMMAR)

test_files = [
    str(MODULE_ROOT.parent / "syntaxes" / "matlab" / (file + ".m"))
    for file in [
        "Account",
        "AnEnum",
        "argumentValidation",
        "CircleArea",
        "controlFlow",
        "lineContinuations",
        "PropertyValidation",
    ]
]


@pytest.mark.parametrize("source", test_files)
class TestMatlabRegression(RegressionTestClass):
    """The regression test class for MATLAB."""

    scope = "source.matlab"

    @property
    def parser(self):
        return parser

    def test(self, source: Path | str):
        py_tokens = self.parse_python(source)
        node_tokens = self.parse_node(source)
        assert py_tokens == node_tokens
