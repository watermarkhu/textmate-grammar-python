#%%

import plistlib
from pathlib import Path


TMFILE = Path(__file__).parent / 'tmlanguage' / 'MATLAB.tmLanguage'


with open(TMFILE, 'rb') as file:
    tmlist = plistlib.load(file, fmt=plistlib.FMT_XML)

# %%
