import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


parser = GrammarParser(TMLIST["repository"]["import"], key="import")


test_vector = [
    (
        "import module",
        "import module.submodule.class",
        {
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
        },
    ),
    (
        "import with wildcard",
        "import module.submodule.*",
        {
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
        },
    ),
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_imports(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))
    assert parsed, MSG_NO_MATCH
    assert data[0].to_dict() == expected, MSG_NOT_PARSED
