import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import LanguageParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


matlabParser = LanguageParser(TMLIST)
parser = matlabParser.get_parser("readwrite_operations")

test_vector = {}

# simple
test_vector["variable"] = {
    "token": "readwrite_operations",
    "content": "variable",
    "captures": [{"token": "", "content": "variable"}],
}

# property
test_vector["variable.property"] = {
    "token": "readwrite_operations",
    "content": "variable.property",
    "captures": [{"token": "", "content": "variable.property"}],
}

# subproperty
test_vector["variable.class.property"] = {
    "token": "readwrite_operations",
    "content": "variable.class.property",
    "captures": [{"token": "", "content": "variable.class.property"}],
}

# property access
test_vector["variable.property(0)"] = {
    "token": "readwrite_operations",
    "content": "variable",
    "captures": [{"token": "", "content": "variable"}],
}

# class method
test_vector["variable.function(argument)"] = {
    "token": "readwrite_operations",
    "content": "variable",
    "captures": [{"token": "", "content": "variable"}],
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_readwrite_operation(check, expected):
    """Test read/write operations"""
    elements = parser.parse(StringIO(check))
    assert elements, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
