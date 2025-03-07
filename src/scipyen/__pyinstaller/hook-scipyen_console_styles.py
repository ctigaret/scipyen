from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("scipyen_console_styles")
hiddenimports = collect_submodules("scipyen_console_styles")
