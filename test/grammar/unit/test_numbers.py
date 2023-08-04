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
        cls.parser = GrammarParser(TMLIST["repository"]["numbers"], key="numbers")

    def test_decimal(test):
        numbers = ["1", ".1", "1.1", ".1e1", "1.1e1", "1e1", "1i", "1j", "1e2j"]
        outputs = [test.parser.parse(StringIO(number)) for number in numbers]

        for number, (parsed, data) in zip(numbers, outputs):
            with test.subTest():
                test.assertTrue(parsed, MSG_NOT_PARSED)
                test.assertEqual(data[0].token, "constant.numeric.decimal.matlab", MSG_NO_MATCH)
                if "i" in number or "j" in number:
                    test.assertEqual(data[0].captures[0].token, "storage.type.number.imaginary.matlab", MSG_NO_MATCH)

    def test_hex(test):
        numbers = ["0xF", "0XF", "0xFs8", "0xFs16", "0xFs32", "0xFs64", "0xFu8", "0xFu16", "0xFu32", "0xFu64"]
        outputs = [test.parser.parse(StringIO(number)) for number in numbers]

        for number, (parsed, data) in zip(numbers, outputs):
            with test.subTest():
                test.assertTrue(parsed, MSG_NO_MATCH)
                test.assertEqual(data[0].token, "constant.numeric.hex.matlab", MSG_NOT_PARSED)
                if "s" in number or "u" in number:
                    test.assertEqual(data[0].captures[0].token, "storage.type.number.hex.matlab", MSG_NOT_PARSED)

    def test_binary(test):
        numbers = ["0b1", "0B1", "0b1s8", "0b1s16", "0b1s32", "0b1s64", "0b1u8", "0b1u16", "0b1u32", "0b1u64"]
        outputs = [test.parser.parse(StringIO(number)) for number in numbers]

        for number, (parsed, data) in zip(numbers, outputs):
            with test.subTest():
                test.assertTrue(parsed, MSG_NO_MATCH)
                test.assertEqual(data[0].token, "constant.numeric.binary.matlab", MSG_NOT_PARSED)
                if "s" in number or "u" in number:
                    test.assertEqual(data[0].captures[0].token, "storage.type.number.binary.matlab", MSG_NOT_PARSED)


if __name__ == "__main__":
    unittest.main()
