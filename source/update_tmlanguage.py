import git
import shutil
from pathlib import Path


GRAMMAR_REPO = "https://github.com/mathworks/MATLAB-Language-grammar"
LOCAL_REPO = Path(__file__).parent / "MATLAB-Language-grammar"


try:
    repo = git.Repo(LOCAL_REPO)
    assert repo.remote().url == GRAMMAR_REPO
except:
    if LOCAL_REPO.is_dir():
        shutil.rmtree(LOCAL_REPO)
    repo = git.Repo.clone_from(GRAMMAR_REPO, to_path=LOCAL_REPO)

srcpath = LOCAL_REPO / "Matlab.tmbundle" / "Syntaxes" / "MATLAB.tmLanguage"
destpath = Path(__file__).parents[1] / "sphinx-matlab" / "tmlanguage"
shutil.copy2(srcpath, destpath)

with open(destpath / "version.txt", "w") as f:
    f.write(repo.head.object.committed_datetime.isoformat() + "\n")
    f.write(repo.head.object.hexsha)
