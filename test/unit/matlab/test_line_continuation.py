import pytest
from textmate_grammar.handler import ContentHandler
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


test_vector = {}

test_vector["... Some comment"] = {
    "token": "meta.continuation.line.matlab",
    "captures": [
        {"token": "punctuation.separator.continuation.line.matlab", "content": "..."},
        {"token": "comment.continuation.line.matlab", "content": " Some comment"},
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_line_continuation(check, expected):
    """Test line continuation"""
    parsed, elements, _ = parser.parse(ContentHandler(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED

