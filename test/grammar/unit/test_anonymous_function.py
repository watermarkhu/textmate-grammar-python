import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import LanguageParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


matlabParser = LanguageParser(TMLIST)
parser = matlabParser.get_parser("anonymous_function")

test_vector = {}

# single line
test_vector["@(x,  y) x.^2+y;"] = {
    "token": "meta.function.anonymous.matlab",
    "begin": [{"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}],
    "content": "@(x,  y) x.^2+y",
    "captures": [
        {
            "token": "meta.parameters.matlab",
            "begin": [{"token": "punctuation.definition.parameters.begin.matlab", "content": "("}],
            "end": [{"token": "punctuation.definition.parameters.end.matlab", "content": ")"}],
            "content": "(x,  y)",
            "captures": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {"token": "punctuation.separator.parameter.comma.matlab", "content": ","},
                {"token": "variable.parameter.input.matlab", "content": "y"},
            ],
        },
        {
            "token": "meta.parameters.matlab",
            "content": " x.^2+y",
            "captures": [
                {
                    "token": "MATLAB",
                    "content": "x.^2+y;",
                    "captures": [
                        {"token": "keyword.operator.arithmetic.matlab", "content": ".^"},
                        {"token": "constant.numeric.decimal.matlab", "content": "2"},
                        {"token": "keyword.operator.arithmetic.matlab", "content": "+"},
                        {"token": "punctuation.terminator.semicolon.matlab", "content": ";"},
                    ],
                }
            ],
        },
    ],
}

# multiple lines
test_vector["@(x,...\n  y) x...\n   .^2+y;"] = {
    "token": "meta.function.anonymous.matlab",
    "begin": [{"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}],
    "content": "@(x,...\n  y) x...\n   .^2+y",
    "captures": [
        {
            "token": "meta.parameters.matlab",
            "begin": [{"token": "punctuation.definition.parameters.begin.matlab", "content": "("}],
            "end": [{"token": "punctuation.definition.parameters.end.matlab", "content": ")"}],
            "content": "(x,...\n  y)",
            "captures": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {"token": "punctuation.separator.parameter.comma.matlab", "content": ","},
                {
                    "token": "meta.continuation.line.matlab",
                    "content": "...",
                    "captures": [
                        {"token": "punctuation.separator.continuation.line.matlab", "content": "..."}
                    ],
                },
                {"token": "variable.parameter.input.matlab", "content": "y"},
            ],
        },
        {
            "token": "meta.parameters.matlab",
            "content": " x...\n   .^2+y",
            "captures": [
                {
                    "token": "MATLAB",
                    "content": "x...\n   .^2+y;",
                    "captures": [
                        {
                            "token": "meta.continuation.line.matlab",
                            "content": "...",
                            "captures": [
                                {"token": "punctuation.separator.continuation.line.matlab", "content": "..."}
                            ],
                        },
                        {"token": "keyword.operator.arithmetic.matlab", "content": ".^"},
                        {"token": "constant.numeric.decimal.matlab", "content": "2"},
                        {"token": "keyword.operator.arithmetic.matlab", "content": "+"},
                        {"token": "punctuation.terminator.semicolon.matlab", "content": ";"},
                    ],
                }
            ],
        },
    ],
}

# multiple lines with comments
test_vector["@(x,... comment\n   y)... comment \n   x... more comment\n   .^2+y;"] = {
    "token": "meta.function.anonymous.matlab",
    "begin": [{"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}],
    "content": "@(x,... comment\n   y)... comment \n   x... more comment\n   .^2+y",
    "captures": [
        {
            "token": "meta.parameters.matlab",
            "begin": [{"token": "punctuation.definition.parameters.begin.matlab", "content": "("}],
            "end": [{"token": "punctuation.definition.parameters.end.matlab", "content": ")"}],
            "content": "(x,... comment\n   y)",
            "captures": [
                {"token": "variable.parameter.input.matlab", "content": "x"},
                {"token": "punctuation.separator.parameter.comma.matlab", "content": ","},
                {
                    "token": "meta.continuation.line.matlab",
                    "content": "... comment",
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
            "content": "... comment \n   x... more comment\n   .^2+y",
            "captures": [
                {
                    "token": "MATLAB",
                    "content": "... comment \n   x... more comment\n   .^2+y;",
                    "captures": [
                        {
                            "token": "meta.continuation.line.matlab",
                            "content": "... comment ",
                            "captures": [
                                {"token": "punctuation.separator.continuation.line.matlab", "content": "..."},
                                {"token": "comment.continuation.line.matlab", "content": " comment "},
                            ],
                        },
                        {
                            "token": "meta.continuation.line.matlab",
                            "content": "... more comment",
                            "captures": [
                                {"token": "punctuation.separator.continuation.line.matlab", "content": "..."},
                                {"token": "comment.continuation.line.matlab", "content": " more comment"},
                            ],
                        },
                        {"token": "keyword.operator.arithmetic.matlab", "content": ".^"},
                        {"token": "constant.numeric.decimal.matlab", "content": "2"},
                        {"token": "keyword.operator.arithmetic.matlab", "content": "+"},
                        {"token": "punctuation.terminator.semicolon.matlab", "content": ";"},
                    ],
                }
            ],
        },
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_anonymous_function(check, expected):
    """Test anonymous function"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
