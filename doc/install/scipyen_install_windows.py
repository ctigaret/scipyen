import sys, os, subprocess, io, datetime, winreg
from contextlib import contextmanager
from functools import singledispatch
#from collections import deque

@contextmanager
def registry_key(parent, name:str):
    key = winreg.OpenKey(parent, name)
    try:
        yield key
    finally:
        winreg.CloseKey(key)

@singledispatch
def get_n_subkeys(key):
    """Returns the number of subkeys in the key
    """
    pass

@get_n_subkeys.register(str)
def _(key):
    if key.startswith("HKEY") and key in winreg.__dict__:
        return winreg.QueryInfoKey(key)[0]
    else:
        raise ValueError(f"key {key} does not exist in the Windows registry")

@get_n_subkeys.register(winreg.HKEYType)
def _(key):
    if not key:
        raise ValueError(f"key {key} is invalid")
    return winreg.QueryInfoKey(key)[0]

@singledispatch
def get_n_values(key):
    """
    Return the number of values in the key
    """
    pass

@get_n_values.register(str)
def _(key):
    if key.startswith("HKEY") and key in winreg.__dict__:
        return winreg.QueryInfoKey(key)[1]
    else:
        raise ValueError(f"key {key} does not exist in the Windows registry")

@get_n_subkeys.register(winreg.HKEYType)
def _(key):
    if not key:
        raise ValueError(f"key {key} is invalid")
    return winreg.QueryInfoKey(key)[1]

@singledispatch
def get_subkeys(key):
    """
    Return a list of subkey names for this key
    """
    pass

@get_subkeys.register(str)
def _(key):
    if key.startswith("HKEY") and key in winreg.__dict__:
        return [winreg.EnumKey(key, k) for k in range(get_n_subkeys(key))]
    else:
        raise ValueError(f"key {key} does not exist in the Windows registry")


@get_subkeys.register(winreg.HKEYType)
def _(key):
    if not key:
        raise ValueError(f"key {key} is invalid")
    return [winreg.EnumKey(key, k) for k in range(get_n_subkeys(key))]

@singledispatch
def get_key_values(key):
    """
    Returns a list of values in this key
    """
    pass

@get_key_values.register(str)
def _(key):
    if key not in winreg.__dict__:
        raise ValueError(f"key {key} does not exist in the Windows registry")

    values_dict = dict()
    for k in range(get_n_values(key)):
        name, obj, obj_type = winreg.EnumValue(key, k)
        values_dict[name]=(obj, obj_type)

    return values_dict

@get_key_values.register(winreg.HKEYType)
def _(key):
    if not key:
        raise ValueError(f"key {key} is invalid")

    values_dict = dict()
    for k in range(get_n_values(key)):
        name, obj, obj_type = winreg.EnumValue(key, k)
        values_dict[name]=(obj, obj_type)

    return values_dict

#def find_reg_subkey(parent, name, cache=list()):
    #if isinstance(parent, str) and parent.startswith("HKEY") and parent in winreg.__dict__.keys():
        #subkeys = get_subkeys(parent)
        #if name in subkeys:
            #cache.append(parent)
            #return parent
        #else

def check_VS():
    with registry_key(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE") as software_key:
        with registry_key(software_key, "Microsoft") as ms_key:
            return "VisualStudio" in get_subkeys(ms_key)


def get_pyver():
    return ".".join([str(sys.version_info.major), str(sys.version_info.minor), str(sys.version_info.micro)])

def get_env_name():
    default = "scipyenv"
    ret = input(f"Enter environment name (default is {default}): ")
    if len(ret.strip()) == 0:
        ret = default

    return ret

def get_env_home():
    default = "e:\\"
    ret = input(f"Enter the directory where the virtual environment will be created (default is {default}): ")
    if len(ret.strip()) == 0:
        ret = default

    return ret

def installpipreqs(pyvenv, reqs, force=False):
    activate_script = os.path.join(pyvenv, "Scripts", "activate.bat")
    flagfile=os.path.join(pyvenv, ".pipdone")
    if not os.path.isfile(activate_script):
        raise OSError(f"File {activate_script} not found !")
    if not os.path.isfile(flagfile) or force == True:
        print("Installing Python packages from PyPI")
        subprocess.run(f"{activate_script} & set SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True & python -m pip install -r {reqs}",
                       shell=True, check=True)

        with open(flagfile, "w") as flag:
            flag.write(f"Python packages from PyPI installed on {datetime.datetime.now}")

        #os.system(f"{activate_script} & set SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True & python -m pip install -r {reqs}")

def make_scipyact(pyvenv):
    now = f"{datetime.datetime.now()}".replace(" ", "_").replace(":", "_").replace(".", "_")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")

    userscripts = os.path.join(userhome, "Scripts")

    activation_script = os.path.join(userscripts, "scipyact.bat")
    pyvenvactivation = os.path.join(pyvenv, "Scripts", "activate.bat")

    if not os.path.isdir(userscripts):
        os.mkdir(userscripts)

    if userscripts not in userpath:
        newpath=";".join([userpath, "Scripts"])
        subprocess.run(f"setx PATH {newpath}", shell=True, check=True)
        os.environ["PATH"]=newpath

    if os.path.isfile(activation_script):
        name, ext = os.path.splitext(activation_script)
        backup=f"{name}.{now}{ext}"
        subprocess.run(f"copy {activation_script} {backup}", shell=True, check=True)

    with open(activation_script, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write(f"call {pyvenvactivation}\n")
        batch_file.write("echo on\n")


def make_scipyact_vs64(pyvenv):
    now = f"{datetime.datetime.now()}".replace(" ", "_").replace(":", "_").replace(".", "_")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")

    userscripts = os.path.join(userhome, "Scripts")

    script = os.path.join(userscripts, "scipyact_vs64.bat")

    pyvenvactivation = os.path.join(pyvenv, "Scripts", "activate.bat")

    vcvarsall = os.path.join("C:\\", "Program Files (x86)", "Microsoft Visual Studio",
                             "2019", "Community", "VC", "Auxiliary", "Build","vcvarsall.bat")

    if not os.path.isfile(vcvarsall):
        raise OSError("Please install VisualStudio 2019 and try again")

    if os.path.isfile(script):
        name, ext = os.path.splitext(script)
        backup = f"{name}.{now}{ext}"
        subprocess.run(f"copy {script} {backup}", shell=True, check=True)

    with open(script, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write(f'call "{vcvarsall}"  amd64 \n')
        batch_file.write(f'set "PROMPT=(X64) $p$g" \n')
        batch_file.write(f'call {pyvenvactivation} \n')
        batch_file.write("echo on\n")

def make_vs64_bat():
    now = f"{datetime.datetime.now()}".replace(" ", "_").replace(":", "_").replace(".", "_")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")

    userscripts = os.path.join(userhome, "Scripts")

    vs64script = os.path.join(userscripts, "vs64.bat")

    vcvarsall = os.path.join("C:\\", "Program Files (x86)", "Microsoft Visual Studio",
                             "2019", "Community", "VC", "Auxiliary", "Build","vcvarsall.bat")

    if not os.path.isfile(vcvarsall):
        raise OSError("Please install VisualStudio 2019 and try again")

    if os.path.isfile(vs64script):
        name, ext = os.path.splitext(vs64script)
        backup = f"{name}.{now}{ext}"
        subprocess.run(f"copy {vs64script} {backup}", shell=True, check=True)

    with open(vs64script, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write(f'call "{vcvarsall}" amd64\n')
        batch_file.write(f'set "PROMPT=(X64) $p$g" \n')
        batch_file.write("echo on\n")

def makevirtenv(loc, name):
    path=os.path.join(loc, name)
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise OSError(f"{path} exists but is not a directory")
        pyvenvcfg = os.path.join(path, "pyvenv.cfg")
        if not os.path.exists(pyvenvcfg) or not os.path.isfile(pyvenvcfg):
            raise OSError(f"Directory {path} exists but does not seem to be a virtual environment directory")
    else:
        print(f"environment will be created as {path}")
        os.system(f"python -m virtualenv {path}")

    return path

def make_launch_script(pyvenv, scipydir):
    now = f"{datetime.datetime.now()}".replace(" ", "_").replace(":", "_").replace(".", "_")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")

    userscripts = os.path.join(userhome, "Scripts")

    scipyenscript = os.path.join(userscripts, "scipyen.bat")
    pyvenvactivation = os.path.join(pyvenv, "Scripts", "activate.bat")
    scipystartup = os.path.join(scipydir, "scipyen.py")

    if not os.path.isdir(userscripts):
        os.mkdir(userscripts)

    if userscripts not in userpath:
        newpath=";".join([userpath, "Scripts"])
        subprocess.run(f"setx PATH {newpath}", shell=True, check=True)
        os.environ["PATH"]=newpath

    if os.path.isfile(scipyenscript):
        backup=f"{scipyenscript}.{now}"
        subprocess.run(f"copy {scipyenscript} {backup}", shell=True, check=True)

    with open(scipyenscript, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write(f"call {pyvenvactivation}\n")
        batch_file.write(f"cmd /C 'python {scipystartup}' \n")



virtual_env_name = f"{get_env_name()}.{get_pyver()}"

ve_home = get_env_home()

realscript = __file__

print(f"realscript={realscript}")

virtual_env_path = makevirtenv(ve_home, virtual_env_name)

if len(virtual_env_path.strip()):
    make_scipyact(virtual_env_path)
    make_scipyact_vs64(virtual_env_path)
    make_vs64_bat()

reqsfile=os.path.join(os.path.dirname(realscript), "pip_requirements.txt")

installpipreqs(virtual_env_path, reqsfile)




