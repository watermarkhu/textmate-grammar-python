import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


GrammarParser(TMLIST["repository"]["property"], key="property")
GrammarParser(TMLIST["repository"]["readwrite_variable"], key="readwrite_variable")
GrammarParser(TMLIST["repository"]["property_access"], key="property_access")
parser = GrammarParser(TMLIST["repository"]["readwrite_operations"], key="readwrite_operations")

test_vector = [
    (
        "simple",
        "variable",
        {"token": "", "content": "variable", "captures": [{"token": "", "content": "variable"}]},
    ),
    (
        "property",
        "variable.property",
        {
            "token": "",
            "content": "variable.property",
            "captures": [{"token": "", "content": "variable.property"}],
        },
    ),
    (
        "subproperty",
        "variable.class.property",
        {
            "token": "",
            "content": "variable.class.property",
            "captures": [{"token": "", "content": "variable.class.property"}],
        },
    ),
    (
        "property access",
        "variable.property(0)",
        {"token": "", "content": "variable", "captures": [{"token": "", "content": "variable"}]},
    ),
    (
        "class method",
        "variable.function(argument)",
        {"token": "", "content": "variable", "captures": [{"token": "", "content": "variable"}]},
    ),
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_readwrite_operation(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))
    assert parsed, MSG_NO_MATCH
    assert data[0].to_dict() == expected, MSG_NOT_PARSED
