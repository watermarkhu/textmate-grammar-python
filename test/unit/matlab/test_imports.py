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

test_vector["import module.submodule.class"] = { # import module
    "token": "meta.import.matlab",
    "captures": [
        {"token": "keyword.other.import.matlab", "content": "import"},
        {
            "token": "entity.name.namespace.matlab",
            "captures": [
                {"token": "entity.name.module.matlab", "content": "module"},
                {"token": "punctuation.separator.matlab", "content": "."},
                {"token": "entity.name.module.matlab", "content": "submodule"},
                {"token": "punctuation.separator.matlab", "content": "."},
                {"token": "entity.name.module.matlab", "content": "class"},
            ],
        },
    ],
}

test_vector["import module.submodule.*"] = { #import with wildcard
    "token": "meta.import.matlab",
    "captures": [
        {"token": "keyword.other.import.matlab", "content": "import"},
        {
            "token": "entity.name.namespace.matlab",
            "captures": [
                {"token": "entity.name.module.matlab", "content": "module"},
                {"token": "punctuation.separator.matlab", "content": "."},
                {"token": "entity.name.module.matlab", "content": "submodule"},
                {"token": "punctuation.separator.matlab", "content": "."},
                {"token": "variable.language.wildcard.matlab", "content": "*"},
            ],
        },
    ],
}

@pytest.mark.parametrize("check,expected", test_vector.items())
def test_imports(check, expected):
    """Test imports"""
    parsed, elements, _ = parser.parse(ContentHandler(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED