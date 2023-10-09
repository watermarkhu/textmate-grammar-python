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
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].token == "keyword.operator.transpose.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("check,expected", transpose_test_vector.items())
def test_transpose(check, expected):
    """Test transpose"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].token == "keyword.operator.transpose.matlab", MSG_NO_MATCH
