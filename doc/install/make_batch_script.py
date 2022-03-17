import os, sys, pathlib
from pathlib import Path
try:
    import readline
except:
    pass


if os.getenv("VIRTUAL_ENV") is None:
    raise RuntimeError(f"This module must be run inside a Python virtual environment")

if sys.platform == "win32":
    import winshell

#from win32com.client import Dispatch

__module_path__ = os.path.abspath(os.path.dirname(__file__))


def main():
    module_path_comps = Path(__module_path__).parts
    scipyen_dir_ndx = module_path_comps.index("scipyen")
    scipyendir = Path(*module_path_comps[:scipyen_dir_ndx+1])

    if len(sys.argv) < 2:
        scipyen_sdk_dir = input("Enter the full path to Scipyen SDK directory: ")
    else:
        scipyen_sdk_dir = sys.argv[1]

    if not os.path.isdir(scipyen_sdk_dir):
        raise ValueError(f"{scipyen_sdk_dir} does not exist")

    print(f"Using Scipyen SDK in {scipyen_sdk_dir}")

    scipyen_sdk_dir = Path(scipyen_sdk_dir)

    scipyenv_dir = os.getenv("VIRTUAL_ENV")

    with open(scipyendir / "scipyen.bat", mode = "wt") as batch_file:
        batch_file.write(f"@echo off\n")
        batch_file.write(f"set scipyendir={scipyendir}\n")
        batch_file.write(f"call {Path(scipyenv_dir) / 'Scripts' / 'activate'}\n")
        batch_file.write(f'set "SDK={scipyen_sdk_dir}"\n')
        batch_file.write(f'set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%VIRTUAL_ENV%\lib\site-packages\\vigra;%SDK%\lib;%SDK%\lib64;%LIB%"\n')
        batch_file.write('set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib\site-packages\\vigra;%VIRTUAL_ENV%\lib64;%SDK%\lib;%SDK%\lib64;%LIBPATH%"\n')
        batch_file.write('set "INCLUDE=%VIRTUAL_ENV%\include;%SDK%\include;%INCLUDE%"\n')#
        batch_file.write('set "PATH=%VIRTUAL_ENV%\\bin;%VIRTUAL_ENV%\Scripts;%SDK%\\bin;%PATH%"\n')
        batch_file.write('set "PYTHONSTARTUP=%scipyendir%\scipyen_startup_win.py"\n')
        batch_file.write('echo "Using Python Virtual Environment in %VIRTUAL_ENV%"\n')
        batch_file.write('cmd /C "python %scipyendir%\scipyen.py"\n')

    linkpath = Path(scipyendir / "Scipyen.lnk")
    target = Path(scipyendir / "scipyen.bat")
    workdir = os.getenv("USERPROFILE")

    desktop = winshell.desktop()

    with winshell.shortcut(os.path.join(desktop, "Scipyen.lnk")) as shortcut:
        shortcut.path = str(target)
        shortcut.working_directory = workdir
        shortcut.icon = (str(Path(scipyendir / "doc" / "install" / "windows" / "pythonbackend.ico")), 0)
        #shortcut.icon = sys.executable, 0
        shortcut.description = "Scipyen"

if __name__ == "__main__":
    if sys.platform == "win32":
        main()
