#! /bin/bash
echo -e "You should have installed miniforge3 in your local HOME drectory,"
echo -e "followed by 'conda init' then 'conda config --set auto_activate_base false'"
echo -e ""
echo -e "Edit this file to customize your installation!"


function make_scipyenrc () 
{
# When the installer script is run as regular user, it will create 
# ${HOME}/.scipeynrc which allows activation of the virtual python environment
# used to run Scipyen.
#
# The .scipyenrc script NEEDS TO BE SOURCED (in bash); this is done automatically
# by the Scipyen launch bash script ('scipyen'); for convenience, this script is
# also sourced from ${HOME}/.bashrc in order for the function 'scipyact' to be
# readily available to the user, at the console.
#

if [[ -z "$CONDA_PREFIX" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi
echo -e "\nCreating .scipyenrc\n"

dt=`date '+%Y-%m-%d_%H-%M-%s'`

py_exec=${python_exec}
if [ -r ${HOME}/.scipyenrc ] ; then
# make a backup copy of .scipyenrc
shopt -s lastpipe
echo "Copying ${HOME}/.scipyenrc to ${HOME}/.scipyenrc.$dt"
cp ${HOME}/.scipyenrc ${HOME}/.scipyenrc.$dt
fi
cat<<END > ${HOME}/.scipyenrc
scipyact () {
mamba activate ${scipyenvdir}
echo -e "The Python mamba environment in ${scipyenvdir} is now active.\nTo exit this environment call 'mamba deactivate'"
}
END
shopt -u lastpipe
}

function make_launch_script () 
{
target_dir=${HOME}/bin
    
mkdir -p ${target_dir}
if [ -r ${target_dir}/scipyen ] ; then
    dt=`date '+%Y-%m-%d_%H-%M-%s'`
    mv ${target_dir}/scipyen ${target_dir}/scipyen.$dt
fi
shopt -s lastpipe

# if [[ `id -u` -eq 0 ]] ; then
cat <<END > ${target_dir}/scipyen 
#! /bin/sh
if [ -z \${CONDA_PREFIX} ]; then
conda activate && mamba activate ${scipyenvdir}
fi
export OUTDATED_IGNORE=1
a=\`which xrdb\` # do we have xrdb to read the X11 resources? (on Unix almost surely yes)
if [ \$0 == 0 ] ; then
if [ -r $scipyensrcdir/neuron_python/app-defaults/nrniv ] ; then
xrdb -merge $scipyensrcdir/neuron_python/app-defaults/nrniv
fi
fi
python -Xfrozen_modules=off ${scipyensrcdir}/scipyen.py "\$*"
END
shopt -u lastpipe
chmod +x ${target_dir}/scipyen 
echo -e "Scipyen startup script created in ${target_dir} \n"
}


realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
docdir=${scipyendir}/doc
installscriptdir=${scipyendir}/setup_env
condaprojectfile=${scipyendir}/mambaprojects/linux/scipyenv.yml
scipyensrcdir=${scipyendir}/src/scipyen
scipyenvdir=${HOME}/scipyenv_mamba_3.11

echo -e "Creating mamba environment in ${scipyenvdir}"
mamba env create --prefix ${scipyenvdir} --file ${condaprojectfile}

echo -e "\nTo install the console style KeplerDark open a new shell then call:"
echo -e "'conda activate ${scipyenvdir}'"
echo -e "'cd ${scipyendir}/src/scipyen/gui/scipyen_console_styles'"
echo -e "'pip install --no-deps .'"

make_scipyenrc

make_launch_script


