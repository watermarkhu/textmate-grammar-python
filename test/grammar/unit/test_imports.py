import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parents[3]))

import unittest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST


class TestImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = GrammarParser(TMLIST["repository"]["import"], key="import")

    def test_import_module(test):
        (parsed, res, data) = test.parser("import module.submodule.class")
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
                        {"content": "class", "token": "entity.name.module.matlab"},
                    ],
                },
            ],
        }
        test.assertTrue(parsed)
        test.assertEqual(res, "")
        test.assertEqual(data[0].to_dict(), outDict)

    def test_import_wildcard(test):
        (parsed, res, data) = test.parser("import module.submodule.*")
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
        test.assertEqual(res, "")
        test.assertEqual(data[0].to_dict(), outDict)


if __name__ == "__main__":
    unittest.main()
