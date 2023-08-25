import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


parser = GrammarParser(TMLIST["repository"]["variables"], key="variables")


@pytest.mark.parametrize("input", ["nargin", "nargout", "varargin", "varargout"])
def test_variables(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "variable.language.function.matlab", MSG_NO_MATCH
