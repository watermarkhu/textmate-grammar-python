from pathlib import Path
import plistlib


with open(Path(__file__).parent / "MATLAB.tmLanguage", "rb") as file:
    TMLIST = plistlib.load(file, fmt=plistlib.FMT_XML)
