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

test_vector = {}

# function handle
test_vector["@function"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "keyword.operator.storage.at.matlab", "content": "@"},
        {"token": "variable.other.readwrite.matlab", "content": "function"},
    ],
}

# function handle space
test_vector["@       function"] = test_vector["@function"]

# function handle newline
test_vector["@\nfunction"] = {}

# Metaelements query
test_vector["?Superclass"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "keyword.operator.other.question.matlab", "content": "?"},
        {"token": "variable.other.readwrite.matlab", "content": "Superclass"},
    ],
}
# Assignment operator
test_vector["variable ="] = {
    "token": "source.matlab",
    "captures": [
        {"token": "meta.assignment.variable.single.matlab", "content": "variable"},
        {"token": "keyword.operator.assignment.matlab", "content": "="},
    ],
}

# Colon operator
test_vector["[1:2]"] = {
    "token": "source.matlab",
    "captures": [
        {
            "token": "meta.brackets.matlab",
            "begin": [{"token": "punctuation.section.brackets.begin.matlab", "content": "["}],
            "end": [{"token": "punctuation.section.brackets.end.matlab", "content": "]"}],
            "captures": [
                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                {"token": "keyword.operator.vector.colon.matlab", "content": ":"},
                {"token": "constant.numeric.decimal.matlab", "content": "2"},
            ],
        }
    ],
}

# Colon operator line continuation
test_vector["(1:..."] = {
    "token": "source.matlab",
    "captures": [
        {
            "token": "meta.parens.matlab",
            "begin": [{"token": "punctuation.section.parens.begin.matlab", "content": "("}],
            "captures": [
                {"token": "constant.numeric.decimal.matlab", "content": "1"},
                {"token": "keyword.operator.vector.colon.matlab", "content": ":"},
                {
                    "token": "meta.continuation.line.matlab",
                    "captures": [{"token": "punctuation.separator.continuation.line.matlab", "content": "..."}],
                },
            ],
        }
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_control_statement(check, expected):
    """Test operator control statements"""
    element = parser.parse_language(StringIO(check))
    if expected:
        assert element, MSG_NO_MATCH
        assert element.to_dict() == expected, MSG_NOT_PARSED
    else:
        assert element is None


@pytest.mark.parametrize("check", ["a+b", "a-b", "a*b", "a.*b", "a/b", "a./b", "a\\b", "a.\\b", "a^b", "a.^b", "a+..."])
def test_arithmetic(check):
    """Test arithmatic operators"""
    parsed, elements, _ = parser.parse(StringIO(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[1].token == "keyword.operator.arithmetic.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check", ["a==b", "a~=b", "a&b", "a&&b", "a|b", "a||b", "a==..."])
def test_logical(check):
    """Test logical operators"""
    parsed, elements, _ = parser.parse(StringIO(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[1].token == "keyword.operator.logical.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check", ["a>b", "a>=b", "a<b", "a<=b", "a>..."])
def test_comparative(check):
    """Test comparative operators"""
    parsed, elements, _ = parser.parse(StringIO(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[1].token == "keyword.operator.relational.matlab", MSG_NO_MATCH
