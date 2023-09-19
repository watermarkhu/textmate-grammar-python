from pathlib import Path
import plistlib
import yaml


tmLanguageFile = Path(__file__).parents[3] / "syntaxes" / "matlab" / "Matlab.tmbundle" / "Syntaxes" / "MATLAB.tmLanguage"
tmLanguageYAML = Path(__file__).parent / "grammar.yaml"


if tmLanguageFile.exists():
    with open(tmLanguageFile, "rb") as file:
        TMLIST = plistlib.load(file, fmt=plistlib.FMT_XML)
    with open(tmLanguageYAML, 'w') as f:
        f.write(yaml.dump(TMLIST, indent=2))
else:
    with open(tmLanguageYAML, "r") as file:
        TMLIST = yaml.loads(file.read())


