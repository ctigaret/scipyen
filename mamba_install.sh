#! bash
function get_pyver ()
{
declare -a ver_array
ver_array=( `python3 --version` )
pyver=${ver_array[1]}
oldifs=$IFS
IFS=. 
read major minor micro <<EOF
${pyver##*-}
EOF
IFS=$oldifs
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
    
    echo "using qmake: ${qmake_binary}"
}

function findcmake ()
{
    cmake_binary=`which cmake`
    if [ -z "$cmake_binary" ] ; then
        echo -e "Cannot build vigra without cmake. Goodbye!\n"
        exit 1
    fi
    
}

function dopyqt5 ()
{
    if [[ -z "$CONDA_DEFAULT_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    pip install -r ${installscriptdir}/pip_reqs_mamba_prePyQt5.txt
    
    if [ ! -r ${CONDA_DEFAULT_ENV}/.pyqt5done ] || [[ $reinstall_pyqt5 -gt 0 ]]; then
        mkdir -p ${CONDA_DEFAULT_ENV}/src && cd ${CONDA_DEFAULT_ENV}/src
        
        findqmake
        
        if [ `pwd` != "$CONDA_DEFAULT_ENV"/src ]; then
            echo -e "Not inside $CONDA_DEFAULT_ENV/src - goodbye\n"
            exit 1
        fi
        
        # NOTE: 2023-06-25 10:56:34 
        # when we are root, make sure to use the virtual environment's python 
        # executable here
        if [[ `id -u` -eq 0 ]] ; then
            py_exec="$CONDA_DEFAULT_ENV/bin/${python_exec}"
            sip_wheel_exec="$CONDA_DEFAULT_ENV/bin/sip-wheel"
        else
            py_exec=${python_exec}
            sip_wheel_exec=sip-wheel
        fi
        
        echo "Using ${py_exec} as `whoami` to build PyQt5"
        
        # NOTE: locate_pyqt5_src.py uses distlib to locate the (latest) source 
        # archive (i.e., the sdist) of PyQt5 - its file name typically ends with
        # .tar.gz
#         pyqt5_src_url=`python $installscriptdir/locate_pyqt5_src.py`
        pyqt5_src_url=`${py_exec} $installscriptdir/locate_pyqt5_src.py`
        pyqt5_src=`basename $pyqt5_src_url`
        
        pyqt5_src_dir=${pyqt5_src%.tar.gz}
        
        echo "PyQt5 source is in "${pyqt5_src_dir}
        
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
        pyqt5_build_dir="PyQt5-build"
        
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
            ${sip_wheel_exec} --qmake=${qmake_binary} --confirm-license --jobs $njobs --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
#             sip-wheel --qmake=${qmake_binary} --confirm-license --jobs $njobs --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
        else
            ${sip_wheel_exec} --qmake=${qmake_binary} --confirm-license --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
#             sip-wheel --qmake=${qmake_binary} --confirm-license --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
        fi
#         sip-wheel --qmake=${qmake_binary} --confirm-license --jobs 8 --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi

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
        # ends in .whl » if found then call pip to install it inside the 
        # environment ⟶ IT WORKS!
        wheel_file=`ls | grep whl`
        if [ -z ${wheel_file} ] ; then
            echo -e "No wheel file found in "$(pwd)" - goodbye!\n"
            exit 1
        else
            ${py_exec} -m pip install --force-reinstall ${wheel_file}
            
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot install the PyQt5 wheel; check console output. Goodbye!\n"
                exit 1
            else
                echo "PyQt5 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${CONDA_DEFAULT_ENV}/.pyqt5done
                echo -e "\n\n=====================\n# Pyqt5 installed!\n=====================\n\n"
                
#                 echo -e "\n\n Installing PyQtDataVisualization\n\n"
#                 # NOTE: WARNING: 2023-07-19 00:12:27 avoid this !!!! 
#                 pip install PyQtDataVisualization
            fi
        fi
    fi
}

function makevirtenv ()
{
    echo -e "Trying to create/use virtual environment ${virtual_env} using ${using_python}\n"
    
    if [ -d ${virtual_env} ] ; then
        conda activate ${virtual_env}
        
        if [[ -z ${CONDA_DEFAULT_ENV} ]]; then
            echo -r "Cannot activate a virtual environment from  $virtual_env . Goodbye!\n"
            exit 1
        fi
        
        python_executable=`which python3`
        
        echo -e "Virtual environment activated and will use ${python_executable}\n"
        
    else
        conda create -y --prefix ${virtual_env} python=${major}.${minor}
        if [[ $? -ne 0 ]] ; then
            echo -e "Could NOT create a virtual environment at ${virtual_env}. Bailing out...\n"
            exit 1
        fi
        echo -e "Virtual environment created at ${virtual_env}\n"
        echo -e "Activating the virtual environment\n"
        
        conda activate ${virtual_env}
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Could NOT activate the virtual environment at ${virtual_env}. Bailing out...\n"
            exit 1
        fi
        
        python_executable=`which python3`
        
        echo -e "Virtual environment at ${CONDA_DEFAULT_ENV} activated; python executable is ${python_executable}\n"
        
    fi
}

function condaact() {
__conda_setup="$('/home/cezar/miniforge3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/home/cezar/miniforge3/etc/profile.d/conda.sh" ]; then
        . "/home/cezar/miniforge3/etc/profile.d/conda.sh"
    else
        export PATH="/home/cezar/miniforge3/bin:$PATH"
    fi
fi
unset __conda_setup
# echo $PATH
}

function install_python_packages()
{
    if [ ! -r ${CONDA_DEFAULT_ENV}/.packagesdone ] ; then
        mamba config --add channels conda-forge
        

        echo -e "\n---\nInstalling yaml"
        mamba install --prefix $CONDA_DEFAULT_ENV -y yaml
        
        echo -e "\n---\nInstalling jupyter"
        mamba install --prefix $CONDA_DEFAULT_ENV -y jupyter jupyterthemes jupyter_cms jupyter_qtconsole_colorschemes
        echo -e "\n---\nInstalling jupyterlab"
        mamba install --prefix $CONDA_DEFAULT_ENV -y jupyterlab jupyterlab-pygments jupyterlab-server jupyterlab-widgets
        echo -e "\n---\nInstalling numpy"
        mamba install --prefix $CONDA_DEFAULT_ENV -y numpy

        echo -e "\n---\nInstalling matplotlib"

        mamba install --prefix $CONDA_DEFAULT_ENV -y matplotlib

        echo -e "\n---\nInstalling scipy"
        mamba install --prefix $CONDA_DEFAULT_ENV -y scipy
        echo -e "\n--\nInstalling sympy"
        mamba install --prefix $CONDA_DEFAULT_ENV -y sympy
        echo Installing h5py
        mamba install --prefix $CONDA_DEFAULT_ENV -y h5py
        echo Installing pyqtgraph
        mamba install --prefix $CONDA_DEFAULT_ENV -y pyqtgraph
        echo Installing pywavelets
        mamba install --prefix $CONDA_DEFAULT_ENV -y PyWavelets
        echo Installing pandas
        mamba install --prefix $CONDA_DEFAULT_ENV -y pandas
        echo Installing quantities
        mamba install --prefix $CONDA_DEFAULT_ENV -y quantities
        echo Installing python-neo
        mamba install --prefix $CONDA_DEFAULT_ENV -y python-neo
        echo -e "\n---\nInstalling vigra"
        mamba install --prefix $CONDA_DEFAULT_ENV -y -c conda-forge vigra
        echo Installing cmocean
        mamba install --prefix $CONDA_DEFAULT_ENV -y cmocean
        echo Installing confuse
        mamba install --prefix $CONDA_DEFAULT_ENV -y confuse
        echo Installing inflect
        mamba install --prefix $CONDA_DEFAULT_ENV -y inflect
        echo Installing seaborn
        mamba install --prefix $CONDA_DEFAULT_ENV -y seaborn
        echo Installing pingouin
        mamba install --prefix $CONDA_DEFAULT_ENV -y pingouin
        echo Installing qimage2ndarray
        mamba install --prefix $CONDA_DEFAULT_ENV -y qimage2ndarray
        echo Installing pyxdg
        mamba install --prefix $CONDA_DEFAULT_ENV -y pyxdg
        REM OPTIONAL PACKAGES FROM CONDA
        REM mamba install --prefix $CONDA_DEFAULT_ENV -y qdarkstyle
        echo Installing bokeh
        mamba install --prefix $CONDA_DEFAULT_ENV -y bokeh
        echo Installing scikit-image
        mamba install --prefix $CONDA_DEFAULT_ENV -y scikit-image
        echo Installing scikit-learn
        mamba install --prefix $CONDA_DEFAULT_ENV -y scikit-learn
        echo Installing dill
        mamba install --prefix $CONDA_DEFAULT_ENV -y dill
        echo Installing libNeuroML
        mamba install --prefix $CONDA_DEFAULT_ENV -y libNeuroML
        echo Installing matlab kernel
        mamba install --prefix $CONDA_DEFAULT_ENV -y matlab_kernel
        echo Installing octave kernel
        mamba install --prefix $CONDA_DEFAULT_ENV -y octave_kernel
        echo Installing PyInstaller
        mamba install --prefix $CONDA_DEFAULT_ENV -y pyinstaller
        echo -e "\n---\n Installing additional PyPI packages"
        pip install -r ${installscriptdir}/pip_requirements_mamba.txt

    fi
}

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
echo -e "\nCreating .scipyenrc\n"

if [[ -z "$CONDA_DEFAULT_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

dt=`date '+%Y-%m-%d_%H-%M-%s'`

py_exec=${python_exec}
if [ -r ${HOME}/.scipyenrc ] ; then
# make a backup copy of .scipyenrc
shopt -s lastpipe
echo "Copying ${HOME}/.scipyenrc to ${HOME}/.scipyenrc.$dt"
cp ${HOME}/.scipyenrc ${HOME}/.scipyenrc.$dt
fi
cat<<END > ${HOME}/.scipyenrc
condaact() {
__conda_setup="\$('/home/cezar/miniforge3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ \$? -eq 0 ]; then
    eval "\$__conda_setup"
else
    if [ -f "/home/cezar/miniforge3/etc/profile.d/conda.sh" ]; then
        . "/home/cezar/miniforge3/etc/profile.d/conda.sh"
    else
        export PATH="/home/cezar/miniforge3/bin:\$PATH"
    fi
fi
unset __conda_setup
}

scipyact () {
condaact
conda activate ${CONDA_DEFAULT_ENV}
export LD_LIBRARY_PATH=\${CONDA_DEFAULT_ENV}/lib:\$LD_LIBRARY_PATH
echo -e "The Python virtual environment in \${CONDA_DEFAULT_ENV} is now active.\nTo exit this environment call 'conda deactivate'"
}
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
# .scipyenrc not sourced from .bashrc => backup .bashrc, then append a line to
# source .scipyenrc in there
echo "Copying ${HOME}/.bashrc to ${HOME}/.bashrc.$dt"
cp ${HOME}/.bashrc ${HOME}/.bashrc.$dt
echo "source ${HOME}/.scipyenrc" >> ${HOME}/.bashrc
echo ".bashrc has been modified in ${HOME}"
echo "Sourcing ${HOME}/.bashrc"
source ${HOME}/.bashrc
fi
shopt -u lastpipe
fi
}

function make_launch_script () 
{
if [[ `id -u` -eq 0 ]] ; then
    target_dir=/usr/local/bin
else
    target_dir=${HOME}/bin
fi
    
mkdir -p ${target_dir}
if [ -r ${target_dir}/scipyen ] ; then
    dt=`date '+%Y-%m-%d_%H-%M-%s'`
    mv ${target_dir}/scipyen ${target_dir}/scipyen.$dt
fi
shopt -s lastpipe

# if [[ `id -u` -eq 0 ]] ; then
cat <<END > ${target_dir}/scipyen 
#! /bin/sh
# if [ -z \${CONDA_DEFAULT_ENV} ]; then
source \$HOME/.scipyenrc
condaact
conda activate ${CONDA_DEFAULT_ENV}
# source ${virtual_env}/bin/activate
# fi
git -C $scipyendir rev-parse 2>/dev/null;
if [[ \$? -eq 0 ]]; then
branch=\`git -C ${scipyendir} branch --show-current\`
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'
echo -e "${RED}WARNING:${NC} Running ${GREEN}\${branch}${NC} branch of local scipyen git repository in ${BLUE}$scipyendir${NC} with status:"
git -C $scipyendir status --short --branch
fi
echo -e "\nUsing Python environment in ${CONDA_DEFAULT_ENV}\n"
if [ -z \$BROWSER ]; then
if [ -a \$CONDA_DEFAULT_ENV/bin/browser ]; then
source \$CONDA_DEFAULT_ENV/bin/browser
fi
fi
export LD_LIBRARY_PATH=${CONDA_DEFAULT_ENV}/lib:\${LD_LIBRARY_PATH}
# export LD_LIBRARY_PATH=${CONDA_DEFAULT_ENV}/lib:${CONDA_DEFAULT_ENV}/lib64:\${LD_LIBRARY_PATH}
export OUTDATED_IGNORE=1
a=\`which xrdb\` # do we have xrdb to read the X11 resources? (on Unix almost surely yes)
if [ \$0 == 0 ] ; then
if [ -r $scipyensrcdir/neuron_python/app-defaults/nrniv ] ; then
xrdb -merge $scipyensrcdir/neuron_python/app-defaults/nrniv
fi
fi
${python_executable} -Xfrozen_modules=off ${scipyensrcdir}/scipyen.py
END
shopt -u lastpipe
chmod +x ${target_dir}/scipyen 
echo -e "Scipyen startup script created in ${target_dir} \n"
# else
# ln -s ${scipyensrcdir}/scipyen ${target_dir}/scipyen
# echo -e "Link to scipyen startup script created in ${target_dir} \n"
# fi    
#     mkdir -p ${HOME}/bin
#     if [ -r ${HOME}/bin/scipyen ] ; then
#         dt=`date '+%Y-%m-%d_%H-%M-%s'`
#         mv ${HOME}/bin/scipyen ${HOME}/bin/scipyen.$dt
#     fi
#     ln -s ${scipyensrcdir}/scipyen ${HOME}/bin/scipyen
#     
#     echo -e "Link to scipyen startup script created in ${HOME}/bin \n"
}


function make_desktop_entry ()
{
if [ ! -r ${CONDA_DEFAULT_ENV}/.desktopdone ] || [[ $reinstall_desktop -gt 0 ]] ; then
if [[ `id -u` -eq 0 ]] ; then
target_dir=/usr/local/bin
else
target_dir=${HOME}/bin
fi
tmpfiledir=$(mktemp -d)
# tmpfile=${tmpfiledir}/cezartigaret-Scipyen.desktop
tmpfile=${tmpfiledir}/Scipyen.desktop
script=${target_dir}/scipyen
echo -e "Script to execute: ${script}"
cat<<END > ${tmpfile}
[Desktop Entry]
Type=Application
Name[en_GB]=Scipyen
Name=Scipyen
Comment[en_GB]=Scientific Python Environment for Neurophysiology
Comment=Scientific Python Environment for Neurophysiology
GenericName[en_GB]=Scientific Python Environment for Neurophysiology
GenericName=Scientific Python Environment for Neurophysiology
Icon=pythonbackend
Categories=Science;Utilities;
Exec=${script}
MimeType=
Path=
StartupNotify=true
Terminal=true
TerminalOptions=\s
X-DBUS-ServiceName=
X-DBUS-StartupType=
X-KDE-SubstituteUID=false
X-KDE-Username=
END
xdg-desktop-menu install --novendor ${tmpfile}
if [[ $? -ne 0 ]] ; then
echo -e "Installation of Scipyen application file failed\n"
exit 1
fi
# NOTE: 2023-05-02 15:25:50 this below installs an Icon on the desktop
xdg-desktop-icon install --novendor ${tmpfile}
if [[ $? -ne 0 ]] ; then
echo -e "Installation of Scipyen Desktop file failed\n"
exit 1
fi
echo "Scipyen Desktop file has been installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${CONDA_DEFAULT_ENV}/.desktopdone
echo -e "Scipyen Desktop file has been installed \n"
fi
}


#### NOTE: 2024-02-29 09:01:40 Execution starts here ###

echo -e "WARNING: You should have mamba's miniforge installed"
echo -e "WARNING this script is NOT customized; edit before running"
echo -e "\tthen run from the root scipyen directory (i.e. root of the git tree)"

SECONDS=0
get_pyver
condaact

virtual_env_pfx="scipyenv_mf" #.$pyver"
install_dir=${HOME}
realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
docdir=${scipyendir}/doc
installscriptdir=${docdir}/install


scipyensrcdir=${scipyendir}/src/scipyen
using_python=""
install_neuron=0
use_pypi_neuron=1
use_core_neuron=0
install_fenicsx=0
njobs=4
reinstall_pyqt5=0
reinstall_vigra=0
reinstall_neuron=0
reinstall_fenicsx=0
reinstall_pips=0
reinstall_desktop=0
refresh_git_repos=0
make_dist=0

for i in "$@" ; do
    case $i in
        --python)
        using_python="${i#*=}"
        shift
        ;;
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
        --with_fenicsx)
        install_fenicsx=1
        shift
        ;;
        --install_dir=*)
        install_dir="${i#*=}"
        shift
        ;;
        --refresh_repos)
        refresh_git_repos=1
        shift
        ;;
        --jobs=*)
        njobs="${i#*=}"
        shift
        ;;
        --environment=*)
        virtual_env_pfx="${i#*=}"
        shift
        ;;
        --reinstall=*)
        reinstall="${i#*=}"
        shift
        case $reinstall in
            pyqt5)
            reinstall_pyqt5=1
            ;;
            PyQt5)
            reinstall_pyqt5=1
            ;;
            vigra)
            reinstall_vigra=1
            ;;
            VIGRA)
            reinstall_vigra=1
            ;;
            Vigra)
            reinstall_vigra=1
            ;;
            neuron)
            reinstall_neuron=1
            ;;    
            Neuron)
            reinstall_neuron=1
            ;;    
            NEURON)
            reinstall_neuron=1
            ;;    
            fenicsx)
            reinstall_fenicsx=1
            ;;
            pips)
            reinstall_pips=1
            ;;
            desktopentry)
            reinstall_desktop=1
            ;;
            *)
            ;;
        esac
        ;;
        --about)
        showinstalldoc
        exit 0
        shift
        ;;
        --dist)
        make_dist=1
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
        exit 0
        ;;
        *)
        ;;
    esac
done

install_dir=`realpath ${install_dir}`

if [ -d ${install_dir} ]; then
    if ! [ -w ${install_dir} ]; then
        echo -e "You do not have permission to install in ${install_dir}.\nPlease choose a location to create the virtual environment where you have permissions"
        exit 1
    fi
    
else
    updir=`dirname ${install_dir}`
    
    if ! [ -w ${updir} ]; then
        echo -e "You do not have permission to create ${install_dir}"
        exit 1
    fi
    
    mkdir ${install_dir}
    
fi
echo -e "Will install in ${install_dir}" 

virtual_env=${install_dir}/${virtual_env_pfx}
makevirtenv
echo -e "Using conda virtual environment "$CONDA_DEFAULT_ENV
virtual_env=$CONDA_DEFAULT_ENV
python_exec=$CONDA_DEFAULT_ENV/bin/"python${major}"


# if ! [ -v $CONDA_DEFAULT_ENV ] ; then
#     echo -e "Cannot use conda environment in "${virtual_env}
#     exit 1
# else
#     virtual_env=$CONDA_DEFAULT_ENV
#     python_exec=$CONDA_DEFAULT_ENV/bin/"python${major}"
# fi

if [[ `id -u ` -eq 0 ]] ; then
#     echo "running as root"
    python_executable=`which ${python_exec}`;
else
    python_executable=${python_exec}
fi

# makes a virtual environment and activates it
# if ! [ -v $CONDA_DEFAULT_ENV ] ; then
#     # NOTE: 2023-06-25 20:57:31 
#     # these two MUST be run
#     makevirtenv
# else
#     virtual_env=$CONDA_DEFAULT_ENV
# fi

echo -e "virtual_env is ${virtual_env}"
echo -e "python executable: ${python_executable}"



if [[ ( -n "$CONDA_DEFAULT_ENV" ) && ( -d "$CONDA_DEFAULT_ENV" ) ]] ; then
    echo -e "Checking for, or making 'src' directory inside $CONDA_DEFAULT_ENV ...\n"
    mkdir -p "$CONDA_DEFAULT_ENV/src" && cd "$CONDA_DEFAULT_ENV/src"
    
#     # install pip requirements NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
#     installpipreqs
#     
#     if [[ $? -ne 0 ]] ; then
#         echo -e "Could not install pip requirements; check the console for messages. Goodbye!\n"
#         exit 1
#     fi
    
#     build Pyqt5 NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    install_python_packages
    if [[ $? -eq 0 ]] ; then
    echo -e "Python packages installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${CONDA_DEFAULT_ENV}/.packagesdone
    else
    echo -e "Could not install all required packages. Bailing out...\n"
    exit 1
    fi
    
#     dopyqt5
    
    # build vigra NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
#     dovigra
    
    # build neuron NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    if [ $install_neuron -ne 0 ] ; then
        doneuron
    fi
    
    if  [ $install_fenicsx -ne 0 ] ; then
        dofenicsx
    fi
    
    # make scripts
    make_scipyenrc
#     
#     if [[ `id -u` -ne 0 ]] ; then
#         # only update bashrc for regular users
#         update_bashrc
#     fi
    
    make_launch_script
    
    make_desktop_entry
    
fi

t=$SECONDS

days=$(( t/86400 ))
t=$(( t%(24*3600) ))
hours=$(( t/3600 ))
t=$(( t%3600 ))
minutes=$(( t/60 ))
t=$(( t % 60))
seconds=$(( t ))

echo "Execution time was $days days, $hours hours, $minutes minutes and $seconds seconds"


# conda init
# mamba create -y --prefix $HOME/scipyenv_mf python=3.11
# conda activate $HOME/scipyenv_mf
# mamba activate $HOME/scipyenv_mf


# powershell -ExecutionPolicy Bypass -File %mydir%\make_link.ps1 %mydir%
# echo Scipyen can now be launched from the desktop icon


# :eof
# rem  endlocal

    
