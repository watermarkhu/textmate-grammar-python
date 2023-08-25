import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


parser = GrammarParser(TMLIST["repository"]["control_statements"], key="control_statements")

test_vector = [
    (
        "break",
        "   break",
        {
            "token": "meta.control.matlab",
            "content": "   break",
            "captures": [{"token": "keyword.control.flow.matlab", "content": "break"}],
        },
    ),
    (
        "continue",
        "continue",
        {
            "token": "meta.control.matlab",
            "content": "continue",
            "captures": [{"token": "keyword.control.flow.matlab", "content": "continue"}],
        },
    ),
    (
        "return",
        ";return",
        {
            "token": "meta.control.matlab",
            "content": "return",
            "captures": [{"token": "keyword.control.flow.matlab", "content": "return"}],
        },
    ),
    ("variable", "mybreak", None),
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_control_statement(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))

    if expected:
        assert parsed, MSG_NO_MATCH
        assert data[0].to_dict() == expected, MSG_NOT_PARSED
    else:
        assert ~parsed
