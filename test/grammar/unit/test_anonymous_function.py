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
        GrammarParser(TMLIST["repository"]["line_continuation"], key="line_continuation")
        cls.parser = GrammarParser(TMLIST["repository"]["anonymous_function"], key="anonymous_function")

    # def test_single_line(test):
    #     (parsed, data, _) = test.parser.parse(StringIO("@(x,  y) x.^2+y;"))
    #     outDict = {
    #         "token": "meta.function.anonymous.matlab",
    #         "begin": [{"token": "punctuation.definition.function.anonymous.matlab", "content": "@"}],
    #         "content": "@(x,  y) x.^2+y",
    #         "captures": [
    #             {
    #                 "token": "meta.parameters.matlab",
    #                 "begin": [{"token": "punctuation.definition.parameters.begin.matlab", "content": "("}],
    #                 "content": "(x,  y)",
    #                 "end": [{"token": "punctuation.definition.parameters.end.matlab", "content": ")"}],
    #                 "captures": [
    #                     {"token": "variable.parameter.input.matlab", "content": "x"},
    #                     {"token": "punctuation.separator.parameter.comma.matlab", "content": ","},
    #                     {"token": "variable.parameter.input.matlab", "content": "y"},
    #                 ],
    #             },
    #             {"token": "meta.parameters.matlab", "content": " x.^2+y", "captures": ["x.^2+y"]},
    #         ],
    #     }

    #     test.assertTrue(parsed, MSG_NOT_PARSED)
    #     test.assertDictEqual(data[0].to_dict(), outDict, MSG_NO_MATCH)

    def test_multi_line(test):
        (parsed, data, _) = test.parser.parse(StringIO("@(x,...\n  y) x...\n   .^2+y;"))
        outDict = {
            "token": "meta.function.anonymous.matlab",
            "begin": {"token": "punctuation.definition.function.anonymous.matlab", "content": "@"},
            "captures": [
                {
                    "token": "meta.parameters.matlab",
                    "begin": {"token": "punctuation.definition.parameters.begin.matlab", "content": "("},
                    "end": {"token": "punctuation.definition.parameters.end.matlab", "content": ")"},
                    "captures": [
                        {"token": "variable.parameter.input.matlab", "content": "x"},
                        {"token": "punctuation.separator.parameter.comma.matlab", "content": ","},
                        {
                            "token": "meta.continuation.line.matlab",
                            "captures": [
                                {"token": "punctuation.separator.continuation.line.matlab", "content": "..."}
                            ],
                        },
                        {"token": "variable.parameter.input.matlab", "content": "y"},
                    ],
                },
                {"token": "meta.parameters.matlab", "captures": ["x...\n   .^2+y"]},
            ],
        }

        test.assertTrue(parsed, MSG_NOT_PARSED)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NO_MATCH)


if __name__ == "__main__":
    unittest.main()
