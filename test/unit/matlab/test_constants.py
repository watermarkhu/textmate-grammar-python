import pytest
from textmate_grammar.handler import ContentHandler
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


@pytest.mark.parametrize(
    "check", ["eps", "Inf", "inf", "intmax", "intmin", "namelengthmax", "realmax", "realmin", "pi"]
)
def test_numeric(check):
    """Test constant numeric"""
    parsed, elements, _ = parser.parse(ContentHandler(check))
    assert parsed, MSG_NO_MATCH
    assert elements[0].token == "constant.numeric.matlab", MSG_NOT_PARSED


@pytest.mark.parametrize("check", ["NaN", "nan", "NaT", "nat"])
def test_value_representations(check):
    """Test constant value representations"""
    parsed, elements, _ = parser.parse(ContentHandler(check))
    assert parsed, MSG_NO_MATCH
    assert elements[0].token == "constant.language.nan.matlab", MSG_NOT_PARSED


@pytest.mark.parametrize("check", ["on", "off", "false", "true"])
def test_binary(check):
    """Test constant binary"""
    parsed, elements, _ = parser.parse(ContentHandler(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[0].token == "constant.language.boolean.matlab", MSG_NOT_PARSED
