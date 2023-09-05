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

test_vector = {}

test_vector["break"] = {
    "token": "meta.control.matlab",
    "content": "break",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "break"}],
}

test_vector["continue"] = {
    "token": "meta.control.matlab",
    "content": "continue",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "continue"}],
}

test_vector[";return"] = {
    "token": "meta.control.matlab",
    "content": "return",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "return"}],
}

test_vector["mybreak"] = None


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_control_statement(check, expected):
    """Test control statement"""
    elements = parser.parse(StringIO(check))
    if expected:
        assert elements, MSG_NO_MATCH
        assert elements[0].to_dict() == expected, MSG_NOT_PARSED
    else:
        assert not elements
