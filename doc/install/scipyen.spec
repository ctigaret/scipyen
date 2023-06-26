# -*- mode: python ; coding: utf-8 -*-
# NOTE: 2023-06-26 17:25:32
# do something like:
# mkdir -p scipyen_app && cd scipyen_app
# scipyact
# scipyen_app> pyinstaller --distpath ./dist --workpath ./build --clean $HOME/scipyen/doc/install/scipyen.spec

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

def file2TOCEntry(path, topdirparts, strip_path=True):
    parts = [p for p in path.split('/') if p not in topdirparts]
    path = name = os.path.join(*parts)
    if strip_path:
        name = os.path.basename(path)
    return name, path, 'DATA'

def scanForFiles(path, ext, as_ext:True):
    uis = []
    with os.scandir(path) as dirIt:
        for e in dirIt:
            if e.is_dir():
                _uis = scanForFiles(e.path, ext, as_ext)
                if len(_uis):
                    uis.extend(_uis)
                    
            elif e.is_file():
                if (as_ext and e.path.endswith(ext)) or (not as_ext and ext in e.path):
                    uis.append(e.path)
                
    return uis
        

def DataFiles(topdir, ext, **kw):
    import os
    strip_path = kw.get('strip_path', False)
    as_ext = kw.get("as_ext", True)

    topdirparts = topdir.split('/')
    
    entries = scanForFiles(topdir, ext, as_ext)

    # print(f"entries = {entries}\n\n")
    
    return TOC(
        file2TOCEntry(filename, topdirparts, strip_path=strip_path)
        for filename in entries
        if os.path.isfile(filename))

block_cipher = None

uitoc = DataFiles('/home/cezar/scipyen', ".ui")
print(f"uitoc = {uitoc}\n\n")
jsontoc = DataFiles('/home/cezar/scipyen', ".json")
print(f"jsontoc = {jsontoc}\n\n")
pickletoc = DataFiles('/home/cezar/scipyen', ".pkl")
print(f"pickletoc = {pickletoc}\n\n")

abftoc = DataFiles('/home/cezar/scipyen', ".abf")
print(f"abftoc = {abftoc}\n\n")
atftoc = DataFiles('/home/cezar/scipyen', ".atf")
print(f"atftoc = {atftoc}\n\n")
shtoc =  DataFiles('/home/cezar/scipyen', ".sh")
print(f"shtoc = {shtoc}\n\n")
txttoc =  DataFiles('/home/cezar/scipyen', ".txt")
print(f"txttoc = {txttoc}\n\n")
readmetoc =  DataFiles('/home/cezar/scipyen', "README", as_ext=False)
print(f"readmetoc = {readmetoc}\n\n")

a = Analysis(
    ['/home/cezar/scipyen/scipyen.py'],
    pathex=['/home/cezar/scipyen/'],
    binaries=[],
    # binaries=[('/home/cezar/scipyenv.3.11.3/bin/*', 'bin'),
    #           ('/home/cezar/scipyenv.3.11.3/lib/*', 'lib'),
    #           ('/home/cezar/scipyenv.3.11.3/lib64/*', 'lib64'),
    #           ],
    datas=[('/home/cezar/scipyenv.3.11.3/doc', 'doc'),
           ('/home/cezar/scipyenv.3.11.3/etc', 'etc'),
           ('/home/cezar/scipyenv.3.11.3/include','include'),
           ('/home/cezar/scipyenv.3.11.3/man', 'man'),
           ('/home/cezar/scipyenv.3.11.3/share', 'share'),
           ('/home/cezar/scipyen/ephys/options', 'ephys/options'),
           ('/home/cezar/scipyen/ephys/waveforms', 'ephys/waveforms'),
           ('/home/cezar/scipyen/gui', 'gui'),
           ],
    hiddenimports=[],
    hookspath=[],
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
    uitoc,
    # jsontoc,
    pickletoc,
    abftoc,
    atftoc,
    shtoc,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='scipyen',
)
