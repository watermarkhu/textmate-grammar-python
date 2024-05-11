import logging

import pytest
from textmate_grammar.parsers.matlab import MatlabParser


@pytest.fixture
def parser():
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("textmate_grammar").setLevel(logging.INFO)
    return MatlabParser(remove_line_continuations=False)

