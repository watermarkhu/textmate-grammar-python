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

test_vector = {}

#dot index
test_vector["var.field"] = {'token': 'punctuation.accessor.dot.matlab', 'content': '.'}
#statement separator
test_vector[","] = {'token': 'punctuation.separator.comma.matlab', 'content': ','}
#output termination
test_vector["end;"] = {'token': 'punctuation.terminator.semicolon.matlab', 'content': ';'}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_punctuation(check, expected):
    """Test punctuation"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED