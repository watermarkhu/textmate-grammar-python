import pytest
from textmate_grammar.handler import ContentHandler
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


test_vector = {}

# function handle
test_vector["@function"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "keyword.operator.storage.at.matlab", "content": "@"},
        {"token": "variable.other.readwrite.matlab", "content": "function"},
    ],
}

# function handle space
test_vector["@    function"] = test_vector["@function"]


# Metaelements query
test_vector["?Superclass"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "keyword.operator.other.question.matlab", "content": "?"},
        {"token": "variable.other.readwrite.matlab", "content": "Superclass"},
    ],
}
# Assignment operator
test_vector["variable ="] = {
    "token": "source.matlab",
    "captures": [
        {
            "token": "meta.assignment.variable.single.matlab",
            "captures": [{"token": "variable.other.readwrite.matlab", "content": "variable"}],
        },
        {"token": "keyword.operator.assignment.matlab", "content": "="},
    ],
}

# Colon operator
test_vector["[1:2]"] = {
    "token": "source.matlab",
    "captures": [
        {
            "token": "meta.brackets.matlab",
            "begin": [{"token": "punctuation.section.brackets.begin.matlab", "content": "["}],
            "end": [{"token": "punctuation.section.brackets.end.matlab", "content": "]"}],
            "captures": [
                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                {"token": "keyword.operator.vector.colon.matlab", "content": ":"},
                {"token": "constant.numeric.decimal.matlab", "content": "2"},
            ],
        }
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_control_statement(check, expected):
    """Test operator control statements"""
    element = parser.parse_language(ContentHandler(check))
    if expected:
        assert element, MSG_NO_MATCH
        assert element.to_dict() == expected, MSG_NOT_PARSED
    else:
        assert element is None


@pytest.mark.parametrize(
    "check", ["a+b", "a-b", "a*b", "a.*b", "a/b", "a./b", "a\\b", "a.\\b", "a^b", "a.^b"]
)
def test_arithmetic(check):
    """Test arithmatic operators"""
    element = parser.parse_language(ContentHandler(check))
    assert element, MSG_NO_MATCH
    assert element.captures[1].token == "keyword.operator.arithmetic.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check", ["a==b", "a~=b", "a&b", "a&&b", "a|b", "a||b"])
def test_logical(check):
    """Test logical operators"""
    element = parser.parse_language(ContentHandler(check))
    assert element, MSG_NO_MATCH
    assert element.captures[1].token == "keyword.operator.logical.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check", ["a>b", "a>=b", "a<b", "a<=b"])
def test_comparative(check):
    """Test comparative operators"""
    element = parser.parse_language(ContentHandler(check))
    assert element, MSG_NO_MATCH
    assert element.captures[1].token == "keyword.operator.relational.matlab", MSG_NO_MATCH
