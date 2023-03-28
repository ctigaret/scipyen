* * *
# Building a virtual Python environment for running scipyen on Windows.
2023-03-2

## General recommendations
* AVOID building on networked drive
* Use only ASCII characters for file and directory names, avoid spaces and punctuation marks other than '.' (dot),  '_' (underscore) or '-' (dash)

## Required software
These requirements are to be downloaded and *installed in their default installation locations* (shown below).  This is needed for the installation script to locate these tools.

* [Python](https://www.python.org/downloads/) (>= 3.10)
    - launch the installer, install for *everybody* and 
    - *allow* add Python to the system PATH
    - *associate* `*.py` files with `%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe`
    - **NOTE:** If (re)installing a newer version of Python **make sure you uninstall the old version first!**
* [VisualStudio](https://visualstudio.microsoft.com/free-developer-offers/) 
    - needed to build VIGRA and its python bindings. 
    - VisualStudio Community Edition 2019 is used at of the time of writing.
* [wget](https://gnuwin32.sourceforge.net/packages/wget.htm)
    - needed to automate downloading of libraries
    - installs under `C:\Program Files (x86)\GnuWin32\bin\` as `wget.exe`
* [cmake](https://cmake.org/download/)
    - needed to build VIGRA and its python bindings
    - pull the `msi` installer, and run it
    - in the installer, select `add CMake to the system PATH for all users`
    - installs in `C:\Program Files\CMake\bin\` as `cmake.exe`, `cmake-gui.exe`
* [7-zip](https://www.7-zip.org/download.html)
    - needed to unpack `boost` libraries
    - installs in `C:\Program Files\7-Zip\` as `7z.exe`
* [Netwide assembler (nasm)](https://www.nasm.us/pub/nasm/releasebuilds/2.15.05/win64/nasm-2.15.05-installer-x64.exe)
    - needed to build `jpeg` libraries
    - run the installer (allow the installer to run)
    - installs in `C:\Programs Files\NASM\` as `nasm.exe`
    - *manually add*  to the `PATH` environment variable.
* [git](https://git-scm.com/download/win)
    - needed to make a local clone of the `scipyen` git repository.

* [Doxygen](https://www.doxygen.nl/download.html)
    - Needed to build VIGRA documentation.
    - run the installer (allow the installer to run)
    - installs in `C:\Program Files\doxygen\bin\` as `doxygen.exe`

* [Boost C++ libraries](https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.7z)
    - needed to build VIGRA Python bindings
    - download manually somewhere in your file system, then remember this location; the installation script will ask for it

## Additional useful software
The following utilities should be downloaded and installed manually

* [ReText](https://pypi.org/project/ReText/) editor for [Markdown](https://daringfireball.net/projects/markdown/) and [ReStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html) files
    - to install:
    
        ```cmd
            python -m pip install retext
        ```

    - to run:
        
        ```cmd
            python -m ReText
        ```

* [Kate](https://kate-editor.org/) text editor; get the installer from [here](https://kate-editor.org/get-it/).

* * *

## Clone the Scipyen git repository and create a virtual Python environment using `virtualenv`.

The virtual Python environment and the Scipyen repository **should be** in distinct directories. 

* These can both be on the same partition (`drive`) or on different partitions, as long as they are both *local* to your machine).
* Neither need to be on the partition's root. It should be possible to place them anywhere ina directory tree, as long as the path name does *not* contain spaces or punctuation characters ('.', '_' and '-' *are* allowed).

### Stages and steps
#### Stage I - generate the python virtual environment and activation scripts
1.Clone the ``scipyen`` git repository. Choose a directory where to install it - this can be the root of a partition, or anywhere else locally. 

* Open a `Command Prompt` window and navigate to where you want to clone the repository locally then checkout the `dev` branch. 
* The following `cmd` snippet this will create the directory `e:\scipyen` containing the local repository clone (**note:** in all the examples below we use the `E:` drive)

``` 
e:
git clone https://github.com/ctigaret/scipyen.git
git checkout dev
git pull
```
        
2.Install or upgrade [`virtualenv`](https://pypi.org/project/virtualenv/)

```cmd
    python -m pip install virtualenv
```

3.Run

```cmd
python e:\scipyen\doc\install\scipyen_install_windows.py
```
**Note:** This will create a virtual environment directory; by default this is `e:\scipyenv.X.Y.Z` where `X`, `Y`, and `Z` are the major, minor and micro versions of the python executable. 

Unpon a first run, the script will:

* ask you to provide:
    - an evironment name prefix (default is `scipyenv`)
    - a location of the new environment (default is drive `E:`)

* install Python package dependencies of `Scipyen` (listed in `scipyen\doc\install\pip_requirements.txt`)
* create a `Scripts` directory in your home (user) directory i.e.`%USERPROFILE%\Scripts` which will be added to your `%PATH%` permanently, and containing:
    - `scipyen.bat` - launches `Scipyen` (and also activates the `scipyenv.X.Y.Z` environment)
    - `scipyact.bat` - activates the `scipyenv.X.Y.Z` environment
    - `vs64.bat` - activates the VisualStudio development environment
    - `scipyenv_vs64.bat` - activates the `scipyenv.X.Y.Z` environment *inside* the VisualStudio development environment.

#### Stage II - building the binary libraries inside the virtual environment
4.For the moment, the following must be *downloaded manually* and placed in `e:\scipyenv.X.Y.Z\src\`

* the boost library archive ([`boost_1_81_0.7z`](https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.7z))
* the HDF5 source archive for CMake ([`CMake-hdf5-1.14.0.zip`](https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.0/src/CMake-hdf5-1.14.0.zip))

5.Activate BOTH the VisualStudio AND Scipyen environments then run the `scipyen_install_windows.py` script again to perform subsequent build steps:

```cmd
scipyenv_vs64
python e:\scipyen\doc\install\scipyen_install_windows.py
```
Each step of **Stage II** builds a set of libraries:

* fftw
* zlib
* libjpeg
* libpng
* libtiff
* boost_1_81_0
* hdf5
* vigra

and creates one or two directories for each, inside `e:\scipyenv.X.Y.Z\src\`

For example, *except for `fftw` and `boost` libraries*, the steps will associate two directories: `<libname>` (the *source tree*) and `<libname_build>` (the *build tree*), where `libname` is the name of the library being built (e.g., `zlib`, `tifflib`, etc).

Each *successful* step will also generate a *dotfile* inside the root
directory of the environment (i.e., `e:\scipyenv.X.Y.Z`) named after `libname`: `.<libname>done`, e.g. `.fftwdone`, `.tiffdone`, etc.

**NOTE:** If something goes wrong in a step:

* Check the console output. 
* In the case of `boost` libraries, check the `e:\scipyenv.X.Y.Z\src\boost_build.log` file. 
* For HDF5 libaries, check the `e:\scipyenv.X.Y.Z\src\CMake-hdf5-N\hdf5.log` file, where `N` is the `hdf5` version number you have downloaded (as of 2023-03-28 this is `1.14.0`). 
* Make the necessary corrections, the run the script again with BOTH environments activated as above. 

**NOTE:** To force the re-execution of a particular step on a subsequent run of the script, remove either the *source tree*, the *build tree*, or the *dotfile* for the offending library, and run the script again with BOTH environments activated as above. 

**NOTE:** The libraries are being built in the sequence shown above, because of the way they depend on each other. When a build step fails, the script will stop.

