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
        cls.parser = GrammarParser(TMLIST["repository"]["import"], key="import")

    def test_import_module(test):
        (parsed, data, _) = test.parser.parse(StringIO("import module.submodule.class"))
        outDict = {
            "token": "meta.import.matlab",
            "captures": [
                {"token": "keyword.other.import.matlab", "content": "import"},
                {
                    "token": "entity.name.namespace.matlab",
                    "captures": [
                        {"token": "entity.name.module.matlab", "content": "module"},
                        {"token": "punctuation.separator.matlab", "content": "."},
                        {"token": "entity.name.module.matlab", "content": "submodule"},
                        {"token": "punctuation.separator.matlab", "content": "."},
                        {"token": "entity.name.module.matlab", "content": "class"},
                    ],
                },
            ],
        }

        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)

    def test_import_wildcard(test):
        (parsed, data, _) = test.parser.parse(StringIO("import module.submodule.*"))
        outDict = {
            "token": "meta.import.matlab",
            "captures": [
                {"token": "keyword.other.import.matlab", "content": "import"},
                {
                    "token": "entity.name.namespace.matlab",
                    "captures": [
                        {"token": "entity.name.module.matlab", "content": "module"},
                        {"token": "punctuation.separator.matlab", "content": "."},
                        {"token": "entity.name.module.matlab", "content": "submodule"},
                        {"token": "punctuation.separator.matlab", "content": "."},
                        {"token": "variable.language.wildcard.matlab", "content": "*"},
                    ],
                },
            ],
        }
        test.assertTrue(parsed, MSG_NO_MATCH)
        test.assertDictEqual(data[0].to_dict(), outDict, MSG_NOT_PARSED)


if __name__ == "__main__":
    unittest.main()
