import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import unittest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


class TestComment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blockParser = GrammarParser(TMLIST["repository"]["comment_block"], key="comment_block")
        cls.parser = GrammarParser(TMLIST["repository"]["comments"], key="comments")

    def test_inline_comment(test):
        (parsed, data, _) = test.parser.parse(StringIO(" % Test this is a comment. \n"))
        outDict = {
            "token": "Inline comment",
            "begin": [{"token": "punctuation.whitespace.comment.leading.matlab", "content": " "}],
            "content": " % Test this is a comment. ",
            "captures": [
                {
                    "token": "comment.line.percentage.matlab",
                    "begin": [{"token": "punctuation.definition.comment.matlab", "content": "%"}],
                    "content": "% Test this is a comment. ",
                }
            ],
        }
        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)

    def test_section_comment(test):
        (parsed, data, _) = test.parser.parse(StringIO("  %% This is a section comment \n"))
        outDict = {
            "token": "Section comment",
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
        }
        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)

    def test_multiline_comment(test):
        (parsed, data, _) = test.blockParser.parse(StringIO("  %{\nThis is a comment\nmultiple\n %}"))
        outDict = {
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
        }

        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(content=True), outDict, MSG_NOT_PARSED)


if __name__ == "__main__":
    unittest.main()
