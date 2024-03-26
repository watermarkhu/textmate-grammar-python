import pytest

from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser

test_vector = {}

test_vector["... Some comment"] = {
    "token": "meta.continuation.line.matlab",
    "children": [
        {"token": "punctuation.separator.continuation.line.matlab", "content": "..."},
        {"token": "comment.continuation.line.matlab", "content": " Some comment"},
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_line_continuation(check, expected):
    """Test line continuation"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.children[0].to_dict() == expected, MSG_NOT_PARSED
