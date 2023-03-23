#!/bin/bash

# Installation script stub for scipyen 23c19
#
# Author: Cezar M. Tigaret <cezar.tigaret@gmail.com>
#
# Distributed under GNU GPL License v.2
#
# NOTE: If you read this, this means you already have a local clone of the 
# Scipyen repository.
#
# Scipyen requires Python >= 3.9 and is meant to run inside a virtual python 
# environment. The `virtualenv` facility is recommended.
#
# This script will create the virtual environment and install any required third
# party software INSIDE the virtual environment. 
#
# Assuming Scipyen is cloned inside $HOME/scipyen then launch the script like this:
#
# sh ${HOME}/scipyen/doc/install/install_test.sh
#
# NOTE: The script itself requires a few other command line tools - these are 
# supplied by the Linux distribution and usually are installed by default, but 
# it is worth checking they are available beforehand:
#
#   • usually are installed by default:
#       ∘ date
#
#   • development tools: cmake, make, C++ compiler
#
# Some of the required third party software is available as Python packages on
# on PyPI - hence installable via `pip`. The required packages are listed in
# the file `pip_requirements.txt` in this directory.
#
# ATTENTION: The actual `pip` tool to be used is `pip3` (i.e. for python v 3 and 
# later) or, better, 'python3 -m pip <... pip commands & options ...>' .
#
# Other third party software may not be available on PyPI, or needs to be built
# locally (inside the virtual environment), provided that dependencies are 
# installed on the host computer:
#
# • PyQt5 - Python bindings for Qt5 widget toolkit (framework) - necessary for Scipyen GUI
#   ∘ web sites: 
#       ⋆ https://pypi.org/project/PyQt5/ 
#       ⋆ https://www.riverbankcomputing.com/software/pyqt/
#   ∘ can be installed via `pip` directly from PyPI: python3 -m pip install PyQt5
#   ∘ NOTE: On some distribution, installation via pip may fail; in this case a
#       locall (custom) build is necessary - see below
#   ∘ to customize the installation on Linux, the following dependencies are needed
#       ⋆ build toolchain (e.g. make, GNU c++ compiler etc)
#       ⋆ development packages for Qt5 - including qmake (!)
#       ⋆ Python >= 3.10, cython
#       ⋆ see also the web sites above, in particular:
#           https://www.riverbankcomputing.com/static/Docs/PyQt5/installation.html
#
# • VIGRA - C++ library for computer vision - used by image analysis and processing code in Scipyen
#   ∘ NOTE: VIGRA provides its own python bindings, which are actually used by Scipyen.
#       However, there is no `pip` package available as of this time (2023-03-23 09:49:41)
#       Therefore, VIGRA library and its python bindings MUST be built locally.
#   ∘ web sites: 
#       ⋆ http://ukoethe.github.io/vigra/
#       ⋆ https://github.com/ukoethe/vigra
#   ∘ dependencies: please see the VIGRA Homepage http://ukoethe.github.io/vigra/
#       and here: http://ukoethe.github.io/vigra/doc-release/vigra/Installation.html
#       Notably, these include (alogside with their development packages):
#       ⋆ boost C++ libraries
#       ⋆ ctyhon, sphinx, doxygen
#       ⋆ fftw3
#       ⋆ tiff, png, jpeg, zlib, hdf5
#       ⋆ an appropriate software building toolchain (depends on platform, see
#           the link above for details) - on Linux this includes `cmake`
#
# • NEURON - this is OPTIONAL; NEURON can be launched and interoperate(*) with Scipyen
#   ∘ web sites: 
#       ⋆ https://neuron.yale.edu/neuron/
#       ⋆ https://github.com/neuronsimulator/nrn
#   ∘ can be installed via `pip` directly from PyPI: python3 -m pip install neuron
#   ∘ for a custom build of NEURON, please see:
#     https://github.com/neuronsimulator/nrn/blob/master/docs/install/install_instructions.md
#
#   ∘ NOTE: (*) interoperability with Scipyen is experimental, and at an incipient stage
#
# If you want to add or remove packages manually, you can do so using `pip`; if 
# you think these changes are worth propagating to the main scipyen repository
# then please inform the main author (Cezar Tigaret). 
#
# WARNING: Please be advised that all calls to `pip` for package installation 
# or removal should be done with the python virtual environment activated. The 
# authors cannot advise on possible troubleshooting when packages are installed
# outside the virtual environment.
# 
# NOTE: The script performs the following steps:
#
# 1. create virtual environment
# 2. activate virtual environment
# 3. install python packages from PyPI according to pip_requirements.txt
# 4. download the latest PyQt5 sdist, build a wheel locally and install it
# 5. clone vigra git repository, build and install it
# 6. clone neuron git repository, build and install it
#
#
# NOTE: The steps 3 - 6 also generate a local "flag" (saved as hidden files 
# in the top directory of the environment) such that should something go wrong
# in a particular step, the steps sucessfully executed prior to the fault will 
# be skipped on a subsequent run.
#
# These flags are:
# .pipdone
# .pyqtdone
# .vigradone
# .nrndone
#
# Should you want to re-run a (previously sucessful) step, juts remove the 
# corresponding flag from the environment directory.
#
# TODO: customize:
# 1. which branch of scipyen git repo should be used?
#   • buy default this should be the master branch, but currently we use the dev
#       branch; as new contributors join us, they might want to work on their
#       own branch
# 2. the location (i.e. the containing directory) of the virtual environment
# 3. the name of the virtual environment
# 4. let the user choose to custommize these or just run unattended
# 5. let the user choose if nrn should be built and installed
# 6. various options for building:
#   • PyQt5 (e.g. modules to leave out) vigra
#   • vigra (e.g. do we want openEXR); NOTE: HDF5, vigranumpy are mandatory
#   • nrn (e.g. do we want coreneuron or a plain nrn stack?)

function show_help ()
{
    echo -e "\n***                                                         ***"
    echo -e "* Virtual Python environment installation script for Scipyen. *"
    echo -e "***                                                         ***\n"
    echo -e "(C) 2023 Cezar M. Tigaret "
    echo -e "<cezar tigaret at gmail com> , <tigaretc at cardiff ac uk>"
    echo -e "\nInstructions:"
    echo -e "============\n"
    echo -e "Run 'instal.sh' without options for a fully automated installation"
    echo -e "using built-in defaults.\n"
    echo -e "Options:"
    echo -e "=======\n"
    echo -e "--install_dir=DIR\t => specifies a directory where the virtual "
    echo -e "\t\t\tenvironment will be created (default is ${HOME})\n"
    echo -e "--environment=<name>\t => specifies a custom name for the virtual environment"
    echo -e "\t\t\t(default is ${virtual_env})\n"
    echo -e "--with_neuron\t\t => when passed, will install neuron python"
    echo -e "\t\t\tfrom PyPI. See also:\n"
    echo -e "\t\t\thttps://neuron.yale.edu/neuron/\n\t\t\thttps://github.com/neuronsimulator/nrn\n\t\t\thttps://pypi.org/project/NEURON/\n"
    echo -e "--build_neuron\t\t => when passed, will build neuron python locally.\n"
    echo -e "--with_coreneuron\t => when passed, local neuron build will use coreneuron."
    echo -e "\t\t\t(by default coreneuron is not used).\n"
    echo -e "\t\t\tFor details about coreneuron see:"
    echo -e "\t\t\thttps://github.com/BlueBrain/CoreNeuron\n"
    echo -e "\t\t\tNOTE: Only used when '--build_neuron' is passed .\n"
    echo -e "-h | -? | --help \t => show this help message and quit\n"
    
}
function findqmake ()
{
    qmake_binary=`which qmake`
    if [ -z "$qmake_binary" ] ; then
        qmake_binary=`which qmake-qt5`
    fi
    
    if [ -z "$qmake_binary" ] ; then
        read -e -p "Enter a full path to qmake (or qmake-qt5): " qmake_binary
    fi
    
    if [ -z "$qmake_binary" ] ; then
        echo -e "Cannot build Pyqt5 without qmake. Goodbye!\n"
        exit 1
    fi
}

function findcmake ()
{
    cmake_binary=`which cmake`
    if [ -z "$cmake_binary" ] ; then
        echo -e "Cannot build vigra without cmake. Goodbye!\n"
        exit 1
    fi
    
}

function upgrade_virtualenv ()
{
    havevenv=`python3 -m virtualenv --version`
    if [ -z $havenev ] ; then
        echo "Installing virtualenv locally...\n"
        pip install --user virtualenv
    else
        echo "Upgrading virtualenv locally...\n"
        pip install --user --upgrade virtualenv
    fi
}

function makevirtenv ()
{
    #NOTE: Generates a virtual enviornment
    # check if the environment directory exists (and that it does belong to a
    # virtual python environment - that is, it contains a file named "pyenv.cfg"
    # containing "virtualenv" in it, has a "bin" directory with "activate" script,
    # which can be sourced to generate VIRTUAL_ENV variable)
    if [ -d $ve_path/$virtual_env ] ; then
        if [ -a $ve_path/$virtual_env/pyvenv.cfg ] ; then
            aa=`cat $ve_path/$virtual_env/pyvenv.cfg | grep "virtualenv"`
            if [ -n "$aa" ] ; then
                if [ ! -d $ve_path/$virtual_env/bin ] ; then
                    echo -e "$ve_path/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                    exit 1
                fi
                if [ ! -r $ve_path/$virtual_env/bin ] ; then
                    echo -e "$ve_path/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                    exit 1
                fi
                source $ve_path/$virtual_env/bin/activate
                if [[ -z ${VIRTUAL_ENV} ]]; then
                    echo -r "Cannot activate a virtual environment from  $ve_path/$virtual_env . Goodbye!\n"
                    exit 1
                fi
            else
                echo -e "$ve_path/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                exit 1
            fi 
        fi
    else
        python3 -m virtualenv $virtual_env && source $ve_path/$virtual_env/bin/activate
    fi
    
}

function installpipreqs ()
{
    # installs pip packaged listed in pip_requirements
    # assumes (and therefore REQUIRES that the virtual environment is active)
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pipdone ] ; then
        # NOTE: since around Jan 2023 sklearn has been deprecated in favour of 
        # scikit-learn, suchn that an error message is issues whenever pip tries
        # to install sklearn.
        # HOWEVER, a LARGE number of packages still list sklearn among their 
        # dependencies, yet pip has no way to check this BEFORE installing them,
        # Until all of them catch up with this, we circumvent the error message
        # by setting up the environment variable below
        # For details please see https://pypi.org/project/sklearn/
        export SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True 
        pip install -r "$installscriptdir"/pip_requirements-experimental-23c21.txt
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Cannot install required packages from PyPI. Bailing out. Goodbye!\n"
            exit 1
        else
            echo "pip packages installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pipdone
            echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
        fi
    fi
}

function dopyqt5 ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pyqt5done ] ; then
        mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src
        
        findqmake
        
        if [ `pwd` != "$VIRTUAL_ENV"/src ]; then
            echo -e "Not inside $VIRTUAL_ENV/src - goodbye\n"
            exit 1
        fi
        
        # NOTE: locate_pyqt5_src.py uses distlib to locate the (latest) source 
        # archive (i.e., the sdist) of PyQt5 - its file name typically ends with
        # .tar.gz
        pyqt5_src_url=`python $installscriptdir/locate_pyqt5_src.py`
        pyqt5_src=`basename $pyqt5_src_url`
        
        pyqt5_src_dir=${pyqt5_src%.tar.gz}
        
        echo "PyQt5 source is in "$pyqt5_src_dir
        
        # NOTE: the sdist might have been downloaded alreay - so check this first
        # before actually downloading
        if [ ! -r ${pyqt5_src} ] ; then
            wget $pyqt5_src_url && tar xzf $pyqt5_src 

            if [[ $? -ne 0 ]] ; then
            echo -e "Cannot obtain the PyQt5 source. Bailing out. Goodbye!\n"
            exit 1
            fi
        
        fi
        
        # NOTE: good practice is to create an out-of-source build tree, » ...
        pyqt5_build_dir="PyQt5-build"
        mkdir -p ${pyqt5_build_dir}
        
        # NOTE: » ... but run the build process INSIDE the expanded sdist dir
        # is because sip-wheel will get extra options from there :)
        cd ${pyqt5_src_dir}
        
        echo "Generating PyQt5 wheel in "$(pwd)"..."
        
        sip-wheel --qmake=${qmake_binary} --confirm-license --jobs 8 --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi

        if [[ $? -ne 0 ]] ; then
            echo -e "sip Cannot build a PyQt5 wheel. Bailing out. Goodbye!\n"
            exit 1
        fi
        
        # NOTE: check is a wheel file has been produced; the filename typically
        # ends in .whl » if found then call pip to install it inside the 
        # environment ⟶ IT WORKS!
        wheel_file=`ls | grep whl`
        if [ -z ${wheel_file} ] ; then
            echo -e "No wheel file found in "$(pwd)" - goodbye!\n"
            exit 1
        else
            python -m pip install ${wheel_file}
            
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot install the PyQt5 wheel; check console output. Goodbye!\n"
                exit 1
            else
                echo "PyQt5 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pyqt5done
                echo -e "\n\n=====================\n# Pyqt5 installed!\n=====================\n\n"
            fi
        fi
    fi
}

function dovigra ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.vigradone ] ; then
        cd $VIRTUAL_ENV/src
        
        findcmake
        
        git clone https://github.com/ukoethe/vigra.git && mkdir -p vigra-build && cd vigra-build
        
        $cmake_binary -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DWITH_BOOST_GRAPH=1 -DWITH_BOOST_THREAD=1 -DWITH_HDF5=1 -DWITH_OPENEXR=1 -DWITH_VIGRANUMPY=1 -DLIB_SUFFIX=64 ../vigra
        
        make && make install
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Cannot build vigra; check console output. Bailing out. Goodbye!\n"
            exit 1
        else
            echo "VIGRA installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.vigradone
            echo -e "\n\n=====================\n# Building vigra DONE!\n=====================\n\n"
        fi
    fi
    
    
}

function doneuron ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.nrndone ] ; then
        if [ $use_pypi_neuron -ne 0 ] ; then
            python3 -m pip install neuron
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot install NEURON; check console output. Bailing out. Goodbye!\n"
                exit 1
            else
                echo "NEURON installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.nrndone 
                echo -e "\n\n=====================\n# Building NEURON DONE!\n=====================\n\n"
            fi
        else
            cd $VIRTUAL_ENV/src
            
            findcmake
            
            git clone https://github.com/neuronsimulator/nrn && mkdir -p nrn-build && cd nrn-build
            
            if [ $use_core_neuron -ne 0 ] ; then
                $cmake_binary -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=1 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_CORENEURON=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_REL_PATH=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABL_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 ../nrn
            else
                $cmake_binary -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=1 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_REL_PATH=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABL_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 ../nrn
            fi
            
            $cmake_binary --build . --parallel 8 --target install
            
            
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot build NEURON; check console output. Bailing out. Goodbye!\n"
                exit 1
            fi
            
            python3 -m pip install -r ${VIRTUAL_ENV}/src/nrn/docs/docs_requirements.txt
            
            cd ${VIRTUAL_ENV}/src/nrn-build && make docs # && mkdir ${VIRTUAL_ENV}/doc && cp -r ${VIRTUAL_ENV}/src/nrn-build
            
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot build NEURON; check console output. Bailing out. Goodbye!\n"
                exit 1
            fi
            echo "NEURON installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.nrndone 
            echo -e "\n\n=====================\n# Building NEURON DONE!\n=====================\n\n"
        fi
    fi
}

function make_scipyenrc () 
{
# Creates ${HOME}/.scipeynrc which allows activation of the virtual python environment
# used to run Scipyen.
#
# The ${HOME}/.scipyenrc defines a single bash function - 'scipyact' - which 
# when called, activates the virtual environment and optionally sets up a few 
# needed environment variables (see below in the code)
#
# The .scipyenrc script NEEDS TO BE SOURCED (in bash); this is done automatically
# by the Scipyen launch bash script ('scipyen'); for convenience, this script is
# also sourced from ${HOME}/.bashrc in order for the function 'scipyact' to be
# readily available to the user, at the console.
#
# Parameters::
# $1 = absolute path to the virtual environment directory
# $2 = absolute path to the custom built python installation (e.g. /usr/local)
#       default: /usr/local
#
#       NOTE: ONLY USED IF PYTHON IS IN CUSTOM-BUILT
#       
# $3 = x.y, where x and y are, respectively, the major and minor verison of the
#       python executable
# test if python complains about platform dependent libs

if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

# scipyenvdir=${VIRTUAL_ENV} # not really needed, right?
dt=`date '+%Y-%m-%d_%H-%M-%s'`
if [ -r ${HOME}/.scipyenrc ] ; then
# make a backup copy of .scipyenrc
shopt -s lastpipe
echo "Copying ${HOME}/.scipyenrc to ${HOME}/.scipyenrc.$dt"
cp ${HOME}/.scipyenrc ${HOME}/.scipyenrc.$dt
fi
cat<<END > ${HOME}/.scipyenrc
scipyact () {
source ${VIRTUAL_ENV}/bin/activate
}
export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:$LD_LIBRARY_PATH
END
shopt -u lastpipe
}

function update_bashrc () 
{
dt=`date '+%Y-%m-%d_%H-%M-%s'`
if [ ! -r ${HOME}/.bashrc ]; then
cat<<END > ${HOME}/.bashrc
source ${HOME}/.scipyenrc
END
echo ".bashrc has been created in ${HOME}"
echo "Sourcing ${HOME}/.bashrc"
source ${HOME}/.bashrc
else
shopt -s lastpipe
# check if .scipyenrc is sourced from .bashrc
cat ${HOME}/.bashrc | grep "source ${HOME}/.scipyenrc" | read source_set
# echo "source_set="$source_set
if [ -z "${source_set}" ]; then
# .scipyenrc not sourced from .bashrc => backup .bashrc then append a line to
# source .scipyenrc in there
echo "Copying ${HOME}/.bashrc to ${HOME}/.bashrc.$dt"
cp ${HOME}/.bashrc ${HOME}/.bashrc.$dt
echo "source ${HOME}/.scipyenrc" >> ${HOME}/.bashrc
echo ".bashrc has been modified in ${HOME}"
echo "Sourcing ${HOME}/.bashrc"
source ${HOME}/.bashrc
fi
fi
}

function get_pyver ()
{
    declare -a ver_array
    ver_array=( `python3 --version` )
    pyver=${ver_array[1]}
}

function linkscripts () 
{
    mkdir -p ${HOME}/bin
    if [ -r ${HOME}/bin/scipyen ] ; then
        dt=`date '+%Y-%m-%d_%H-%M-%s'`
        cp ${HOME}/bin/scipyen ${HOME}/bin/scipyen.$dt
    fi
    ln -s ${scipyendir}/scipyen ${HOME}/bin/scipyen
}

#### Execution starts here ###
# start_time=`date +%s`
SECONDS=0
get_pyver

# upgrade_virtualenv="N"
# use_preexisting="Y"
# TODO: switch to a relevant name e.g. scipyenv
# virtual_env="testenv"
virtual_env="scipyenv.$pyver"
ve_path=$HOME
# pyqt5_version=5.15.9
# pyqt5_repo=https://files.pythonhosted.org/packages/source/P/PyQt5/
# pyqt5_src=PyQt5-$pyqt5_version.tar.gz
# NOTE: figure out is /where is dbus-python.h
# pcgconf (pkg-config) must be installed
# pkgconf --liat-all  | grep dbus => list of dbus-* packages including dbus-python
# qdbus_python_dir=


realscript=`realpath $0`
installscriptdir=`dirname "$realscript"`
docdir=`dirname "$installscriptdir"`
scipyendir=`dirname "$docdir"`
install_neuron=0
use_pypi_neuron=1
use_core_neuron=0

for i in "$@" ; do
    case $i in
        --with_neuron)
        install_neuron=1
        use_pypi_neuron=1
        shift
        ;;
        --build_neuron)
        install_neuron=1
        use_pypi_neuron=0
        shift
        ;;
        --with_coreneuron)
        use_core_neuron=1
        shift
        ;;
        --install_dir=*)
        ve_path="${i#*=}"
        shift
        ;;
        --environment=*)
        virtual_env="${i#*=}"
        shift
        ;;
        -h|-?|--help)
        show_help
        exit 0
        shift
        ;;
        -*|--*)
        echo -e "Unknown option $i"
        show_help
        shift
        exit 1
        ;;
        *)
        ;;
    esac
done

# makes a virtual environment and activates it
upgrade_virtualenv && makevirtenv

if [[ $? -ne 0 ]] ; then
    echo -e "\nCould not create and/or activate a virtual environment. Goodbye!\n"
    exit 1
fi

# verify that the newly created virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

if [[ ( -n "$VIRTUAL_ENV" ) && ( -d "$VIRTUAL_ENV" ) ]] ; then
    echo -e "Creating 'src' directory inside $VIRTUAL_ENV ...\n"
    mkdir -p "$VIRTUAL_ENV/src" && cd "$VIRTUAL_ENV/src"
    
    # install pip requirements
    installpipreqs
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Could not install pip requirements; check the console for messages. Goodbye!\n"
        exit 1
    fi
    
    # build Pyqt5
    dopyqt5
    
    
    # build vigra
    dovigra
    
    # build neuron
    if [ $install_neuron -ne 0 ] ; then
        doneuron
    fi
    
    # make scripts
    #make_scipyenrc && update_bashrc && linkscripts
    
fi

# stop_time=`date +%s`
echo Execution time was `expr $stop_time - $start_time` seconds.

t=$SECONDS

echo "Execution time was $(( t/86400 )) days and $(( t/60 - 1440*(t/86400))) minutes"




