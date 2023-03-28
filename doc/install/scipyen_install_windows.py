import sys, os, subprocess, io, datetime, winreg, shutil
from contextlib import contextmanager
from functools import singledispatch
#from collections import deque

@contextmanager
def registry_key(parent, name:str):
    key = winreg.OpenKey(parent, name)
    try:
        yield key
    finally:
        winreg.CloseKey(key)

@singledispatch
def get_n_subkeys(key):
    """Returns the number of subkeys in the key
    """
    pass

@get_n_subkeys.register(str)
def _(key):
    if key.startswith("HKEY") and key in winreg.__dict__:
        return winreg.QueryInfoKey(key)[0]
    else:
        raise ValueError(f"key {key} does not exist in the Windows registry")

@get_n_subkeys.register(winreg.HKEYType)
def _(key):
    if not key:
        raise ValueError(f"key {key} is invalid")
    return winreg.QueryInfoKey(key)[0]

@singledispatch
def get_n_values(key):
    """
    Return the number of values in the key
    """
    pass

@get_n_values.register(str)
def _(key):
    if key.startswith("HKEY") and key in winreg.__dict__:
        return winreg.QueryInfoKey(key)[1]
    else:
        raise ValueError(f"key {key} does not exist in the Windows registry")

@get_n_subkeys.register(winreg.HKEYType)
def _(key):
    if not key:
        raise ValueError(f"key {key} is invalid")
    return winreg.QueryInfoKey(key)[1]

@singledispatch
def get_subkeys(key):
    """
    Return a list of subkey names for this key
    """
    pass

@get_subkeys.register(str)
def _(key):
    if key.startswith("HKEY") and key in winreg.__dict__:
        return [winreg.EnumKey(key, k) for k in range(get_n_subkeys(key))]
    else:
        raise ValueError(f"key {key} does not exist in the Windows registry")


@get_subkeys.register(winreg.HKEYType)
def _(key):
    if not key:
        raise ValueError(f"key {key} is invalid")
    return [winreg.EnumKey(key, k) for k in range(get_n_subkeys(key))]

@singledispatch
def get_key_values(key):
    """
    Returns a list of values in this key
    """
    pass

@get_key_values.register(str)
def _(key):
    if key not in winreg.__dict__:
        raise ValueError(f"key {key} does not exist in the Windows registry")

    values_dict = dict()
    for k in range(get_n_values(key)):
        name, obj, obj_type = winreg.EnumValue(key, k)
        values_dict[name]=(obj, obj_type)

    return values_dict

@get_key_values.register(winreg.HKEYType)
def _(key):
    if not key:
        raise ValueError(f"key {key} is invalid")

    values_dict = dict()
    for k in range(get_n_values(key)):
        name, obj, obj_type = winreg.EnumValue(key, k)
        values_dict[name]=(obj, obj_type)

    return values_dict

def check_flag_file(flagname, pyvenv):
    flagfile = os.path.join(pyvenv, flagname)
    return os.path.isfile(flagfile)

def make_flag_file(flagname, pyvenv, msg):
    flagfilename=os.path.join(pyvenv, flagname)
    with open(flagfilename, "w") as flagfile:
        flagfile.write(msg)


#def find_reg_subkey(parent, name, cache=list()):
    #if isinstance(parent, str) and parent.startswith("HKEY") and parent in winreg.__dict__.keys():
        #subkeys = get_subkeys(parent)
        #if name in subkeys:
            #cache.append(parent)
            #return parent
        #else

def check_VS():
    with registry_key(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE") as software_key:
        with registry_key(software_key, "Microsoft") as ms_key:
            return "VisualStudio" in get_subkeys(ms_key)


def get_pyver():
    return ".".join([str(sys.version_info.major), str(sys.version_info.minor), str(sys.version_info.micro)])

def get_pyinclude():
    pypath = get_pysys()
    return os.path.join(pypath, "include")


def get_pylibs():
    pypath = get_pysys()
    return os.path.join(pypath, "libs")

def get_pysys():
    ver = "".join(["Python",str(sys.version_info.major), str(sys.version_info.minor)])
    syspath = os.environ["PATH"].split(";")
    pypaths = [s for s in syspath if ver in s and os.path.split(s)[0].endswith(ver)]
    return pypaths[0]

    
    
    
def get_env_name():
    default = "scipyenv"
    ret = input(f"Enter environment name prefix (default is {default}): ")
    if len(ret.strip()) == 0:
        ret = default

    return ret

def get_env_home():
    default = "e:\\"
    ret = input(f"Enter the directory where the virtual environment will be created (default is {default}): ")
    if len(ret.strip()) == 0:
        ret = default

    return ret

def installpipreqs(pyvenv, reqs): #, force=False):
    activate_script = os.path.join(pyvenv, "Scripts", "activate.bat")
    if not os.path.isfile(activate_script):
        raise OSError(f"File {activate_script} not found !")
    print("Installing Python packages from PyPI")
    subprocess.run(f"{activate_script} & set SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True & python -m pip install -r {reqs}",
                    shell=True, check=True)
    #flagfile=os.path.join(pyvenv, ".pipdone")
    #if not os.path.isfile(flagfile) or force == True:

        #with open(flagfile, "w") as flag:
            #flag.write(f"Python packages from PyPI installed on {datetime.datetime.now}")

        #os.system(f"{activate_script} & set SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True & python -m pip install -r {reqs}")

def make_scipyact(pyvenv):
    now = f"{datetime.datetime.now()}".replace(" ", "_").replace(":", "_").replace(".", "_")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")

    userscripts = os.path.join(userhome, "Scripts")

    activation_script = os.path.join(userscripts, "scipyact.bat")
    pyvenvactivation = os.path.join(pyvenv, "Scripts", "activate.bat")

    if not os.path.isdir(userscripts):
        os.mkdir(userscripts)

    if userscripts not in userpath:
        newpath=";".join([userpath, userscripts])
        subprocess.run(f"setx PATH {newpath}", shell=True, check=True)
        os.environ["PATH"]=newpath

    if os.path.isfile(activation_script):
        name, ext = os.path.splitext(activation_script)
        backup=f"{name}.{now}{ext}"
        subprocess.run(f"copy {activation_script} {backup}", shell=True, check=True)

    with open(activation_script, "w") as batch_file:
        batch_file.write("@echo off\n")
        binpath=os.path.join(pyvenv, "bin")
        oldpath=os.environ["PATH"]
        newpath = ";".join([oldpath, binpath])
        batch_file.write(f"set PATH {newpath}")
        os.environ["PATH"]=newpath
        batch_file.write(f"call {pyvenvactivation}\n")
        batch_file.write("echo on\n")


def make_scipyact_vs64(pyvenv):
    now = f"{datetime.datetime.now()}".replace(" ", "_").replace(":", "_").replace(".", "_")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")

    userscripts = os.path.join(userhome, "Scripts")

    script = os.path.join(userscripts, "scipyact_vs64.bat")

    pyvenvactivation = os.path.join(pyvenv, "Scripts", "activate.bat")

    vcvarsall = check_visualstudio()

    if os.path.isfile(script):
        name, ext = os.path.splitext(script)
        backup = f"{name}.{now}{ext}"
        subprocess.run(f"copy {script} {backup}", shell=True, check=True)

    with open(script, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write(f'call "{vcvarsall}"  amd64 \n')
        batch_file.write(f'set "PROMPT=(X64) $p$g" \n')
        batch_file.write(f'call {pyvenvactivation} \n')
        batch_file.write("echo on\n")

def make_vs64_bat():
    now = f"{datetime.datetime.now()}".replace(" ", "_").replace(":", "_").replace(".", "_")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")

    userscripts = os.path.join(userhome, "Scripts")

    vs64script = os.path.join(userscripts, "vs64.bat")

    vcvarsall = check_visualstudio()

    if os.path.isfile(vs64script):
        name, ext = os.path.splitext(vs64script)
        backup = f"{name}.{now}{ext}"
        subprocess.run(f"copy {vs64script} {backup}", shell=True, check=True)

    with open(vs64script, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write(f'call "{vcvarsall}" amd64\n')
        batch_file.write(f'set "PROMPT=(X64) $p$g" \n')
        batch_file.write("echo on\n")

def makevirtenv(loc, name):
    path=os.path.join(loc, name)
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise OSError(f"{path} exists but is not a directory")
        pyvenvcfg = os.path.join(path, "pyvenv.cfg")
        if not os.path.exists(pyvenvcfg) or not os.path.isfile(pyvenvcfg):
            raise OSError(f"Directory {path} exists but does not seem to be a virtual environment directory")
    else:
        print(f"environment will be created as {path}")
        os.system(f"python -m virtualenv {path}")

    return path

def make_launch_script(pyvenv, scipydir):
    now = f"{datetime.datetime.now()}".replace(" ", "_").replace(":", "_").replace(".", "_")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")

    userscripts = os.path.join(userhome, "Scripts")

    scipyenscript = os.path.join(userscripts, "scipyen.bat")
    pyvenvactivation = os.path.join(pyvenv, "Scripts", "activate.bat")
    scipystartup = os.path.join(scipydir, "scipyen.py")

    if not os.path.isdir(userscripts):
        os.mkdir(userscripts)

    if userscripts not in userpath:
        newpath=";".join([userpath, "Scripts"])
        subprocess.run(f"setx PATH {newpath}", shell=True, check=True)
        os.environ["PATH"]=newpath

    if os.path.isfile(scipyenscript):
        backup=f"{scipyenscript}.{now}"
        subprocess.run(f"copy {scipyenscript} {backup}", shell=True, check=True)

    with open(scipyenscript, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write(f"call {pyvenvactivation}\n")
        batch_file.write(f"cmd /C 'python {scipystartup}' \n")

def check_visualstudio():
    vcvarsall = os.path.join("C:\\", "Program Files (x86)", "Microsoft Visual Studio",
                             "2019", "Community", "VC", "Auxiliary", "Build","vcvarsall.bat")

    if not os.path.isfile(vcvarsall):
        raise OSError("Please install VisualStudio 2019 and try again")

    return vcvarsall

def check_wget():
    wget = os.path.join("C:\\", "Program Files (x86)", "GnuWin32", "bin", "wget.exe")
    if not os.path.isfile(wget):
        raise OSError("Please install GNU wget from https://sourceforge.net/projects/gnuwin32/ in the default location and try again")

    return wget

def check_7z():
    sevenzip=os.path.join("C:\\", "Program Files", "7-Zip", "7z.exe")
    if not os.path.isfile(sevenzip):
        raise OSError("Please install 7-zip from https://www.7-zip.org/download.html in its default location and try again")
    
    return sevenzip

def check_cmake():
    """Not used: cmake MUST be in PATH nsince its installation"""
    cmake=os.path.join("C:\\", "Program Files", "CMake", "bin", "cmake.exe")
    if not os.path.isfile(cmake):
        raise OSError("Please install CMake then try again")

    return cmake

def pre_install(re_create_scripts=False, reinstallpips=False):
    vcvarsall = check_visualstudio()
    wget = check_wget()

    virtual_env_name = f"{get_env_name()}.{get_pyver()}"

    ve_home = get_env_home()

    realscript = __file__

    #print(f"realscript={realscript}")
    userhome = os.getenv("USERPROFILE")
    userpath = os.getenv("PATH")
    userscripts = os.path.join(userhome, "Scripts")

    virtual_env_path = makevirtenv(ve_home, virtual_env_name)

    if len(virtual_env_path.strip()):
        if not check_flag_file(".batchscriptsdone", virtual_env_path) or re_create_scripts:
            make_scipyact(virtual_env_path)
            make_scipyact_vs64(virtual_env_path)
            make_vs64_bat()
            make_flag_file(".batchscriptsdone", virtual_env_path, f"Batch scripts created on {datetime.datetime.now}")

    reqsfile=os.path.join(os.path.dirname(realscript), "pip_requirements.txt")

    if not check_flag_file(".pipdone", virtual_env_path) or reinstallpips:
        installpipreqs(virtual_env_path, reqsfile)
        make_flag_file(".pipdone", virtual_env_path, f"Python packages from PyPI installed on {datetime.datetime.now}")

    if not os.path.isdir(userscripts):
        os.mkdir(userscripts)

    if userscripts not in userpath:
        newpath=";".join([userpath, "Scripts"])
        subprocess.run(f"setx PATH {newpath}", shell=True, check=True)
        os.environ["PATH"]=newpath

    venv_src = os.path.join(virtual_env_name, "src")
    print("\n\nNext steps:\n")
    print(f"1. Download boost from https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.7z into {venv_src}")
    print(f"2. In a new comand prompt window call scipyact_vs64, then run this script again")


def make_sdk_src():

    virtual_env, venv_drive = get_venv()

    sdk_src = os.path.join(virtual_env, "src")

    if not os.path.isdir(sdk_src):
        venv_drive = os.path.splitdrive(virtual_env)[0]
        subprocess.run(f"{venv_drive} && cd {virtual_env} && mkdir src",
                       shell=True, check=True)

def get_venv():
    if "VIRTUAL_ENV" not in os.environ:
        raise OSError("\n\nATTENTION:\n\nYou must run this after activating the python environment. Have you called 'scipyact_vs64' ?")
    virtual_env = os.environ["VIRTUAL_ENV"]
    venv_drive = os.path.splitdrive(virtual_env)[0]

    return virtual_env, venv_drive

def wget_fftw():
    make_sdk_src()
    venv, vdrive = get_venv()
    wget = check_wget()
    #print(f"wget: {wget}")
    new_path = ";".join([os.environ["PATH"], os.path.dirname(wget)])
    os.environ["PATH"] = new_path
    fftw_src = os.path.join(venv, "src", "fftw")
    #print(f"fftw_src: {fftw_src}")
    if not os.path.isdir(fftw_src):
        src = os.path.join(venv, "src")
        #print(f"src: {src}")
        subprocess.run(f"{vdrive} && cd {src} && mkdir fftw",
                       shell=True, check=True)

    os.chdir(fftw_src)
    if not os.path.isfile(os.path.join(fftw_src, "fftw-3.3.5-dll64.zip")):
        subprocess.run(f"wget --no-check-certificate https://fftw.org/pub/fftw/fftw-3.3.5-dll64.zip",
                    shell=True, check=True)

    subprocess.run(f"tar -xf fftw-3.3.5-dll64.zip")

    for f in ["libfftw3-3.def", "libfftw3f-3.def", "libfftw3l-3.def"]:
        subprocess.run(f"lib /machine:x64 /def:{f}",
                       shell=True, check=True)

    dist = dict()
    dist["*.exe"] = os.path.join(venv, "bin")
    dist["*.dll"] = os.path.join(venv, "bin")
    dist["*.lib"] = os.path.join(venv, "Lib")
    dist["*.def"] = os.path.join(venv, "Lib")
    dist["*.exp"] = os.path.join(venv, "Lib")
    dist["*.h"] = os.path.join(venv, "include")


    for k,v in dist.items():
        subprocess.run(f"copy {k} {v}",
                       shell=True, check=True)

def build_zlib():
    venv, vdrive=get_venv()
    # cmake=check_cmake()# NOTE: cmake MUST be in the PATH since its installation!
    src_dir = os.path.join(venv, "src", "zlib")
    build_dir = os.path.join(venv, "src", "zlib-build")
    if not os.path.isdir(src_dir):
        os.chdir(os.path.join(venv, "src"))
        subprocess.run("git clone https://github.com/madler/zlib.git",
                       shell=True, check=True)
        
    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)
        
    os.chdir(build_dir)
    
    # NOTE: cmake SHOULD automatically identify a default generator
    # as of 2023-03-27 13:31:25,
    # on this machine this is Visual Studio 16 2019
    bindir = os.path.join(venv, "bin")
    incdir = os.path.join(venv, "include")
    libdir = os.path.join(venv, "Lib")
    mandir = os.path.join(venv, "share", "man")
    pkgconfdir = os.path.join(venv, "share", "pkgconfig")
    cmake_args = " ".join([
                           f"-DCMAKE_INSTALL_PREFIX={venv}",
                           f"-DINSTALL_BIN_DIR={bindir}",
                           f"-DINSTALL_LIB_DIR={libdir}",
                           f"-DINSTALL_MAN_DIR={mandir}",
                           f"-DINSTALL_PKGCONFIG_DIR={pkgconfdir}",
                           f"-S {src_dir}",
                           f"-B {build_dir}",
                           ])
        
    subprocess.run(f"cmake {cmake_args}", shell=True, check=True)
    subprocess.run(f"cmake --build . --target ALL_BUILD --config Release", shell=True, check=True)
    subprocess.run(f"cmake --install . --prefix {venv} --config Release", shell=True, check=True)

def build_jpeg():
    venv, vdrive=get_venv()
    src_dir = os.path.join(venv, "src", "libjpeg")
    build_dir = os.path.join(venv, "src", "libjpeg-build")
    bindir = os.path.join(venv, "bin")
    incdir = os.path.join(venv, "include")
    libdir = os.path.join(venv, "Lib")
    mandir = os.path.join(venv, "share", "man")
    pkgconfdir = os.path.join(venv, "share", "pkgconfig")
    if not os.path.isdir(src_dir):
        os.chdir(os.path.join(venv, "src"))
        subprocess.run("git clone https://github.com/winlibs/libjpeg.git",
                       shell=True, check=True)
        
    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)
        
    os.chdir(build_dir)
    cmake_args = " ".join([
                           f"-DCMAKE_INSTALL_PREFIX={venv}",
                           f"-DDEPENDENCY_SEARCH_PREFIX={venv}",
                           f"-DINSTALL_BIN_DIR={bindir}",
                           f"-DINSTALL_LIB_DIR={libdir}",
                           f"-DINSTALL_MAN_DIR={mandir}",
                           f"-DINSTALL_PKGCONFIG_DIR={pkgconfdir}",
                           f"-DWITH_JPEG7=ON",
                           f"-DWITH_JPEG8=ON",
                           f"-S {src_dir}",
                           f"-B {build_dir}",
                           ])
    
    subprocess.run(f"cmake {cmake_args}", shell=True, check=True)
    subprocess.run(f"cmake --build . --target ALL_BUILD --config Release", shell=True, check=True)
    subprocess.run(f"cmake --install . --prefix {venv} --config Release", shell=True, check=True)

def build_png():
    venv, vdrive=get_venv()
    src_dir = os.path.join(venv, "src", "libpng")
    build_dir = os.path.join(venv, "src", "libpng-build")
    bindir = os.path.join(venv, "bin")
    incdir = os.path.join(venv, "include")
    libdir = os.path.join(venv, "Lib")
    mandir = os.path.join(venv, "share", "man")
    pkgconfdir = os.path.join(venv, "share", "pkgconfig")
    if not os.path.isdir(src_dir):
        os.chdir(os.path.join(venv, "src"))
        subprocess.run("git clone https://github.com/winlibs/libpng.git",
                       shell=True, check=True)
        
    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)
        
    os.chdir(build_dir)
    cmake_args = " ".join([
                           f"-DCMAKE_INSTALL_PREFIX={venv}",
                           f"-DDEPENDENCY_SEARCH_PREFIX={venv}",
                           f"-DINSTALL_BIN_DIR={bindir}",
                           f"-DINSTALL_LIB_DIR={libdir}",
                           f"-DINSTALL_MAN_DIR={mandir}",
                           f"-DINSTALL_PKGCONFIG_DIR={pkgconfdir}",
                           f"-S {src_dir}",
                           f"-B {build_dir}",
                           ])
    
    subprocess.run(f"cmake {cmake_args}", shell=True, check=True)
    subprocess.run(f"cmake --build . --target ALL_BUILD --config Release", shell=True, check=True)
    subprocess.run(f"cmake --install . --prefix {venv} --config Release", shell=True, check=True)
    
def build_tiff():
    venv, vdrive=get_venv()
    src_dir = os.path.join(venv, "src", "libtiff")
    build_dir = os.path.join(venv, "src", "libtiff-build")
    bindir = os.path.join(venv, "bin")
    incdir = os.path.join(venv, "include")
    libdir = os.path.join(venv, "Lib")
    mandir = os.path.join(venv, "share", "man")
    pkgconfdir = os.path.join(venv, "share", "pkgconfig")
    if not os.path.isdir(src_dir):
        os.chdir(os.path.join(venv, "src"))
        subprocess.run("git clone https://gitlab.com/libtiff/libtiff.git",
                       shell=True, check=True)
        
    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)
        
    os.chdir(build_dir)
    cmake_args = " ".join([
                           f"-DCMAKE_INSTALL_PREFIX={venv}",
                           f"-DDEPENDENCY_SEARCH_PREFIX={venv}",
                           f"-DINSTALL_BIN_DIR={bindir}",
                           f"-DINSTALL_LIB_DIR={libdir}",
                           f"-DINSTALL_MAN_DIR={mandir}",
                           f"-DINSTALL_PKGCONFIG_DIR={pkgconfdir}",
                           f"-S {src_dir}",
                           f"-B {build_dir}",
                           ])
    
    subprocess.run(f"cmake {cmake_args}", shell=True, check=True)
    subprocess.run(f"cmake --build . --target ALL_BUILD --config Release", shell=True, check=True)
    subprocess.run(f"cmake --install . --prefix {venv} --config Release", shell=True, check=True)
    
def build_boost():
    venv, vdrive=get_venv()
    venv_src = os.path.join(venv, "src")
    boost_build_log=os.path.join(venv_src, "boost_build.log")
    os.chdir(venv_src)
    wget = check_wget()
    sevenzip = check_7z()
    new_path = ";".join([os.environ["PATH"], os.path.dirname(wget), os.path.dirname(sevenzip)])
    os.environ["PATH"] = new_path
    
    default_boost_archive = os.path.join(venv, "src", "boost_1_81_0.7z")
    if os.path.isfile(default_boost_archive):
        boost_archive=default_boost_archive
    else:
        boost_archive = input(f"Input the fully qualified path and file name for the DOWNLOADED boost source archive (the {default_boost_archive} was not found): ")
    
    if len(boost_archive.strip()) == 0:
        boost_archive=default_boost_archive
        
#     # NOTE: 2023-03-27 21:30:33 doesn't seem to work TODO/FIXME
#     # NOTE: 2023-03-28 09:13:40 test the new curl download strategy; 
#     # for now use manually dl-ed 7z archive
#     if not os.path.isfile(boost_archive):
#         dlcmd = " ".join(['curl "https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.7z"',
#                 '-H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"',
#                 '-H "Accept-Language: en-GB,en;q=0.9,en-US;q=0.8,ro;q=0.7,fr;q=0.6,cy;q=0.5"',
#                 '-H "Connection: keep-alive"',
#                 '-H "Cookie: ab.storage.deviceId.a9882122-ac6c-486a-bc3b-fab39ef624c5=^%^7B^%^22g^%^22^%^3A^%^22ff8b1c5c-8f01-e657-a1aa-73a2c6a6d5d0^%^22^%^2C^%^22c^%^22^%^3A1679990528908^%^2C^%^22l^%^22^%^3A1679990528908^%^7D"',
#                 '-H "Referer: https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/"',
#                 '-H "Sec-Fetch-Dest: document"',
#                 '-H "Sec-Fetch-Mode: navigate"',
#                 '-H "Sec-Fetch-Site: same-origin"',
#                 '-H "Sec-Fetch-User: ?1"',
#                 '-H "Upgrade-Insecure-Requests: 1"',
#                 '-H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"',
#                 '-H "sec-ch-ua: ^\^"Google Chrome^\^";v=^\^"111^\^", ^\^"Not(A:Brand^\^";v=^\^"8^\^", ^\^"Chromium^\^";v=^\^"111^\^""',
#                 '-H "sec-ch-ua-mobile: ?0"',
#                 '-H "sec-ch-ua-platform: ^\^"Windows^\^""',
#                 '-L',
#                 '--compressed',
#                 '-o {boost_archive}',
#                 ])
#         subprocess.run(f"{dlcmd}", shell=True, check=True)
#         
    if not os.path.isfile(boost_archive):
        raise OSError(f"Boost archive {boost_archive} not found; bailing out. Goodbye!")
    
    ba_name = os.path.basename(boost_archive)
    pfx, ext = os.path.splitext(ba_name)
    
    boost_src = os.path.join(venv_src, pfx)
        
    boost_tool_build = os.path.join(boost_src, "tools", "build")
    
    if not os.path.isdir(boost_src):
        subprocess.run(f"7z x {boost_archive} -o{venv_src} ",
                        shell=True, check=True)
    
    pysys = get_pysys()
    pyver_for_boost = ".".join(["Python",str(sys.version_info.major), str(sys.version_info.minor)])
    # print(f"pysys = {pysys}")
    pyinclude = get_pyinclude()
    # print(f"pyinclude = {pyinclude}")
    pylibs = get_pylibs()
    # print(f"pylibs = {pylibs}")
    venv_include = os.path.join(venv, "include")
    venv_libdir=os.path.join(venv, "Lib")
    
    include=";".join([os.environ["INCLUDE"], pysys, pyinclude, venv_include])
    os.environ["INCLUDE"] = include 
    # print(f"INCLUDE = {include}")
    
    libpath=";".join([os.environ["LIBPATH"], pysys, pylibs, venv_libdir])
    os.environ["LIBPATH"] = libpath
    # print(f"LIBPATH = {libpath}")
    
    libs = ";".join([os.environ["LIB"], pysys, pylibs, venv_libdir])
    os.environ["LIB"] = libs
    
    os.environ["CPLUS_INCLUDE_PATH"]=";".join([pyinclude, venv_include])
    
    b2_args = " ".join([f"toolset=msvc",
                        f"threading=multi",
                        f"address-model=64",
                        f"variant=release",
                        # f"include='{include}'",
                        # f"linkflags=-L{libpath}",
                        f"link=shared",
                        f"--prefix={venv}",
                        f"--build-type=complete",
                        "msvc",
                        "install",
                        ])
    
    
    
    os.chdir(boost_src)
    
    # NOTE: 2023-03-28 09:15:26
    # the code below compiles w/o issues (was failing to locate pyconfig.h 
    # previously, see NOTE: 2023-03-27 21:37:29 below )
    with open("user-config.jam", "w") as boost_user_config_jamfile:
        boost_user_config_jamfile.write(f"using python : {pyver_for_boost} : {pysys} : {pyinclude} : {pylibs}")
    
    # NOTE: 2023-03-27 21:37:29 tried this, 
    # → fatal error C1083: Cannot open include file: 'pyconfig.h': No such file or directory
    # NOTE: 2023-03-28 09:17:05
    # apparently fixed with setting up user-config.jam , see NOTE: 2023-03-28 09:15:26
    # and with additional options to bootstrap
    subprocess.run(f"bootstrap --with-python={pysys} --with-python-version={pyver_for_boost} --with-python-root={pylibs}", shell=True, check=True)
    subprocess.run(f".\\b2 {b2_args} > {boost_build_log}", shell=True, check=True)
    # subprocess.run()
    
    # NOTE: don't remove yet !!!
    # NOTE: 2023-03-28 09:19:18 possibly not needed, see NOTE: 2023-03-28 09:15:26 and NOTE: 2023-03-28 09:17:05
    #
    # boost_tool_build = os.path.join(boost_src, "tools", "build")
    # BoostBuild_dir = os.path.join(venv_src, "Boost.Build")
    # os.chdir(boost_tool_build)
    # subprocess.run("bootstrap", shell=True, check=True)
    # # subprocess.run (f"b2 install --prefix={BoostBuild_dir}", shell=True, check=True)
    # subprocess.run (f".\\b2 --prefix={BoostBuild_dir} toolset=msvc install", shell=True, check=True)
    # new_path=";".join([os.environ["PATH"], os.path.join(BoostBuild_dir, "bin"])
    # os.environ["PATH"] = new_path
    # os.chdir(boost_src)
    # subprocess.run(f"b2 {b2_args} ", shell=True, check=True)
    
def build_hdf5():
    venv, vdrive=get_venv()
    venv_src = os.path.join(venv, "src")
    os.chdir(venv_src)
    hdf5_src_archive_name = "CMake-hdf5-1.14.0.zip"
    default_hdf5_archive=os.path.join(venv, "src", hdf5_src_archive_name)
    if os.path.isfile(default_hdf5_archive):
        hdf5_src_archive=default_hdf5_archive
    else:
        hdf5_src_archive=input(f"Input the fully qualified path and file name of the CMake HDF5 source archive (the {default_hdf5_archive} was not found): ")
        
    if len(hdf5_src_archive.strip()) == 0:
        hdf5_src_archive = default_hdf5_archive
        
    if not os.path.isfile(hdf5_src_archive):
        raise OSError(f"HDF5 CMake sourcre archive {hdf5_src_archive} not found; bailing out. Goodbye!")
    
    a_name = os.path.basename(hdf5_src_archive)
    pfx, ext = os.path.splitext(a_name)
    hdf5_src = os.path.join(venv_src, pfx)
    hdf5_binary = pfx.replace("CMake-", "")
    hdf5_binary_archive = os.path.join(hdf5_src, f"{hdf5_binary}-win64.zip")
    # TODO
#         dlcmd = " ".join([
#             f'curl "https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.0/src/{hdf5_src_archive_name}"',
#             '-H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"',
#             '-H "Accept-Language: en-GB,en;q=0.9,en-US;q=0.8"',
#             '-H "Connection: keep-alive"',
#             '-H "Cookie: _ga=GA1.2.943308084.1631701310; _gid=GA1.2.1811147552.1679993942"',
#             '-H "Referer: https://confluence.hdfgroup.org/"' ,
#             '-H "Sec-Fetch-Dest: document"' ,
#             '-H "Sec-Fetch-Mode: navigate"' ,
#             '-H "Sec-Fetch-Site: same-site"' ,
#             '-H "Sec-Fetch-User: ?1"' ,
#             '-H "Upgrade-Insecure-Requests: 1"' ,
#             '-H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.54"',
#             '-H "sec-ch-ua: ^\^"Microsoft Edge^\^";v=^\^"111^\^", ^\^"Not(A:Brand^\^";v=^\^"8^\^", ^\^"Chromium^\^";v=^\^"111^\^"",'
#             '-H "sec-ch-ua-mobile: ?0"' ,
#             '-H "sec-ch-ua-platform: ^\^"Windows^\^""',
#             '--compressed',
#             '-L',
#             f'-o {hdf5_src_archive}'])
#         
#             subprocess.run(f"{dlcmd}", shell=True, check=True)

    
    # hdf5_build = os.path.join(venv_src, f"{pfx}-build")
    if not os.path.isdir(hdf5_src):
        subprocess.run(f"tar xf {hdf5_src_archive}", shell=True, check=True)
        
    os.chdir(hdf5_src)
    # NOTE: 2023-03-28 11:09:37
    # optionally, ONLY if no suitable batch script is found in hdf5_src
    # subprocess.run(f"echo ctest -S HDF5config.cmake,BUILD_GENERATOR=VS201964,INSTALLDIR=e:\scipyen_sdk -C Release -V -O hdf5.log > build.bat",
    #                shell=True, check=True)
    # subprocess.run(f"build.bat")
    hdf5_build_dir = os.path.join(hdf5_src, "build")
    
    # NOTE: don;t rebuild if build dir is found unless --rebuild-hdf5 is passed in sys.argv
    if not os.path.isfile(hdf5_binary_archive):
        subprocess.run(f"build-VS2019-64.bat")
    
    hdf5_binary_dir = os.path.join(venv_src,os.path.basename(os.path.splitext(hdf5_binary_archive)[0]))
    
    if not os.path.isfile(hdf5_binary_archive):
        raise OSError(f"Building the HDF5 binary archive failed; please see the {hdf5_src}\hdf5.log for details")

    os.chdir(venv_src)
    subprocess.run(f"tar xf {hdf5_binary_archive} -C .", shell=True, check=True)
    
    if not os.path.isdir(hdf5_binary_dir):
        raise OSError(f"Archive {hdf5_binary_archive} coud not be expanded. Goodbye!")
    
    subdirs = [s for s in os.listdir(hdf5_binary_dir) if os.path.isdir(os.path.join(hdf5_binary_dir, s))]
    
    src_subdirs = [os.path.join(hdf5_binary_dir, s) for s in subdirs]
    dest_dirs = [os.path.join(venv, s) for s in subdirs]
    
    for s_dir, d_dir in zip(src_subdirs, dest_dirs):
        shutil.copytree(s_dir, d_dir, dirs_exist_ok=True)
        
    
def build_vigra():
    venv, vdrive=get_venv()
    venv_src = os.path.join(venv, "src")
    pysys = get_pysys()
    pyinclude = get_pyinclude()
    pylibs = get_pylibs()
    venv_include = os.path.join(venv, "include")
    venv_libdir=os.path.join(venv, "Lib")
    
    boost_dir=os.path.join(venv, "Lib", "cmake")    
    boost_include_dir = os.path.join(venv, "include", "boost-1_81")
    boost_python_library=[s for s in os.listdir(os.path.join(venv, "Lib")) if s.startswith("boost_python") and s.endswith("lib")]
    
    if len(boost_python_library) == 0:
        raise OSError("Boost Python library not found. Goodbye!")
    
    else:
        boost_python_libfile = boost_python_library[0]
        
    
    
    hdf5_sz_libfile = os.path.join(venv, "Lib", "libszaec.lib")
    
    if not os.path.isfile(hdf5_sz_libfile):
        raise OSError("HDF5 sz library file not found. Goodbye!")
    
    include=";".join([os.environ["INCLUDE"], pysys, pyinclude, venv_include])
    os.environ["INCLUDE"] = include 

    libpath=";".join([os.environ["LIBPATH"], pysys, pylibs, venv_libdir])
    os.environ["LIBPATH"] = libpath
    
    new_path = ";".join([os.environ["PATH"], os.path.join("C:", "Program Files", "doxygen", "bin")])
    os.environ["PATH"] = new_path

    os.chdir(venv_src)
    
    libs = ";".join([os.environ["LIB"], pysys, pylibs, venv_libdir])
    os.environ["LIB"] = libs
    
    os.environ["CPLUS_INCLUDE_PATH"]=";".join([pyinclude, venv_include])
    
    vigra_src = os.path.join(venv_src, "vigra")
    vigra_build = os.path.join(venv_src, "vigra-build")
    
    # subprocess.run(f"git clone https://github.com/ukoethe/vigra.git")
    if not os.path.isdir(vigra_src):
        subprocess.run(f"git clone https://github.com/ukoethe/vigra.git")
        
    if not os.path.isdir(vigra_build):
        os.mkdir(vigra_build)
        
    os.chdir(vigra_build)
    
    
    cmake_args = " ".join([f"-DCMAKE_INSTALL_PREFIX={venv}",
                           f"-DCMAKE_PREFIX_PATH={venv}",
                           # "-DCMAKE_BUILD_TYPE=Release",
                           f"-DPython_ROOT_DIR={venv}",
                           "-DPython_FIND_VIRTUALENV=ONLY",
                           "-DBUILD_SHARED_LIBS=ON",
                           f"-DBoost_DIR={boost_dir_path}",
                           f"-DBoost_INCLUDE_DIR={boost_include_dir}",
                           f"-DBoost_PYTHON_LIBRARY={boost_python_libfile}",
                           f"-DHDF5_SZ_LIBRARY={hdf5_sz_libfile}",
                           "-DWITH_VIGRANUMPY=ON" ,
                           "-DWITH_BOOST_THREAD=ON" ,
                           "-DWITH_BOOST_GRAPH=OFF" ,
                           "-DWITH_HDF5=ON" ,
                           "-DWITH_OPENEXR=OFF" ,
                           "-DWITH_LEMON=OFF" ,
                           "-DLIB_SUFFIX=64" ,
                           # "-DLIBDIR_SUFFIX=64",
                           "-DCMAKE_SKIP_INSTALL_RPATH=1",
                           "-DCMAKE_SKIP_RPATH=1",
                           "-DAUTOEXEC_TESTS=OFF",
                           "-DBUILD_DOCS=ON",
                           "-DBUILD_TESTS=OFF",
                           "-DAUTOBUILD_TESTS=OFF",
                           f"{vigra_src}"])
    
    subprocess.run(f"cmake {cmake_args}", shell=True, check=True)
    # subprocess.run(f"cmake build {vigra_build} ")

if __name__ == "__main__":
    if sys.platform != "win32":
        raise OSError("This script must be run on a Windows platform")
    
    if "VIRTUAL_ENV" in os.environ:
        venv, vdrive = get_venv()
        make_sdk_src()
        if not check_flag_file(".fftwdone", venv):
            wget_fftw()
            make_flag_file(".fftwdone", venv, f"fftw3 libraries installed on {datetime.datetime.now()}")

        if not check_flag_file(".zlibdone", venv):
            build_zlib()
            make_flag_file(".zlibdone", venv, f"zlib installed on {datetime.datetime.now()}")
            
        if not check_flag_file(".jpegdone", venv):
            build_jpeg()
            make_flag_file(".jpegdone", venv, f"jpeg installed on {datetime.datetime.now()}")
            
        if not check_flag_file(".pngdone", venv):
            build_png()
            make_flag_file(".pngdone", venv, f"png installed on {datetime.datetime.now()}")
            
        if not check_flag_file(".tiffdone", venv):
            build_tiff()
            make_flag_file(".tiffdone", venv, f"png installed on {datetime.datetime.now()}")
            
        if not check_flag_file(".boostdone", venv):
            build_boost()
            make_flag_file(".boostdone", venv, f"boost installed on {datetime.datetime.now()}")
            
        if not check_flag_file(".hdf5done", venv):
            build_hdf5()
            make_flag_file(".hdf5done", venv, f"hdf5 installed on {datetime.datetime.now()}")
            
        if not check_flag_file(".vigradone", venv):
            build_vigra()
            # make_flag_file(".vigradone", venv, f"vigra installed on {datetime.datetime.now()}")
            
        # print(f"\n\nScipyen virtual environment build complete at {datetime.datetime.now()}")
    else:
        pre_install()

