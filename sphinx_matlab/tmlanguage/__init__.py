from pathlib import Path
import plistlib
import json


with open(Path(__file__).parent / "MATLAB.tmLanguage", "rb") as file:
    TMLIST = plistlib.load(file, fmt=plistlib.FMT_XML)


def write_json(path: str = ""):
    if not path:
        path = Path(__file__).parent / "MATLAB.json"
    with open(path, 'w') as f:
        f.write(json.dumps(TMLIST, indent=2))