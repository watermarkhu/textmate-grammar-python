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
        cls.parser = GrammarParser(TMLIST["repository"]["line_continuation"], key="line_continuation")

    def test_line_continuation(test):
        (parsed, data) = test.parser.parse(StringIO("... Some comment"))
        outDict = {
            "content": [
                {"content": "...", "token": "punctuation.separator.continuation.line.matlab"},
                {"content": " Some comment", "token": "comment.continuation.line.matlab"},
            ],
            "token": "meta.continuation.line.matlab",
        }

        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)


if __name__ == "__main__":
    unittest.main()
