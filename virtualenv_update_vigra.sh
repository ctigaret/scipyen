#!/bin/bash
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# Bash script functions for updating Scipyen's VIGRA build from sources
#
# 
# Use this script when the platform you're running Scipyen on has been updated
# (hence VIGRA must be recompiled against new system library versions)
#
# CAUTION: You must have activated the virtual python environment BEFORE runnning this script
#
# e.g., run 'source <path-to-your-virtual-env>/bin/activate' first
# then cd to the directory containing this script, then run the script with
#  './virtualenv_update_vigra.sh'
#
# NOTE: On Linux, we use virtual environments created with 'virtualenv', NOT with
# the Python's stock 'venv' !

mydir=`pwd`
realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
docdir=${scipyendir}/doc
installscriptdir=${scipyendir}/setup_env
scipyensrcdir=${scipyendir}/src/scipyen
refresh_git_repos=1

njobs=`nproc --all`

for i in "$@" ; do
    case $i in
        --refresh-git)
        refresh_git_repos=0
        shift
        ;;
        *)
        ;;
    esac
done


function findcmake ()
{
    cmake_binary=`which cmake`
    if [ -z "$cmake_binary" ] ; then
        echo -e "Cannot build vigra without cmake. Goodbye!\n"
        exit 1
    fi
    
}

if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

findcmake

vigra_src=${VIRTUAL_ENV}/src/vigra
vigra_build=${VIRTUAL_ENV}/src/vigra-build

echo -e "VIGRA source will be downloaded to ${vigra_src}"
echo -e "VIGRA source will be built in ${vigra_build}"

if [ ! -r ${vigra_src} ] ; then
    echo -e "Cloning vigra git repository...\n"
    git clone https://github.com/ukoethe/vigra.git
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot clone vigra git repository. Goodbye!\n"
        exit 1
    fi
    
else
    # refresh the git repo...
    if [[ $refresh_git_repos -gt 0 ]] ; then
        echo -e "Refreshing vigra git repository...\n"
        cd ${vigra_src}
        git pull
        cd ${mydir}
    fi
fi
    
if [ -d ${vigra_build} ] ; then
    rm -fr ${vigra_build}
fi

echo -e "Creating vigra build tree outside the source tree\n"
mkdir -p ${vigra_build} && cd ${vigra_build}

$cmake_binary -DPython_INCLUDE_DIRS=$(python -c "import sysconfig; print(sysconfig.get_paths()['include'])") \
                -DPython_LIBRARIES=$(python -c "import distutils.sysconfig as sysconfig; print(sysconfig.get_config_var('LIBDIR'))") \
                -DPython_EXECUTABLE:FILEPATH=`which python` \
                -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DWITH_BOOST_GRAPH=1 -DWITH_BOOST_THREAD=1 -DWITH_HDF5=1 -DWITH_OPENEXR=1 -DWITH_VIGRANUMPY=1 -DLIB_SUFFIX=64 ${vigra_src}

if [[ $njobs -gt 0 ]] ; then
    make --jobs=$njobs && make install
else
    make && make install
fi


if [[ $? -ne 0 ]] ; then
    echo -e "Cannot build vigra; check console output. Bailing out. Goodbye!\n"
    exit 1
else
    echo -e "VIGRA installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.vigra_done
    echo -e "\n\n=====================\n# Building vigra DONE!\n=====================\n\n"
fi







