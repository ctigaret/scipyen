#!/bin/bash

# Installation script stub for scipyen 23c19


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
    if [ -z "$qmake_binary" ] ; then
        echo -e "Cannot build vigra without cmake. Goodbye!\n"
        exit 1
    fi
    
}

function upgrade_virtualenv ()
{
    echo "Upgrading virtualenv locally..."
    pip install --user --upgrade virtualenv
}

function makevirtenv ()
{
    read -e -p "Location of virtual environment ['$HOME']: " ve_path
    if [[ $? -ne 0 ]] ; then
        echo -e "Goodbye!\n"
        exit 1
    fi
    
    if [ -z "$ve_path" ] ; then
        ve_path=$HOME
    fi
    
    if [ -d "$ve_path" ] ; then
        cd $ve_path
    else
        echo -e "Specified path $ve_path doe not exist. Goodbye!\n"
        exit 1
    fi
    
    read -e -p "Name of virtual environment [$virtual_env]: " virtual_env
    if [[ $? -ne 0 ]] ; then
        echo -e "Goodbye!\n"
        exit 1
    fi
    
    if [ -d $ve_path/$virtual_env ] ; then
        # NOTE: best thing is to avoid re-using virtual environments => force 
        # creation of a new environment
        # echo -e "Directory $ve_path/$virtual_env already exists.\n\nGoodbye!\n"
        # exit 1
        if [ -a $ve_path/$virtual_env/pyvenv.cfg ] ; then
            aa=`cat $ve_path/$virtual_env/pyvenv.cfg | grep "virtualenv"`
            if [ -n "$aa" ] ; then
                echo -e "Looks like $ve_path/$virtual_env is a virtual environment"
                read -e -p "Do you want to use this environment ? [n/$use_preexisting]: " use_prexisting
                if [[ ($use_prexisting == "y") || ($use_prexisting == "Y") || ($use_prexisting == "Yes") || ($use_prexisting == "YES") ]] ; then
                    source $ve_path/$virtual_env/bin/activate
                else
                echo -e "Create a a new environment directory by running this script again. Goodbye!\n"
                exit 1
                fi
            fi 
        fi
    else
        python3 -m virtualenv $virtual_env && source $ve_path/$virtual_env/bin/activate
    fi
    
}

function installpipreqs ()
{
    # assumes (and therefore REQUIRES that the virtual environment is active)
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    pip install -r "$installscriptdir"/pip_requirements-experimental-23c21.txt
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot install required packages from PyPI. Bailing out. Goodbye!\n"
        exit 1
    else
        echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
    fi
    
    
}

function dopyqt5 ()
{
    
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    cd $VIRTUAL_ENV/src
    
    findqmake
    
    if [ `pwd` != "$VIRTUAL_ENV"/src ]; then
        echo -e "Not inside $VIRTUAL_ENV/src - goodbye\n"
        exit 1
    fi
    
    wget $pyqt5_repo/$pyqt5_src && tar xzf $pyqt5_src && mkdir -p PyQt5-build
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot obtain the PyQt5 source. Bailing out. Goodbye!\n"
        exit 1
    fi
    
    #sip-build --qmake=`which qmake-qt5` --confirm-license --build-dir ../PyQt5-build --qt-shared --disable QtQuick3D --disable QtRemoteObjects --no-dbus-python --pep484-pyi --no-make --verbose --target-dir $VIRTUAL_ENV
    #sip-build --qmake=`which qmake-qt5` --confirm-license --build-dir ../PyQt5-build --qt-shared --disable QtQuick3D --disable QtRemoteObjects --no-dbus-python --no-designer-plugin --no-qml-plugin --pep484-pyi --no-make --verbose --target-dir $VIRTUAL_ENV
    sip-build --qmake="$qmake_binary" --confirm-license --build-dir ../PyQt5-build --qt-shared --disable QtQuick3D --disable QtRemoteObjects --no-dbus-python --pep484-pyi --no-make --verbose --target-dir $VIRTUAL_ENV/lib64/python3.10/site-packages

    if [[ $? -ne 0 ]] ; then
        echo -e "sip-build Cannot configure PyQt5 source. Bailing out. Goodbye!\n"
        exit 1
    fi
    
    cd "$VIRTUAL_ENV"/src/PyQt5-build
    
    make && make install
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot build and/or install PyQt5; check console output. Goodbye!\n"
        exit 1
    else
        echo -e "\n\n=====================\n# Pyqt5 installed!\n=====================\n\n"
    fi
    
}

function dovigra ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    cd $VIRTUAL_ENV/src
    
    findcmake
    
    git clone https://github.com/ukoethe/vigra.git && mkdir -p vigra-build && cd vigra-build
    
    $cmake_binary -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DWITH_BOOST_GRAPH=1 -DWITH_BOOST_THREAD=1 -DWITH_HDF5=1 -DWITH_OPENEXR=1 -DWITH_VIGRANUMPY=1 -DLIB_SUFFIX=64 ../vigra
    
    make && make install
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot build vigra; check console output. Bailing out. Goodbye!\n"
        exit 1
    else
        echo -e "\n\n=====================\n# Building vigra DONE!\n=====================\n\n"
    fi
    
}

function doneuron ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    cd $VIRTUAL_ENV/src
    
    findcmake
    
    git clone https://github.com/neuronsimulator/nrn && mkdir -p nrn-build && cd nrn-build
    
    $cmake_binary -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=1 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_CORENEURON=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_REL_PATH=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABL_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 ../nrn
    $cmake_binary --build . --parallel 8 --target install
    
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot build NEURON; check console output. Bailing out. Goodbye!\n"
        exit 1
    else
        echo -e "\n\n=====================\n# Building NEURON DONE!\n=====================\n\n"
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
cat<<END > ${HOME}/.scipyenrc
scipyact () {
source ${VIRTUAL_ENV}/bin/activate
}
export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:$LD_LIBRARY_PATH
END
}

function update_bashrc () 
{
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
dt=`date '+%Y-%m-%d_%H-%M-%s'`
echo "Copying ${HOME}/.bashrc to ${HOME}/dot.bashrc.$dt"
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

#### Execution starts here ###

get_pyver

upgrade_virtualenv="N"
use_preexisting="Y"
# TODO: switch to a relevant name e.g. scipyenv
virtual_env="testenv"
virtual_env="scipyenv.$pyver"
ve_path=$HOME
pyqt5_version=5.15.9
pyqt5_repo=https://files.pythonhosted.org/packages/source/P/PyQt5/
pyqt5_src=PyQt5-$pyqt5_version.tar.gz
# NOTE: figure out is /where is dbus-python.h
# pcgconf (pkg-config) must be installed
# pkgconf --liat-all  | grep dbus => list of dbus-* packages including dbus-python
# qdbus_python_dir=


realscript=`realpath $0`
installscriptdir=`dirname "$realscript"`
docdir=`dirname "$installscriptdir"`
scipyendir=`dirname "$docdir"`

# echo $scipyendir
#### BEGIN testing - comment out
# findqmake
# echo $qmake
# exit
#### END testing - comment out

read -e -p "Upgrade virtualenv locally? [y/$upgrade_virtualenv]: " upgrade_virtualenv # no timeout

# NOTE: this is already set to "N"
# if [ -z $upgrade_virtualenv ] ; then
#     upgrade_virtualenv="N"
# fi

if [[ $? -ne 0 ]] ; then
    echo -e "Goodbye!\n"
    exit 1
fi


if [[ ($upgrade_virtualenv == "y") || ($upgrade_virtualenv == "Y") || ($upgrade_virtualenv == "Yes") || ($upgrade_virtualenv == "YES") || ($upgrade_virtualenv == "yes")]] ; then
# echo $upgrade_virtualenv
    upgrade_virtualenv

    if [[ $? -ne 0 ]] ; then
        echo -e "\nError upgrading pip. Goodbye!\n"
        exit 1
    fi
fi

# makes a virtual environment and activates it
makevirtenv

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
    doneuron
    
    # pull scipyen repo
    get_scipyen
    
    # make scripts
    makescripts
fi


# virtualenv scipyenv_23c19
# source scipyenv_23c19/bin/activate
# pip install -r ~/scipyen/doc/install/pip_requirements.txt

