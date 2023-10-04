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
    parsed, elements, _ = parser.parse(StringIO(check))
    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
