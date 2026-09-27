#!/bin/bash
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# Bash script functions for updating Scipyen's PyQt5 built from source code

# 
# Use this script when the platform you're running Scipyen on has been updated
# (hence PyQt6 must be recompiled against new system Qt5 versions)
#
# CAUTION: You must have activated the virtual python environment BEFORE runnning this script
#
# e.g., run 'source <path-to-your-virtual-env>/bin/activate' first
# then cd to the directory containing this script, then run the script with
#  './virtualenv_update_pyqt5.sh'
#
# NOTE: On Linux, we use virtual environments created with 'virtualenv', NOT with
# the Python's stock 'venv' !

realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
docdir=${scipyendir}/doc
installscriptdir=${scipyendir}/setup_env
scipyensrcdir=${scipyendir}/src/scipyen
mydir=`pwd`
njobs=`nproc --all`


function findqmake ()
{
    # Identifes which qmake is there available on the platform.
    # 
    # Since Linux dsitributions currently provide both Qt5 and Qt6, their respective
    # qmake tools bear different names.
    #
    # Not sure this is as generic as possible across the Linux distributions...
    #
    
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
    
    echo "using qmake: ${qmake_binary}"
}

if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

findqmake

mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src

py_exec="$VIRTUAL_ENV/bin/${python_exec}"
sip_wheel_exec="$VIRTUAL_ENV/bin/sip-wheel"
if [[ `id -u` -eq 0 ]] ; then
    echo -e "\n****\nCannot run as administrator!\n****\n"
    exit 1
fi

#             echo "Using ${py_exec} as user `whoami` to build PyQt5"

pyqt5_src_url=`${py_exec} $installscriptdir/locate_pyqt5_src.py`
pyqt5_src=`basename $pyqt5_src_url`

pyqt5_src_dir=${VIRTUAL_ENV}/src/${pyqt5_src%.tar.gz}

echo "PyQt5 source will be located in "${pyqt5_src_dir}

# NOTE: the sdist might have been downloaded alreay - so check this first
# before actually downloading
if [ ! -r ${pyqt5_src} ] ; then
    wget ${pyqt5_src_url} && tar xzf ${pyqt5_src} 

    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot obtain the PyQt5 source. Bailing out. Goodbye!\n"
    exit 1
    fi
    
else
    if [ -d ${pyqt5_src_dir} ] ; then
        rm -fr ${pyqt5_src_dir}
    fi
    tar xzf ${pyqt5_src}
fi

# NOTE: good practice is to create an out-of-source build tree, » ...
pyqt5_build_dir=${VIRTUAL_ENV}/src/PyQt5-build

# NOTE: clear build dir if it exists -- best to start fresh
if [ -d ${pyqt5_build_dir} ] ; then
    rm -fr ${pyqt5_build_dir}
fi
mkdir -p ${pyqt5_build_dir}

# NOTE: » ... but run the build process INSIDE the expanded sdist dir
# this is because sip-wheel will get extra options from there :)
cd ${pyqt5_src_dir}

echo "Generating PyQt5 wheel in "$(pwd)"..."

# NOTE: 2023-03-23 14:03:48 - enable parallel jobs - to change, either:
# • change the value of the --jobs option (e.g. half the number of 
# cores in your system seems to be a good choice), or
# • remove the --jobs option altogether
if [[ $njobs -gt 0 ]] ; then
    ${sip_wheel_exec} --qmake=${qmake_binary} --confirm-license --jobs $njobs --qt-shared --verbose --build-dir ${pyqt5_build_dir} --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
else
    ${sip_wheel_exec} --qmake=${qmake_binary} --confirm-license --qt-shared --verbose --build-dir ${pyqt5_build_dir} --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
fi

if [[ $? -ne 0 ]] ; then
    echo -e "sip Cannot build a PyQt5 wheel. Bailing out. Goodbye!\n"
    echo -e "You might want to upgrade sip and Pyqt5-sip in this environment\n"
    echo -e " by calling \n\n"
    echo -e "pip install --upgrade sip\n"
    echo -e "pip install --upgrade PyQt5-sip\n\n"
    echo -e "Then run this script again"
    exit 1
fi

# NOTE: check is a wheel file has been produced; the filename typically
# ends in .whl and nis located in the source tree, NOT in the build tree!
# » if found then call pip to install it inside the 
# environment ⟶ IT WORKS!
wheel_file=`ls | grep whl`
if [ -z ${wheel_file} ] ; then
    echo -e "No wheel file found in "$(pwd)" - goodbye!\n"
    exit 1
else
    if [ -z ${uv_exec} ] ; then
        pip install --force-reinstall ${wheel_file}
    else
        ${uv_exec} pip install --force-reinstall ${wheel_file} 
    fi
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot install the PyQt5 wheel; check console output. Goodbye!\n"
        exit 1
    else
        echo "PyQt5 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pyqt5build_done
        echo -e "\n\n=====================\n# Pyqt5 installed!\n=====================\n\n"
    fi
fi

cd ${mydir}

