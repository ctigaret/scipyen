from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("nixio")
# all_imports = collect_submodules("nixio")
hiddenimports = collect_submodules("nixio")
# hiddenimports = []



