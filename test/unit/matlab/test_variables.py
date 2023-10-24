import sys
import pytest
import logging
import pytest
from textmate_grammar.handler import ContentHandler
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


@pytest.mark.parametrize("check", ["nargin", "nargout", "varargin", "varargout"])
def test_variables(check):
    """Test variables"""
    parsed, elements, _ = parser.parse(ContentHandler(check))
    assert parsed, MSG_NO_MATCH
    assert elements[0].token == "variable.language.function.matlab", MSG_NO_MATCH
