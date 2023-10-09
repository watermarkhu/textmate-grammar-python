import sys
import logging
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.DEBUG)
parser = LanguageParser(matlab.GRAMMAR)
parser.initialize_repository()


test_vector = {}

# single line
test_vector["@(x,  y) x.^2+y;"] = {
    "token": "meta.function.anonymous.matlab",
    "begin": [{"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}],
    "captures": [
        {
            "token": "meta.parameters.matlab",
            "begin": [{"token": "punctuation.definition.parameters.begin.matlab", "content": "("}],
            "end": [{"token": "punctuation.definition.parameters.end.matlab", "content": ")"}],
            "captures": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {"token": "punctuation.separator.parameter.comma.matlab", "content": ","},
                {"token": "variable.parameter.input.matlab", "content": "y"},
            ],
        },
        {
            "token": "meta.parameters.matlab",
            "captures": [
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
    "begin": [{"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}],
    "captures": [
        {
            "token": "meta.parameters.matlab",
            "begin": [{"token": "punctuation.definition.parameters.begin.matlab", "content": "("}],
            "end": [{"token": "punctuation.definition.parameters.end.matlab", "content": ")"}],
            "captures": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {"token": "punctuation.separator.parameter.comma.matlab", "content": ","},
                {
                    "token": "meta.continuation.line.matlab",
                    "captures": [{"token": "punctuation.separator.continuation.line.matlab", "content": "..."}],
                },
                {"token": "variable.parameter.input.matlab", "content": "y"},
            ],
        },
        {
            "token": "meta.parameters.matlab",
            "captures": [
                {"token": "variable.other.readwrite.matlab", "content": "x"},
                {
                    "token": "meta.continuation.line.matlab",
                    "captures": [{"token": "punctuation.separator.continuation.line.matlab", "content": "..."}],
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
    "begin": [{"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}],
    "captures": [
        {
            "token": "meta.parameters.matlab",
            "begin": [{"token": "punctuation.definition.parameters.begin.matlab", "content": "("}],
            "end": [{"token": "punctuation.definition.parameters.end.matlab", "content": ")"}],
            "captures": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {"token": "punctuation.separator.parameter.comma.matlab", "content": ","},
                {
                    "token": "meta.continuation.line.matlab",
                    "captures": [
                        {"token": "punctuation.separator.continuation.line.matlab", "content": "..."},
                        {"token": "comment.continuation.line.matlab", "content": " comment"},
                    ],
                },
                {"token": "variable.parameter.input.matlab", "content": "y"},
            ],
        },
        {
            "token": "meta.parameters.matlab",
            "captures": [
                {
                    "token": "meta.continuation.line.matlab",
                    "captures": [
                        {"token": "punctuation.separator.continuation.line.matlab", "content": "..."},
                        {"token": "comment.continuation.line.matlab", "content": " comment "},
                    ],
                },
                {"token": "variable.other.readwrite.matlab", "content": "x"},
                {
                    "token": "meta.continuation.line.matlab",
                    "captures": [
                        {"token": "punctuation.separator.continuation.line.matlab", "content": "..."},
                        {"token": "comment.continuation.line.matlab", "content": " more comment"},
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
    parsed, elements, _ = parser.parse(StringIO(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
