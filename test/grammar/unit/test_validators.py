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


test_vector = [
    (
        "simple",
        "argument\n",
        {
            "token": "meta.assignment.definition.property.matlab",
            "content": "argument\n",
            "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
        },
    ),
    (
        "default and comment",
        "argument = 1 % description",
        {
            "token": "meta.assignment.definition.property.matlab",
            "content": "argument = 1 % description",
            "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
            "end": [{"token": "Handle things like arg = val; nextArg", "content": "= 1 % description"}],
        },
    ),
    (
        "size and type",
        "argument (1,1) string;",
        {
            "token": "meta.assignment.definition.property.matlab",
            "content": "argument (1,1) string;",
            "captures": [
                {
                    "token": "Size declaration",
                    "content": " (1,1)",
                    "captures": [
                        {"token": "punctuation.section.parens.begin.matlab", "content": "("},
                        {
                            "token": "meta.parens.size.matlab",
                            "content": "1,1",
                            "captures": [
                                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                            ],
                        },
                        {"token": "punctuation.section.parens.end.matlab", "content": ")"},
                    ],
                },
                {"token": "storage.type.matlab", "content": "string"},
            ],
            "begin": [{"token": "variable.object.property.matlab", "content": "argument"}],
        },
    ),
    (
        "using validation functions",
        "x (1,:) {mustBeNumeric,mustBeReal}\n",
        {
            "token": "meta.assignment.definition.property.matlab",
            "content": "x (1,:) {mustBeNumeric,mustBeReal}\n",
            "captures": [
                {
                    "token": "Size declaration",
                    "content": " (1,:)",
                    "captures": [
                        {"token": "punctuation.section.parens.begin.matlab", "content": "("},
                        {
                            "token": "meta.parens.size.matlab",
                            "content": "1,:",
                            "captures": [
                                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                            ],
                        },
                        {"token": "punctuation.section.parens.end.matlab", "content": ")"},
                    ],
                },
                {
                    "token": "meta.block.validation.matlab",
                    "content": "mustBeNumeric,mustBeReal",
                    "begin": [{"token": "punctuation.section.block.begin.matlab", "content": "{"}],
                    "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
                },
            ],
            "begin": [{"token": "variable.object.property.matlab", "content": "x"}],
        },
    ),
    (
        "string in validation function",
        "method {mustBeMember(method,{'linear','spline'})}",
        {
            "token": "meta.assignment.definition.property.matlab",
            "content": "method {mustBeMember(method,{'linear','spline'})}",
            "captures": [
                {
                    "token": "meta.block.validation.matlab",
                    "content": "mustBeMember(method,{'linear','spline'})",
                    "captures": [
                        {
                            "token": "meta.block.validation.matlab",
                            "content": "'linear','spline'",
                            "captures": [
                                {
                                    "token": "string.quoted.single.matlab",
                                    "content": "'linear'",
                                    "captures": [{"token": "", "content": "linear"}],
                                    "begin": [
                                        {
                                            "token": "punctuation.definition.string.begin.matlab",
                                            "content": "'",
                                        }
                                    ],
                                    "end": [
                                        {"token": "punctuation.definition.string.end.matlab", "content": "'"}
                                    ],
                                },
                                {
                                    "token": "string.quoted.single.matlab",
                                    "content": "'spline'",
                                    "captures": [{"token": "", "content": "spline"}],
                                    "begin": [
                                        {
                                            "token": "punctuation.definition.string.begin.matlab",
                                            "content": "'",
                                        }
                                    ],
                                    "end": [
                                        {"token": "punctuation.definition.string.end.matlab", "content": "'"}
                                    ],
                                },
                            ],
                            "begin": [{"token": "punctuation.section.block.begin.matlab", "content": "{"}],
                            "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
                        },
                        {
                            "token": "string.quoted.single.matlab",
                            "content": "'spline'",
                            "captures": [{"token": "", "content": "spline"}],
                            "begin": [
                                {"token": "punctuation.definition.string.begin.matlab", "content": "'"}
                            ],
                            "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
                        },
                        {
                            "token": "string.quoted.single.matlab",
                            "content": "','spline'",
                            "captures": [
                                {"token": "", "content": ","},
                                {"token": "", "content": "'"},
                                {"token": "", "content": "spline"},
                            ],
                            "begin": [
                                {"token": "punctuation.definition.string.begin.matlab", "content": "'"}
                            ],
                            "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
                        },
                    ],
                    "begin": [{"token": "punctuation.section.block.begin.matlab", "content": "{"}],
                    "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
                }
            ],
            "begin": [{"token": "variable.object.property.matlab", "content": "method"}],
        },
    ),
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_validators(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))
    assert parsed, MSG_NO_MATCH
    assert data[0].to_dict() == expected, MSG_NOT_PARSED
