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
parser = matlabParser.get_parser("string")

test_vector = {}

# Singel quoted
test_vector[r"'This %.3f ''is'' %% a \\ string\n'"] = {
    "token": "string.quoted.single.matlab",
    "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": "'"}],
    "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
    "content": "'This %.3f ''is'' %% a \\\\ string\\n'",
    "captures": [
        {"token": "constant.character.escape.matlab", "content": "%.3f"},
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
    "content": '"This %.3f ""is"" %% a \\\\ string\\n"',
    "captures": [
        {"token": "constant.character.escape.matlab", "content": '""'},
        {"token": "constant.character.escape.matlab", "content": '""'},
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_string(check, expected):
    "Test strings"
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
