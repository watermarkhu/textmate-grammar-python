import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


GrammarParser(TMLIST["repository"]["shell_string"], key="shell_string")
GrammarParser(TMLIST["repository"]["string_quoted_single"], key="string_quoted_single")
GrammarParser(TMLIST["repository"]["string_quoted_double"], key="string_quoted_double")
parser = GrammarParser(TMLIST["repository"]["string"], key="string")

test_vector = [
    (   
        "single quoted",
        r"'This %.3f ''is'' %% a \\ string\n'",
        {
            "token": "string.quoted.single.matlab",
            "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": "'"}],
            "content": "'This %.3f ''is'' %% a \\\\ string\\n'",
            "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
            "captures": [
                {"token": "constant.character.escape.matlab", "content": "%.3f"},
                {"token": "constant.character.escape.matlab", "content": "''"},
                {"token": "constant.character.escape.matlab", "content": "''"},
                {"token": "constant.character.escape.matlab", "content": "%%"},
                {"token": "constant.character.escape.matlab", "content": "\\\\"},
                {"token": "constant.character.escape.matlab", "content": "\\n"},
            ],
        },
    ),
    (
        "double quoted",
        r'"This %.3f ""is"" %% a \\ string\n"',
        {
            "token": "string.quoted.double.matlab",
            "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": '"'}],
            "content": '"This %.3f ""is"" %% a \\\\ string\\n"',
            "end": [{"token": "punctuation.definition.string.end.matlab", "content": '"'}],
            "captures": [
                {"token": "constant.character.escape.matlab", "content": '""'},
                {"token": "constant.character.escape.matlab", "content": '""'},
            ],
        },
    ),
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_string(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))
    assert parsed, MSG_NO_MATCH
    assert data[0].to_dict() == expected, MSG_NOT_PARSED
