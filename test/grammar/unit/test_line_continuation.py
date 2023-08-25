import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


parser = GrammarParser(TMLIST["repository"]["line_continuation"], key="line_continuation")

test_vector = [
    (
        "line continuation",
        "... Some comment",
        {
            "token": "meta.continuation.line.matlab",
            "content": "... Some comment",
            "captures": [
                {"token": "punctuation.separator.continuation.line.matlab", "content": "..."},
                {"token": "comment.continuation.line.matlab", "content": " Some comment"},
            ],
        },
    )
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_line_continuation(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))
    assert parsed, MSG_NO_MATCH
    assert data[0].to_dict() == expected, MSG_NOT_PARSED
