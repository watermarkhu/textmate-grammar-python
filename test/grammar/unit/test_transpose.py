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


conjugate_transpose_test_vector = {
    "A'": {},  # variable
    "[1]'": {},  # matrix
    "{1}'": {},  # cell
    "A(1)'": {},  # indexed
}


transpose_test_vector = {
    "A.'": {}
}

@pytest.mark.parametrize("check,expected", conjugate_transpose_test_vector.items())
def test_conjugate_transpose(check, expected):
    """Test conjugate transpose"""
    elements = parser_conjugate.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].token == "keyword.operator.transpose.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check,expected", transpose_test_vector.items())
def test_transpose(check, expected):
    """Test transpose"""
    elements = parser_transpose.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].token == "keyword.operator.transpose.matlab", MSG_NO_MATCH
