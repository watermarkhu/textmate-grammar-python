import pytest
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


test_vector = {}

# simple
test_vector["variable"] = {
    "token": "source.matlab",
    "children": [{"token": "variable.other.readwrite.matlab", "content": "variable"}],
}

# property
test_vector["variable.property"] = {
    "token": "source.matlab",
    "children": [
        {"token": "variable.other.readwrite.matlab", "content": "variable"},
        {"token": "punctuation.accessor.dot.matlab", "content": "."},
        {"token": "variable.other.property.matlab", "content": "property"},
    ],
}

# subproperty
test_vector["variable.class.property"] = {
    "token": "source.matlab",
    "children": [
        {"token": "variable.other.readwrite.matlab", "content": "variable"},
        {"token": "punctuation.accessor.dot.matlab", "content": "."},
        {"token": "variable.other.property.matlab", "content": "class"},
        {"token": "punctuation.accessor.dot.matlab", "content": "."},
        {"token": "variable.other.property.matlab", "content": "property"},
    ],
}

# property access
test_vector["variable.property(0)"] = {
    "token": "source.matlab",
    "children": [
        {"token": "variable.other.readwrite.matlab", "content": "variable"},
        {"token": "punctuation.accessor.dot.matlab", "content": "."},
        {
            "token": "meta.function-call.parens.matlab",
            "begin": [
                {"token": "entity.name.function.matlab", "content": "property"},
                {"token": "punctuation.section.parens.begin.matlab", "content": "("},
            ],
            "end": [{"token": "punctuation.section.parens.end.matlab", "content": ")"}],
            "children": [{"token": "constant.numeric.decimal.matlab", "content": "0"}],
        },
    ],
}

# class method
test_vector["variable.function(argument)"] = {
    "token": "source.matlab",
    "children": [
        {"token": "variable.other.readwrite.matlab", "content": "variable"},
        {"token": "punctuation.accessor.dot.matlab", "content": "."},
        {
            "token": "meta.function-call.parens.matlab",
            "begin": [
                {"token": "entity.name.function.matlab", "content": "function"},
                {"token": "punctuation.section.parens.begin.matlab", "content": "("},
            ],
            "end": [{"token": "punctuation.section.parens.end.matlab", "content": ")"}],
            "children": [{"content": "argument", "token": "variable.other.readwrite.matlab"}],
        },
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_readwrite_operation(check, expected):
    """Test read/write operations"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.to_dict() == expected, MSG_NOT_PARSED
