# -*- mode: python ; coding: utf-8 -*-
import io, os, sys, subprocess, shutil, tempfile
from PyInstaller.utils.hooks import (collect_data_files, collect_submodules, 
                                     collect_all)

# NOTE: 2023-06-26 17:25:32
# do something like:
# mkdir -p scipyen_app && cd scipyen_app
# scipyact
# scipyen_app> pyinstaller --distpath ./dist --workpath ./build --clean --noconfirm $HOME/scipyen/scipyen.spec
# or from the $HOME:
# scipyen_app> pyinstaller --distpath scipyen_app/dist --workpath scipyen_app/build --clean --noconfirm scipyen/scipyen.spec

myfile = sys.argv[-1]


if "--distpath" in sys.argv:
    ndx = sys.argv.index("--distpath")
    if ndx < (len(sys.argv) - 1):
        distpath = sys.argv[ndx+1]
        
    else:
        distpath = DEFAULT_DISTPATH
else:
    distpath = DEFAULT_DISTPATH

if not os.path.isabs(myfile):
    myfile = os.path.abspath(myfile)
    
mydir = os.path.dirname(myfile)

print(f"\nWARNING: External IPython consoles - including NEURON - are NOT yet supported by the bundled Scipyen\n\n")

def datafile(path, strip_path=True):
    parts = path.split('/')
    path = name = os.path.join(*parts)
    if strip_path:
        name = os.path.basename(path)
    return name, path, 'DATA'

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
    if len(target_path) == 0:
        target_path = '.'
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
txttoc = DataFiles('/home/cezar/scipyen/src', ".txt", forAnalysis=True)
svgtoc = DataFiles('/home/cezar/scipyen/src', ".svg", forAnalysis=True)
pngtoc = DataFiles('/home/cezar/scipyen/src', ".png", forAnalysis=True)
jpgtoc = DataFiles('/home/cezar/scipyen/src', ".jpg", forAnalysis=True)
giftoc = DataFiles('/home/cezar/scipyen/src', ".fig", forAnalysis=True)
tifftoc = DataFiles('/home/cezar/scipyen/src', ".tif", forAnalysis=True)
tifftoc.extend(DataFiles('/home/cezar/scipyen/src', ".tiff", forAnalysis=True))
icotoc = DataFiles('/home/cezar/scipyen/src', ".ico", forAnalysis=True)
xsltoc = DataFiles('/home/cezar/scipyen/src', ".xsl", forAnalysis=True)
shtoc = DataFiles('/home/cezar/scipyen/src', ".sh", forAnalysis=True)
qrctoc = DataFiles('/home/cezar/scipyen/src', ".qrc", forAnalysis=True)
readmetoc = DataFiles('/home/cezar/scipyen/src', "README", as_ext=False, forAnalysis=True)
pkltoc = DataFiles('/home/cezar/scipyen/src', ".pkl", forAnalysis=True)
hdftoc = DataFiles('/home/cezar/scipyen/src', ".h5", forAnalysis=True)
hdftoc.extend(DataFiles('/home/cezar/scipyen/src', ".hdf5", forAnalysis=True))
hdftoc.extend(DataFiles('/home/cezar/scipyen/src', ".hdf", forAnalysis=True))
abftoc = DataFiles('/home/cezar/scipyen/src', ".abf", forAnalysis=True)
atftoc = DataFiles('/home/cezar/scipyen/src', ".atf", forAnalysis=True)
yamltoc = DataFiles('/home/cezar/scipyen/src', ".yaml", forAnalysis=True)

# NOTE: 2023-06-28 11:09:08 DOES NOT WORK WITH SCIYEN BECAUSE SCIPYEN IS NOT 
# A(N INSTALLED) PACKAGE
# datas = collect_data_files("scipyen")
binaries = list()
datas = list()
hiddenimports = list()

tempdir = ""
desktoptempdir=""
# origin_fn = None
# origin_file = None
namesfx = ""

if os.path.isdir(os.path.join(mydir, ".git")):
    gitout = subprocess.run(["git", "-C", mydir, "branch", "--show-current"],
                            capture_output=True)
    
    if gitout.returncode == 0 and len(gitout.stdout):
        gitbranch = gitout.stdout.decode().split("\n")[0]
        if gitbranch != "master":
            namesfx = f"_{gitbranch}"
            
        if len(gitbranch):
            gitout = subprocess.run(["git", "-C", mydir, "status", "--short", "--branch"],
                                    capture_output=True)
            if gitout.returncode == 0:
                branch_status = gitout.stdout.decode().split("\n")
                branch_status.insert(0, f"Bundled from '{gitbranch}' git branch with status:")
                
                print(f"branch_status = {branch_status}")
                
                if len(branch_status):
                    tempdir = tempfile.mkdtemp()
                    origin_file_name = os.path.join(tempdir, "bundle_origin")
                    with open(origin_file_name, "wt") as origin_file:
                        for s in branch_status:
                            origin_file.write(f"{s}\n")
                        
                    datas.append((origin_file_name, '.'))
                        
product = f"scipyen{namesfx}"
bundlepath = os.path.join(distpath, product)

desktoptempdir = tempfile.mkdtemp()
desktop_file_name = os.path.join(desktoptempdir, f"Scipyen{namesfx}.desktop")
desktop_icon_file = os.path.join(bundlepath,"gui/resources/images/pythonbackend.svg")
exec_file = os.path.join(bundlepath, "scipyen")
desktop_file_contents = ["[Desktop Entry]",
"Type=Application"
"Name[en_GB]=Scipyen",
"Name=Scipyen",
"Comment[en_GB]=Scientific Python Environment for Neurophysiology",
"Comment=Scientific Python Environment for Neurophysiology",
"GenericName[en_GB]=Scientific Python Environment for Neurophysiology",
"GenericName=Scientific Python Environment for Neurophysiology",
f"Icon={desktop_icon_file}",
"Categories=Science;Utilities;",
"Exec=%k/scipyen",
"MimeType=",
"Path=",
"StartupNotify=true",
"Terminal=true",
"TerminalOptions=\s",
"X-DBUS-ServiceName=",
"X-DBUS-StartupType=",
"X-KDE-SubstituteUID=false",
"X-KDE-Username=",
]
with open(desktop_file_name, "wt") as desktop_file:
    for line in desktop_file_contents:
        desktop_file.write(f"{line}\n")

datas.append((desktop_file_name, '.'))

# NOTE: 2023-06-28 11:06:50 This WORKS!!! 
# see NOTE: 2023-06-28 11:07:31 and NOTE: 2023-06-28 11:08:08
datas.extend(uitoc)
datas.extend(txttoc)
datas.extend(svgtoc)
datas.extend(pngtoc)
datas.extend(jpgtoc)
datas.extend(giftoc)
datas.extend(tifftoc)
datas.extend(icotoc)
datas.extend(xsltoc)
datas.extend(shtoc)
datas.extend(qrctoc)
datas.extend(readmetoc)
datas.extend(pkltoc)
datas.extend(hdftoc)
datas.extend(abftoc)
datas.extend(atftoc)
datas.extend(yamltoc)

# NOTE: 2023-06-28 11:45:44
# I think the next line below ('collect_all') is better than trying to see what
# can be tweaked in hook-pygments.py / hook-pkg_resources.py
jqc_datas, jqc_binaries, jqc_hiddenimports = collect_all("jupyter_qtconsole_colorschemes")
datas.extend(jqc_datas)
binaries.extend(jqc_binaries)
hiddenimports.extend(jqc_hiddenimports)

# NOTE: 2023-06-29 08:32:55
# try as above for jupyter_client (needed because "local-provisioner" issues 
# when starting external IPython console in Scipyen)

jc_datas, jc_binaries, jc_hiddenimports = collect_all("jupyter_client")
datas.extend(jc_datas)
binaries.extend(jc_binaries)
hiddenimports.extend(jc_hiddenimports)

# print(f"\ndatas = {datas}\n")

a = Analysis(
    ['/home/cezar/scipyen/src/scipyen/scipyen.py'],
    pathex=['/home/cezar/scipyen/src/scipyen'], # ← to find the scipyen package
    binaries=binaries,
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
    name='scipyen', # name of the final executable
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
    strip=False,
    upx=True,
    upx_exclude=[],
    name=product, # name of distribution directry (e.g, 'scipyen_dev' etc)
    # name='scipyen',
)

if isinstance(tempdir, str) and os.path.isdir(tempdir):
    shutil.rmtree(tempdir)
    
if isinstance(desktoptempdir, str) and os.path.isdir(desktoptempdir):
    shutil.rmtree(desktoptempdir)
    