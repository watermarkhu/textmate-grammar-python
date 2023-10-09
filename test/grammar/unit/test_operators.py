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

# function handle
test_vector["@function"] = {'token': 'keyword.operator.storage.at.matlab', 'content': '@'}

# function handle space
test_vector["@       function"] = {'token': 'keyword.operator.storage.at.matlab', 'content': '@'}

# function handle newline
test_vector["@\nfunction"] = {}

# Metaelements query
test_vector["?Superclass"] = {'token': 'keyword.operator.other.question.matlab', 'content': '?'}

# Assignment operator
test_vector["variable ="] = {'token': 'keyword.operator.assignment.matlab', 'content': '='}

# Colon operator
test_vector["[1:2"] = {'token': 'keyword.operator.vector.colon.matlab', 'content': ':'}

# Colon operator line continuation
test_vector["(1:..."] = {'token': 'keyword.operator.vector.colon.matlab', 'content': ':'}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_control_statement(check, expected):
    """Test operator control statements"""
    elements = parser.parse(StringIO(check))
    if expected:
        assert elements, MSG_NO_MATCH
        assert elements[0].to_dict() == expected, MSG_NOT_PARSED
    else:
        assert not elements


@pytest.mark.parametrize(
    "check", ["a+b", "a-b", "a*b", "a.*b", "a/b", "a./b", "a\\b", "a.\\b", "a^b", "a.^b", "a+..."]
)
def test_arithmetic(check):
    """Test arithmatic operators"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NOT_PARSED
    assert elements[0].token == "keyword.operator.arithmetic.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check", ["a==b", "a~=b", "a&b", "a&&b", "a|b", "a||b", "a==..."])
def test_logical(check):
    """Test logical operators"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NOT_PARSED
    assert elements[0].token == "keyword.operator.logical.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check", ["a>b", "a>=b", "a<b", "a<=b", "a>..."])
def test_comparative(check):
    """Test comparative operators"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NOT_PARSED
    assert elements[0].token == "keyword.operator.relational.matlab", MSG_NO_MATCH
