from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("nixio")
hiddenimports = collect_submodules("nixio")

