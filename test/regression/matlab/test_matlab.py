from __future__ import annotations

from pathlib import Path

import pytest
from textmate_grammar.parsers.matlab import MatlabParser

from .. import MODULE_ROOT, RegressionTestClass

parser = MatlabParser()

test_files = (
    [
        MODULE_ROOT.parents[1] / "syntaxes" / "matlab" / (file + ".m")
        for file in [
            "Account",
            "AnEnum",
            "argumentValidation",
            "CircleArea",
            "controlFlow",
            "lineContinuations",
            "PropertyValidation",
        ]
    ]
    + list((MODULE_ROOT.parents[1] / "syntaxes" / "matlab" / "test").glob("*.m"))
    + list((Path(__file__).parent.resolve() / "src" / "OpenTelemetry-Matlab").glob("**/*.m"))
)


class TestMatlabRegression(RegressionTestClass):
    """The regression test class for MATLAB."""

    scope = "source.matlab"

    @property
    def parser(self):
        return parser

    @pytest.mark.parametrize("source", test_files, ids=[f.stem for f in test_files])
    def test(self, source: Path | str):
        py_tokens = self.parse_python(source)
        node_tokens = self.parse_node(source)
        
        dn = sorted(set(node_tokens.keys()).difference(set(py_tokens.keys())))
        dp = sorted(set(py_tokens.keys()).difference(set(node_tokens.keys())))
        element = parser.parse_file(source)
        assert py_tokens == node_tokens
