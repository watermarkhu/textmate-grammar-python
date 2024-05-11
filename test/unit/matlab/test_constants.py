import pytest

from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED


@pytest.mark.parametrize(
    "check",
    [
        "eps",
        "Inf",
        "inf",
        "intmax",
        "intmin",
        "namelengthmax",
        "realmax",
        "realmin",
        "pi",
    ],
)
def test_numeric(parser, check):
    """Test constant numeric"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.children[0].token == "constant.numeric.matlab", MSG_NOT_PARSED


@pytest.mark.parametrize("check", ["NaN", "nan", "NaT", "nat"])
def test_value_representations(parser, check):
    """Test constant value representations"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.children[0].token == "constant.language.nan.matlab", MSG_NOT_PARSED


@pytest.mark.parametrize("check", ["on", "off", "false", "true"])
def test_binary(parser, check):
    """Test constant binary"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert (
        element.children[0].token == "constant.language.boolean.matlab"
    ), MSG_NOT_PARSED
