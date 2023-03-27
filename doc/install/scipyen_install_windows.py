import sys, os, subprocess, io, datetime, winreg
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
    ver = "".join(["Python",str(sys.version_info.major), str(sys.version_info.minor)])
    syspath = os.environ["PATH"].split(";")
    pypaths = [s for s in syspath if ver in s and os.path.split(s)[0].endswith(ver)]
    pypath = pypaths[0]
    return os.path.join(pypath, "include")


def get_pylibs():
    ver = "".join(["Python",str(sys.version_info.major), str(sys.version_info.minor)])
    syspath = os.environ["PATH"].split(";")
    pypaths = [s for s in syspath if ver in s and os.path.split(s)[0].endswith(ver)]
    pypath = pypaths[0]
    return os.path.join(pypath, "libs")



    
    
    
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
    os.chdir(venv_src)
    wget = check_wget()
    sevenzip = check_7z()
    new_path = ";".join([os.environ["PATH"], os.path.dirname(wget), os.path.dirname(sevenzip)])
    os.environ["PATH"] = new_path
    
    default_boost_archive = os.path.join(venv, "src", "boost_1_81_0.7z")
    boost_archive = input(f"Enter for fully qualified path and file name for the DOWNLOADED boost source archive (default is {default_boost_archive}): ")
    
    if len(boost_archive.strip()) == 0:
        boost_archive=default_boost_archive
        
    if not os.path.isfile(boost_archive):
        raise OSError(f"Boost archive {boost_archive} not found; bailing out. Goodbye!")
    
    ba_name = os.path.basename(boost_archive)
    pfx, ext = os.path.splitext(ba_name)
    
    boost_src = os.path.join(venv_src, pfx)
        
    # NOTE: 2023-03-27 21:30:33 doesn't seem to work TODO/FIXME
    # if not os.path.isfile(boost_archive):
    #     subprocess.run(f"wget https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.7z",
    #                    shell=True, check=True)
        
        
    if not os.path.isdir(boost_src):
        subprocess.run(f"7z x {boost_archive} -o{venv_src} ",
                        shell=True, check=True)
    pyinclude = get_pyinclude()
    pylibs = get_pylibs()
    venv_include = os.path.join(venv, "include")
    venv_libdir=os.path.join(venv, "Lib")
    
    include=";".join([os.environ["INCLUDE"], pyinclude, venv_include])
    os.environ["INCLUDE"] = include 
    libpath=";".join([os.environ["LIBPATH"], pylibs, venv_libdir])
    os.environ["LIBPATH"] = libpath
    libs = ";".join([os.environ["LIB"], pylibs, venv_libdir])
    os.environ["LIB"] = libs
    
    # os this, then pass include= below
    # include=";".join([os.environ["INCLUDE"], pyinclude, venv_include])
    
    
    
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
    
    # NOTE: 2023-03-27 21:37:29 tried this, 
    # → fatal error C1083: Cannot open include file: 'pyconfig.h': No such file or directory
    subprocess.run("bootstrap", shell=True, check=True)
    subprocess.run(f".\\b2 {b2_args} > scipyenv_build.log", shell=True, check=True)
    # subprocess.run()
    
    # NOTE: don't remove yet !!!
    # boost_tool_build = os.path.join(boost_src, "tools", "build")
    # BoostBuild_dir = os.path.join(venv_src, "Boost.Build")
    # os.chdir(boost_tool_build)
    # subprocess.run("bootstrapt", shell=True, check=True)
    # # subprocess.run (f"b2 install --prefix={BoostBuild_dir}", shell=True, check=True)
    # subprocess.run (f".\\b2 --prefix={BoostBuild_dir} toolset=msvc install", shell=True, check=True)
    # new_path=";".join([os.environ["PATH"], os.path.join(BoostBuild_dir, "bin"])
    # os.environ["PATH"] = new_path
    # os.chdir(boost_src)
    # subprocess.run(f"b2 {b2_args} ", shell=True, check=True)
    

#print(f"name={__name__}")

if __name__ == "__main__":
    if "VIRTUAL_ENV" in os.environ:
        venv, vdrive = get_venv()
        make_sdk_src()
        if not check_flag_file(".fftwdone", venv):
            wget_fftw()
            make_flag_file(".fftwdone", venv, f"fftw3 libraries installed on {datetime.datetime.now}")

        if not check_flag_file(".zlibdone", venv):
            build_zlib()
            make_flag_file(".zlibdone", venv, f"zlib installed on {datetime.datetime.now}")
            
        if not check_flag_file(".jpegdone", venv):
            build_jpeg()
            make_flag_file(".jpegdone", venv, f"jpeg installed on {datetime.datetime.now}")
            
        if not check_flag_file(".pngdone", venv):
            build_png()
            make_flag_file(".pngdone", venv, f"png installed on {datetime.datetime.now}")
            
        if not check_flag_file(".tiffdone", venv):
            build_tiff()
            make_flag_file(".tiffdone", venv, f"png installed on {datetime.datetime.now}")
            
        if not check_flag_file(".boostdone", venv):
            build_boost()
            
            
    else:
        pre_install()

