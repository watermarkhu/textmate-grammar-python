import pytest
from textmate_grammar.handler import ContentHandler
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


@pytest.mark.parametrize("check", ["1", ".1", "1.1", ".1e1", "1.1e1", "1e1", "1i", "1j", "1e2j"])
def test_decimal(check):
    """Test numbers decimal"""
    element = parser.parse_language(ContentHandler(check))
    assert element, MSG_NO_MATCH
    assert element.captures[0].token == "constant.numeric.decimal.matlab", MSG_NO_MATCH
    if "i" in check or "j" in check:
        assert element.captures[0].captures[0].token == "storage.type.number.imaginary.matlab", MSG_NO_MATCH


@pytest.mark.parametrize(
    "check", ["0xF", "0XF", "0xFs8", "0xFs16", "0xFs32", "0xFs64", "0xFu8", "0xFu16", "0xFu32", "0xFu64"]
)
def test_hex(check):
    """Test numbers hex"""
    element = parser.parse_language(ContentHandler(check))
    assert element, MSG_NO_MATCH
    assert element.captures[0].token == "constant.numeric.hex.matlab", MSG_NO_MATCH
    if "s" in check or "u" in check:
        assert element.captures[0].captures[0].token == "storage.type.number.hex.matlab", MSG_NO_MATCH


@pytest.mark.parametrize(
    "check", ["0b1", "0B1", "0b1s8", "0b1s16", "0b1s32", "0b1s64", "0b1u8", "0b1u16", "0b1u32", "0b1u64"]
)
def test_binary(check):
    """Test numbers binary"""
    element = parser.parse_language(ContentHandler(check))
    element.captures[0].flatten()
    assert element, MSG_NO_MATCH
    assert element.captures[0].token == "constant.numeric.binary.matlab", MSG_NO_MATCH
    if "s" in check or "u" in check:
        assert element.captures[0].captures[0].token == "storage.type.number.binary.matlab", MSG_NO_MATCH
