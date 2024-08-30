#!/bin/bash
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


realscript=`realpath $0`
scipyendir=`dirname $realscript`

make_pyenv () {
# NOTE: this function is only used when we intend to use Scipyen with a Python
# virtual environment that uses a custom-built Python stack. Usually that is
# installed in /usr/local and by calling 'make altinstall' so that it doesn't
# interfere with the system-wide Python installed by the distribution
#
# Parameters:
# $1 - absolute path of the directory where a custom built Python is installed
#       by default this is /usr/local
# The function uses 'pyenv_src'  template file 
sed "s|PYTHON_INSTALL_DIR|$1|g" pyenv_src > ${HOME}/.pyenv
}

make_scipyenrc () {
# Creates ${HOME}/.scipeynrc which activates the virtual python environment
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
source ${1}/bin/activate 
err=$(mktemp)

# I found that when the virtual environment uses python built from sources (and 
# installed in /usr/local as per default) then python complains that it cannot
# find platform libraries. This happens when it is running /etc/pythonstartup
# It might be related/specific to OpenSUSE, but not sure. Therefore below I 
# check if running the python exec in the virtual environment finds  platform 
# libraries.
# If it doesn't then - CONTRARY to the policy of the virtualenv - I set the 
# PYTHONHOME variable to point to where the built python is installed, by creating
# the ${HOME}/.pyenv script file to be sourced from bash, AFTER activating the
# python virtual environment - hence 'scipyact' function will be defined accordingly.
#
# In the situation where the python executable DOES find its platform libraries,
# I create a simpler version of the 'scipyact' which only sources the default
# activation script of the virtual environment.
if ${1}/bin/python -c "import sys" 2>"$err" ; then
shopt -s lastpipe
cat "$err" | grep "platform" | read error_msg
# echo "${1}/bin/python says: $error_msg"
if [ ! -z "$error_msg" ] ;then
make_pyenv ${2} # we need to make .pyenv
# then source ${HOME}/.pyenv AFTER the activation of the virtual environment
# by calling 'activate' script inside the 'bin' directory of the virtual
# environment
cat<<END > ${HOME}/.scipyenrc
scipyenvdir=${1}
scipyact () {
source ${1}/bin/activate
source ${HOME}/.pyenv ${3}
}
END
else
# python DID find its own platform libraries, therefore we just source the 'activate'
# script located inside the virtual environment 'bin' directory
# NOTE: an updated LD_LIBRARY_PATH is exported ony when not invoking .pyenv
cat<<END > ${HOME}/.scipyenrc
scipyenvdir=${1}
scipyact () {
source ${1}/bin/activate
}
export LD_LIBRARY_PATH=${1}/lib:${1}/lib64:$LD_LIBRARY_PATH
END
fi
else
echo "Cannot run python in ${1}: error code is "$?
fi
deactivate
}

update_bashrc () {
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
# .scipyenrc not sources from .bashrc => backup .bashrc then append a line to
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

get_python_data () {
# Guess what python we're using
# 
# Parameters:
# $1 = absolute path to where the virtual environment is
if [ ! -r ${1}/pyvenv.cfg ]; then
echo "Cannot read virtual environment configuration (pyvenv.cfg) in ${1}"
exit
fi
shopt -s lastpipe
# get these from reading pyvenv.cfg in the virtual environment directory
cat ${1}/pyvenv.cfg | grep home | read a b pynstall
cat ${1}/pyvenv.cfg | grep base-executable | read a b pyexec

declare -a ver_array
ver_array=( `$pyexec --version` )
pyver=${ver_array[1]::-2}
}

link_scripts () {
# Create symbolic links to scipyen launch and utility bash scripts
#
# Parameters:
# $1 = absolute path to where virtual environment is
# $2 = absolue path to where scipyen git clone is 
if [ ! -d ${HOME}/bin ]; then
mkdir ${HOME}/bin
fi

if [ -z $BROWSER ]; then
if [ -a ${1}/bin/browser ]; then
source ${1}/bin/browser
fi
fi

if [ ! -L ${1}/bin/scipyen ]; then
ln -s ${2}/scipyen ${1}/bin/scipyen
fi

if [ ! -L ${HOME}/bin/scipyen ]; then
ln -s ${2}/scipyen ${HOME}/bin/scipyen
fi

if [ ! -L ${1}/bin/notebook ]; then
ln -s ${2}/noteboook.sh ${1}/bin/notebook
fi

if [ ! -L ${1}/bin/jupyterlab ]; then
ln -s ${2}/jupyterlab.sh ${1}/bin/jupyterlab
fi

if [ ! -L ${1}/bin/set_browser ] ; then
ln -s ${2}/set_browser.sh ${1}/bin/set_browser
fi

if [ -d ${1}/nrnipython ] ; then
if [ ! -L ${1}/bin/nrnipython ]; then
ln -s ${2}/nrnipython/nrnipython ${1}/bin/nrnipython
fi

if [ ! -L ${1}/bin/nrnpython ]; then
ln -s ${2}/nrnipython/nrnipython ${1}/bin/nrnpython
fi

if [ ! -L ${1}/bin/nrnpy ]; then
ln -s ${2}/nrnipython/nrnipython ${1}/bin/nrnpy
fi
fi

}

scipyenvdir=`realpath ${1}`

if [ -z ${scipyenvdir} ] ; then

echo "Enter the full location of the virtual Python environment (e.g. ${HOME}/scipyenv39)"
read -e scipyenvdir
fi
if [ -z ${scipyenvdir} ] ; then
echo "I cannot continue without knowing where the virtual Python environment is..."
echo "Goodbye!"
exit
fi

get_python_data $scipyenvdir

make_scipyenrc $scipyenvdir $pynstall $pyver && update_bashrc && source ${HOME}/.bashrc


source ${HOME}/.scipyenrc


link_scripts ${scipyenvdir} ${scipyendir}







