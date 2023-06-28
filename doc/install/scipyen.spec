# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

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
        
def file2TOCEntry(path:str, topdirparts:list, strip_path:bool=True, file_category:str="DATA"):
    parts = [p for p in path.split('/') if p not in topdirparts]
    path = name = os.path.join(*parts)
    path = os.path.dirname(path)
    if strip_path:
        name = os.path.basename(path)
    return name, path, file_category


def DataFiles(topdir, ext, **kw):
    import os
    strip_path = kw.get('strip_path', False)
    as_ext = kw.get("as_ext", True)

    topdirparts = topdir.split('/')
    
    items = scanForFiles(topdir, ext, as_ext)

    if ext == ".ui":
        print(f"ui files = {items}\n\n")

    
    return TOC(
        file2TOCEntry(filename, topdirparts, strip_path=strip_path)
        for filename in items
        if os.path.isfile(filename))

block_cipher = None

# uitoc = DataFiles('/home/cezar/scipyen/src', ".ui", strip_path=True)
uitoc = DataFiles('/home/cezar/scipyen/src', ".ui", strip_path=False)
print(f"uitoc = {uitoc}\n\n")
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

datas = collect_data_files("scipyen") # works only when scipyen is a package
datas.extend(uitoc)

print(f"\ndatas = {datas}\n")

a = Analysis(
    ['../../src/scipyen/scipyen.py'],
    pathex=['/home/cezar/scipyen/src'], # ← to find the scipyen package
    binaries=[],
    # binaries=[('/home/cezar/scipyenv.3.11.3/bin/*', 'bin'),
    #           ('/home/cezar/scipyenv.3.11.3/lib/*', 'lib'),
    #           ('/home/cezar/scipyenv.3.11.3/lib64/*', 'lib64'),
    #           ],
    datas=datas,
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
    hiddenimports=[],
    hookspath=['/home/cezar/scipyen/src/__pyinstaller'],
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
