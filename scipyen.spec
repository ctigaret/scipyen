# -*- mode: python ; coding: utf-8 -*-
import io, os, sys, subprocess, shutil, tempfile, typing, pathlib, traceback
from PyInstaller.utils.hooks import (collect_data_files, collect_submodules, 
                                     collect_all)
from PyInstaller.building.datastruct import Tree

hasNeuron=False
try:
    import neuron
    hasNeuron = True
except:
    hasNeuron = False

myfile = sys.argv[-1] # the spec file ; this is THE LAST argument in the argument list to pyinstaller
myfile = pathlib.Path(myfile).absolute()
scipyen_dir = os.fspath(myfile.parent)

print(f"scipyen_dir = {scipyen_dir}")

# NOTE: 2023-06-26 17:25:32
# This is for the developer, NOT the final user:
# To create a distributable scipyen application, you need to:
# 1) clone the scipyen git repo locally (e.g. to $HOME/scipyen)- NOTE: this is assumed to be the case from here onwards
# 2) use the install.sh script to create a local virtual environment with all the 
#   binaries needed for Scipyen (this includes building PyQt5, VIGRA and - -optionally - NEURON)
# 3) activate the new environment, then buld the distributable app:
#   in a bash shell do something like (NOTE: 'user@host:>'is your terminal prompt
#   and it may look different on your machine, make sure you understand this):
#
#       user@host:>scipyact # to activate the environment
#       user@host:>mkdir -p scipyen_app && cd scipyen_app
#       user@host:~/scipyen_app> pyinstaller --distpath ./dist --workpath ./build --clean --noconfirm $HOME/scipyen/scipyen.spec
#
#   alternatively, you don't have to cd to scipyen_app, so from the $HOME, call:
#       user@host:> pyinstaller --distpath scipyen_app/dist --workpath scipyen_app/build --clean --noconfirm scipyen/scipyen.spec
#
#
# On windows I use mamba (a faster alternative to <ana>conda) to build a virtual environment (e.g. e:\scipyenv) - best is
# to use a Miniforge terminal running with as administrator.
# With that environment activated (see mamba documentation for details), call (e.g. from the root of e: drive):
# pyinstaller --dist_path e:\scipyen_app\dist --workpath e:\scipyen_app\build --clean --noconfirm e:\scipyen\scipyen_win10.spec
# NOTE: You may have to modify the paths above to suit your local installation
# TODO: For more customization contemplate calling pyinstaller as above from a
# bash script


if "--distpath" in sys.argv:
    ndx = sys.argv.index("--distpath")
    if ndx < (len(sys.argv) - 1):
        distpath = sys.argv[ndx+1]

    else:
        distpath = DEFAULT_DISTPATH
else:
    distpath = DEFAULT_DISTPATH

if not myfile.is_absolute():
    myfile = myfile.absolute()

    
mydir = myfile.parents[0]

print(f"\nWARNING: External IPython consoles - including NEURON - are NOT yet supported by the bundled Scipyen\n\n")

#def datafile(path, strip_path=True):
    #parts = path.split('/')
    #path = name = os.path.join(*parts)
    #if strip_path:
        #name = os.path.basename(path)
    #return name, path, 'DATA'

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
    if not isinstance(src_path, pathlib.Path):
        src_path = pathlibPath(src_path)

    parts = [p for p in src_path.parts if p not in topdirparts]
    #parts = [p for p in path.split('/') if p not in topdirparts]
    #my_path = name = os.path.join(*parts)
    #target_path = os.path.dirname(my_path)

    my_path = name = pathlib.Path(parts[0]).joinpath(*parts[1:])
    target_path = os.fspath(my_path.parent)
    return target_path, os.fspath(src_path), file_category

def file2entry(src_path:str, topdirparts:list, strip_path:bool=True) -> tuple:
    """Returns a 2-tuple (source_full_path, target_dir)
    To be used in the Analysis constructor, below
    
    Parameters:
    ===========
    src_path: fully-qualified path to the file (including the file name & extension)
        
    topdirparts: a list of directories representing the path to the actual file
    
    """
    if not isinstance(src_path, pathlib.Path):
        src_path = pathlib.Path(src_path)

    parts = [p for p in src_path.parts if p not in topdirparts]
    # if isinstance(destination, str):
    #     parts.insert(0, destination)
        
    my_path = name = pathlib.Path(parts[0]).joinpath(*parts[1:])
    #my_path = name = os.path.join(*parts)
    #target_path = os.path.dirname(my_path)
    try:
        target_path = os.fspath(my_path.parent)
    except:
        traceback.print_exc()
        target_path = '.'

    if len(target_path) == 0:
        target_path = '.'
        
    return os.fspath(src_path), target_path
    

def DataFiles(topdir, ext, **kw):
    import os
    # strip_path = kw.get('strip_path', False)
    as_ext = kw.get("as_ext", True)
    forAnalysis = kw.get("forAnalysis", False)
    # destination = kw.get("destination", None)

    if not isinstance(topdir, pathlib.Path):
        topdir = pathlib.Path(topdir)

    topdirparts = topdir.parts
    
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
        # return [file2entry(filename, topdirparts, destination=destination) for filename in items]
    
    return TOC(
        file2TOCEntry(filename, topdirparts) for filename in items if os.path.isfile(filename))


def getQt5PluginsDir():
    # NOTE: on windows this is qtpaths; on SuSE this is qtpaths-qt5
    if sys.platform == "win32":
        qtpaths_exec = "qtpaths"
    else:
        qtpaths_exec = "qtpaths-qt5"
    pout = subprocess.run([qtpaths_exec, "--plugin-dir"],
                          encoding="utf-8", capture_output=True)
    
    if pout.returncode != 0:
        raise RuntimeError(f"The subprocess for qtpaths-qt5 returned {pout.returncode}")
    
    plugins_dir = pout.stdout.strip("\n")
    
    return plugins_dir

def getQt5Plugins(path):
    return Tree(root=path, prefix="PyQt5/Qt5/plugins", typecode="BINARY")
    
block_cipher = None

# uitoc = DataFiles('/home/cezar/scipyen/src', ".ui", strip_path=True)

# NOTE: 2023-06-28 11:07:31
# expects a list of tuples (src_full_path_or_glob, dest_dir), see NOTE: 2023-06-28 11:08:08
# "forAnalysis" is a flag indicating that tuples are generated for use by the Analysis object
# constructed below
uitoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".ui", forAnalysis=True) # WARNING must be reflected in core.sysutils.adapt_ui_path
#print(f"uitoc: {uitoc}")
txttoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".txt", forAnalysis=True)
svgtoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".svg", forAnalysis=True)
pngtoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".png", forAnalysis=True)
jpgtoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".jpg", forAnalysis=True)
giftoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".fig", forAnalysis=True)
tifftoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".tif", forAnalysis=True)
tifftoc.extend(DataFiles(os.path.join(scipyen_dir, 'src'), ".tiff", forAnalysis=True))
icotoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".ico", forAnalysis=True)
xsltoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".xsl", forAnalysis=True)
shtoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".sh", forAnalysis=True)
qrctoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".qrc", forAnalysis=True)
readmetoc = DataFiles(os.path.join(scipyen_dir, 'src'), "README", as_ext=False, forAnalysis=True)
pkltoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".pkl", forAnalysis=True)
hdftoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".h5", forAnalysis=True)
hdftoc.extend(DataFiles(os.path.join(scipyen_dir, 'src'), ".hdf5", forAnalysis=True))
hdftoc.extend(DataFiles(os.path.join(scipyen_dir, 'src'), ".hdf", forAnalysis=True))
abftoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".abf", forAnalysis=True)
atftoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".atf", forAnalysis=True)
yamltoc = DataFiles(os.path.join(scipyen_dir, 'src'), ".yaml", forAnalysis=True)

# NOTE: 2023-06-28 11:09:08 
# collect_data_files DOES NOT WORK WITH SCIPYEN BECAUSE SCIPYEN IS NOT 
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

# NOTE: 2023-07-14 15:19:48
# this gets the name of the scipyen git branch we are packaging ⇒ namesfx
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
                        
platform = sys.platform
product = f"scipyen{namesfx}_{platform}"

bundlepath = os.path.join(distpath, product)

print(f"bundlepath = {bundlepath}")
if sys.platform == "linux":
    desktoptempdir = tempfile.mkdtemp()
    desktop_file_name = os.path.join(desktoptempdir, f"Scipyen{namesfx}.desktop")
    # desktop_icon_file = os.path.join(bundlepath,"gui/resources/images/pythonbackend.svg")
    desktop_icon_file = "pythonbackend.svg"
    exec_file = os.path.join(bundlepath, "scipyen")
    desktop_file_contents = ["[Desktop Entry]",
    "Type=Application",
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
    "TerminalOptions=\s--noclose",
    "X-DBUS-ServiceName=",
    "X-DBUS-StartupType=",
    "X-KDE-SubstituteUID=false",
    "X-KDE-Username=",
    ]
    with open(desktop_file_name, "wt") as desktop_file:
        for line in desktop_file_contents:
            desktop_file.write(f"{line}\n")
            
    dist_install_script = ["#!/bin/bash",
                        "mydir=`dirname $0`",
                        "whereami=`realpath ${mydir}`",
                        "chown -R root:root ${whereami}",
                        "ln -s -b ${whereami}/scipyen /usr/local/bin/",
                        "ln -s -b ${whereami}/Scipyen.desktop /usr/share/applications/"]

    install_script_tempdir = tempfile.mkdtemp()
    dist_install_script_name = os.path.join(install_script_tempdir, "dist_install.sh")

    with open(dist_install_script_name, "wt") as dist_install:
        for line in dist_install_script:
            dist_install.write(f"{line}\n")
            
    datas.append(("/home/cezar/scipyen/src/scipyen/gui/resources/images/pythonbackend.svg", '.'))
    datas.append((desktop_file_name, '.'))
    datas.append((dist_install_script_name, '.'))

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
print(f"jqc_hiddenimports = {jqc_hiddenimports}")
datas.extend(jqc_datas)
binaries.extend(jqc_binaries)
hiddenimports.extend(jqc_hiddenimports)

# NOTE: 2023-06-29 08:32:55
# try as above for jupyter_client (needed because "local-provisioner" issues 
# when starting external IPython console in Scipyen)

jc_datas, jc_binaries, jc_hiddenimports = collect_all("jupyter_client")
print(f"jc_hiddenimports = {jc_hiddenimports}")
datas.extend(jc_datas)
binaries.extend(jc_binaries)
hiddenimports.extend(jc_hiddenimports)
# hiddenimports.extend(["python-dateutil", "pyzmq"])

zmq_datas, zmq_binaries, zmq_hiddenimports = collect_all("pyzmq")
datas.extend(zmq_datas)
binaries.extend(zmq_binaries)
hiddenimports.extend(zmq_hiddenimports)

qt5plugins_dir = getQt5PluginsDir()

qt5plugins_toc = getQt5Plugins(qt5plugins_dir)

# print(f"qt5plugins_toc = {qt5plugins_toc}")

# binaries.extend(qt5plugins)

# NOTE: 2023-07-15 10:47:12
# stuff that the PyInstaller built-in hooks for PyQt5 is definitely missing:
# kde extensions & plugins (that's OK as we don't have python bindings for it)
# deepin extensions & plugins (dtk, dde; again, that's OK since we don't have python bindings for these)


# if hasNeuron:
#     nrn_data, nrn_binaries, nrn_hiddenimports = collect_all("neuron")
#     datas.extend(nrn_data)
#     binaries.extend(nrn_binaries)
#     hiddenimports.extend(nrn_hiddenimports)

# print(f"\ndatas = {datas}\n")

# NOTE: 2023-07-14 15:22:26
# hookspath contains code for pyinstaller hooks called ONLY when the Analyser
# detects an import in Scipyen code; these won't work for NEURON stuff....

a = Analysis(
    [os.path.join(scipyen_dir, 'src/scipyen/scipyen.py')],
    pathex=[os.path.join(scipyen_dir, 'src/scipyen')], # ← to find the scipyen package
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
    hookspath=[os.path.join(scipyen_dir, 'src/scipyen/__pyinstaller')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == "win32":
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
        icon=os.path.join(scipyen_dir, "doc/install/pythonbackend.ico")
    )
else:
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
    # a.binaries,
    a.binaries + qt5plugins_toc,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=product, # name of distribution directory (e.g, 'scipyen_dev' etc)
)

if isinstance(tempdir, str) and os.path.isdir(tempdir):
    shutil.rmtree(tempdir)
    
if isinstance(desktoptempdir, str) and os.path.isdir(desktoptempdir):
    shutil.rmtree(desktoptempdir)
    
