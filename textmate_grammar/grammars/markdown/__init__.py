from pathlib import Path
import shutil
import yaml


tmLanguageFile = (
    Path(__file__).parents[3]
    / "syntaxes"
    / "markdown"
    / "markdown.tmLanguage.base.yaml"
)
tmLanguageYAML = Path(__file__).parent / "grammar.yaml"


if tmLanguageFile.exists():
    shutil.copyfile(tmLanguageFile, tmLanguageYAML)

with open(tmLanguageYAML, "r") as file:
    try:
        GRAMMAR = yaml.load(file.read(), Loader=yaml.CLoader)
    except ImportError:
        GRAMMAR = yaml.load(file.read(), Loader=yaml.Loader)
