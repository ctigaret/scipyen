# Scipyen installation
Author: Cezar M. Tigaret <cezar.tigaret@gmail.com>

Distributed under [GNU General Public License v.3.0 (GPLv3)](https://www.gnu.org/licenses/gpl-3.0.en.html)

* * * 

# Table of Contents
1. [Introduction](#Introduction )
2. [Installation on Linux](#linux-install)
    1. [Preamble](#linux-preamble)
    2. [Installation under a locally built python environment](#with-virtualenv)
        1. [Usage of install.sh script](#install_sh-usage)
    3. [Installation using Anaconda](#linux_anaconda)
3. [Installation on Windows](#windows-install)

# <a name=Introduction/>Introduction

Scipyen requires [Python](https://www.python.org/) >= 3.9 and is meant to run 
inside a virtual python environment. The recommended tools to create this are

* [`virtualenv`](https://pypi.org/project/virtualenv/) or `conda` (from [Anaconda](https://www.anaconda.com/)) for [Linux](#linux-install)
* `conda` (from [Anaconda](https://www.anaconda.com/)) for Windows


**NOTE:** You will need about 3 GiB free disk space for the python environment.

**WARNING:** 
The Scipyen repository ***should be*** be located ***outside*** the virtual environment directory.

# <a name=linux-install/>Installation on Linux
The virtual environment can be created automatically using the [`install.sh`](#install_sh_usage) [script](install.sh)

## <a name=linux-preamble/>Preamble

By default, the `install.sh` script will create a local virtual python environment
where it will
* install required python packages from the [Python Package Index](https://pypi.org/)
* build required C++-based libraries
    - PyQt5
    - boost
    - vigra
    - (optionally) NEURON
    
The build process can be configured with command line switched passed to the script (see below).

In the future, the script will allow the alternative use of `conda` on Linux also.

**NOTE:**
The script itself requires a few other command line tools - these are 
supplied by the Linux distribution and usually are installed by default, but 
it is worth checking that they are available beforehand:

  • `date` (usually are installed by default)
  
  • `virtualenv` python package
  
  • [`glow`](https://github.com/charmbracelet/glow) (to display [Markdown](https://daringfireball.net/projects/markdown/) documents on the console)

  • development tools: `cmake`, `make`, C++ compiler suite, assembler, etc., see below.
  
## <a name=with-virtualenv/>Installation under a locally built python environment
**NOTE** This method offers the greatest flexibility including the 
possibility to use `NEURON` simulation environment from within Scipyen.

### <a name=install_sh_usage/>Usage of install.sh script

Assuming Scipyen is cloned inside `${HOME}/scipyen` launch the script like this:

```bash
sh ${HOME}/scipyen/doc/install/install.sh
```
* `--install_dir=DIR` - specifies a directory where the virtual environment will be created (default is `${HOME}`)
* `--environment=NAME` - specifies a custom name for the virtual environment; (default is `scipyenv.x.y.z` where `x`, `y`, and `z` are the `python` interpreter version numbers"
* `--with_neuron` - when present, will install neuron python from PyPI. See also:
    - https://neuron.yale.edu/neuron/
    - https://github.com/neuronsimulator/nrn/
    - https://pypi.org/project/NEURON/
* `--build_neuron` - when present, will build neuron python locally.
* `--with_coreneuron` - when present, local `neuron` build will use `coreneuron` (by default, `coreneuron` is not used). 
This option has effect only when `neuron` is built locally. For details about `coreneuron` see
    https://github.com/BlueBrain/CoreNeuron
* `--jobs=N` where `N` is an integer `>= 0`; enables parallel tasks during building 
of `PyQt5` and `neuron` (default is `4`)
* `--reinstall=<name>` whene `<name>` is one of `pyqt5`, `vigra` ,`neuron`; (re)installation or (re)building of any of these components;
can be passed more than once.
* `-h | -? | --help` shows a brief help message then quit
* `--about` shows this document on the console (requires `glow`).
    
    
### Description
Scipyen requires third party software installed in a virtual `python` environment.

#### Needed Python packages
Some of this is available as Python packages on [PyPI](https://pypi.org/) - hence installable via `pip`. 
The required packages are listed in the file `pip_requirements.txt` in this directory.

**ATTENTION:**
The actual `pip` tool to be used is `pip3` (i.e. for `python` version 3 and later). 
A better (as in more explicit) solution is to call (see [pip user guide](https://pip.pypa.io/en/latest/user_guide/) for details):
    
```bash
python3 -m pip <... pip commands & options ...>
```
#### Software built locally
Other third party software may not be available on [PyPI](https://pypi.org/), or needs to be built
locally (inside the virtual environment), provided that dependencies are 
installed on the host computer:

##### [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - Python bindings for `Qt5` toolkit
These are necessary for `Scipyen`'s GUI.

* On Windows, this can be installed via `pip` directly from [the PyPI repository](https://pypi.org/project/PyQt5/) by calling
      
      ```sh
      python3 -m pip install PyQt5
      ```

* **NOTE:** On some Linux distributions installation via `pip` may fail, in particular
when the expected Qt project build tool `qmake` is available under a different 
name (e.g., `qmake-qt5`); in this case a local build is necessary.

Local `PyQt5` build is also useful for a custom selection of `Qt` components, and
for a better integration of `Scipyen`'s GUI with the desktop look and feel
when using `KDE/Plasma` desktop.

To build `PyQt5` locally in Lnux the following dependencies are needed:

    - build toolchain (e.g. `make`, GNU c++ compiler etc)
    - development packages for `Qt5` - including `qmake` (!)
    - Python >= 3.10, `cython`
    - For details see [PyQt5 home page](https://www.riverbankcomputing.com/static/Docs/PyQt5/installation.html).

**WARNING:**
By default, this script uses parallel compilation to build PyQt5 locally. 
In some circumstances this may crash the build process with an error like the one below:

```sh
      {standard input}: Assembler messages: 
      {standard input}: Warning: end of file not at end of a line; newline inserted 
      {standard input}:1353: Error: unbalanced parenthesis in operand 1.
```
      
The error is likely generated by a race condition (the assembler triying to process 
a file that is incomplete at that particular stage in the build).

If this happens, then pass `--jobs=N` option to this script with `N` a small number 
(half the number of cores is a good guess) or even `0`.

##### [VIGRA](http://ukoethe.github.io/vigra/) - C++ library for computer vision
This library privides `python` bindings (`vigranumpy`) that are used by `Scipyen` code for image analysis and processing.

Depending on the Python version used by your environment, there may be no binary `vigranumpy` packages available. Therefore, VIGRA library and its python bindings must be built locally.

This requires a few dependencies listed [here](http://ukoethe.github.io/vigra/doc-release/vigra/Installation.html), 
which include [`cmake`](https://cmake.org/), [`boost C++`](https://www.boost.org/), [`cython`](https://cython.org/),
[`sphinx`](https://www.sphinx-doc.org/en/master/) (*NOTE* that this is installed as per `pip_requirements.txt` file),
[`fftw3`](https://www.fftw.org/), [`libtiff`](http://simplesystems.org/libtiff/),
[`libpng`](http://www.libpng.org/pub/png/libpng.html) (also available [here](https://libpng.sourceforge.io/index.html)),
[`libjpeg`](https://libjpeg.sourceforge.net/), and the *recommended* [`HDF5`](https://www.hdfgroup.org/solutions/hdf5/),
[`doxygen`](https://www.doxygen.nl/).


##### [NEURON](https://neuron.yale.edu/neuron/) simulation environment.
The `python` interface in recent versions of [NEURON](https://neuron.yale.edu/neuron/)
enables Scipyen to launch and operate with `NEURON`. This interoperability 
is still at an incipient stage, therefore `NEURON` is **NOT** installed by default.

To enable `NEURON`, pass either `--with_neuron` or `--build-neuron` options to the install script.

* The `--with-neuron` option simply installs the currently available `NEURON python` 
package from its [PyPI repository](https://pypi.org/project/NEURON/).
* The `--build-neuron` option builds `NEURON` locally from its [GitHub repository](https://github.com/neuronsimulator/nrn)
    - For dependencies and options to customize the build, see [here](https://github.com/neuronsimulator/nrn/blob/master/docs/install/install_instructions.md)
    - When built locally, `NEURON` can be configured to use [The BlueBrain Project's](https://github.com/BlueBrain) [`coreneuron`](https://github.com/BlueBrain/CoreNeuron).
    

### Environment customization
If you want to add or remove packages manually, you can do so using `pip`; if 
you think these changes are worth propagating to the main scipyen repository
then please inform the main author ([Cezar Tigaret](tigaretc@cardiff.ac.uk)). 

**WARNING:** Please be advised that all calls to `pip` for package installation 
or removal should be done **with the python virtual environment activated**. The 
author(s) cannot advise on possible troubleshooting when packages are installed
outside the virtual environment.

## <a name=linux_anaconda/>Installation using Anaconda
To be written.

# <a name=windows-install></a>Installation on Windows
## Create a conda virtual environment
**NOTE:** Below, we assume the `scipyen` git repository clone and the `conda`
environment are in two distinct directories on drive E:, e.g.:
    * `e:\scipyen` -- the clone of Scipyen git repository
    * `e:\scipyenv` -- the directory of the virtual conda environment
    
Please adapt to your particular situation, but **keep these directories separate**.


1. Install [Python](https://pytyon.org) (>= 3.10)
1. Install [Anaconda](https://naconda.org)
2. Launch Anaconda Command Prompt and run the `scipyen\doc\install.bat` script.

For example:
```
e:\scipyen\doc\install\install.bat
```

The script will ask for the full path to the new environment.

## Run Scipyen
1. Open Anaconda Prompt
2. Activate the environment created above
```
conda activate e:\scipyenv
```
3. With the the environment activated, launch `scipyen`
```
python e:\scipyen\scipyen.py
```


2023-03-31

