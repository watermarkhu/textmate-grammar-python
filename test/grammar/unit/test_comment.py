import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[3]))

import unittest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST


class TestComment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        GrammarParser(TMLIST["repository"]["comment_block"], key="comment_block")
        cls.parser = GrammarParser(TMLIST["repository"]["comments"], key="comments")

    def test_inline_comment(test):
        (parsed, data) = test.parser(StringIO(" % Test this is a comment. \n"))
        outDict = {
            "begin": [{"content": "%", "token": "punctuation.definition.comment.matlab"}],
            "content": [
                {"content": " Test this is a comment. \n", "token": "comment.line.percentage.matlab"}
            ],
            "end": "",
            "token": "comment.line.percentage.matlab",
        }
        test.assertTrue(parsed)
        test.assertEqual(data[0].to_dict(), outDict)

    def test_section_comment(test):
        (parsed, data) = test.parser(StringIO("  %% This is a section comment \n"))
        outDict = {
            "begin": [{"content": "%%", "token": "punctuation.definition.comment.matlab"}],
            "content": [
                {
                    "begin": [
                        {
                            "content": " ",
                            "token": "punctuation.whitespace.comment.leading.matlab",
                        }
                    ],
                    "content": "This is a section comment ",
                    "end": "",
                    "token": "entity.name.section.matlab",
                }
            ],
            "end": "\n",
            "token": "comment.line.double-percentage.matlab",
        }
        test.assertTrue(parsed)
        test.assertEqual(data[0].to_dict(), outDict)

    def test_multiline_comment(test):
        (parsed, data) = test.parser(StringIO("  %{\nThis is a comment\nmultiple\n %}"))
        outDict = {
            "token": "comment.block.percentage.matlab",
            "begin": [
                {
                    "token": "punctuation.whitespace.comment.leading.matlab",
                    "content": "  ",
                },
                {
                    "token": "punctuation.definition.comment.begin.matlab",
                    "content": "%{",
                },
            ],
            "content": [
                {"content": "This is a comment\n", "token": ""},
                {"content": "multiple\n", "token": ""},
            ],
            "end": [
                {
                    "token": "punctuation.whitespace.comment.leading.matlab",
                    "content": " ",
                },
                {"content": "%}", "token": "punctuation.definition.comment.end.matlab"},
            ],
        }

        test.assertTrue(parsed)
        test.assertEqual(data[0].to_dict(), outDict)


if __name__ == "__main__":
    unittest.main()
