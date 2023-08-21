from pathlib import Path
import plistlib
import json


tmLanguageFile = Path(__file__).parents[2] / "syntaxes" / "Matlab.tmbundle" / "Syntaxes" / "MATLAB.tmLanguage"
tmLanguageJSON = Path(__file__).parent / "MATLAB.tmLanguage.json"


if tmLanguageFile.exists():
    with open(tmLanguageFile, "rb") as file:
        TMLIST = plistlib.load(file, fmt=plistlib.FMT_XML)
    with open(tmLanguageJSON, 'w') as f:
        f.write(json.dumps(TMLIST, indent=2))
else:
    with open(tmLanguageJSON, "r") as file:
        TMLIST = json.loads(file.read())


