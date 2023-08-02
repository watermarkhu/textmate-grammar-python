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
        cls.parser = GrammarParser(TMLIST["repository"]["import"], key="import")

    def test_import_module(test):
        (parsed, data) = test.parser(StringIO("import module.submodule.class"))
        outDict = {
            "content": [
                {"content": "import", "token": "keyword.other.import.matlab"},
                {
                    "content": [
                        {"content": "module", "token": "entity.name.module.matlab"},
                        {"content": ".", "token": "punctuation.separator.matlab"},
                        {"content": "submodule", "token": "entity.name.module.matlab"},
                        {"content": ".", "token": "punctuation.separator.matlab"},
                        {"content": "class", "token": "entity.name.module.matlab"},
                    ],
                    "token": "entity.name.namespace.matlab",
                },
            ],
            "token": "meta.import.matlab",
        }

        test.assertTrue(parsed)
        test.assertEqual(data[0].to_dict(), outDict)

    def test_import_wildcard(test):
        (parsed, data) = test.parser(StringIO("import module.submodule.*"))
        outDict = {
            "token": "meta.import.matlab",
            "content": [
                {"content": "import", "token": "keyword.other.import.matlab"},
                {
                    "token": "entity.name.namespace.matlab",
                    "content": [
                        {"content": "module", "token": "entity.name.module.matlab"},
                        {"content": ".", "token": "punctuation.separator.matlab"},
                        {"content": "submodule", "token": "entity.name.module.matlab"},
                        {"content": ".", "token": "punctuation.separator.matlab"},
                        {"content": "*", "token": "variable.language.wildcard.matlab"},
                    ],
                },
            ],
        }
        test.assertTrue(parsed)
        test.assertEqual(data[0].to_dict(), outDict)


if __name__ == "__main__":
    unittest.main()
