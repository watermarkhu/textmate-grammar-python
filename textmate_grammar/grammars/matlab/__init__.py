from pathlib import Path
import plistlib
import yaml


try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


tmLanguageFile = Path(__file__).parents[3] / "syntaxes" / "matlab" / "Matlab.tmbundle" / "Syntaxes" / "MATLAB.tmLanguage"
tmLanguageYAML = Path(__file__).parent / "grammar.yaml"


if tmLanguageFile.exists():
    with open(tmLanguageFile, "rb") as file:
        GRAMMAR = plistlib.load(file, fmt=plistlib.FMT_XML)
    with open(tmLanguageYAML, 'w') as f:
        f.write(yaml.dump(GRAMMAR, indent=2))
else:
    with open(tmLanguageYAML, "r") as file:
        GRAMMAR = yaml.load(file.read(), Loader=Loader)


