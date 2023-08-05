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
        (parsed, data, _) = test.parser.parse(StringIO("... Some comment"))
        outDict = {
            "token": "meta.continuation.line.matlab",
            "captures": [
                {
                    "token": "punctuation.separator.continuation.line.matlab",
                    "content": "...",
                },
                {
                    "token": "comment.continuation.line.matlab",
                    "content": " Some comment",
                },
            ],
        }

        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)


if __name__ == "__main__":
    unittest.main()
