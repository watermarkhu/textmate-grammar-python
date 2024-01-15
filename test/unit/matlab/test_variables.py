import pytest

from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


@pytest.mark.parametrize("check", ["nargin", "nargout", "varargin", "varargout"])
def test_variables(check):
    """Test variables"""
    element = parser.parse_string(check)
    assert element, MSG_NOT_PARSED
    assert (
        element.children[0].token == "variable.language.function.matlab"
    ), MSG_NO_MATCH
