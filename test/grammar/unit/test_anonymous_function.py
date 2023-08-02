import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[3]))

import unittest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST


class TestImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        GrammarParser(TMLIST["repository"]["line_continuation"], key="line_continuation")
        cls.parser = GrammarParser(TMLIST["repository"]["anonymous_function"], key="anonymous_function")

    def test_single_line(test):
        (parsed, data) = test.parser(StringIO("@(x,  y) x.^2+y;"))
        outDict = {
            "begin": [{"content": "@", "token": "punctuation.definition.function.anonymous.matlab"}],
            "content": [
                {
                    "begin": [{"content": "(", "token": "punctuation.definition.parameters.begin.matlab"}],
                    "content": [
                        {"content": "x", "token": "variable.parameter.input.matlab"},
                        {"content": ",", "token": "punctuation.separator.parameter.comma.matlab"},
                        {"content": "y", "token": "variable.parameter.input.matlab"},
                    ],
                    "end": [{"content": ")", "token": "punctuation.definition.parameters.end.matlab"}],
                    "token": "meta.parameters.matlab",
                },
                "(x,  y) x.^2+y",
            ],
            "end": "",
            "token": "meta.function.anonymous.matlab",
        }

        test.assertTrue(parsed)
        test.assertEqual(data[0].to_dict(), outDict)


if __name__ == "__main__":
    unittest.main()
