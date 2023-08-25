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
    "input", ["eps", "Inf", "inf", "intmax", "intmin", "namelengthmax", "realmax", "realmin", "pi"]
)
def test_numeric(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "constant.numeric.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("input", ["NaN", "nan", "NaT", "nat"])
def test_value_representations(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "constant.language.nan.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("input", ["on", "off", "false", "true"])
def test_binary(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "constant.language.boolean.matlab", MSG_NO_MATCH
