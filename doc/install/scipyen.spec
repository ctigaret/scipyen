# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (collect_data_files, collect_submodules, 
                                     collect_all)

# NOTE: 2023-06-26 17:25:32
# do something like:
# mkdir -p scipyen_app && cd scipyen_app
# scipyact
# scipyen_app> pyinstaller --distpath ./dist --workpath ./build --clean --noconfirm $HOME/scipyen/doc/install/scipyen.spec


def datafile(path, strip_path=True):
    parts = path.split('/')
    path = name = os.path.join(*parts)
    if strip_path:
        name = os.path.basename(path)
    return name, path, 'DATA'

# def Datafiles(*filenames, **kw):
#     import os
#     
# 
#     strip_path = kw.get('strip_path', True)
#     return TOC(
#         datafile(filename, strip_path=strip_path)
#         for filename in filenames
#         if os.path.isfile(filename))

def scanForFiles(path, ext, as_ext:True):
    items = []
    with os.scandir(path) as dirIt:
        for e in dirIt:
            if e.is_dir():
                _items = scanForFiles(e.path, ext, as_ext)
                if len(_items):
                    items.extend(_items)
                    
            elif e.is_file():
                if (as_ext and e.path.endswith(ext)) or (not as_ext and ext in e.path):
                    items.append(e.path)
                
    return items
        
def file2TOCEntry(src_path:str, topdirparts:list, file_category:str="DATA"):
    parts = [p for p in path.split('/') if p not in topdirparts]
    my_path = name = os.path.join(*parts)
    target_path = os.path.dirname(my_path)
    return target_path, src_path, file_category

def file2entry(src_path:str, topdirparts:list, strip_path:bool=True) -> tuple:
    """Returns a 2-tuple (source_full_path, target_dir)
    To be used in the Analysis constructor, below
    """
    parts = [p for p in src_path.split('/') if p not in topdirparts]
    my_path = name = os.path.join(*parts)
    target_path = os.path.dirname(my_path)
    # if strip_path:
    #     name = os.path.basename(path)
    return src_path, target_path
    

def DataFiles(topdir, ext, **kw):
    import os
    # strip_path = kw.get('strip_path', False)
    as_ext = kw.get("as_ext", True)
    forAnalysis = kw.get("forAnalysis", False)

    topdirparts = topdir.split('/')
    
    items = scanForFiles(topdir, ext, as_ext)

    # if ext == ".ui":
    #     print(f"ui files = {items}\n\n")
    
    # NOTE: 2023-06-28 11:14:37
    # The Analysis.datas expects a list (src, dest) where:
    #
    #   • src is the absolute or relative path of a data file
    #   • dest is the directory where the data file will be placed
    #
    # The COLLECT constructor expects a TOC, where the TOC is a list-like object
    #   with tuples (name, path, typecode) where:
    #
    #   • name - final name (path ?) inside the bundle -- the runtime name
    #   • path - the full path name in build (source?)
    #   • typecode - "DATA" for data files, see PyInstaller.building.datastruct.TOC for details
    #
    #   WARNING: the name, path in the COLLECT are, respectively, the same as 
    #   dest, src in Analysis.datas (but the order is reversed)

    if forAnalysis:
        return [file2entry(filename, topdirparts) for filename in items]
    
    return TOC(
        file2TOCEntry(filename, topdirparts)
        for filename in items
        if os.path.isfile(filename))

block_cipher = None

# uitoc = DataFiles('/home/cezar/scipyen/src', ".ui", strip_path=True)

# NOTE: 2023-06-28 11:07:31
# expects a list of tuples (src_full_path_or_glob, dest_dir), see NOTE: 2023-06-28 11:08:08
uitoc = DataFiles('/home/cezar/scipyen/src', ".ui", forAnalysis=True)
# print(f"uitoc = {uitoc}\n\n")
# 
# pickletoc = DataFiles('/home/cezar/scipyen/src', ".pkl")
# print(f"pickletoc = {pickletoc}\n\n")
# 
# abftoc = DataFiles('/home/cezar/scipyen/src', ".abf")
# print(f"abftoc = {abftoc}\n\n")
# atftoc = DataFiles('/home/cezar/scipyen/src', ".atf")
# print(f"atftoc = {atftoc}\n\n")
# shtoc =  DataFiles('/home/cezar/scipyen/src', ".sh")
# print(f"shtoc = {shtoc}\n\n")
# txttoc =  DataFiles('/home/cezar/scipyen/src', ".txt")
# print(f"txttoc = {txttoc}\n\n")
# readmetoc =  DataFiles('/home/cezar/scipyen/src', "README", as_ext=False)
# print(f"readmetoc = {readmetoc}\n\n")

# NOTE: 2023-06-28 11:09:08 DOES NOT WORK WITH SCIYEN BECAUSE SCIPYEN IS NOT 
# A(N INSTALLED) PACKAGE
# datas = collect_data_files("scipyen")
binaries = list()
datas = list()
hiddenimports = list()

# NOTE: 2023-06-28 11:06:50 This WORKS!!! 
# see NOTE: 2023-06-28 11:07:31 and NOTE: 2023-06-28 11:08:08
datas.extend(uitoc)

# jqc_data = collect_data_files("jupyter_qtconsole_colorschemes")
# datas.extend(jqc_data)
# # NOTE: 2023-06-28 11:45:44
# # either this, or override hook-pygments.py / hook-pkg_resources.py
# jqc = collect_submodules("jupyter_qtconsole_colorschemes")

jqc_datas, jqc_binaries, jqc_hiddenimports = collect_all("jupyter_qtconsole_colorschemes")
datas.extend(jqc_datas)
binaries.extend(jqc_binaries)
hiddenimports.extend(jqc_hiddenimports)

# print(f"\ndatas = {datas}\n")

a = Analysis(
    ['../../src/scipyen/scipyen.py'],
    pathex=['/home/cezar/scipyen/src/scipyen'], # ← to find the scipyen package
    binaries=[],
    # binaries=[('/home/cezar/scipyenv.3.11.3/bin/*', 'bin'),
    #           ('/home/cezar/scipyenv.3.11.3/lib/*', 'lib'),
    #           ('/home/cezar/scipyenv.3.11.3/lib64/*', 'lib64'),
    #           ],
    datas=datas,
    # NOTE: 2023-06-28 11:08:08
    # Example of what is needed for this attribute:
    # datas=[('/home/cezar/scipyenv.3.11.3/doc', 'doc'),
    #        ('/home/cezar/scipyenv.3.11.3/etc', 'etc'),
    #        ('/home/cezar/scipyenv.3.11.3/include','include'),
    #        ('/home/cezar/scipyenv.3.11.3/man', 'man'),
    #        ('/home/cezar/scipyenv.3.11.3/share', 'share'),
    #        ('/home/cezar/scipyen/src/ephys/options', 'ephys/options'),
    #        ('/home/cezar/scipyen/src/ephys/waveforms', 'ephys/waveforms'),
    #        # ('/home/cezar/scipyen/src/gui', 'gui'),
    #        # ('/home/cezar/scipyen/src/imaging', 'imaging'),
    #        ],
    # hiddenimports=[],
    hiddenimports=hiddenimports,
    hookspath=['/home/cezar/scipyen/src/scipyen/__pyinstaller'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='scipyen',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    # uitoc,
    # jsontoc,
    # pickletoc,
    # abftoc,
    # atftoc,
    # shtoc,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='scipyen',
)