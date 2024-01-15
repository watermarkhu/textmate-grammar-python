import pytest
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


test_vector = {}

# Singel quoted
test_vector[r"'This %.3f ''is'' %% a \\ string\n'"] = {
    "token": "string.quoted.single.matlab",
    "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": "'"}],
    "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
    "children": [
        {"token": "constant.character.escape.matlab", "content": "%.3f"},
        {"token": "constant.character.escape.matlab", "content": "''"},
        {"token": "constant.character.escape.matlab", "content": "''"},
        {"token": "constant.character.escape.matlab", "content": "%%"},
        {"token": "constant.character.escape.matlab", "content": "\\\\"},
        {"token": "constant.character.escape.matlab", "content": "\\n"},
    ],
}

# Double quoted
test_vector[r'"This %.3f ""is"" %% a \\ string\n"'] = {
    "token": "string.quoted.double.matlab",
    "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": '"'}],
    "end": [{"token": "punctuation.definition.string.end.matlab", "content": '"'}],
    "children": [
        {"token": "constant.character.escape.matlab", "content": '""'},
        {"token": "constant.character.escape.matlab", "content": '""'},
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_string(check, expected):
    "Test strings"
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.children[0].to_dict() == expected, MSG_NOT_PARSED
