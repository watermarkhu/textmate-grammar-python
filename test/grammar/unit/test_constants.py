import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


parser = GrammarParser(TMLIST["repository"]["constants"], key="constants")


@pytest.mark.parametrize(
    "check", ["eps", "Inf", "inf", "intmax", "intmin", "namelengthmax", "realmax", "realmin", "pi"]
)
def test_numeric(check):
    """Test constant numeric"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].token == "constant.numeric.matlab", MSG_NOT_PARSED


@pytest.mark.parametrize("check", ["NaN", "nan", "NaT", "nat"])
def test_value_representations(check):
    """Test constant value representations"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].token == "constant.language.nan.matlab", MSG_NOT_PARSED


@pytest.mark.parametrize("check", ["on", "off", "false", "true"])
def test_binary(check):
    """Test constant binary"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].token == "constant.language.boolean.matlab", MSG_NOT_PARSED
