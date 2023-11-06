import pytest
from textmate_grammar.handler import ContentHandler
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


test_vector = {}

test_vector["break"] = {
    "token": "meta.control.matlab",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "break"}],
}

test_vector["continue"] = {
    "token": "meta.control.matlab",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "continue"}],
}

test_vector["return"] = {
    "token": "meta.control.matlab",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "return"}],
}

@pytest.mark.parametrize("check,expected", test_vector.items())
def test_control_statement(check, expected):
    """Test control statement"""
    element = parser.parse_language(ContentHandler(check))
    assert element, MSG_NO_MATCH
    assert element.captures[0].to_dict() == expected, MSG_NOT_PARSED