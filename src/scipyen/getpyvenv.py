import sys, os
from pathlib import Path

venvdir = os.environ["VIRTUAL_ENV"]
venvcfg = os.fspath(Path(venvdir)/"pyvenv.cfg")
with open(venvcfg, "r", encoding="utf-8") as f:
    t = f.readlines()
    
#print(t)

def _parse_pyvenv_line_(x):
    k,v = x.split(" = ")
    k = k.replace(" ", "") # remove spaces in dict keys
    
    v = v.replace("\n", "") # remove crlf from value
    #v = Path(v).resolve()
    
    return (k,v)
    
pyvenv = dict(_parse_pyvenv_line_(line) for line in t)

print(pyvenv)

os.environ["OLD_PYTHONHOME"] = os.environ.get("PYTHONHOME", "")
pyprefix = pyvenv["base-prefix"]
pyexecprefix = pyvenv["base-exec-prefix"]
os.environ["PYTHONHOME"] = f"{pyprefix}:{pyexecprefix}"

