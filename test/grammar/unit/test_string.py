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
        (parsed, data) = test.single.parse(StringIO("'a'"))
        data[0].print()

        test.assertTrue(parsed, MSG_NO_MATCH)
        # test.assertEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)


if __name__ == "__main__":
    unittest.main()
