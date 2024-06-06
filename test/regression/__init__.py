from __future__ import annotations

import os
import platform
import re
import subprocess
import warnings
from abc import ABC, abstractmethod
from itertools import groupby
from pathlib import Path

import textmate_grammar
from textmate_grammar.parsers.base import LanguageParser

MODULE_ROOT = Path(textmate_grammar.__path__[0])
INDEX = MODULE_ROOT.parents[1] / "test" / "regression" / "node_root" / "index.js"

if platform.system() != "Linux":
    warnings.warn(f"Regression tests on {os.name} is not supported", stacklevel=1)

elif "CI" not in os.environ or not os.environ["CI"] or "GITHUB_RUN_ID" not in os.environ:
    nvm_dir = Path(os.environ["HOME"]) / ".nvm"
    nvm_script = nvm_dir / "nvm.sh"
    env = os.environ.copy()
    env["NVM_DIR"] = str(nvm_dir)

    if not nvm_script.exists():
        raise OSError(
            'Node environment not setup. Please run "bash install.sh" in the test/regression directory. '
        )

    pipe = subprocess.Popen(f". {nvm_script}; env", stdout=subprocess.PIPE, shell=True, env=env)
    output = pipe.communicate()[0]
    NODE_ENV = dict(line.split("=", 1) for line in output.decode().splitlines())

else:
    NODE_ENV = os.environ.copy()


class RegressionTestClass(ABC):
    """The base regression test class.

    This the the base test class to compare between python and (original) typescript implementations of the
    textmate languange grammar. The two parse methods of the test class, parse_python and parse_node, will
    produce the same formatted output, which can then be tested using the check_regression method.

    Any testclass must implement a parser and scope property, used to setup the Python and Typescipt
    tokenization engines, respectively.
    """

    line_pattern = re.compile("(\\d+)\\-(\\d+)\\:([a-z\\.\\|\\-]+)\\:(.+)")

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
        stdout = subprocess.run(
            ["node", str(INDEX), self.scope, file],
            check=False,
            capture_output=True,
            text=True,
            env=NODE_ENV,
        ).stdout
        tokens = []
        for line in stdout.split("\n"):
            matching = self.line_pattern.match(line)
            if matching:
                scope_names = matching.group(3).split("|")
                tokens.append(
                    (
                        int(matching.group(1)),
                        int(matching.group(2)),
                        matching.group(4),
                        scope_names,
                    )
                )
        token_dict = {}
        for _, group in groupby(tokens, lambda x: (x[0], x[3])):
            group_items = list(group)
            item = group_items[0]
            content = "".join([t[2] for t in group_items])
            tokens = item[3]
            token_dict[(item[0], item[1])] = (content, tokens)

        return token_dict
