import pytest

from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser

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
    "children": [
        {
            "token": "entity.name.section.matlab",
            "begin": [
                {
                    "token": "punctuation.whitespace.comment.leading.matlab",
                    "content": " ",
                }
            ],
            "content": "This is a section comment ",
        }
    ],
}

# multiline comment
test_vector["%{\nThis is a comment\nmultiple\n %}"] = {
    "token": "comment.block.percentage.matlab",
    "begin": [
        {"token": "punctuation.definition.comment.begin.matlab", "content": "%{"}
    ],
    "end": [
        {"token": "punctuation.whitespace.comment.leading.matlab", "content": " "},
        {"token": "punctuation.definition.comment.end.matlab", "content": "%}"},
    ],
    "content": "%{\nThis is a comment\nmultiple\n %}",
}


@pytest.mark.parametrize("check,expected", test_vector.items())
def test_comment(check, expected):
    """Test comment"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.children[0].to_dict() == expected, MSG_NOT_PARSED
