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
    element = parser.parse_language(ContentHandler(check))
    assert element, MSG_NO_MATCH
    assert element.captures[0].token == "variable.language.function.matlab", MSG_NO_MATCH
