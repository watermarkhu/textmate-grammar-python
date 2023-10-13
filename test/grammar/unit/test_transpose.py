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
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = LanguageParser(matlab.GRAMMAR)
parser.initialize_repository()

conjugate_transpose_test_vector = {}

# variable
conjugate_transpose_test_vector["A'"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "variable.other.readwrite.matlab", "content": "A"},
        {"token": "keyword.operator.transpose.matlab", "content": "'"},
    ],
}

# matrix
conjugate_transpose_test_vector["[1]'"] = {
    "token": "source.matlab",
    "captures": [
        {
            "token": "meta.brackets.matlab",
            "begin": [{"token": "punctuation.section.brackets.begin.matlab", "content": "["}],
            "end": [{"token": "punctuation.section.brackets.end.matlab", "content": "]"}],
            "captures": [{"token": "constant.numeric.decimal.matlab", "content": "1"}],
        },
        {"token": "keyword.operator.transpose.matlab", "content": "'"},
    ],
}

# cell
conjugate_transpose_test_vector["{1}'"] = {
    "token": "source.matlab",
    "captures": [
        {
            "token": "meta.cell.literal.matlab",
            "begin": [{"token": "punctuation.section.braces.begin.matlab", "content": "{"}],
            "end": [{"token": "punctuation.section.braces.end.matlab", "content": "}"}],
            "captures": [{"token": "constant.numeric.decimal.matlab", "content": "1"}],
        },
        {"token": "keyword.operator.transpose.matlab", "content": "'"},
    ],
}

# indexed
conjugate_transpose_test_vector["A(1)'"] = {
    "token": "source.matlab",
    "captures": [
        {
            "token": "meta.function-call.parens.matlab",
            "begin": [
                {"token": "entity.name.function.matlab", "content": "A"},
                {"token": "punctuation.section.parens.begin.matlab", "content": "("},
            ],
            "end": [{"token": "punctuation.section.parens.end.matlab", "content": ")"}],
            "captures": [{"token": "constant.numeric.decimal.matlab", "content": "1"}],
        },
        {"token": "keyword.operator.transpose.matlab", "content": "'"},
    ],
}


transpose_test_vector = {
    "A.'": {
        "token": "source.matlab",
        "captures": [
            {"token": "variable.other.readwrite.matlab", "content": "A"},
            {"token": "keyword.operator.transpose.matlab", "content": ".'"},
        ],
    }
}


@pytest.mark.parametrize("check,expected", conjugate_transpose_test_vector.items())
def test_conjugate_transpose(check, expected):
    """Test conjugate transpose"""
    element = parser.parse_language(StringIO(check))
    assert element, MSG_NO_MATCH
    assert element.to_dict() == expected, MSG_NOT_PARSED


@pytest.mark.parametrize("check,expected", transpose_test_vector.items())
def test_transpose(check, expected):
    """Test transpose"""
    element = parser.parse_language(StringIO(check))
    assert element, MSG_NO_MATCH
    assert element.to_dict() == expected, MSG_NOT_PARSED
