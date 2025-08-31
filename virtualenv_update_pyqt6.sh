#!/bin/bash
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# Bash script functions for updating Scipyen's PyQt6 built from source code

# 
# Use this script when the platform you're running Scipyen on has been updated
# (hence PyQt6 must be recompiled against new system Qt6 versions)
#
# CAUTION: You must have activated the virtual python environment BEFORE runnning this script
#
# e.g., run 'source <path-to-your-virtual-env>/bin/activate' first
# then cd to the directory containing this script, then run the script with
#  './virtualenv_update_pyqt6.sh'
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

function findqmake6 ()
{
    qmake6_binary=`which qmake6`
    if [ -z "$qmake6_binary" ] ; then
        qmake6_binary=`which qmake-qt6`
    fi
    
    if [ -z "$qmake6_binary" ] ; then
        read -e -p "Enter a full path to qmake6 (or qmake-qt6): " qmake6_binary
    fi
    
    if [ -z "$qmake6_binary" ] ; then
        echo -e "Cannot build PyQt6 without qmake6. Goodbye!\n"
        exit 1
    fi
    
    echo "using qmake: ${qmake6_binary}"
}


if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

findqmake6


mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src

if [ `pwd` != "$VIRTUAL_ENV"/src ]; then
    echo -e "Not inside $VIRTUAL_ENV/src - goodbye\n"
    exit 1
fi
py_exec=`which python3`
echo -e "python executable: "${py_exec}
sip_wheel_exec="$VIRTUAL_ENV/bin/sip-wheel"
if [[ `id -u` -eq 0 ]] ; then
    echo -e "\n****\nCannot run as administrator!\n****\n"
    exit 1
fi

#             echo "Using ${py_exec} as `whoami` to build PyQt6"

# NOTE: locate_pyqt6_src.py uses distlib to locate the (latest) source 
# archive (i.e., the sdist) of PyQt6 - its file name typically ends with
# .tar.gz
pyqt6_src_url=`${py_exec} $installscriptdir/locate_pyqt6_src.py`
pyqt6_src=`basename ${pyqt6_src_url}`

pyqt6_src_dir=${VIRTUAL_ENV}/src/${pyqt6_src%.tar.gz}

echo "PyQt6 source will be located in "${pyqt6_src_dir}

# NOTE: the sdist might have been downloaded alreay - so check this first
# before actually downloading
if [ ! -r ${pyqt6_src} ] ; then
    wget ${pyqt6_src_url} && tar xzf ${pyqt6_src} 

    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot obtain the PyQt6 source. Bailing out. Goodbye!\n"
    exit 1
    fi
else
    if [ -d ${pyqt6_src_dir} ] ; then
        rm -fr ${pyqt6_src_dir}
    fi
    tar xzf ${pyqt6_src}
fi

# NOTE: good practice is to create an out-of-source build tree, » ...
pyqt6_build_dir=${VIRTUAL_ENV}/src/PyQt6-build

# NOTE: clear build dir if it exists -- best to start fresh
if [ -d ${pyqt6_build_dir} ] ; then
    rm -fr ${pyqt6_build_dir}
fi
mkdir -p ${pyqt6_build_dir}

# NOTE: » ... but run the build process INSIDE the expanded sdist dir
# this is because sip-wheel will get extra options from there :)
cd ${pyqt6_src_dir}

echo "Generating PyQt6 wheel in "$(pwd)"..."

# NOTE: 2023-03-23 14:03:48 - enable parallel jobs - to change, either:
# • change the value of the --jobs option (e.g. half the number of 
# cores in your system seems to be a good choice), or
# • remove the --jobs option altogether
if [[ $njobs -gt 0 ]] ; then
    ${sip_wheel_exec} --verbose --build-dir ${pyqt6_build_dir} --qmake ${qmake6_binary} --confirm-license --license-dir ${pyqt6_src_dir}/sip --jobs $njobs
else
    ${sip_wheel_exec} --verbose --build-dir ${pyqt6_build_dir} --qmake ${qmake6_binary} --confirm-license --license-dir ${pyqt6_src_dir}/sip
fi

if [[ $? -ne 0 ]] ; then
    echo -e "sip Cannot build a PyQt6 wheel. Bailing out. Goodbye!\n"
    echo -e "You might want to upgrade sip and PyQt6-sip in this environment\n"
    echo -e " by calling \n\n"
    echo -e "pip install --upgrade sip\n"
    echo -e "pip install --upgrade PyQt6-sip\n\n"
    echo -e "Then run this script again"
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
    if [ -z ${uv_exec} ] ; then
        pip install --force-reinstall ${wheel_file}
    else
        ${uv_exec} pip install --force-reinstall ${wheel_file} 
    fi
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot install the PyQt6 wheel; check console output. Goodbye!\n"
        exit 1
    else
        echo "PyQt6 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pyqt6done
        echo -e "\n\n=====================\n# Pyqt6 installed!\n=====================\n\n"
    fi
fi
