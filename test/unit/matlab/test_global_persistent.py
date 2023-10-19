import sys
import pytest
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parents[2]))
sys.path.append(str(Path(__file__).parents[3]))

from textmate_grammar.handler import ContentHandler
from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = LanguageParser(matlab.GRAMMAR)
parser._initialize_repository()


test_vector = {}

test_vector["   global variable"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "storage.modifier.matlab", "content": "global"},
        {"token": "variable.other.readwrite.matlab", "content": "variable"},
    ],
}

test_vector["   persistent variable"] = {
    "token": "source.matlab",
    "captures": [
        {"token": "storage.modifier.matlab", "content": "persistent"},
        {"token": "variable.other.readwrite.matlab", "content": "variable"},
    ],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_global_persistent(check, expected):
    """Test global persistent"""
    element = parser.parse_language(ContentHandler(check))
    assert element is not None, MSG_NO_MATCH
    assert element.to_dict() == expected, MSG_NOT_PARSED