import sys
import pytest
import subprocess
from pathlib import Path
from abc import ABC, abstractmethod

module_root = Path(__file__).parents[2]
sys.path.append(str(module_root))

from textmate_grammar.language import LanguageParser
from textmate_grammar.grammars import matlab


INDEX = Path(__file__).parent /  "node_root" / "index.js"

class RegressionTestClass(ABC):
    """The base regression test class.
    
    This the the base test class to compare between python and (original) typescript implementations of the
    textmate languange grammar. The two parse methods of the test class, parse_python and parse_node, will 
    produce the same formatted output, which can then be tested using the check_regression method. 

    Any testclass must implement a parser and scope property, used to setup the Python and Typescipt
    tokenization engines, respectively. 
    """

    @property
    @abstractmethod
    def parser(self) -> LanguageParser:
        pass

    @property
    @abstractmethod
    def scope(self) -> str:
        pass

    def parse_python(self, file: Path | str) -> dict:
        element = self.parser.parse_file(file)
        token_dict = {}
        for pos, content, scope_names in element.flatten():
            token_dict[pos] = (content, scope_names)
        return token_dict

    def parse_node(self, file: Path | str) -> dict:
        result = subprocess.run(["node", INDEX, self.scope, file], check=False, capture_output=True, text=True)
        token_dict = {}
        for line in result.stdout.split("\n"):
            if line:
                pos_ind = line.find(":")
                scope_ind = line.find(":", pos_ind+1)
                pos = tuple([int(s) for s in line[:pos_ind].split("-")])
                scope_names = line[(pos_ind+1):scope_ind].split("|")
                token_dict[pos] = (line[(scope_ind+1):], scope_names)
        return token_dict
 
    def check_regression(self, file: Path | str):
        py_tokens = self.parse_python(file)
        node_tokens = self.parse_node(file)
        assert py_tokens == node_tokens


test_file = module_root / "syntaxes" / "matlab" / "Account.m"

@pytest.mark.parametrize("source", [test_file])
class TestMatlabRegression(RegressionTestClass):
    """The regression test class for MATLAB."""

    scope = "source.matlab"

    @classmethod
    def setup_class(cls) -> None:
        cls._parser = LanguageParser(matlab.GRAMMAR)
        cls._parser.initialize_repository()
    
    @property
    def parser(self):
        return self._parser
    
    def test(self, source: Path | str):
        self.check_regression(source)
