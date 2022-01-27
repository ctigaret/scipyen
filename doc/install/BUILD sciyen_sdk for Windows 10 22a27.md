## 2022-01-27 10:53:24
Problem solved by building VIGRA against statically-built png libraries
(libpng-a.lib);
(should check if there are issues with building libpng from github as
shared lib on Windows -i.e. as dll)

All other dependencies of VIGRA (ZLIB, TIFF, JPEG, HDF5) were built dynamically
and installed (as with static libpng) in scipyen_sdk.

These dependencies were built as follows (these are general/generic steps;
details for each library are given below; the list here assumes each step works
w/o trouble):

 1. activate the scipyen with VS2019 environment (call "scipyact_vs64", see below)

 2. clone their git repository in a place e.g. "scipyen_sdk_src"
    this will create the source tree (e.g., "scipyen_sdk_src\vigra")

 3. create an out-of-source build tree (e.g., "vigra-build" alongside "vigra" in
    the "scipyen_sdk_src" directory)

 4. cd to the build tree and launch cmake-gui to configure, then generate a
 VisualStudio2019 solution for x64 platform

 5. from cmake-gui launch VStudio (press "Open Project")

 6. Inside VStudio:

* At the toolbar select "Release" and "x64" (NOTE for libpng, "Release Library" was selected)

* In Solution explorer select ALL_BUILD solution (or project), build it

* In solution explorer, select INSTALL solution (or project), build it.



It turns out one can archive scipyen_sdk as a zip file and carry it over to
another Windows 10 machine.

The "vigranumpy" python package is installed in scipyenv\Lib\site-packages\vigra
on the build machine. This package can also be archived as zip file and carried
over to another Windows 10 machine. On the new (target) machine the zip file
needs to be extracted and its contents placed in the equivalent "site-packages"
(sub)directory of the "scipyenv" virtual environment created on the target
machine.

NOTE that "scipyenv\Lib\site-packages" is created automatically WHEN INSTALLING
3rd party pythyon packages in the virtual environment, using "pip"; therefore,
these packages need to be installed first, by calling:
    pip install -r <pip_requirements>

where <pip_requirements> is the name of the requirements text file FOR WINDOWS,
located in "scipyen\doc\install" directory.


Finally, the batch scripts scipyact.bat, scipyact_vs64.bat and scipyen.bat only
need to be edited to point to thew correct location of scipyen_sdk directory.

NOTE that scipyact_vs64.bat is ONLY used to build the "scipyen_sdk" tree, from
sources (located in "scipyen_sdk_src").

To use scipyen one only needs to call scipyact.bat first, then "scipyen.bat".


## 2022-01-26 10:37:43
AVOID building on networked drive - on a virtual machine, create a 2nd VDI image
for a 2nd partition (~100 GiB)

Building on network drive will:
1. slow down the process
2. interfere with building processes (e.g. HDF5 and VIGRA)

## 2022-01-26 18:48:50
attempted on Bruker Windows 10 VirtualBox image building apparently works but
launching scipyen fails with:

    python.exe - Ordinal not found
    in libpng.dll

## 2022-01-26 18:50:10
replicating the recipe on Hermes Windows 10 VirtualBox image
    the issue is replicated on Hermes (despite apparently successful build):

    python.exe - Ordinal Not Found
    the ordinal 169 could not be located in tghe dynamic link library
    e:zscipyen_sdk\bin\libpng16.dll

and, at command line:

    Traceback (most recent call last):

    File "e:\scipyen\scipyen.py", line 16, in <module>
        path_to_vigraimpex = win32api.GetModuleFileName(win32api.LoadLibrary(vigraimpex_mod))
        pywintypes.error: (182, 'LoadLibrary', 'The operating system cannot run %1.')

## 2022-01-26 20:46:50
might have something to do with INSTALL projects overwriting runtime dlls in scipyen_sdk


* * *
# Tools for building scipyen dependencies.
* * *
These must be installed system-wide (make sure there is enough space on C:\drive)
(for convenience, installer are provided in the "DownloadsForScipyen" bundle;
 below I give the details of the version used, but you <b>may</b> use a more
 recent version)

## python-3.9.7 -- with options:
* for everyone
* raise the limit on PATH

<b>NOTE</b>: scipyen is written with <b>Python3.9</b> in mind, and some of its dependencies
(boost, vigra) were build against <b>this</b> version of Python.
The code has not yet been tested against Python 3.10 or newer.

## git
Download from [here](https://git-scm.com/download/win)
The version used here is Git-2.33.0.2-64-bit.exe but you may

## kate
Useful and powerful text editor - if you do not like VisualStudio Code, etc.
Download app from Microsoft Store.

## doxygen
VIGRA dependency, required to build documentation.
Get it from [here](https://www.doxygen.nl/download.html)

## cmake
Download Windows installer from [here](https://cmake.org/download/).
Current sdk uses CMake-3.22.1, you may choose a more recent version
* Run the installer, select options:
    * add CMake to the system PATH for all users
    * create CMake desktop icon

## Visual Studio Community Edition 2019
Make sure it is all uptodate and it includes:
* Desktop development with C++


## 7zip for windows 10
Get it from [here](https://www.7-zip.org/download.html)
I used 7z2107-x64.exe

## MPICH
Download from [here](https://www.microsoft.com/en-us/download/confirmation.aspx?id=57467):
* msmpisetup.exe <- run this first
* msmpisdk.msi

    If you choose to install these, then edit
    scipyact.bat, vs64.bat and scipyact_vs64.bat
    to append:
    C:\Program Files (x86)\Microsoft SDKs\MPI\Include to %INCLUDE%
    C:\Program Files (x86)\Microsoft SDKs\MPI\Lib to %LIB% and %LIBPATH%
    C:\Program Files\Microsoft MPI\Bin to %PATH%

## nasm: (for building jpeg)
Get nasm-2.15.05-installer-x64.exe from [here](https://www.nasm.us/pub/nasm/releasebuilds/2.15.05/win64/nasm-2.15.05-installer-x64.exe)
* Run installer as administrator;
* Manually add c:\Programs Files\NASM to %PATH%

## Ruby
Download installer + devkit from [here](https://rubyinstaller.org/downloads/)
I used rubyinstaller-devkit-3.0.2-1-x64.exe

## StrawberryPerl
Get strawberry-perl-5.32.1.1-64bit.msi from [here](https://strawberryperl.com/)

## flex and bison - required to build neuron
Download from [here](https://sourceforge.net/projects/winflexbison/)
I use the win_flex_bison-latest.zip
Extract win_bison.exe and win_flex.exe to %USERPROFILE%\Scripts

## readline & termcap - requires msys2, see below
* start MSYS2-MinGW64 from the Start menu
* run pacman -Su
* run pacman -S --needed mingw-w64-x86_64-readline
    * reply with Y (yes)

NOTE: Readline and termcap libraries are in c:\msys64\mingw64\include, lib, etc.

## msys2-64bit
Download installer from [here](https://www.msys2.org/)
Run the installer, follow the instruction [here](https://www.msys2.org/)
* make sure you run it after first installation ("Run MSYS2 Now")

* * *
# Build the sdk tree
* * *

* * *
## Choose a drive with enough space (> 10 GiB) for the sdk sources
* * *


-----------------------------------------------------------------------
2.1 create a python virtual environment 
-----------------------------------------------------------------------
e:\>virtualenv scipyenv

-----------------------------------------------------------------------
2.2 make scipyen_sdk and scipyen_sdk_src directories
-----------------------------------------------------------------------
e:\>mkdir scipyen_sdk
e:\>mkdir scipyen_sdk_src

-----------------------------------------------------------------------
2.3 clone scipyen git repo
-----------------------------------------------------------------------
e:\>git clone https://github.com/ctigaret/scipyen.git

clone master and dev branches; remain on dev branch for now:
    
    cd scipyen
    git checkout master
    git pull
    git checkout dev
    git pull
    

-----------------------------------------------------------------------
2.4 Copy the batch files from scipyen\doc\install\win32 scripts
to your home directory (%USERPROFILE%)
-----------------------------------------------------------------------


2.4.1:
    make directory Scripts in %USERPROFILE%, and copy there the following:
        scipyact.bat
        scipyact_vs64.bat
        vs64.bat
        scipyen.bat
        
    Purpose of these scripts:
        scipyact.bat - activates the python virtual environment
            MUST be called before launghing scipyen
            
        scipyact_vs64.bat - actvated the python virtual environment 
            AND the developer environment (under Visual Studio 2019)
            
        vs64.bat - activates ONLY the VS2019 development environment
        
        scipyen.bat - launches Scipyen
            MUST be called AFTER calling scipyact.bat
    
    EDIT scipyen.bat:
        change scipyendir to where sciyen git repo is located
        e.g.:
            set scipyendir=e:\scipyen
        
    EDIT scipyact.bat:
        edit activation_script to point to the virtual environment
        activation script
        
        edit SDK to point to where scipyen_sdk is
        
        make sure the paths to the Python environment are correct
        (i.e. %USERPROFILE%\AppData\Local\Programs\Python\Python39)
    
    Similarly, make sure the paths to the Python environment are correct
    in vs64.bat

from scipyen repo copy scipyen_startup.py to scipyenv\Scripts
NOTE: scipyenv is the virtual environment directory
2022-01-26 23:18:27
    copy scipyen_startup.py into scipyen_sdk directory

    
Add %USERPROFILE%\Scripts to your PATH:
    use Settings -> search for environment -> Edit environment variables
    for your account -> select PATH in top half of dialog -> click Edit ->
    -> add c:\Users\<xxx>\Scripts
    
    restart the command prompt
    
* * *========================
3. Install pip requirements in the virtual environment
* * *========================

From anywhere (but typically, the parent directory of scipyenv):
    
    3.1 activate the virtual environment, e.g.:
        e:\>scipyact
        
    3.2 call 'pip install -r ***' where *** is a pip_requirements_*_win64.txt
    found in scipyen\doc\install:
        e:\>pip install -r pip_requirements_0_win64.txt
        e:\>pip install -r e:\scipyen\doc\install\pip_requirements_1_win64.txt
        e:\>pip install -r e:\scipyen\doc\install\pip_requirements_2.txt
        e:\>pip install -r e:\scipyen\doc\install\pip_requirements_3.txt
        
     (be prepared to wait)   
     
    When alll is done, check that you have a working juoyter-qtconsole
     
* * *========================
4. Install VIGRA
* * *========================

Open a new command prompt, activate sciyen WITH VidualStudio development

e:\>scipyen_vs64

--------------------------------------------------------------------------------
4.1. Install vigra dependencies in scipyen_sdk
--------------------------------------------------------------------------------
vigra dependencies tree:
    
    vigra   <-  fftw3
                libjpeg <-  zlib
                libpng  <-  zlib 
                libtiff
                hdf5    <-  zlib
                boost_python <- boost <- icu (skipped)
                openexr (optional) <- Imath, openssl, icu
                python (done above)
                numpy, sphinx, nose (done above via pip)
                cmake (done above)
                
.......................................................................                
zlib
.......................................................................                
2022-01-26 19:18:15
use zlib github (Hermes)
git clone https://github.com/madler/zlib.git
make out-of-source build tree for cmake:
    mkdir zlib-build
    cd zlib-build
    cmake-gui ..\zlib
1st configure => select VS2019, x64, native compilers
    then check destinations go under e:\scipyen_sdk
    configure -> genertate -> open project (VS2019)
    select Release + x64
    Build ALL_BUILD
    Build INSTALL



.......................................................................                
2. libpng
.......................................................................                

2022-01-26 18:50:56
using libpng github (on Hermes):

git clone https://github.com/glennrp/libpng.git
make out-of-source build tree
mkdir libpng-build
cd libpng-build
cmake-gui ..\libpng
set the CMAKE_INSTALL_PREFIX to e:z\scipyen_sdk
configure -> generate -> open project (opens with VStudio)
    Select Release + x64
    Build ALL-BUILD
    Build INSTALL

2022-01-26 22:54:42
try this:
git clone https://github.com/winlibs/libpng.git
modify libpng/projects/vstudio2019/zlib.props to point to the zlib source above
in scipyact_vs64 call devenv -> open libpng/projects/vstudio2019/vstudio.sln
choose Release Library + x64 (i.e. build static)
in solution explorer select libpng -> Build

then configure vigra-build (using cmake-gui) to point to the static zlib and
libpng_a libraries in "libpng/projects/vstudio2019/x64/Release Library"

... AND IT WORKS!

.......................................................................                
jpeg - requires nasm
.......................................................................                

git clone https://github.com/winlibs/libjpeg.git

build with cmake-gui in out-of-source tree

cd scipyen_sdk_src
mkdir libjpeg-build
cd libjpeg-build

cmake-gui ..\libjpeg -DCMAKE_INSTALL_PREFIX=e:\scipyen_sdk -DDEPENDENCY_SEARCH_PREFIX=e:\scipyen_sdk
=> select VS 16 2019 + default native compilers
configure -> select installation to <path to>\scipyen_sdk
set WITH_JPEG7 and WITH_JPEG8 ON
configure until no more red lines; check no errors
generate -> check no errors
open project => opens VS2019 ->
    select release + x64
    Build ALL_BUILD
    Build INSTALL
            
    
.......................................................................                
fftw
.......................................................................                

download fftw-3.3.5-dll64.zip from http://www.fftw.org/install/windows.html

extract to scipyen_sdk_src\fftw3

cd into fftw3 then run:

lib /machine:x64 /def:libfftw3-3.def
lib /machine:x64 /def:libfftw3f-3.def
lib /machine:x64 /def:libfftw3l-3.def

then copy:
    copy *.exe ..\..\scipyen_sdk\bin\
    copy *.dll ..\..\scipyen_sdk\bin\
    copy *.lib ..\..\scipyen_sdk\lib\
    copy *.def ..\..\scipyen_sdk\lib\
    copy *.exp ..\..\scipyen_sdk\lib\
    copy *.h  ..\..\scipyen_sdk\include\
        
    *.exe and *.dll files to %SDK%\bin\
    *.lib, *.def, *.exp files to %SDK%\lib\
    *.h files (actually, only fftw3.h) to %SDK%\include\
    COPYING, COPYRIGHT, NEWS, README* to %SDK%\share\doc\fftw3\

.......................................................................                
tiff - requires jpeg; no support for OpenGL and deflate
.......................................................................                
In e:\scipyen_sdk_src run:
    git clone https://gitlab.com/libtiff/libtiff.git
    
build with cmake in out-of-source tree => generate VS2019 solution
    mkdir libtiff-build
    cd libtiff-build
    
    cmake-gui -DCMAKE_INSTALL_PREFIX=e:\scipyen_sdk -DDEPENDENCY_SEARCH_PREFIX=e:\scipyen_sdk ..\libtiff
        
    configure: first run: select VS 16 2019, X64;
    configure, set install_prefix to scipyen_sdk,
    configure -> generate -> open project opes VS2019
        select Release + x64
        Build -> ALL_BUILD
        Build INSTALL
        
check that it works:
    from http://www.simplesystems.org/libtiff/images.html download
    https://download.osgeo.org/libtiff/pics-3.8.0.tar.gz

    unpack with 7zip => %SDK%\share\libtiffpic

open command prompt, cd %SDK%\share\libtiffpic
tiffcp -lzw cramps.tif x.tif
tiffcmp cramps.tif x.tif
tiff2pdf -o cramps.pdf cramps.tif
tiff2bw jello.tif jello_bw.tif

also you may run tiffinfo on all tif files in this directory

.......................................................................                
boost - built w/o support for icu, mpi
.......................................................................                

from https://www.boost.org/doc/libs/1_77_0/more/getting_started/windows.html#get-boost
download boost_1_77_0.7z
extract to scipyen_sdk_src => will create scipyen_sdk_src\boost_1_77_0

Activate scipyen_vs64 environment

Create the b2 Boost.Build program

    cd boost_1_77_0\tools\build
    bootstrap
    .\b2 --prefix=e:\scipyen_sdk_src\Boost.Build toolset=msvc install

 Build & install boost

    cd e:\scipyen_sdk_src\boost_1_77_0


    Run:
        
    ..\Boost.Build\bin\b2 toolset=msvc threading=multi address-model=64 variant=release link=shared --prefix=e:\scipyen_sdk --build-type=complete msvc install

    NOTE: always use the same toolset setting!
    
    This will install:
    * boost headers (*.hpp) in scipyen_sdk\include\boost_1_77_0\boost
        => add this path e:\scipyen_sdk\include\boost_1_77_0\
            to the relevant variables when building vigra

    * the *.dll and *.lib files in scipyen_sdk\lib
    
.......................................................................                
hdf5
.......................................................................                
See:
https://portal.hdfgroup.org/display/support/Building+HDF5+with+CMake

recommended download: CMake-hdf5-1.12.0.zip
but you may widh to use CMake-hdf5-1.10.6.zip; in this case DISREGARD the
instructions to patch vigra for HDF5 below

extract CMake-hdf5-1.12.0.zip to e:\scipyen_sdk_src
    => creates  e:\scipyen_sdk_src\CMake-hdf5-1.12.0 directory
    
    cd CMake-hdf5-1.12.0
    
    # Create a build script by running the following line:
    # ATTENTION: NO COMMAS in the value to the -S option !
e:\scipyen_sdk_src\CMake-hdf5-1.12.0>echo ctest -S HDF5config.cmake,BUILD_GENERATOR=VS201964,INSTALLDIR=e:\scipyen_sdk -C Release -V -O hdf5.log > build.bat
    
    #run the build script
e:\scipyen_sdk_src\CMake-hdf5-1.12.0>build
    
This will generate a zip file inside the CMake-hdf5-1.12.0 directory:
    HDF5-1.10.6-win64.zip
    
    extract and merge almost all of its contents with the correspnoding 
    directories in e:\scipyen_sdk
    
    exceptions are:
        * all document files in the root HDF5-1.10.6-win64 directory should go to
            e:\scipyen_sdk\share\doc\hdf5
        
        * DO overwrite all files in the destination, when asked
        (this will replace zlib from above with a new one - it's OK)
        
.......................................................................                
VIGRA - without OpenEXR support
.......................................................................                
e:\scipyen_sdk_src>git clone https://github.com/ukoethe/vigra.git

patch the vigra source tree as per scipyen\doc\install\vigra_patches\README

Create out-of-source build tree:            
e:\scipyen_sdk_src>mkdir vigra-build
e:\scipyen_sdk_src>cd vigra-build

Then run:
    cmake-gui ..\vigra -DCMAKE_INSTALL_PREFIX=e:\scipyen_sdk -DDEPENDENCY_SEARCH_PREFIX=e:\scipyen_sdk
        
    in CMake GUI you must set:
        Boost_PYTHON_LIBRARY to 
            e:\scipyen_sdk\lib\boost_python39-vc142-mt-x64-1_77.lib
        
        deselect the following:
            BUILD_TESTS, AUTOEXEC_TESTS, TEST_VIGRANUMPY
        
        set CMAKE_INSTALL_PREFIX to e:\scipyen_sdk
        set LIB_SUFFIX to 64
        
        set CMAKE_INSTALL_PREFIX to
            e:\scipyen_sdk
            
        Check all other libraries and paths are correct, especially for the 
        dependencies built above (HDF5, jpeg, tiff, png)
        
        Check locations for Python are correct (yes, use the Python.exe in the 
                                                scipyenv)
        
        Configure repeatedly until no more red lines in the GUI.
        Check the output to have vigranumpy built and installed
        
        Finally press Generate to generate VStudio solution, then
        Click "open project" => Opens VStudio
        in VStudio, make sure Release + x64 are selected
        Select ALL_BUILD then run Build/Build Solution
        
    The doc_cpp.vcxproj and doc_python.vcxproj will likely FAIL
    Ignore that
    
    Then in Solution explorer select INSTALL project, right-click, build.
    
    This will install:
        header files in scipeyn_sdk\include (including "windows.h")
        vigranumpy in e:\scipyenv\lib\site-packages\vigra
        vigraimpex.lib in e:\scipyen_sdk\lib64
        vigraimpex.dll in e:\scipyen_sdk\bin
        doc in e:\scipyen_sdk\doc
        
        
* * *

final steps:
copy scipyen_startup.py
from sciyen\doc\install\python\windows
to scipyenv\scripts
        
## NEURON
git clone https://github.com/neuronsimulator/nrn

make out-of-source build tree in scipyen_sdk_src:

    mkdir nrn-build
    cd nrn-build
    cmake-gui ..\nrn

In cmake-gui adjust the variables pointing to the readline and termcap libs
Set CMAKE_INSTALL_PREFIX to where scipyen_sdk is
Set NRN_MODULE_INSTALL_OPTIONS to where scipyen_sdk is
Enable NRN_ENABLE_CORENEURON
"Configure" -> ... -> "Generate" -> "Open Project"
Build solution ALL_BUILD
tbc

NOTE: below are the instructions for linux

devenv

"Configure" will also pull iv, coreneuron
        CMAKE_INSTALL_PREFIX (-DCMAKE_INSTALL_PREFIX=) $VIRTUAL_ENV
        NRN_ENABLE_CORENEURON=true
        NRN_ENABLE_INTERVIEWS=true
        NRN_ENABLE_MECH_DLL_STYLE=true
        NRN_ENABLE_MODULE_INSTALL=true
        NRN_ENABLE_INTERNAL_READLINE=false
        NRN_MODULE_INSTALL_OPTIONS --prefix= --home=$VIRTUAL_ENV
        NRN_ENABLE_MPI=true
        NRN_ENABLE_MPI_DYNAMIC=false
        NRN_ENABLE_PYTHON=true (default python3 fallback to python2)
        NRN_ENABLE_PYTHON_DYNAMIC=false
        NRN_ENABLE_RX3D=true
        NRN_ENABLE_SHARED=true
        NRN_ENABLE_TESTS=false
        NRN_ENABLE_THREADS=true
        LIB_INSTALL_DIR=$VIRTUAL_ENV/lib64
        IV_ENABLE_SHARED=true
nmake
nmake install

    NOTE: Run the following in order to properly install neuron python modules
    inside the site-packages corresponding  to the environment's python version

cd $VIRTUAL_ENV/src/nrn-build/src/nrnpython

python setup.py install
    (to install nrnpython in site-packages)

    NOTE: Optional: Build neuron documentation locally and install locally
        (see $VIRTUAL_ENV/src/nrn/docs/README.md)

pip3 install -r $VIRTUAL_ENV/src/nrn/docs/docs_requirements.txt

    (installs required python packages (e.g.commonmark, sphinx-rtd-theme,
        recommonmark, plotly, etc) inside the virtual environment)

cd $VIRTUAL_ENV/src/nrn-build
make docs (NOTE this may fail --> no problems !)

    Optionally, copy/move (or, better make a symbolic link)
    $VIRTUAL_ENV/src/nrn/docs/_build to $VIRTUAL_ENV/doc/neuron

