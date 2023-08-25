import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


parser = GrammarParser(TMLIST["repository"]["punctuation"], key="punctuation")

test_vector = [
    ("dot index", "var.field", {'token': 'punctuation.accessor.dot.matlab', 'content': '.'}),
    ("statement separator", ",", {'token': 'punctuation.separator.comma.matlab', 'content': ','}),
    ("output termination", "end;", {'token': 'punctuation.terminator.semicolon.matlab', 'content': ';'})
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_punctuation(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))
    assert parsed, MSG_NO_MATCH
    assert data[0].to_dict() == expected, MSG_NOT_PARSED