import pytest
from ...unit import MSG_NO_MATCH, MSG_NOT_PARSED
from . import parser


conjugate_transpose_test_vector = {}

# variable
conjugate_transpose_test_vector["A'"] = {
    "token": "source.matlab",
    "children": [
        {"token": "variable.other.readwrite.matlab", "content": "A"},
        {"token": "keyword.operator.transpose.matlab", "content": "'"},
    ],
}

# matrix
conjugate_transpose_test_vector["[1]'"] = {
    "token": "source.matlab",
    "children": [
        {
            "token": "meta.brackets.matlab",
            "begin": [{"token": "punctuation.section.brackets.begin.matlab", "content": "["}],
            "end": [{"token": "punctuation.section.brackets.end.matlab", "content": "]"}],
            "children": [{"token": "constant.numeric.decimal.matlab", "content": "1"}],
        },
        {"token": "keyword.operator.transpose.matlab", "content": "'"},
    ],
}

# cell
conjugate_transpose_test_vector["{1}'"] = {
    "token": "source.matlab",
    "children": [
        {
            "token": "meta.cell.literal.matlab",
            "begin": [{"token": "punctuation.section.braces.begin.matlab", "content": "{"}],
            "end": [{"token": "punctuation.section.braces.end.matlab", "content": "}"}],
            "children": [{"token": "constant.numeric.decimal.matlab", "content": "1"}],
        },
        {"token": "keyword.operator.transpose.matlab", "content": "'"},
    ],
}

# indexed
conjugate_transpose_test_vector["A(1)'"] = {
    "token": "source.matlab",
    "children": [
        {
            "token": "meta.function-call.parens.matlab",
            "begin": [
                {"token": "entity.name.function.matlab", "content": "A"},
                {"token": "punctuation.section.parens.begin.matlab", "content": "("},
            ],
            "end": [{"token": "punctuation.section.parens.end.matlab", "content": ")"}],
            "children": [{"token": "constant.numeric.decimal.matlab", "content": "1"}],
        },
        {"token": "keyword.operator.transpose.matlab", "content": "'"},
    ],
}


transpose_test_vector = {
    "A.'": {
        "token": "source.matlab",
        "children": [
            {"token": "variable.other.readwrite.matlab", "content": "A"},
            {"token": "keyword.operator.transpose.matlab", "content": ".'"},
        ],
    }
}


@pytest.mark.parametrize("check,expected", conjugate_transpose_test_vector.items())
def test_conjugate_transpose(check, expected):
    """Test conjugate transpose"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.to_dict() == expected, MSG_NOT_PARSED


@pytest.mark.parametrize("check,expected", transpose_test_vector.items())
def test_transpose(check, expected):
    """Test transpose"""
    element = parser.parse_string(check)
    assert element, MSG_NO_MATCH
    assert element.to_dict() == expected, MSG_NOT_PARSED
