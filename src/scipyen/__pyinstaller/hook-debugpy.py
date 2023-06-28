import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
sys._xoptions["frozen_modules"] = False
datas = collect_data_files("debugpy")
hiddenimports = collect_submodules("debugpy")
# all_imports = collect_submodules("debugpy")
