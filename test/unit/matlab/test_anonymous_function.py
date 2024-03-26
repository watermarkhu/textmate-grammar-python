import pytest

from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser

test_vector = {}

# single line
test_vector["@(x,  y) x.^2+y"] = {
    "token": "meta.function.anonymous.matlab",
    "begin": [
        {"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}
    ],
    "children": [
        {
            "token": "meta.parameters.matlab",
            "begin": [
                {
                    "token": "punctuation.definition.parameters.begin.matlab",
                    "content": "(",
                }
            ],
            "end": [
                {
                    "token": "punctuation.definition.parameters.end.matlab",
                    "content": ")",
                }
            ],
            "children": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {
                    "token": "punctuation.separator.parameter.comma.matlab",
                    "content": ",",
                },
                {"token": "variable.parameter.input.matlab", "content": "y"},
            ],
        },
        {
            "token": "meta.parameters.matlab",
            "children": [
                {"token": "variable.other.readwrite.matlab", "content": "x"},
                {"token": "keyword.operator.arithmetic.matlab", "content": ".^"},
                {"token": "constant.numeric.decimal.matlab", "content": "2"},
                {"token": "keyword.operator.arithmetic.matlab", "content": "+"},
                {"token": "variable.other.readwrite.matlab", "content": "y"},
            ],
        },
    ],
}

# multiple lines
test_vector["@(x,...\n  y) x...\n   .^2+y"] = {
    "token": "meta.function.anonymous.matlab",
    "begin": [
        {"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}
    ],
    "children": [
        {
            "token": "meta.parameters.matlab",
            "begin": [
                {
                    "token": "punctuation.definition.parameters.begin.matlab",
                    "content": "(",
                }
            ],
            "end": [
                {
                    "token": "punctuation.definition.parameters.end.matlab",
                    "content": ")",
                }
            ],
            "children": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {
                    "token": "punctuation.separator.parameter.comma.matlab",
                    "content": ",",
                },
                {
                    "token": "meta.continuation.line.matlab",
                    "children": [
                        {
                            "token": "punctuation.separator.continuation.line.matlab",
                            "content": "...",
                        }
                    ],
                },
                {"token": "variable.parameter.input.matlab", "content": "y"},
            ],
        },
        {
            "token": "meta.parameters.matlab",
            "children": [
                {"token": "variable.other.readwrite.matlab", "content": "x"},
                {
                    "token": "meta.continuation.line.matlab",
                    "children": [
                        {
                            "token": "punctuation.separator.continuation.line.matlab",
                            "content": "...",
                        }
                    ],
                },
                {"token": "keyword.operator.arithmetic.matlab", "content": ".^"},
                {"token": "constant.numeric.decimal.matlab", "content": "2"},
                {"token": "keyword.operator.arithmetic.matlab", "content": "+"},
                {"token": "variable.other.readwrite.matlab", "content": "y"},
            ],
        },
    ],
}


# multiple lines with comments
test_vector["@(x,... comment\n   y)... comment \n   x... more comment\n   .^2+y"] = {
    "token": "meta.function.anonymous.matlab",
    "begin": [
        {"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}
    ],
    "children": [
        {
            "token": "meta.parameters.matlab",
            "begin": [
                {
                    "token": "punctuation.definition.parameters.begin.matlab",
                    "content": "(",
                }
            ],
            "end": [
                {
                    "token": "punctuation.definition.parameters.end.matlab",
                    "content": ")",
                }
            ],
            "children": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {
                    "token": "punctuation.separator.parameter.comma.matlab",
                    "content": ",",
                },
                {
                    "token": "meta.continuation.line.matlab",
                    "children": [
                        {
                            "token": "punctuation.separator.continuation.line.matlab",
                            "content": "...",
                        },
                        {
                            "token": "comment.continuation.line.matlab",
                            "content": " comment",
                        },
                    ],
                },
                {"token": "variable.parameter.input.matlab", "content": "y"},
            ],
        },
        {
            "token": "meta.parameters.matlab",
            "children": [
                {
                    "token": "meta.continuation.line.matlab",
                    "children": [
                        {
                            "token": "punctuation.separator.continuation.line.matlab",
                            "content": "...",
                        },
                        {
                            "token": "comment.continuation.line.matlab",
                            "content": " comment ",
                        },
                    ],
                },
                {"token": "variable.other.readwrite.matlab", "content": "x"},
                {
                    "token": "meta.continuation.line.matlab",
                    "children": [
                        {
                            "token": "punctuation.separator.continuation.line.matlab",
                            "content": "...",
                        },
                        {
                            "token": "comment.continuation.line.matlab",
                            "content": " more comment",
                        },
                    ],
                },
                {"token": "keyword.operator.arithmetic.matlab", "content": ".^"},
                {"token": "constant.numeric.decimal.matlab", "content": "2"},
                {"token": "keyword.operator.arithmetic.matlab", "content": "+"},
                {"token": "variable.other.readwrite.matlab", "content": "y"},
            ],
        },
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_anonymous_function(check, expected):
    """Test anonymous function"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.children[0].to_dict() == expected, MSG_NOT_PARSED
