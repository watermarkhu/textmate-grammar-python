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

test_vector = {}

test_vector["   global variable"] = {
    "token": "global_persistent",
    "content": "   global",
    "captures": [{"token": "storage.modifier.matlab", "content": "global"}],
}

test_vector["   persistent variable"] = {
    "token": "global_persistent",
    "content": "   persistent",
    "captures": [{"token": "storage.modifier.matlab", "content": "persistent"}],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_global_persistent(check, expected):
    """Test global persistent"""
    elements = parser.parse(StringIO(check))
    if expected:
        assert elements, MSG_NO_MATCH
        assert elements[0].to_dict() == expected, MSG_NOT_PARSED
    else:
        assert not elements
