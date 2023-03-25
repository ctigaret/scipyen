# Using Scipyen in Windows

We will use a virtual UN*X-like environment provided by [MSYS2](https://www.msys2.org/)

## Step 1. Install [msys2](https://www.msys2.org/)

NOTE: `msys2` installer will create a separate directory tree wherever it is installed.

### MSYS2 installation directory
By default, `msys2` is installed in `c:\msys64` but you can choose a drive (partition)
with more space e.g. `e:\`. You can also give whatever name you want to where
`msys2` wil be installed, but **do avoid spaces, accented characters or any non-ascii
characters in the directory name**.

Below, we assume `msys2` was installed on the `E:\` drive, in the `E:\msys64`
directory. We refer to this directory as the **msys2 installation directory**.

### MSYS2 Environment ≠ Python virtual environment!
`E:\msys64` contains several directories named after the virtual UN\*X - like 
[*environments*](https://www.msys2.org/docs/environments/) that `msys2` provides.

Of these, we use `ucrt64` environment. The windows executable giving you a shell
into it is launched with the `MSYS2 UCRT64` icon created by the `msys2` installer.

One can also use the all new and shiny "Windows Terminal", see the [msys2](https://www.msys2.org/)
web site for how to set this up.

Alongside the `msys2`'s UN\*X environment-specific directories there are several
other directories used in common by the environments: `dev`, `etc`, **`home`**, `opt`,
`tmp`, `usr`, `var`.

Your $HOME directory (from the point of view of the UN\*X environment you are 
running) is located in `E:\msys64\home\<user name>` (shown in **`boldface`** above) 
and corresponds to the `/home/<user name>` directory inside the UN*X shell.

The Scipyen git repository and the *virtual python environment* needed to run 
Scipyen will be located in your UN\*X home directory!

## Step 2 Install msys2 packages.

Launch `msys2 ucrt64` terminal, then install the packages listed in the table 
below.

**NOTE:**

* search a package with 
```bash
pacman -Ss
```
* to limit searching to packages suitable for the ucrt64 environment, call:
```bash
  pacman -Ss <name> | grep ucrt64
```
* install packages specifically for the MSYS2 environment in use (in this case, 
`ucrt64`) using [`pacboy`](https://www.msys2.org/docs/package-naming/)[^pacboy] :
```bash
pacboy -S<name of package>:u
```
examples from history:
```bash
    2  pacman -S mingw-w64-ucrt-x86_64-gcc
    4  pacman -Ss fftw
    5  pacman -S mingw-w64-ucrt-x86_64-fftw
    6  pacman -S pactoys
    7  pacboy help
    8  pacman -Ss libtiff
    9  pacboy -S libtiff:u
```
[^pacboy]: This is installed with `pactoys`. When using `pacboy` the name of the 
package does not need to befully-qualified; you can just give the name of the 
software you want and `pacboy` will resolve the package name based on what is 
available and the environment (the `:u` switch at the end). See [here](https://www.msys2.org/docs/package-naming/)
for details.

   | Packages                                                          |   Hermes |  Bruker
   | :-----------------------------------------------------------------| :--------| :------
   | pactoys (for pacboy)                                              |   ✓      |  ✓
   | base-devel                                                        |   ✓      | 
   | gcc                                                               |   ✓      |  ✓
   | toolchain (includes gcc, make, binutils, etc)                     |   ✓      |  ✓
   | autptools (pacman -S autotools)                                   |   ✓      | 
   | cmake (ucrt64 version; see msys2.org site for details)            |   ✓      |  ✓
   | bison                                                             |   ✓      |  ✓
   | bisonc++ [^bisonc]                                                |   ✓      |  ✓
   | flex                                                              |   ✓      |  ✓
   | flex c++ [^flexc]                                                 |   ✓      |  ✓
   | llvm (needed to build python-blis), lld, clang, compiler-rt       |
   | git # NOTE: use pacman -S git                                     |   ✓      |  ✓
   | doxygen [^docygen]                                                |   ✓      |  ✓
   | mpi (openmpi)                                                     |          | 
   | X11 ?                                                             |          | 
   | ncurses                                                           |   ✓      |  ✓
   | xcomposite ?                                                      |          | 
   | python                                                            |   ✓      |  ✓
   | cython                                                            |   ✓      |  ✓
   | libtiff                                                           |   ✓      |  ✓
   | libpng                                                            |   ✓      |  ✓
   | libjpeg                                                           |   ✓      |  ✓
   | zlib                                                              |   ✓      |  ✓
   | openexr                                                           |   ✓      |  ✓
   | hdf5                                                              |   ✓      |  ✓
   | fftw                                                              |   ✓      |  ✓
   | ffmpeg                                                            |   ✓      |  ✓
   | boost & boost-numpy, boost-threads, boost-graph                   |   ✓      |  ✓ 
   | qt5                                                               |   ✓      |  ✓
   | python-pyqt5                                                      |   ✓      | 
   | pyqt5-sip                                                         |   ✓      | 
   | vigra (installs python-numpy)                                     |   ✓      | 
   | python-pip                                                        |   ✓      | 
   | ** experimenting **                                               |          | 
   | cmakerc                                                           |   ✓      | 
   | gnuplot                                                           |   ✓      | 
   | ** useful stuff **                                                |          | 
   | man                                                               |   ✓      |
   | info (∈)                                                          |   ✓      |  ✓


## Step 3 install VcXsrv Windows X server
from here https://sourceforge.net/projects/vcxsrv/files/latest/download
    
    
[^bisonc]: use `pacman -S bison pacman -S bisonc++`
[^flexc]: use `pacman -S flex pacman -S flex++`
[^doxygen]: use `pacman -S doxygen then pacboy -S doxygen:u`

## Step 4 Run the scipyen install script

**Update 2023-03-25 18:03:56**
  * Before running the scipyen install.sh script, install directly in msys2, via `pacman -S`
  (or `pacboy -S <name>:u`)
    - python-cython
    - python-numpy
    - python-pywavelets
    - python-matplotlib
    - python-matplotlib-inline
    - python-seaborn
    - python-pandas
    - python-numexpr
    - python-pywin32
    - python-pywin32-ctypes
    - python-pyqt5
    - python-pyqt5-3d
    - python-scikit-image => python-scipy, python-imageio, python-networkx, python-tiffile & others
    - python-scikit-learn => python-threadpoolctl, python-joblib
    - python-scikit-build => python-wheel, python-distro
      
    
    ```bash
      $ python3 -m pip list
      Package      Version
      ------------ -------
      asciidoc     10.2.0
      Cython       0.29.33
      distlib      0.3.6
      editdistance 0.6.2
      filelock     3.10.4
      numpy        1.24.2
      pip          23.0.1
      platformdirs 3.1.1
      PyQt5        5.15.9
      PyQt5-sip    12.11.1
      PyWavelets   1.4.1
      setuptools   67.6.0
      virtualenv   20.21.0
    
    ```
  * clone packages from Explosion: `editdistance`, `murmurhash`, `cymem`, `preshed` git repository:
    ```bash
    mkdir src && cd src
    git clone https://github.com/roy-ht/editdistance
    cd editdistance
    python3 setup.py build
    python3 setup.py install
    git clone https://github.com/explosion/murmurhash.git
    cd murmurhash
    python3 setup.py build
    python3 setup.py install
    cd ..
    git clone https://github.com/explosion/cymem.git
    cd cymem
    python3 setup.py build
    python3 setup.py install
    git clone https://github.com/explosion/preshed.git
    cd preshed
    python3 setup.py build
    python3 setup.py install
    cd ..
  ```
  
  * finally, call (pip packages already installed in the steps above will be skipped):
```bash
python3 -m pip install -r scipyen/doc/install/pip_requirements.txt
```
then 

**NOTES:** 

1. Some of the `PyPI` packages listed in `scipyen/doc/install/pip_requirements.txt`
are not available as binary packages; therefore, `pip` will download their `sdist` 
versions and try to compile locally. Depending on what msys environment provides, 
some packages may fail to compile (see below). These packages can be installed
directly in msys2 using `pacman` and therefore will be skipped by install.sh:
  * `pywavelets` → `pacboy -S python-pywavelets:u`
  * 
  
2. The "platform" reported by python executable will still be `win32` !!!

3. The following packages can be installed in your `msys2` `(ucrt64)` environment
and therefore will be skipped by the `install.sh` script:
  * cython
