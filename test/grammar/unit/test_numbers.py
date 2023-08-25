import sys
from pathlib import Path
from io import StringIO

sys.path.append(str(Path(__file__).parents[1]))
sys.path.append(str(Path(__file__).parents[3]))

import pytest
from sphinx_matlab.grammar import GrammarParser
from sphinx_matlab.tmlanguage import TMLIST
from unit import MSG_NO_MATCH, MSG_NOT_PARSED


parser = GrammarParser(TMLIST["repository"]["numbers"], key="numbers")


@pytest.mark.parametrize("input", ["1", ".1", "1.1", ".1e1", "1.1e1", "1e1", "1i", "1j", "1e2j"])
def test_decimal(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "constant.numeric.decimal.matlab", MSG_NO_MATCH
    if "i" in input or "j" in input:
        assert data[0].captures[0].token == "storage.type.number.imaginary.matlab", MSG_NO_MATCH


@pytest.mark.parametrize(
    "input", ["0xF", "0XF", "0xFs8", "0xFs16", "0xFs32", "0xFs64", "0xFu8", "0xFu16", "0xFu32", "0xFu64"]
)
def test_hex(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "constant.numeric.hex.matlab", MSG_NO_MATCH
    if "s" in input or "u" in input:
        assert data[0].captures[0].token == "storage.type.number.hex.matlab", MSG_NO_MATCH


@pytest.mark.parametrize(
    "input", ["0b1", "0B1", "0b1s8", "0b1s16", "0b1s32", "0b1s64", "0b1u8", "0b1u16", "0b1u32", "0b1u64"]
)
def test_binary(input):
    parsed, data, _ = parser.parse(StringIO(input))

    assert parsed, MSG_NOT_PARSED
    assert data[0].token == "constant.numeric.binary.matlab", MSG_NO_MATCH
    if "s" in input or "u" in input:
        assert data[0].captures[0].token == "storage.type.number.binary.matlab", MSG_NO_MATCH
