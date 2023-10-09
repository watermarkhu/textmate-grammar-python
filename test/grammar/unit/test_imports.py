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

test_vector["import module.submodule.class"] = { # import module
    "token": "meta.import.matlab",
    "content": "import module.submodule.class",
    "captures": [
        {"token": "keyword.other.import.matlab", "content": "import"},
        {
            "token": "entity.name.namespace.matlab",
            "content": "module.submodule.class",
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
    "content": "import module.submodule.*",
    "captures": [
        {"token": "keyword.other.import.matlab", "content": "import"},
        {
            "token": "entity.name.namespace.matlab",
            "content": "module.submodule.*",
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
    elements = parser.parse(StringIO(check))
    if expected:
        assert elements, MSG_NO_MATCH
        assert elements[0].to_dict() == expected, MSG_NOT_PARSED
    else:
        assert not elements
