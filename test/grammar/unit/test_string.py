import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import unittest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


class TestImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        GrammarParser(TMLIST["repository"]["shell_string"], key="shell_string")
        cls.single = GrammarParser(TMLIST["repository"]["string_quoted_single"], key="string_quoted_single")
        cls.double = GrammarParser(TMLIST["repository"]["string_quoted_double"], key="string_quoted_double")
        cls.parser = GrammarParser(TMLIST["repository"]["string"], key="string")

    def test_single_quoted(test):
        (parsed, data, _) = test.parser.parse(StringIO(r"'This %.3f ''is'' %% a \\ string\n'"))

        outDict = {
            "token": "string.quoted.single.matlab",
            "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": "'"}],
            "content": "This %.3f ''is'' %% a \\\\ string\\n",
            "end": [{"token": "punctuation.definition.string.end.matlab", "content": "'"}],
            "captures": [
                {"token": "constant.character.escape.matlab", "content": "%.3f"},
                {"token": "constant.character.escape.matlab", "content": "''"},
                {"token": "constant.character.escape.matlab", "content": "''"},
                {"token": "constant.character.escape.matlab", "content": "%%"},
                {"token": "constant.character.escape.matlab", "content": "\\\\"},
                {"token": "constant.character.escape.matlab", "content": "\\n"},
            ],
        }

        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)

    def test_double_quoted(test):
        (parsed, data, _) = test.double.parse(StringIO(r'"This %.3f ""is"" %% a \\ string\n"'))

        outDict = {
            "token": "string.quoted.double.matlab",
            "begin": [{"token": "punctuation.definition.string.begin.matlab", "content": '"'}],
            "content": 'This %.3f ""is"" %% a \\\\ string\\n',
            "end": [{"token": "punctuation.definition.string.end.matlab", "content": '"'}],
            "captures": [
                {"token": "constant.character.escape.matlab", "content": '""'},
                {"token": "constant.character.escape.matlab", "content": '""'},
            ],
        }

        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)


if __name__ == "__main__":
    unittest.main()
