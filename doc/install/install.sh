#!/bin/bash

# Installation script stub for scipyen 23c19
#
# Author: Cezar M. Tigaret <cezar.tigaret@gmail.com>
#
# Distributed under GNU GPL License v.2
#

function showinstalldoc () 
{
    glowexec=`which glow`
    if [ -n $glowexec ] ; then
        glow -p $installscriptdir/Install.md
    else
        cat $installscriptdir/Install.md
    fi
}
function show_help ()
{
    echo -e "\n***                                                         ***"
    echo -e "* Virtual Python environment installation script for Scipyen. *"
    echo -e "***                                                         ***\n"
    echo -e "(C) 2023 Cezar M. Tigaret "
    echo -e "<cezar tigaret at gmail com> , <tigaretc at cardiff ac uk>"
    echo -e "\nInstructions:"
    echo -e "============\n"
    echo -e "Run 'instal.sh' without options for a fully automated installation"
    echo -e "using built-in defaults.\n"
    echo -e "Options:"
    echo -e "=======\n"
    echo -e "--install_dir=DIR\t => specifies a directory where the virtual "
    echo -e "\t\t\tenvironment will be created (default is ${HOME})\n"
    echo -e "--environment=<name>\t => specifies a custom name for the virtual environment"
    echo -e "\t\t\t(default is ${virtual_env})\n"
    echo -e "--with_neuron\t\t => when passed, will install neuron python"
    echo -e "\t\t\tfrom PyPI. See also:\n"
    echo -e "\t\t\thttps://neuron.yale.edu/neuron/\n\t\t\thttps://github.com/neuronsimulator/nrn\n\t\t\thttps://pypi.org/project/NEURON/\n"
    echo -e "--build_neuron\t\t => when passed, will build neuron python locally.\n"
    echo -e "--with_coreneuron\t => when passed, local neuron build will use coreneuron."
    echo -e "\t\t\t(by default coreneuron is not used).\n"
    echo -e "\t\t\tFor details about coreneuron see:"
    echo -e "\t\t\thttps://github.com/BlueBrain/CoreNeuron\n"
    echo -e "\t\t\tNOTE: Only used when '--build_neuron' is passed .\n"
    echo -e "--jobs=N\t\t\t => enables parallel tasks during building;"
    echo -e "\t\t\t used when building PyQt5 and NEURON; default is 4"
    echo -e "--reinstall=NAME\t\t\t forces re-installation/re-building of NAME"
    echo -e "\t\t\tNAME can be pips, pyqt5, vigra, or neuron; can be passed more than once."
    echo -e "--about\t\t\t Displays Install.md at the console (requires the program 'glow')"
    echo -e "-h | -? | --help \t => show this help message and quit\n"
    
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
}

function findcmake ()
{
    cmake_binary=`which cmake`
    if [ -z "$cmake_binary" ] ; then
        echo -e "Cannot build vigra without cmake. Goodbye!\n"
        exit 1
    fi
    
}

function upgrade_virtualenv ()
{
    havevenv=`python3 -m virtualenv --version`
    if [ -z $havenev ] ; then
        echo -e "Installing virtualenv locally...\n"
        pip install --user virtualenv
    else
        echo -e "Upgrading virtualenv locally...\n"
        pip install --user --upgrade virtualenv
    fi
}

function makevirtenv ()
{
    #NOTE: Generates a virtual enviornment
    # check if the environment directory exists (and that it does belong to a
    # virtual python environment - that is, it contains a file named "pyenv.cfg"
    # containing "virtualenv" in it, has a "bin" directory with "activate" script,
    # which can be sourced to generate VIRTUAL_ENV variable)
    if [ -d $ve_path/$virtual_env ] ; then
        if [ -a $ve_path/$virtual_env/pyvenv.cfg ] ; then
            aa=`cat $ve_path/$virtual_env/pyvenv.cfg | grep "virtualenv"`
            if [ -n "$aa" ] ; then
                if [ ! -d $ve_path/$virtual_env/bin ] ; then
                    echo -e "$ve_path/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                    exit 1
                fi
                if [ ! -r $ve_path/$virtual_env/bin ] ; then
                    echo -e "$ve_path/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                    exit 1
                fi
                source $ve_path/$virtual_env/bin/activate
                if [[ -z ${VIRTUAL_ENV} ]]; then
                    echo -r "Cannot activate a virtual environment from  $ve_path/$virtual_env . Goodbye!\n"
                    exit 1
                fi
            else
                echo -e "$ve_path/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                exit 1
            fi 
        fi
    else
        python3 -m virtualenv $virtual_env && source $ve_path/$virtual_env/bin/activate
    fi
    
}

function installpipreqs ()
{
    # installs pip packaged listed in pip_requirements
    # assumes (and therefore REQUIRES that the virtual environment is active)
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pipdone ] || [[ $reinstall_pips -gt 0 ]] ; then
        # NOTE: since around Jan 2023 sklearn has been deprecated in favour of 
        # scikit-learn, suchn that an error message is issues whenever pip tries
        # to install sklearn.
        # HOWEVER, a LARGE number of packages still list sklearn among their 
        # dependencies, yet pip has no way to check this BEFORE installing them,
        # Until all of them catch up with this, we circumvent the error message
        # by setting up the environment variable below
        # For details please see https://pypi.org/project/sklearn/
        export SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True 
        pip install -r "$installscriptdir"/pip_requirements-experimental-23c21.txt
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Cannot install required packages from PyPI. Bailing out. Goodbye!\n"
            exit 1
        else
            echo "pip packages installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pipdone
            echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
        fi
    fi
}

function dopyqt5 ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pyqt5done ] || [[ $reinstall_pyqt5 -gt 0 ]]; then
        mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src
        
        findqmake
        
        if [ `pwd` != "$VIRTUAL_ENV"/src ]; then
            echo -e "Not inside $VIRTUAL_ENV/src - goodbye\n"
            exit 1
        fi
        
        # NOTE: locate_pyqt5_src.py uses distlib to locate the (latest) source 
        # archive (i.e., the sdist) of PyQt5 - its file name typically ends with
        # .tar.gz
        pyqt5_src_url=`python $installscriptdir/locate_pyqt5_src.py`
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
        mkdir -p ${pyqt5_build_dir}
        
        # NOTE: » ... but run the build process INSIDE the expanded sdist dir
        # is because sip-wheel will get extra options from there :)
        cd ${pyqt5_src_dir}
        
        echo "Generating PyQt5 wheel in "$(pwd)"..."
        
        # NOTE: 2023-03-23 14:03:48 - enable parallel jobs - to change, either:
        # • change the value of the --jobs option (e.g. half the number of 
        # cores in your system seems to be  good choice), or
        # • remove the --jobs option altogether
        if [[ $njobs -gt 0 ]] ; then
            sip-wheel --qmake=${qmake_binary} --confirm-license --jobs $njobs --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
        else
            sip-wheel --qmake=${qmake_binary} --confirm-license --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
        fi
#         sip-wheel --qmake=${qmake_binary} --confirm-license --jobs 8 --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi

        if [[ $? -ne 0 ]] ; then
            echo -e "sip Cannot build a PyQt5 wheel. Bailing out. Goodbye!\n"
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
            python -m pip install ${wheel_file}
            
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot install the PyQt5 wheel; check console output. Goodbye!\n"
                exit 1
            else
                echo "PyQt5 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pyqt5done
                echo -e "\n\n=====================\n# Pyqt5 installed!\n=====================\n\n"
            fi
        fi
    fi
}

function dovigra ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.vigradone ] || [[ $reinstall_vigra -gt 0 ]]; then
        cd $VIRTUAL_ENV/src
        
        findcmake
        
        git clone https://github.com/ukoethe/vigra.git && mkdir -p vigra-build && cd vigra-build
        
        $cmake_binary -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DWITH_BOOST_GRAPH=1 -DWITH_BOOST_THREAD=1 -DWITH_HDF5=1 -DWITH_OPENEXR=1 -DWITH_VIGRANUMPY=1 -DLIB_SUFFIX=64 ../vigra
        
        make && make install
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Cannot build vigra; check console output. Bailing out. Goodbye!\n"
            exit 1
        else
            echo "VIGRA installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.vigradone
            echo -e "\n\n=====================\n# Building vigra DONE!\n=====================\n\n"
        fi
    fi
    
    
}

function doneuron ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    echo "Reinstall neuron: $reinstall_neuron"
    echo "Using PyPI: $use_pypi_neuron"
    echo "Using coreneuron: $use_core_neuron"
    if [ ! -r ${VIRTUAL_ENV}/.nrndone ] || [[ $reinstall_neuron -gt 0 ]]; then
        if [ $use_pypi_neuron -ne 0 ] ; then
            python3 -m pip install neuron
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot install NEURON; check console output. Bailing out. Goodbye!\n"
                exit 1
            else
                echo "NEURON installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.nrndone 
                echo -e "\n\n=====================\n# Building NEURON DONE!\n=====================\n\n"
            fi
        else
            cd $VIRTUAL_ENV/src
            
            findcmake
            
            if [ ! -d ${VIRTUAL_ENV}/src/nrn ] ; then
                echo -e "Cloning nrn repository"
                git clone https://github.com/neuronsimulator/nrn
            fi
            
            mkdir -p ${VIRTUAL_ENV}/src/nrn-build && cd ${VIRTUAL_ENV}/src/nrn-build
            
            if [ $use_core_neuron -ne 0 ] ; then
                echo -e "Configuring local neuron build with coreneuron ..."
                $cmake_binary -DPYTHON_EXECUTABLE=$(which python3) -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=1 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_CORENEURON=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_REL_PATH=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABL_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 -DNRN_ENABLE_DOCS=ON ../nrn
            else
                echo -e "Configuring local neuron build ..."
                $cmake_binary -DPYTHON_EXECUTABLE=$(which python3) -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=1 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_REL_PATH=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABL_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 -DNRN_ENABLE_DOCS=ON ../nrn
            fi
            
            echo -e "Building neuron locally and installing ..."
            if [[ $njobs -gt 0 ]] ; then
                $cmake_binary --build . --parallel $njobs --target install
            else
                $cmake_binary --build . --target install
            fi
            
            
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot build NEURON; check console output. Bailing out. Goodbye!\n"
                exit 1
            fi
            
#             echo -e "Installing nrnpython"
            # check where nrnpython is installed:
            lib_sites=`python -c "import sys, os; venv=os.getenv(\"VIRTUAL_ENV\"); print([p for p in sys.path if p.startswith(venv) and \"lib\" in p][0])"`
            lib64_sites=`python -c "import sys, os; venv=os.getenv(\"VIRTUAL_ENV\"); print([p for p in sys.path if p.startswith(venv) and \"lib64\" in p][0])"`
  
            # try to see if neuron is in lib/site-packages/python3.10
            if [ ! -d ${lib_sites}/neuron ] ; then
                # not found => try to see if it is in lib64_sites
                if [ ! -d{lib64_sites}/neuron ] ; then
                    # not found there either;
                    # try to see if it is in lib/python
                    if [ -d ${VIRTUAL_ENV}/lib/python/neuron ] ; then
                        ln -s ${VIRTUAL_ENV}/lib/python/neuron -d ${lib_sites}/neuron
                    elif [ -d ${VIRTUAL_ENV}/lib/python/site-packages/neuron ] ; then
                        ln -s ${VIRTUAL_ENV}/lib/python/site-packages/neuron -d ${lib_sites}/neuron
                    elif [ -d ${VIRTUAL_ENV}/lib64/python/neuron ] ; then
                        ln -s ${VIRTUAL_ENV}/lib64/python/neuron -d ${lib64_sites}/neuron
                    elif [ -d ${VIRTUAL_ENV}/lib64/python/site-packages/neuron ] ; then
                        ln -s ${VIRTUAL_ENV}/lib64/python/site-packages/neuron -d ${lib64_sites}/neuron
                    else
                        echo -e "Could not find the installed neuron python module; check your installation"
                    fi
                fi
            fi
#             cd ${VIRTUAL_ENV}/src/nrn-build/src/nrnpython && python3 setup.py install
            
#             python3 -m pip install -r ${VIRTUAL_ENV}/src/nrn/docs/docs_requirements.txt
            
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot build NEURON; check console output. Bailing out. Goodbye!\n"
                exit 1
            fi
            echo "NEURON installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.nrndone 
            echo -e "\n\n=====================\n# Building NEURON DONE!\n=====================\n\n"
        fi
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
dt=`date '+%Y-%m-%d_%H-%M-%s'`
if [ -r ${HOME}/.scipyenrc ] ; then
# make a backup copy of .scipyenrc
shopt -s lastpipe
echo "Copying ${HOME}/.scipyenrc to ${HOME}/.scipyenrc.$dt"
cp ${HOME}/.scipyenrc ${HOME}/.scipyenrc.$dt
fi
cat<<END > ${HOME}/.scipyenrc
scipyact () {
source ${VIRTUAL_ENV}/bin/activate
}
export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:$LD_LIBRARY_PATH
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
# .scipyenrc not sourced from .bashrc => backup .bashrc then append a line to
# source .scipyenrc in there
echo "Copying ${HOME}/.bashrc to ${HOME}/.bashrc.$dt"
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

function linkscripts () 
{
    mkdir -p ${HOME}/bin
    if [ -r ${HOME}/bin/scipyen ] ; then
        dt=`date '+%Y-%m-%d_%H-%M-%s'`
        cp ${HOME}/bin/scipyen ${HOME}/bin/scipyen.$dt
    fi
    ln -s ${scipyendir}/scipyen ${HOME}/bin/scipyen
}

#### Execution starts here ###
# start_time=`date +%s`
SECONDS=0
get_pyver

# upgrade_virtualenv="N"
# use_preexisting="Y"
# TODO: switch to a relevant name e.g. scipyenv
# virtual_env="testenv"
virtual_env="scipyenv.$pyver"
ve_path=$HOME
# pyqt5_version=5.15.9
# pyqt5_repo=https://files.pythonhosted.org/packages/source/P/PyQt5/
# pyqt5_src=PyQt5-$pyqt5_version.tar.gz
# NOTE: figure out is /where is dbus-python.h
# pcgconf (pkg-config) must be installed
# pkgconf --liat-all  | grep dbus => list of dbus-* packages including dbus-python
# qdbus_python_dir=


realscript=`realpath $0`
installscriptdir=`dirname "$realscript"`
docdir=`dirname "$installscriptdir"`
scipyendir=`dirname "$docdir"`
install_neuron=0
use_pypi_neuron=1
use_core_neuron=0
njobs=4
reinstall_pyqt5=0
reinstall_vigra=0
reinstall_neuron=0
reinstall_pips=0

for i in "$@" ; do
    case $i in
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
        --install_dir=*)
        ve_path="${i#*=}"
        shift
        ;;
        --jobs=*)
        njobs="${i#*=}"
        shift
        ;;
        --environment=*)
        virtual_env="${i#*=}"
        shift
        ;;
        --reinstall=*)
        reinstall="${i#*=}"
        shift
        case $reinstall in
            pyqt5)
            reinstall_pyqt5=1
            ;;
            vigra)
            reinstall_vigra=1
            ;;
            neuron)
            reinstall_neuron=1
            ;;    
            pips)
            reinstall_pips=1
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

# makes a virtual environment and activates it
upgrade_virtualenv && makevirtenv

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
#     echo -e "Creating 'src' directory inside $VIRTUAL_ENV ...\n"
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
    if [ $install_neuron -ne 0 ] ; then
        doneuron
    fi
    
    # make scripts
    #make_scipyenrc && update_bashrc && linkscripts
    
fi

# stop_time=`date +%s`
# echo Execution time was `expr $stop_time - $start_time` seconds.

t=$SECONDS

days=$(( t/86400 ))
hours=$(( t/3600 - 24*days ))
minutes=$(( t/60 - 1440*days ))
seconds=$(( t - 85400*days))

echo "Execution time was $days days, $hours hours, $minutes minutes and $seconds seconds"




