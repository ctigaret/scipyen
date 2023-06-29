from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

datas, binaries, hiddenimports = collect_all("jupyter_client")
# datas = collect_data_files("jupyter_client")
# hiddenimports = collect_submodules("jupyter_client")
