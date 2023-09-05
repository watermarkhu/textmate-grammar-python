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
parser = matlabParser.get_parser("validators")


test_vector = {}

# Simple
test_vector["argument\n"] = {
    "token": "meta.assignment.definition.property.matlab",
    "content": "argument\n",
    "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
}

# default and commente
test_vector["argument = 1 % description"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
    "content": "argument = 1 % description",
    "end": [
        {
            "token": "",
            "content": "= 1 % description",
            "captures": [
                {
                    "token": "MATLAB",
                    "content": "= 1 % description",
                    "captures": [
                        {"token": "keyword.operator.assignment.matlab", "content": "="},
                        {"token": "constant.numeric.decimal.matlab", "content": "1"},
                        {"token": "", "content": "% description"},
                    ],
                }
            ],
        }
    ],
}

# size and type
test_vector["argument (1,1) string;"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
    "end": [
        {
            "token": "MATLAB",
            "content": ";",
            "captures": [{"token": "punctuation.terminator.semicolon.matlab", "content": ";"}],
        }
    ],
    "content": "argument (1,1) string;",
    "captures": [
        {
            "token": "",
            "content": " (1,1)",
            "captures": [
                {"token": "punctuation.section.parens.begin.matlab", "content": "("},
                {
                    "token": "meta.parens.size.matlab",
                    "content": "1,1",
                    "captures": [
                        {"token": "constant.numeric.decimal.matlab", "content": "1"},
                        {"token": "punctuation.separator.comma.matlab", "content": ","},
                        {"token": "constant.numeric.decimal.matlab", "content": "1"},
                    ],
                },
                {"token": "punctuation.section.parens.end.matlab", "content": ")"},
            ],
        },
        {"token": "storage.type.matlab", "content": "string"},
    ],
}


# using validation functions
test_vector["x (1,:) {mustBeNumeric,mustBeReal}\n"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "x"}],
    "content": "x (1,:) {mustBeNumeric,mustBeReal}\n",
    "captures": [
        {
            "token": "",
            "content": " (1,:)",
            "captures": [
                {"token": "punctuation.section.parens.begin.matlab", "content": "("},
                {
                    "token": "meta.parens.size.matlab",
                    "content": "1,:",
                    "captures": [
                        {"token": "constant.numeric.decimal.matlab", "content": "1"},
                        {"token": "punctuation.separator.comma.matlab", "content": ","},
                        {"token": "keyword.operator.vector.colon.matlab", "content": ":"},
                    ],
                },
                {"token": "punctuation.section.parens.end.matlab", "content": ")"},
            ],
        },
        {
            "token": "meta.block.validation.matlab",
            "begin": [{"token": "punctuation.section.block.begin.matlab", "content": "{"}],
            "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
            "content": "mustBeNumeric,mustBeReal",
        },
    ],
}

# string in validation function
test_vector["method {mustBeMember(method,{'linear','spline'})}"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "method"}],
    "content": "method {mustBeMember(method,{'linear','spline'})}",
    "captures": [
        {"token": "storage.type.matlab", "content": "mustBeMember"},
        {
            "token": "",
            "content": "(method,{'linear','spline'})",
            "captures": [
                {"token": "punctuation.section.parens.begin.matlab", "content": "("},
                {
                    "token": "meta.parens.size.matlab",
                    "content": "method,{'linear','spline'}",
                    "captures": [
                        {"token": "punctuation.separator.comma.matlab", "content": ","},
                        {"token": "punctuation.separator.comma.matlab", "content": ","},
                    ],
                },
                {"token": "punctuation.section.parens.end.matlab", "content": ")"},
            ],
        },
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_validators(check, expected):
    """Test validators"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
