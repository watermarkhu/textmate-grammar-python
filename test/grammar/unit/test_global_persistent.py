import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


parser = GrammarParser(TMLIST["repository"]["global_persistent"], key="global_persistent")

test_vector = [
    (
        "global",
        "   global variable",
        {
            "token": "global_persistent",
            "content": "   global",
            "captures": [{"token": "storage.modifier.matlab", "content": "global"}],
        },
    ),
    (
        "persistent",
        "   persistent variable",
        {
            "token": "global_persistent",
            "content": "   persistent",
            "captures": [{"token": "storage.modifier.matlab", "content": "persistent"}],
        },
    ),
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_global_persistent(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))

    if expected:
        assert parsed, MSG_NO_MATCH
        assert data[0].to_dict() == expected, MSG_NOT_PARSED
    else:
        assert ~parsed
