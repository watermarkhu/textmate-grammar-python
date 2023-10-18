import subprocess
from pathlib import Path

module_root = Path(__file__).parents[2]

scope = "source.matlab"
source = module_root / "syntaxes" / "matlab" / "Account.m"
index = Path(__file__).parent /  "node_root" / "index.js"

result = subprocess.run(["node", index, scope, source], check=False, capture_output=True, text=True)

tokens = []
for line in result.stdout.split("\n"):
    if line:
        pos_ind = line.find(":")
        scope_ind = line.find(":", pos_ind+1)

        pos = tuple([int(s) for s in line[:pos_ind].split("-")])
        scope_names = line[(pos_ind+1):scope_ind].split("|")
        tokens.append([pos, line[(scope_ind+1):], scope_names])

print(tokens)