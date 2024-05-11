import pytest
from textmate_grammar.handler import ContentHandler

from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED

test_vector = {}

# Simple
test_vector["argument\n"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
    "content": "argument",
}

# default
test_vector["argument ="] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
    "end": [{"token": "keyword.operator.assignment.matlab", "content": "="}],
    "content": "argument =",
}

# size and type
test_vector["argument (1,1) string;"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
    "end": [{"token": "punctuation.terminator.semicolon.matlab", "content": ";"}],
    "children": [
        {"token": "punctuation.section.parens.begin.matlab", "content": "("},
        {
            "token": "meta.parens.size.matlab",
            "children": [
                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                {"token": "punctuation.separator.comma.matlab", "content": ","},
                {"token": "constant.numeric.decimal.matlab", "content": "1"},
            ],
        },
        {"token": "punctuation.section.parens.end.matlab", "content": ")"},
        {"token": "storage.type.matlab", "content": "string"},
    ],
}


# using validation functions
test_vector["x (1,:) {mustBeNumeric,mustBeReal}\n"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "x"}],
    "children": [
        {"token": "punctuation.section.parens.begin.matlab", "content": "("},
        {
            "token": "meta.parens.size.matlab",
            "children": [
                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                {"token": "punctuation.separator.comma.matlab", "content": ","},
                {"token": "keyword.operator.vector.colon.matlab", "content": ":"},
            ],
        },
        {"token": "punctuation.section.parens.end.matlab", "content": ")"},
        {
            "token": "meta.block.validation.matlab",
            "begin": [
                {"token": "punctuation.section.block.begin.matlab", "content": "{"}
            ],
            "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
            "children": [
                {
                    "token": "variable.other.readwrite.matlab",
                    "content": "mustBeNumeric",
                },
                {"token": "variable.other.readwrite.matlab", "content": "mustBeReal"},
            ],
        },
    ],
}

# string in validation function
test_vector["method {mustBeMember(method,{'linear','spline'})}\n"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "method"}],
    "children": [
        {
            "token": "meta.block.validation.matlab",
            "begin": [
                {"token": "punctuation.section.block.begin.matlab", "content": "{"}
            ],
            "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
            "children": [
                {"token": "variable.other.readwrite.matlab", "content": "method"},
                {
                    "token": "meta.block.validation.matlab",
                    "begin": [
                        {
                            "token": "punctuation.section.block.begin.matlab",
                            "content": "{",
                        }
                    ],
                    "end": [
                        {
                            "token": "punctuation.section.block.end.matlab",
                            "content": "}",
                        }
                    ],
                    "children": [
                        {
                            "token": "string.quoted.single.matlab",
                            "begin": [
                                {
                                    "token": "punctuation.definition.string.begin.matlab",
                                    "content": "'",
                                }
                            ],
                            "end": [
                                {
                                    "token": "punctuation.definition.string.end.matlab",
                                    "content": "'",
                                }
                            ],
                            "content": "'linear'",
                        },
                        {
                            "token": "string.quoted.single.matlab",
                            "begin": [
                                {
                                    "token": "punctuation.definition.string.begin.matlab",
                                    "content": "'",
                                }
                            ],
                            "end": [
                                {
                                    "token": "punctuation.definition.string.end.matlab",
                                    "content": "'",
                                }
                            ],
                            "content": "'spline'",
                        },
                    ],
                },
            ],
        }
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_validators(parser, check, expected):
    """Test validators"""
    validatorParser = parser.repository["validators"]
    parsed, elements, _ = validatorParser.parse(ContentHandler(check))

    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
