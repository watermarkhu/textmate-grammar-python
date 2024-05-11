import pytest

from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED

test_vector = {}

# function handle
test_vector["@function"] = {
    "token": "source.matlab",
    "children": [
        {"token": "keyword.operator.storage.at.matlab", "content": "@"},
        {"token": "variable.other.readwrite.matlab", "content": "function"},
    ],
}

# function handle space
test_vector["@    function"] = test_vector["@function"]


# Metaelements query
test_vector["?Superclass"] = {
    "token": "source.matlab",
    "children": [
        {"token": "keyword.operator.other.question.matlab", "content": "?"},
        {"token": "variable.other.readwrite.matlab", "content": "Superclass"},
    ],
}
# Assignment operator
test_vector["variable ="] = {
    "token": "source.matlab",
    "children": [
        {
            "token": "meta.assignment.variable.single.matlab",
            "children": [
                {"token": "variable.other.readwrite.matlab", "content": "variable"}
            ],
        },
        {"token": "keyword.operator.assignment.matlab", "content": "="},
    ],
}

# Colon operator
test_vector["[1:2]"] = {
    "token": "source.matlab",
    "children": [
        {
            "token": "meta.brackets.matlab",
            "begin": [
                {"token": "punctuation.section.brackets.begin.matlab", "content": "["}
            ],
            "end": [
                {"token": "punctuation.section.brackets.end.matlab", "content": "]"}
            ],
            "children": [
                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                {"token": "keyword.operator.vector.colon.matlab", "content": ":"},
                {"token": "constant.numeric.decimal.matlab", "content": "2"},
            ],
        }
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_control_statement(parser, check, expected):
    """Test operator control statements"""
    element = parser.parse_string(check)
    if expected:
        assert element, MSG_NO_MATCH
        assert element.to_dict() == expected, MSG_NOT_PARSED
    else:
        assert element is None


@pytest.mark.parametrize(
    "check",
    ["a+b", "a-b", "a*b", "a.*b", "a/b", "a./b", "a\\b", "a.\\b", "a^b", "a.^b"],
)
def test_arithmetic(parser, check):
    """Test arithmatic operators"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert (
        element.children[1].token == "keyword.operator.arithmetic.matlab"
    ), MSG_NO_MATCH


@pytest.mark.parametrize("check", ["a==b", "a~=b", "a&b", "a&&b", "a|b", "a||b"])
def test_logical(parser, check):
    """Test logical operators"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.children[1].token == "keyword.operator.logical.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check", ["a>b", "a>=b", "a<b", "a<=b"])
def test_comparative(parser, check):
    """Test comparative operators"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert (
        element.children[1].token == "keyword.operator.relational.matlab"
    ), MSG_NO_MATCH
