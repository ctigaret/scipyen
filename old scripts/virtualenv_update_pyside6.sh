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

# function findqmake6 ()
# {
#     qmake6_binary=`which qmake6`
#     if [ -z "$qmake6_binary" ] ; then
#         qmake6_binary=`which qmake-qt6`
#     fi
#     
#     if [ -z "$qmake6_binary" ] ; then
#         read -e -p "Enter a full path to qmake6 (or qmake-qt6): " qmake6_binary
#     fi
#     
#     if [ -z "$qmake6_binary" ] ; then
#         echo -e "Cannot build PyQt6 without qmake6. Goodbye!\n"
#         exit 1
#     fi
#     
#     echo "using qmake: ${qmake6_binary}"
# }

function get_qtpaths ()
{
declare -a ver_array
qtpaths_exec=`which qtpaths`
ver_array=( `${qtpaths_exec} --qt-version` )
qtver=${ver_array}
oldifs=$IFS
IFS=-.
read major minor micro <<EOF
${qtver##*-}
EOF
IFS=$oldifs
if [[ ${major} -lt 6 ]] ; then
qtpaths_exec=`which qtpaths6`
ver_array=( `${qtpaths_exec} --qt-version` )
qtver=${ver_array}
oldifs=$IFS
IFS=-.
read major minor micro <<EOF
${qtver##*-}
EOF
IFS=$oldifs
fi
if [[ ${major} -ne 6 ]] ; then
# echo "Cannot find qtpaths for Qt6. Bailing out..."
exit 1
fi
full_path_to_qtpaths=`readlink -f ${qtpaths_exec}`
}

if [[ `id -u` -eq 0 ]] ; then
    echo -e "\n****\nCannot run as administrator!\n****\n"
    exit 1
fi

if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

# findqmake6

get_qtpaths


mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src

if [ `pwd` != "$VIRTUAL_ENV"/src ]; then
    echo -e "Not inside $VIRTUAL_ENV/src - goodbye\n"
    exit 1
fi
py_exec=`which python3`
echo -e "python executable: "${py_exec}

if [ -d pyside6-build ] ; then
    rm -fr pyside6-build
fi

mkdir -p pyside6-build && cd pyside6-build

build_venv_subdir=`basename ${VIRTUAL_ENV}`
mkdir ${build_venv_subdir} && cd ${build_venv_subdir}
mkdir -p install && cd install
mkdir -p lib
ln -s lib lib64

base_build_dir=${VIRTUAL_ENV}/src/pyside6-build
cd ${VIRTUAL_ENV}/src

if [ -d pyside-setup ] ; then
    rm -fr pyside-setup
fi

git clone https://code.qt.io/pyside/pyside-setup
cd pyside-setup && git checkout 6.9.2
if [ -z ${uv_exec} ] ; then
    pip install -r requirements.txt
    pip install -r requirements-doc.txt
    pip install -r requirements-coin.txt
else
    ${uv_exec} pip install -r requirements.txt
    ${uv_exec} pip install -r requirements-doc.txt
    ${uv_exec} pip install -r requirements-coin.txt
fi
qtinfopatch=${installscriptdir}/pyside6/qtinfo.diff
patch build_scripts/qtinfo.py ${qtinfopatch}

if [[ $njobs -gt 0 ]] ; then
    if [ -z ${uv_exec} ] ; then
        python setup.py build --qtpaths=${full_path_to_qtpaths} --build-tests --build-base=${base_build_dir} --parallel=$njobs
    else
        uv run setup.py build --qtpaths=${full_path_to_qtpaths} --build-tests --build-base=${base_build_dir} --parallel=$njobs
    fi
else
    if [ -z ${uv_exec} ] ; then
        python setup.py build --qtpaths=${full_path_to_qtpaths} --build-tests --build-base=${base_build_dir}
    else
        uv run setup.py build --qtpaths=${full_path_to_qtpaths} --build-tests --build-base=${base_build_dir}
    fi
fi

if [[ $? -ne 0 ]] ; then
    echo -e "\nCould not build PySide6. Goodbye!\n"
    exit 1
fi
build_dir=${base_build_dir}/`basename ${VIRTUAL_ENV}`
python create_wheels.py --no-examples --build-dir=${build_dir}

if [[ $? -ne 0 ]] ; then
    echo -e "\nCould not create PySide6 wheels. Goodbye!\n"
    exit 1
fi

if [ -z ${uv_exec} ] ; then
    pip install ${VIRTUAL_ENV}/src/pyside-setup/dist/*.whl
else
    uv pip install ${VIRTUAL_ENV}/src/pyside-setup/dist/*.whl
fi

if [[ $? -ne 0 ]] ; then
    echo -e "\nCould not install PySide6 wheels. Goodbye!\n"
    exit 1
else
    echo -e "\nPySide6 wheel have been successfully built and installed"
fi

