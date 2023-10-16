import sys
import pytest
import logging
from pathlib import Path
sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

from textmate_grammar.handler import ContentHandler
from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = LanguageParser(matlab.GRAMMAR)
parser.initialize_repository()

test_vector = {}

test_vector["break"] = {
    "token": "meta.control.matlab",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "break"}],
}

test_vector["continue"] = {
    "token": "meta.control.matlab",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "continue"}],
}

test_vector["return"] = {
    "token": "meta.control.matlab",
    "captures": [{"token": "keyword.control.flow.matlab", "content": "return"}],
}

@pytest.mark.parametrize("check,expected", test_vector.items())
def test_control_statement(check, expected):
    """Test control statement"""
    parsed, elements, _ = parser.parse(ContentHandler(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED