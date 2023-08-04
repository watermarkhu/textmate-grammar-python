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
        cls.single = GrammarParser(TMLIST["repository"]["string_quoted_single"], key="string_quoted_single")
        cls.double = GrammarParser(TMLIST["repository"]["string_quoted_double"], key="string_quoted_double")
        cls.parser = GrammarParser(TMLIST["repository"]["string"], key="string")

    def test_line_continuation(test):
        (parsed, data) = test.single.parse(StringIO("'n'"))
        data[0].print()
        outDict = {
            "token": "string.quoted.single.matlab",
            "begin": {"token": "punctuation.definition.string.begin.matlab", "content": "'"},
            "end": {"token": "punctuation.definition.string.end.matlab", "content": "'"},
            "captures": [{"token": "constant.character.escape.matlab", "content": "n"}],
        }

        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)


if __name__ == "__main__":
    unittest.main()
