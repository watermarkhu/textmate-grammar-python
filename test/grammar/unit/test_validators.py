import sys
import logging
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from textmate_grammar.elements import UnparsedElement
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
matlabParser = LanguageParser(matlab.GRAMMAR)
matlabParser.initialize_repository()
parser = matlabParser.repository["validators"]


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
    "captures": [
        {"token": "punctuation.section.parens.begin.matlab", "content": "("},
        {
            "token": "meta.parens.size.matlab",
            "captures": [
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
    "captures": [
        {"token": "punctuation.section.parens.begin.matlab", "content": "("},
        {
            "token": "meta.parens.size.matlab",
            "captures": [
                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                {"token": "punctuation.separator.comma.matlab", "content": ","},
                {"token": "keyword.operator.vector.colon.matlab", "content": ":"},
            ],
        },
        {"token": "punctuation.section.parens.end.matlab", "content": ")"},
        {
            "token": "meta.block.validation.matlab",
            "begin": [{"token": "punctuation.section.block.begin.matlab", "content": "{"}],
            "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
            "content": "mustBeNumeric,mustBeReal",
        },
    ],
}

# string in validation function
test_vector["method {mustBeMember(method,{'linear','spline'})}\n"] = {
    "token": "meta.assignment.definition.property.matlab",
    "begin": [{"token": "variable.object.property.matlab", "content": "method"}],
    "captures": [
        {
            "token": "meta.block.validation.matlab",
            "begin": [{"token": "punctuation.section.block.begin.matlab", "content": "{"}],
            "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
            "captures": [
                {
                    "token": "meta.block.validation.matlab",
                    "begin": [{"token": "punctuation.section.block.begin.matlab", "content": "{"}],
                    "end": [{"token": "punctuation.section.block.end.matlab", "content": "}"}],
                    "captures": [
                        {
                            "token": "string.quoted.single.matlab",
                            "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": "'"}],
                            "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
                            "content": "'linear'",
                        },
                        {
                            "token": "string.quoted.single.matlab",
                            "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": "'"}],
                            "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
                            "content": "'spline'",
                        },
                    ],
                }
            ],
        }
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_validators(check, expected):
    """Test validators"""
    parsed, unparsed_elements, _ = parser.parse(StringIO(check), find_one=False)

    elements = []
    for element in unparsed_elements:
        if isinstance(element, UnparsedElement):
            elements.extend(element.parse())
        else:
            elements.append(element.parse_unparsed())

    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
