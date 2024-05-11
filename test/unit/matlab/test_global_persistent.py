import pytest

from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED

test_vector = {}

test_vector["   global variable"] = {
    "token": "source.matlab",
    "children": [
        {"token": "storage.modifier.matlab", "content": "global"},
        {"token": "variable.other.readwrite.matlab", "content": "variable"},
    ],
}

test_vector["   persistent variable"] = {
    "token": "source.matlab",
    "children": [
        {"token": "storage.modifier.matlab", "content": "persistent"},
        {"token": "variable.other.readwrite.matlab", "content": "variable"},
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_global_persistent(parser, check, expected):
    """Test global persistent"""
    element = parser.parse_string(check)
    assert element is not None, MSG_NO_MATCH
    assert element.to_dict() == expected, MSG_NOT_PARSED
