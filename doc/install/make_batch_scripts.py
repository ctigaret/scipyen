
import os, sys, pathlib, subprocess, traceback, shutil, tempfile
if sys.platform != "win32":
    raise EnvironmentError(f"This script cannot run on {sys.platform}")
import winreg
try:
    import win32con, win32gui
except:
    print("You need to run 'pip install --user pywin32' first")
    sys.exit(1)

    #raise()

try:
    import winshell
except:
    print("You need to run 'pip install --user winshell' first")
    sys.exit(1)
    #raise()

from pathlib import Path
try:
    import readline
except:
    pass

#if os.getevirtualenv.createRuntimeError(f"This module must be run inside a Python virtual environment")


#from win32com.client import Dispatch

__module_path__ = os.path.abspath(os.path.dirname(__file__))

def install_precompiled_vigra(vigra_archive:Path, p:Path):
    if not vigra_archive.exists():
        raise RuntimeError("Cannot find archive with vigranumpy modules")

    print(f"Installing vigranumpy package from {vigra_archive} to {p / 'Lib' / 'site-packages'}")
    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.unpack_archive(vigra_archive, tmpdirname)
        # is this a container dir or is it 'Lib'?
        lib_dir = Path(tmpdirname) / 'Lib' #/ 'site-packages' / 'vigra'
        if lib_dir.exists():
            # Lib found in temp dir -> straight from archive
            shutil.copytree(lib_dir, p / 'Lib' , dirs_exist_ok=True)
            #shutil.copytree(lib_dir, p / 'Lib' / 'site-packages' , dirs_exist_ok=True)
        else:
            cc = list(c for c in Path(tmpdirname).iterdir() if c.is_dir())
            if len(cc) == 1:
                lib_dir = Path(cc[0] / 'Lib')
                if lib_dir.exists():
                    shutil.copytree(lib_dir, p / 'Lib' , dirs_exist_ok=True)
                    #shutil.copytree(lib_dir, p / 'Lib' / 'site-packages' / 'vigra', dirs_exist_ok=True)
                else:
                    raise RuntimeError("Cannot find 'Lib' directory")

            else:
                raise RuntimeError("This does not seem to be an archive with vigranumpy package")


def create_virtual_environment(p:Path):
    """Creates a virtual Python environment at path p.
    Also installs pip requirements
    """
    try:
        print(f"Creating a Python virtual environment in {p}")

        p_ = str(p).replace("\\", "/")
        sp = subprocess.run(["virtualenv", p_], capture_output=True)
        if sp.returncode == 0:
            try:
                # see https://www.a2hosting.co.uk/kb/developer-corner/python/activating-a-python-virtual-environment-from-a-script-file
                vigra_pkg = input(f"Enter full path to archive with compiled vigranumpy package (use forward slashes e.g. 'e:/vigra_pkg.zip'): ")
                vigra_archive = Path(vigra_pkg)

                activate_this = str(p / "Scripts" / "activate_this.py")

                with open(activate_this) as f:
                    code = compile(f.read(), activate_this, 'exec')
                    exec(code, dict(__file__ = activate_this))
                pip_reqs = Path(__module_path__) / "pip_requirements.txt"
                print(f"Installing pip requirements in {pip_reqs}; please wait ...")
                psp = subprocess.run(["pip", "install", "-r", str(pip_reqs)])
                errors = " with errors" if psp.returncode > 0 else ""
                print(f"Pip requirements installed{errors}!")

                install_precompiled_vigra(vigra_archive, p)

                #if not vigra_archive.exists():
                    #raise RuntimeError("Cannot find archive with vigranumpy modules")

                #print("Installing vigranumpy package")
                #with tempfile.TemporaryDirectory() as tmpdirname:
                    #shutil.unpack_archive(vigra_archive, tmpdirname)
                    ## is this a container dir or is it 'Lib'?
                    #lib_dir = Path(tmpdirname) / 'Lib' / 'site-packages' / 'vigra'
                    #if lib_dir.exists():
                        ## Lib found in temp dir -> straight from archive
                        #shutil.copytree(lib_dir, p / 'Lib' / 'site-packages' , dirs_exist_ok=True)
                    #else:
                        #cc = list(c for c in Path(tmpdirname).iterdir() if c.is_dir())
                        #if len(cc) == 1:
                            #lib_dir = Path(cc[0] / 'Lib' / 'site-packages' /'vigra')
                            #if lib_dir.exists():
                                #shutil.copytree(lib_dir, p / 'Lib' / 'site-packages', dirs_exist_ok=True)
                            #else:
                                #raise RuntimeError("Cannot find 'Lib' directory")

                        #else:
                            #raise RuntimeError("This does not seem to be an archive with vigranumpy package")

                return psp.returncode
            except:
                traceback.print_exc()
                return -1

    except:
        traceback.print_exc()
        return -1


def check_pyenv(scipyendir:Path, scipyen_sdk_dir:Path,
                activation_script="scipyact.bat",
                scripts_dir = "Scripts"):
    """Check if operating under a python environment.
    If not the ask for one and activate it. If one does not exist, create it and
    then activate it.

    Once this is done, check that we have a scripts directory containing a batch
    script for the activation of the virtual Python environment, in the user's
    'PATH' environment variable - this is for convenience


    """
    d = Path(os.getenv("USERPROFILE")) / scripts_dir
    s = d / activation_script

    if not s.exists():
        needs_activation_scripts = True
    else:
        needs_activation_scripts = False

    if os.getenv("VIRTUAL_ENV") is None:
        print("This script needs a virtual Python environment.")
        print("Below, enter the directory of an existing environment")
        print("If not found, a new environment will be created")
        env_dir = input("Enter full path to the environment directory (use forward slashes, e.g. 'c:/a/b'): ")
        env_dir = Path(env_dir)
        if env_dir.is_reserved():
            raise ValueError(f"Cannot use reserved path {env_dir}")
        if not env_dir.is_absolute():
            raise ValueError(f"I need an absolute path; got {env_dir} instead")

        if not env_dir.is_dir() or not env_dir.exists():
            # create the new environment
            if create_virtual_environment(env_dir) == 0:
                try:
                    make_activation_script(scipyendir, env_dir, scipyen_sdk_dir,
                                    script_name = activation_script,
                                    scripts_dir = scripts_dir)
                    return True
                except:
                    traceback.print_exc()
                    return False
                #return True
            return False
        else:
            try:
                activate_this = str(env_dir / "Scripts" / "activate_this.py")
                print(f"Trying to activate the environment in {env_dir}")
                with open(activate_this) as f:
                    code = compile(f.read(), activate_this, 'exec')
                    exec(code, dict(__file__ = activate_this))
                try:
                    import vigra
                except:
                    vigra_pkg = input(f"Enter full path to archive with compiled vigranumpy package (use forward slashes e.g. 'e:/vigra_pkg.zip'): ")
                    vigra_archive = Path(vigra_pkg)
                    install_precompiled_vigra(vigra_archive, env_dir)

                make_activation_script(scipyendir, env_dir,scipyen_sdk_dir,
                                        script_name = activation_script,
                                        scripts_dir = scripts_dir)
                return True
            except:
                traceback.print_exc()
                return False

    else:
        return True

def make_user_scripts_dir(name="Scripts"):
    """Checks if a user scripts directory exists and is in the PATH.
    """
    try:
        scripts_dir = Path(os.getenv("USERPROFILE")) / name

        if not scripts_dir.is_dir() or not scripts_dir.exists():
            scripts_dir.mkdir()

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
        try:
            current_path, _ = winreg.QueryValueEx(key, "PATH")
        except WindowsError:
            current_path_parts = []

        current_path_parts = current_path.split(os.pathsep)


        if str(scripts_dir) not in current_path_parts:
            try:
                current_path_parts.insert(0, str(scripts_dir))

                new_path = os.pathsep.join(current_path_parts)
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                winreg.CloseKey(key)
                win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, "Environment")
            except:
                traceback.print_exc()
                winreg.CloseKey(key)
        else:
            winreg.CloseKey(key)

        return scripts_dir

    except:
        traceback.print_exc()

def make_sdk_activation_script(scipyendir:Path, scipyenv_dir:Path, scipyen_sdk_dir:Path,
                      script_name="scipyact_vs64.bat",
                      scripts_dir = "Scripts"):
    """Use this when compiling the SDK yourself
    """
    d = Path(os.getenv("USERPROFILE")) / scripts_dir
    if not d.is_dir() or not d.exists():
        make_user_scripts_dir(name=scripts_dir)

    scipyact_bat = Path(scripts_dir) / script_name

    # overwrite if it exists!
    with open(scipyact_bat, mode="wt") as batch_file:
        batch_file.write(f'@echo off\n')
        batch_file.write(f'set scipyendir={scipyendir}\n')
        batch_file.write('CALL "C:\Program Files (x86)\Microsoft Visual Studio\\2019\Community\VC\Auxiliary\Build\\vcvarsall.bat" amd64\n')
        batch_file.write(f"call {Path(scipyenv_dir) / 'Scripts' / 'activate'}\n")
        batch_file.write(f'set "SDK={scipyen_sdk_dir}"\n')
        batch_file.write(f'set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%VIRTUAL_ENV%\lib\site-packages\\vigra;%SDK%\lib;%SDK%\lib64;%LIB%"\n')
        batch_file.write('set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib\site-packages\\vigra;%VIRTUAL_ENV%\lib64;%SDK%\lib;%SDK%\lib64;%LIBPATH%"\n')
        batch_file.write('set "INCLUDE=%VIRTUAL_ENV%\include;%SDK%\include;%INCLUDE%"\n')#
        batch_file.write('set "PATH=%VIRTUAL_ENV%\\bin;%VIRTUAL_ENV%\Scripts;%SDK%\\bin;%PATH%"\n')
        batch_file.write('set "PYTHONSTARTUP=%scipyendir%\scipyen_startup_win.py"\n')
        batch_file.write(f'echo Using Python {sys.version}')
        batch_file.write('echo and Virtual Environment in %VIRTUAL_ENV%\n')


def make_activation_script(scipyendir:Path, scipyenv_dir:Path, scipyen_sdk_dir:Path,
                      script_name:str="scipyact.bat",
                      scripts_dir:str = "Scripts"):
    """Creates convenience activation script for the virtual Python environment
    This is named in script_name and located in scripts_dir which if needed is
    created and added to the user's PATH.
    """
    # check if scripts_dir exists in user's home; create if needed and add to
    # PATH
    d = Path(os.getenv("USERPROFILE")) / scripts_dir
    if not d.exists():
        make_user_scripts_dir(name=scripts_dir)

    scipyact_bat = Path(scripts_dir) / script_name



    print(f"Creating activation script {scipyact_bat} for environment in {scipyenv_dir}")
    print(f" with Python {sys.version} and SDK in {scipyen_sdk_dir}")

    # overwrite if it exists!
    with open(scipyact_bat, mode="wt") as batch_file:
        batch_file.write(f'@echo off\n')
        batch_file.write(f'set scipyendir={scipyendir}\n')
        batch_file.write(f"call {Path(scipyenv_dir) / 'Scripts' / 'activate'}\n")
        batch_file.write(f'set "SDK={scipyen_sdk_dir}"\n')
        batch_file.write(f'set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%VIRTUAL_ENV%\lib\site-packages\\vigra;%SDK%\lib;%SDK%\lib64;%LIB%"\n')
        batch_file.write('set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib\site-packages\\vigra;%VIRTUAL_ENV%\lib64;%SDK%\lib;%SDK%\lib64;%LIBPATH%"\n')
        batch_file.write('set "INCLUDE=%VIRTUAL_ENV%\include;%SDK%\include;%INCLUDE%"\n')#
        batch_file.write('set "PATH=%VIRTUAL_ENV%\\bin;%VIRTUAL_ENV%\Scripts;%SDK%\\bin;%PATH%"\n')
        batch_file.write('set "PYTHONSTARTUP=%scipyendir%\scipyen_startup_win.py"\n')
        batch_file.write(f'echo Using Python {sys.version}')
        batch_file.write('echo and Virtual Environment in %VIRTUAL_ENV%\n')

def make_scipyen_launchers(scipyendir:Path, scipyen_sdk_dir:Path, scipyenv_dir:Path,
                           scripts_dir:str = "Scripts",
                           link_name:str = "Scipyen.lnk",
                           script_name:str = "scipyen.bat"):
    """Creates scipyen launcher batch file and a shortcut.
    The batch file is located in the %USERPROFILE%/scripts_dir, whereas the
    shortut is created on the Desktop.
    """

    scripts_dir = make_user_scripts_dir(name = scripts_dir)

    if scripts_dir is None:
        raise RuntimeError("Cannot create scripts directory")

    print(f"Creating scipyen launcher script {Path(scripts_dir) / script_name}")
    with open(Path(scripts_dir) / script_name, mode = "wt") as batch_file:
        batch_file.write(f'@echo off\n')
        batch_file.write(f'set scipyendir={scipyendir}\n')
        batch_file.write(f"call {Path(scipyenv_dir) / 'Scripts' / 'activate'}\n")
        batch_file.write(f'set "SDK={scipyen_sdk_dir}"\n')
        batch_file.write(f'set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%VIRTUAL_ENV%\lib\site-packages\\vigra;%SDK%\lib;%SDK%\lib64;%LIB%"\n')
        batch_file.write('set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib\site-packages\\vigra;%VIRTUAL_ENV%\lib64;%SDK%\lib;%SDK%\lib64;%LIBPATH%"\n')
        batch_file.write('set "INCLUDE=%VIRTUAL_ENV%\include;%SDK%\include;%INCLUDE%"\n')#
        batch_file.write('set "PATH=%VIRTUAL_ENV%\\bin;%VIRTUAL_ENV%\Scripts;%SDK%\\bin;%PATH%"\n')
        batch_file.write('set "PYTHONSTARTUP=%scipyendir%\scipyen_startup_win.py"\n')
        batch_file.write(f'echo Using Python {sys.version} and Virtual Environment in %VIRTUAL_ENV%\n')
        batch_file.write('cmd /C "python %scipyendir%\scipyen.py"\n')

    #linkpath = Path(scipyendir / link_name)
    #target = Path(scipyendir / script_name)
    target = Path(scripts_dir / script_name)
    workdir = os.getenv("USERPROFILE")

    desktop = winshell.desktop()

    print(f"Creating shortcut {os.path.join(desktop, link_name)}")
    with winshell.shortcut(os.path.join(desktop, link_name)) as shortcut:
        shortcut.path = str(target)
        shortcut.working_directory = workdir
        shortcut.icon = (str(Path(scipyendir / "doc" / "install" / "windows" / "pythonbackend.ico")), 0)
        #shortcut.icon = sys.executable, 0
        shortcut.description = "Scipyen"

def main():
    env_activation = "scipyact.bat"
    user_scripts_dir = "Scripts"
    user_launch_script = "scipyen.bat"
    user_shortcut = "Scipyen.lnk"

    module_path_comps = Path(__module_path__).parts
    scipyen_dir_ndx = module_path_comps.index("scipyen")
    scipyendir = Path(*module_path_comps[:scipyen_dir_ndx+1])

    if len(sys.argv) < 2:
        scipyen_sdk_dir = input("Enter the full path to Scipyen SDK directory (use forward slashes e.g. 'e:/scipyen_sdk'): ")
    else:
        scipyen_sdk_dir = sys.argv[1]

    if not os.path.isdir(scipyen_sdk_dir):
        raise ValueError(f"{scipyen_sdk_dir} does not exist")

    print(f"Using Scipyen SDK in {scipyen_sdk_dir}")

    scipyen_sdk_dir = Path(scipyen_sdk_dir)

    # check if we operate under virtual environment or make one
    if not check_pyenv(scipyendir, scipyen_sdk_dir,
                       activation_script=env_activation,
                       scripts_dir=user_scripts_dir):
        raise RuntimeError("I need a virtual Python environment but cannot find or make one")


    scipyenv_dir = os.getenv("VIRTUAL_ENV")

    print(f"Using virtual Python environment in {scipyenv_dir}")

    make_scipyen_launchers(scipyendir, scipyen_sdk_dir, scipyenv_dir,
                           scripts_dir = user_scripts_dir,
                           link_name = user_shortcut,
                           script_name = user_launch_script)

    print(f"You should now be able to launch Scipyen by calling {user_launch_script} at a new command prompt, or by clicking on the {user_shortcut} Desktop shortcut")
    print("")
    print(f"To activate the virtual environment just call {env_activation} script at a new command prompt")

if __name__ == "__main__":
    if sys.platform == "win32":
        main()
    else:
        raise EnvironmentError(f"This script cannot run on {sys.platform} platform")
