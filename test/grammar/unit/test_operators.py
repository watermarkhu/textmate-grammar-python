import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


# See https://mathworks.com/help/matlab/matlab_prog/matlab-operators-and-special-characters.html


parser = GrammarParser(TMLIST["repository"]["operators"], key="operators")

test_vector = [
    ("function handle", "@function", {'token': 'keyword.operator.storage.at.matlab', 'content': '@'}),
    ("function handle space", "@       function", {'token': 'keyword.operator.storage.at.matlab', 'content': '@'}),
    ("function handle newline", "@\nfunction", {}),
    ("Metadata query", "?Superclass", {'token': 'keyword.operator.other.question.matlab', 'content': '?'}),
    ("Assignment operator", "variable =", {}),
    ("Colon operator", "[1:2", {'token': 'keyword.operator.vector.colon.matlab', 'content': ':'}),
    ("Colon operator line continuation", "(1:...", {'token': 'keyword.operator.vector.colon.matlab', 'content': ':'})
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_control_statement(case, input, expected):
    (parsed, data, _) = parser.parse(StringIO(input))

    if expected:
        assert parsed, MSG_NO_MATCH
        assert data[0].to_dict() == expected, MSG_NOT_PARSED
    else:
        assert ~parsed


@pytest.mark.parametrize(
    "input", ["a+b", "a-b", "a*b", "a.*b", "a/b", "a./b", "a\\b", "a.\\b", "a^b", "a.^b", "a+..."]
)
def test_arithmetic(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "keyword.operator.arithmetic.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("input", ["a==b", "a~=b", "a&b", "a&&b", "a|b", "a||b", "a==..."])
def test_logical(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "keyword.operator.logical.matlab", MSG_NO_MATCH


@pytest.mark.parametrize("input", ["a>b", "a>=b", "a<b", "a<=b", "a>..."])
def test_comparative(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "keyword.operator.relational.matlab", MSG_NO_MATCH
