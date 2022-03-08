#!/bin/bash

realscript=`realpath $0`
scipyendir=`dirname $realscript`

make_pyenv () {
# param $1 is where a custom built Python is installed
# by default this is /usr/local
# sed "s|PYTHON_INSTALL_DIR|$1|g" pyenv_src > ${HOME}/bin/pyenv
sed "s|PYTHON_INSTALL_DIR|$1|g" pyenv_src > ${HOME}/.pyenv
}

# make_scipyenrc_old () {
# # param $1 is scipyenvdir i.e. where virtual environment is
# cat<<END > ${HOME}/.scipyenrc
# scipyenvdir=${1}
# scipyact () {
# source ${1}/bin/activate
# }
# END
# }

make_scipyenrc () {
# Creates ${HOME}/.scipeynrc which activates the virtual python environment
# in order to run Scipyen
# The ${HOME}/.scipyenrc defined a single bash function - 'scipyact' - which 
# activates the virtual environment and optionally sets up a few needed environment
# variables (see below in the code)
# The ${HOME}/.scipyenrc script NEEDS TO BE SOURCED (in bash); this is done
# automatically by the Scipyen launch bash script ('scipyen'), but also from 
# .bashrc in order for the function 'scipyact' to be readily available to the user.
#
# params:
# $1 virtual environment directory (full path)
# #2 location of custom built python installation (e.g. /usr/local)
# $3 major.minor verison of python executable
# test if python complains about platform dependent libs
source ${1}/bin/activate 
err=$(mktemp)

# I found that when the virtual environment uses python built from sources (and 
# installed in /usr/local as per defautl) then python complains that it cannot
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
# python did not find platform libraries, so we need to create ${HOME}/.pyenv
make_pyenv ${2}
# then source ${HOME}/.pyenv AFTER the activation of the virtual environment
# by calling 'activate' script indise the 'bin' directory of the virtual
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
# NOTE: LD_LIBRARY_PATH export only needed when not invoking .pyenv
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
cat ${HOME}/.bashrc | grep "source ${HOME}/.scipyenrc" | read source_set
# echo "source_set="$source_set
if [ -z "${source_set}" ]; then
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
# param $1 is scipyenvdir i.e. where virtual environment is
if [ ! -r ${1}/pyvenv.cfg ]; then
echo "Cannot read virtual environment configuration (pyvenv.cfg) in ${1}"
exit
fi
shopt -s lastpipe
cat ${1}/pyvenv.cfg | grep home | read a b pynstall
cat ${1}/pyvenv.cfg | grep base-executable | read a b pyexec

# echo "in get_python_data pyexec="$pyexec
declare -a ver_array
ver_array=( `$pyexec --version` )
pyver=${ver_array[1]::-2}
# echo "in get_python_data pyver="$pyver
}

link_scripts () {
# parameter $1 is scipyenvdir where virtual environment is
# parameter $2 is scipyendir, i.e. where scipyen git clone is 
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
# echo "scipyenvdir "${scipyenvdir}
# if [ ! -z ${scipyenvdir} ] && [ -d ${scipyenvdir} ]; then
# if [ ! -z ${scipyenvdir} ] ; then
if [ -z ${scipyenvdir} ] ; then
echo "I cannot continue without knowing where the virtual Python environment is..."
echo "Goodbye!"
exit
fi

get_python_data $scipyenvdir

# echo pyver=$pyver

# make_scipyenrc $scipyenvdir && update_bashrc && source ${HOME}/.bashrc
make_scipyenrc $scipyenvdir $pynstall $pyver && update_bashrc && source ${HOME}/.bashrc


source ${HOME}/.scipyenrc


link_scripts ${scipyenvdir} ${scipyendir}







