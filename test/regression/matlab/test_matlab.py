from __future__ import annotations

from pathlib import Path

import pytest
from textmate_grammar.parsers.matlab import MatlabParser

from .. import MODULE_ROOT, RegressionTestClass

parser = MatlabParser()

test_files = (
    [
        str(MODULE_ROOT.parents[1] / "syntaxes" / "matlab" / (file + ".m"))
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
    + [str(test) for test in (MODULE_ROOT.parents[1] / "syntaxes" / "matlab" / "test").glob("*.m")]
    + [
        str(Path(__file__).parent.resolve() / "src" / (file + ".m"))
        for file in ["test_multiple_inheritance_ml"]
    ] + [
        str(f) for f in (Path(__file__).parent.resolve() / "src" / "OpenTelemetry-Matlab").glob("**/*.m")
    ]
)


class TestMatlabRegression(RegressionTestClass):
    """The regression test class for MATLAB."""

    scope = "source.matlab"

    @property
    def parser(self):
        return parser

    @pytest.mark.parametrize("source", test_files, ids=test_files)
    def test(self, source: Path | str):
        py_tokens = self.parse_python(source)
        node_tokens = self.parse_node(source)
        assert py_tokens == node_tokens
