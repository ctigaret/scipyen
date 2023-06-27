from PyInstaller.utils.hooks import collect_data_files, collect_submodules
datas = collect_data_files("debugpy")
hiddenimports = collect_submodules("debugpy")
# all_imports = collect_submodules("debugpy")
