import pytest
from textmate_grammar.handler import ContentHandler
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


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
    parsed, elements, _ = parser.parse(ContentHandler(check))
    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
