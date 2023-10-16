import sys
import pytest
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

from textmate_grammar.handler import ContentHandler
from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("textmate_grammar").setLevel(logging.INFO)
parser = LanguageParser(matlab.GRAMMAR)
parser.initialize_repository()


test_vector = {}

# inline comment
test_vector["% Test this is a comment. \n"] = {
    "token": "comment.line.percentage.matlab",
    "begin": [{"token": "punctuation.definition.comment.matlab", "content": "%"}],
    "content": "% Test this is a comment. ",
}


# section comment
test_vector["%% This is a section comment \n"] = {
    "token": "comment.line.double-percentage.matlab",
    "begin": [{"token": "punctuation.definition.comment.matlab", "content": "%%"}],
    "captures": [
        {
            "token": "entity.name.section.matlab",
            "begin": [{"token": "punctuation.whitespace.comment.leading.matlab", "content": " "}],
            "content": "This is a section comment ",
        }
    ],
}

# multiline comment
test_vector["%{\nThis is a comment\nmultiple\n %}"] = {
    "token": "comment.block.percentage.matlab",
    "begin": [{"token": "punctuation.definition.comment.begin.matlab", "content": "%{"}],
    "end": [
        {"token": "punctuation.whitespace.comment.leading.matlab", "content": " "},
        {"token": "punctuation.definition.comment.end.matlab", "content": "%}"},
    ],
    "content": "%{\nThis is a comment\nmultiple\n %}",
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_comment(check, expected):
    """Test comment"""
    parsed, elements, _ = parser.parse(ContentHandler(check), find_one=False)
    assert parsed, MSG_NO_MATCH
    assert elements[0].to_dict() == expected, MSG_NOT_PARSED
