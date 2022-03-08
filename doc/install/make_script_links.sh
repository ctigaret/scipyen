#!/bin/bash

realscript=`realpath $0`
scipyendir=`dirname $realscript`

make_pyenv () {
# param $1 is where a custom built Python is installed
# by default this is /usr/local
# sed "s|PYTHON_INSTALL_DIR|$1|g" pyenv_src > ${HOME}/bin/pyenv
sed "s|PYTHON_INSTALL_DIR|$1|g" pyenv_src > ${HOME}/.pyenv
}

make_scipyenrc () {
# param $1 is scipyenvdir i.e. where virtual environment is
cat<<END > ${HOME}/.scipyenrc
scipyenvdir=${1}
scipyact () {
source ${1}/bin/activate
}
END
}

make_scipyenrc_2 () {
# params:
# $1 virtual environment directory (full path)
# #2 location of custom built python installation (e.g. /usr/local)
# $3 major.minor verison of python executable
# test if python complains about platform dependent libs
source ${1}/bin/activate 
err=$(mktemp)
if python -c "import sys" 2>"$err" ; then
# echo "$err"{
shopt -s lastpipe
cat "$err" | grep "platform" | read error_msg
echo "$error_msg"
# deactivate
if [ ! -z "$error_msg" ] ;then
make_pyenv ${2}
# echo ${1} ${2}
cat<<END > ${HOME}/.scipyenrc
scipyenvdir=${1}
scipyact () {
source ${1}/bin/activate
source ${HOME}/.pyenv ${3}
}
END
else
cat<<END > ${HOME}/.scipyenrc
scipyenvdir=${1}
scipyact () {
source ${1}/bin/activate
}
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

scipyenvdir=${1}

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
make_scipyenrc_2 $scipyenvdir $pynstall $pyver && update_bashrc && source ${HOME}/.bashrc

# exit

# make $HOME/bin directory - in most Linux dsitributions, this should be in your
# $PATH by default;
# if it is not, then edit or create $HOME/.bashrc to contain
# the following line (without the comment hash):
# export PATH=$HOME/bin:$PATH
# and re-start the terminal

# # echo "Custom Python installation (leave empty if using distribution-provided Python):"
# # read pynstall
# # read -e -p "Custom Python installation (leave empty if not used): "
# 
# if [ ! -z $pynstall ] && [ -d $pynstall ] && [ -z $pyver ]; then 
# echo "Enter major.minor version number for the custom Python (e.g. 3.9):"
# read pyver
# if [ -z $pyver ] ; then
#     pyver=3.9
# fi
# echo "Configuring Scipyen to use Python ${pyver} in ${pynstall}"
# 
# echo "Creating ${HOME}/.scipyenrc"
# cat<<END > ${HOME}/.scipyenrc
# scipyenvdir=${scipyenvdir}
# scipyact () {
# source ${scipyenvdir}/bin/activate
# source ${HOME}/bin/pyenv ${pyver}
# }
# END
# 
# else
# echo "Using Python in the virtual environment in ${scipyenvdir}"
# 
# cat<<END > ${HOME}/.scipyenrc
# scipyenvdir=${scipyenvdir}
# scipyact () {
# source ${scipyenvdir}/bin/activate
# }
# 
# END
# 
# 
# 
# fi

source ${HOME}/.scipyenrc

# if [ -z ${VIRTUAL_ENV} ] ; then
# echo "You must run this script while in a virtual python environment"
# echo "in order to install other scripts"
# exit 
# fi

link_scripts ${scipyenvdir} ${scipyendir}







