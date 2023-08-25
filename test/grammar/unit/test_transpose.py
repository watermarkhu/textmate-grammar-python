import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED



parser_transpose = GrammarParser(TMLIST["repository"]["transpose"], key="transpose")
parser_conjugate = GrammarParser(TMLIST["repository"]["conjugate_transpose"], key="conjugate_transpose")


conjugate_transpose_test_vector = [
    ("variable", "A'", {}),
    ("matrix", "[1]'", {}),
    ("cell", "{1}'", {}),
    ("indexed", "A(1)'", {})
]


transpose_test_vector = [
    ("transpose", "A.'", {}),
]

@pytest.mark.parametrize("case,input,expected", conjugate_transpose_test_vector)
def test_conjugate_transpose(case, input,expected):
    (parsed, data, _) = parser_conjugate.parse(StringIO(input))
    assert parsed, MSG_NO_MATCH
    assert data[0].token == "keyword.operator.transpose.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("case,input,expected", transpose_test_vector)
def test_transpose(case, input,expected):
    (parsed, data, _) = parser_conjugate.parse(StringIO(input))
    assert parsed, MSG_NO_MATCH
    assert data[0].token == "keyword.operator.transpose.matlab", MSG_NO_MATCH

