import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


GrammarParser(TMLIST["repository"]["comment_block"], key="comment_block")
parser = GrammarParser(TMLIST["repository"]["comments"], key="comments")

test_vector = [
    (
        "inline comment",
        " % Test this is a comment. \n",
        {
            "token": "",
            "content": " % Test this is a comment. ",
            "captures": [
                {
                    "token": "comment.line.percentage.matlab",
                    "content": "% Test this is a comment. ",
                    "begin": [{"token": "punctuation.definition.comment.matlab", "content": "%"}],
                }
            ],
            "begin": [{"token": "punctuation.whitespace.comment.leading.matlab", "content": " "}],
        },
    ),
    (
        "section comment",
        "  %% This is a section comment \n",
        {
            "token": "",
            "begin": [{"token": "punctuation.whitespace.comment.leading.matlab", "content": "  "}],
            "content": "  %% This is a section comment \n",
            "captures": [
                {
                    "token": "comment.line.double-percentage.matlab",
                    "begin": [{"token": "punctuation.definition.comment.matlab", "content": "%%"}],
                    "content": "%% This is a section comment \n",
                    "captures": [
                        {
                            "token": "entity.name.section.matlab",
                            "begin": [
                                {"token": "punctuation.whitespace.comment.leading.matlab", "content": " "}
                            ],
                            "content": "This is a section comment ",
                        }
                    ],
                }
            ],
        },
    ),
    (
        "multiline comment",
        "  %{\nThis is a comment\nmultiple\n %}",
        {
            "token": "comment.block.percentage.matlab",
            "begin": [
                {"token": "punctuation.whitespace.comment.leading.matlab", "content": "  "},
                {"token": "punctuation.definition.comment.begin.matlab", "content": "%{"},
            ],
            "content": "  %{\nThis is a comment\nmultiple\n %}",
            "end": [
                {"token": "punctuation.whitespace.comment.leading.matlab", "content": " "},
                {"token": "punctuation.definition.comment.end.matlab", "content": "%}"},
            ],
            "captures": [
                {"token": "", "content": "This is a comment\n"},
                {"token": "", "content": "multiple\n"},
            ],
        },
    ),
]


@pytest.mark.parametrize("case,input,expected", test_vector)
def test_comment(case, input, expected):
    elements = parser.parse(StringIO(input))
    if elements:
        assert elements[0].to_dict() == expected, MSG_NOT_PARSED
    else:
        raise Exception(MSG_NO_MATCH)
