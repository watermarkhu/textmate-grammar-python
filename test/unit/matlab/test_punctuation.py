import pytest
from textmate_grammar.handler import ContentHandler
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


test_vector = {}

# dot index
test_vector["var.field"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "variable.other.readwrite.matlab", "content": "var"},
        {"token": "punctuation.accessor.dot.matlab", "content": "."},
        {"token": "variable.other.property.matlab", "content": "field"},
    ],
}

# statement separator
test_vector[","] = {
    "token": "source.matlab",
    "captures": [{"token": "punctuation.separator.comma.matlab", "content": ","}],
}

# output termination
test_vector["var;"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "variable.other.readwrite.matlab", "content": "var"},
        {"token": "punctuation.terminator.semicolon.matlab", "content": ";"},
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_punctuation(check, expected):
    """Test punctuation"""
    element = parser.parse_language(ContentHandler(check))
    assert element, MSG_NO_MATCH
    assert element.to_dict() == expected, MSG_NOT_PARSED
