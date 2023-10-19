import sys
import pytest
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parents[2]))
sys.path.append(str(Path(__file__).parents[3]))

from textmate_grammar.handler import ContentHandler
from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = LanguageParser(matlab.GRAMMAR)
parser._initialize_repository()

test_vector = {}

# Singel quoted
test_vector[r"'This %.3f ''is'' %% a \\ string\n'"] = {
    "token": "string.quoted.single.matlab",
    "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": "'"}],
    "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
    "captures": [
        {"token": "constant.character.escape.matlab", "content": "''"},
        {"token": "constant.character.escape.matlab", "content": "''"},
        {"token": "constant.character.escape.matlab", "content": "%%"},
        {"token": "constant.character.escape.matlab", "content": "\\\\"},
        {"token": "constant.character.escape.matlab", "content": "\\n"},
    ],
}

# Double quoted
test_vector[r'"This %.3f ""is"" %% a \\ string\n"'] = {
    "token": "string.quoted.double.matlab",
    "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": '"'}],
    "end": [{"token": "punctuation.definition.string.end.matlab", "content": '"'}],
    "captures": [
        {"token": "constant.character.escape.matlab", "content": '""'},
        {"token": "constant.character.escape.matlab", "content": '""'},
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_string(check, expected):
    "Test strings"
    parsed, elements, _ = parser.parse(ContentHandler(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
