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
    echo -e "Run 'sh instal.sh' without options for a fully automated installation, using built-in defaults.\n"
    echo -e "Options:"
    echo -e "========\n"
    echo -e "--install_dir=DIR\tSpecify where the virtual environment will be created (default is ${HOME})\n"
    echo -e "--environment=NAME\tCustom name for the virtual environment (default is ${virtual_env})\n"
    echo -e "--with_neuron\t\tInstall binary neuron python distribution from PyPI\n"
    echo -e "--build_neuron\t\tBuild neuron python locally\n"
    echo -e "--with_coreneuron\then '--build_neuron' is passed, build local neuron with coreneuron; by default coreneuron is not used.\n"
    echo -e "--refresh_repos\t When '--refresh_repos' is passed, local repository clones will be refreshed before rebuilding\n"
    echo -e "\tNOTE: This applies to vigra and to local neuron build only\n"
    echo -e "--jobs=N\t\tNumber of parallel tasks during building PyQt5 and neuron; default is 4; set to 0 to disable parallel build\n"
    echo -e "--reinstall=NAME\t\t\tRe-install/re-building NAME, where NAME is one of pips, pyqt5, vigra, neuron, or desktopentry; can be passed more than once\n"
    echo -e "--about\t\t\tDisplay Install.md at the console (requires the program 'glow')\n"
    echo -e "-h | -? | --help \tShow this help message and quit\n"
    echo -e "\nFor details, execute install.sh --about\n"
    echo -e "\n"
    echo -e "When run with the virtual Pythob environment already activated,\n"
    echo -e "the script will use the current virtual environment to perform \n"
    echo -e "(re)installations. WARNING: Make sure you activate the appropriate\n"
    echo -e "Python environment for this !\n"
   
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

function upgrade_virtualenv ()
{
    havevenv=`${python_executable} -m virtualenv --version`
    echo "havevenv = ${havevenv}"
    if [ -z $"havevenv" ] ; then
        echo -e "Scipyen requires virtualenv.\n"
        if [[ `id -u ` -eq 0 ]] ; then
            echo -e "To install virtualenv please use the software manager of your distribution,"
            echo -e "or run this script as regular user (which will install virtualenv locally).\n"
            echo -e "\nQuitting, for now..."
            exit 1
        fi
        echo -e "Installing virtualenv locally...\n"
        ${python_executable} -m pip install --user virtualenv
#         python3 -m pip install --user virtualenv
    else
        if [[ `id -u ` -eq 0 ]] ; then
            echo -e "Skipping the upgrade of virtualenv as root. Please use the software manager of your distribution to upgrade if needed.\n"
        else
            echo -e "Upgrading virtualenv locally...\n"
            ${python_executable} -m pip install --user --upgrade virtualenv
        fi
    fi
}

function makevirtenv ()
{
    echo -e "Trying to create/use virtual environment ${virtual_env} in ${install_dir} using ${using_python}\n"
    #NOTE: Generates a virtual environment
    # check if the environment directory exists (and that it does belong to a
    # virtual python environment - that is, it contains a file named "pyenv.cfg"
    # containing "virtualenv" in it, has a "bin" directory with "activate" script,
    # which can be sourced to generate VIRTUAL_ENV variable)
    if [ -d $install_dir/$virtual_env ] ; then
        if [ -a $install_dir/$virtual_env/pyvenv.cfg ] ; then
            aa=`cat $install_dir/$virtual_env/pyvenv.cfg | grep "virtualenv"`
            if [ -n "$aa" ] ; then
                if [ ! -d $install_dir/$virtual_env/bin ] ; then
                    echo -e "$install_dir/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                    exit 1
                fi
                if [ ! -r $install_dir/$virtual_env/bin ] ; then
                    echo -e "$install_dir/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                    exit 1
                fi
                
                echo -e "Virtual environment found; activating it...\n"
                
                source $install_dir/$virtual_env/bin/activate
                
                if [[ -z ${VIRTUAL_ENV} ]]; then
                    echo -r "Cannot activate a virtual environment from  $install_dir/$virtual_env . Goodbye!\n"
                    exit 1
                fi
                
                python_executable=`which python3`
                
                echo -e "Virtual environment activated and will use ${python_executable}\n"
                
                
                
            else
                echo -e "$install_dir/$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                exit 1
            fi 
        fi
    else
#         ${python_executable} -m virtualenv --python ${python_executable} $install_dir/$virtual_env && source $install_dir/$virtual_env/bin/activate
        ${python_executable} -m virtualenv --python ${python_executable} $install_dir/$virtual_env
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Could NOT create a virtual environment at ${install_dir}/${virtual_env}. Bailing out...\n"
            exit 1
        fi

        echo -e "Virtual environment created at ${install_dir}/${virtual_env}\n"
        echo -e "Activating the virtual environment\n"
        
        source $install_dir/$virtual_env/bin/activate
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Could NOT activate the virtual environment at ${install_dir}/${virtual_env}. Bailing out...\n"
            exit 1
        fi
        
        python_executable=`which python3`
        
        echo -e "Virtual environment at ${VIRTUAL_ENV} activated; python executable is ${python_executable}\n"
        
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
        #        if [[ $for_msys -eq 1 ]] ; then
        #            python3 -m pip install -r "$installscriptdir"/pip_requirements_msys.txt
        #        else
        #            python3 -m pip install -r "$installscriptdir"/pip_requirements.txt
        #        fi
        #NOTE: commented out previous to prevent a bug with installation
        
        
        # NOTE: 2023-06-25 10:56:34 
        # when we are root, make sure to use the virtual environment's python 
        # executable here
#         if [[ `id -u` -eq 0 ]] ; then
#             py_exec="$VIRTUAL_ENV/bin/${python_exec}"
#         else
#             py_exec=${python_exec}
#         fi
        
        echo -e "Using ${python_executable} as `whoami` to install PyPI packages\n"
        
#         ${python_executable} -m pip install dummy_test
        ${python_executable} -m pip install -r "$installscriptdir"/pip_requirements.txt
#         python3 -m pip install -r "$installscriptdir"/pip_requirements.txt
        
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
        
        # NOTE: 2023-06-25 10:56:34 
        # when we are root, make sure to use the virtual environment's python 
        # executable here
        if [[ `id -u` -eq 0 ]] ; then
            py_exec="$VIRTUAL_ENV/bin/${python_exec}"
            sip_wheel_exec="$VIRTUAL_ENV/bin/sip-wheel"
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
        # cores in your system seems to be  good choice), or
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
        mkdir -p ${VIRTUAL_ENV}/src && cd $VIRTUAL_ENV/src
        
        findcmake
        
        vigra_src=$VIRTUAL_ENV/src/vigra
        vigra_build=$VIRTUAL_ENV/src/vigra-build
        
        if [ ! -r ${vigra_src} ] ; then
            echo -e "Cloning vigra git repository...\n"
            git clone https://github.com/ukoethe/vigra.git
            if [[ $? -ne 0 ]] ; then
                echo -e "Cannot clone vigra git repository. Goodbye!\n"
                exit 1
            fi
            
        else
            # refresh the gir repo...
            if [[ $refresh_git_repos -gt 0 ]] ; then
                echo -e "Refreshing vigra git repository...\n"
                cd ${vigra_src}
                git pull
                cd ..
            fi
        fi
          
        if [ -d ${vigra_build} ] ; then
            rm -fr ${vigra_build}
        fi
        
        echo -e "Creating vigra build tree outside the source tree\n"
        mkdir -p vigra-build && cd vigra-build
        
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

function make_desktop_entry ()
{
if [ ! -r ${VIRTUAL_ENV}/.desktopdone ] || [[ $reinstall_desktop -gt 0 ]] ; then
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
echo "Scipyen Desktop file has been installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.desktopdone
echo -e "Scipyen Desktop file has been installed \n"
fi
}

function doneuron ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    if [[ `id -u` -eq 0 ]] ; then
        py_exec="$VIRTUAL_ENV/bin/${python_exec}"
        sip_wheel_exec="$VIRTUAL_ENV/bin/sip-wheel"
    else
        py_exec=${python_exec}
        sip_wheel_exec=sip-wheel
    fi
    
#     echo "Reinstall neuron: $reinstall_neuron"
#     echo "Using PyPI: $use_pypi_neuron"
#     echo "Using coreneuron: $use_core_neuron"
# NOTE: 2023-03-24 00:30:50 pip install neuron =>
#     /home/cezar/scipyenv.3.10.10/bin/idraw
#     /home/cezar/scipyenv.3.10.10/bin/mkthreadsafe
#     /home/cezar/scipyenv.3.10.10/bin/modlunit
#     /home/cezar/scipyenv.3.10.10/bin/neurondemo
#     /home/cezar/scipyenv.3.10.10/bin/nrngui
#     /home/cezar/scipyenv.3.10.10/bin/nrniv
#     /home/cezar/scipyenv.3.10.10/bin/nrniv-core
#     /home/cezar/scipyenv.3.10.10/bin/nrnivmodl
#     /home/cezar/scipyenv.3.10.10/bin/nrnivmodl-core
#     /home/cezar/scipyenv.3.10.10/bin/nrnpyenv.sh
#     /home/cezar/scipyenv.3.10.10/bin/sortspike
#     /home/cezar/scipyenv.3.10.10/lib64/python3.10/site-packages/NEURON-8.2.2.dist-info/*
#     /home/cezar/scipyenv.3.10.10/lib64/python3.10/site-packages/NEURON.libs/libcoreneuron-f6d04d2a.so
#     /home/cezar/scipyenv.3.10.10/lib64/python3.10/site-packages/NEURON.libs/libnrniv-e0a0fc78.so
#     /home/cezar/scipyenv.3.10.10/lib64/python3.10/site-packages/neuron/*
    if [ ! -r ${VIRTUAL_ENV}/.nrndone ] || [[ $reinstall_neuron -gt 0 ]]; then
        if [ $use_pypi_neuron -ne 0 ] ; then
#             python3 -m pip install neuron
            ${py_exec} -m pip install neuron
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
            
            nrn_build=${VIRTUAL_ENV}/src/nrn-build
            
            if [ ! -d ${VIRTUAL_ENV}/src/nrn ] ; then
                echo -e "Cloning nrn repository"
                git clone https://github.com/neuronsimulator/nrn
            else
                if [[ $refresh_git_repos -gt 0 ]] ; then
                    echo -e "Refreshing nrn repository"
                    cd ${VIRTUAL_ENV}/src/nrn
                    git pull
                    cd ..
                fi
            fi
            
            mkdir -p ${VIRTUAL_ENV}/src/nrn-build && cd ${VIRTUAL_ENV}/src/nrn-build
            
            if [ $use_core_neuron -ne 0 ] ; then
                echo -e "Configuring local neuron build with coreneuron ..."
                $cmake_binary -DPYTHON_EXECUTABLE=${py_exec} -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=0 -DCMAKE_SKIP_RPATH=0 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=0 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_CORENEURON=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABLE_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 -DNRN_ENABLE_DOCS=ON ../nrn
#                 $cmake_binary -DPYTHON_EXECUTABLE=$(which python3) -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=0 -DCMAKE_SKIP_RPATH=0 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=0 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_CORENEURON=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABLE_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 -DNRN_ENABLE_DOCS=ON ../nrn
            else
                echo -e "Configuring local neuron build ..."
                $cmake_binary -DPYTHON_EXECUTABLE=${py_exec} -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=0 -DCMAKE_SKIP_RPATH=0 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=0 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABLE_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 -DNRN_ENABLE_DOCS=ON ../nrn
#                 $cmake_binary -DPYTHON_EXECUTABLE=$(which python3) -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_LIBEXECDIR=libexec -DCMAKE_SKIP_INSTALL_RPATH=0 -DCMAKE_SKIP_RPATH=0 -DIV_ENABLE_SHARED=1 -DNRN_AVOID_ABSOLUTE_PATHS=0 -DNRN_ENABLE_MPI=1 -DNRN_ENABLE_INTERVIEWS=1 -DNRN_ENABLE_PYTHON_DYNAMIC=1 -DNRN_ENABLE_RX3D=1 -DNRN_ENABLE_SHARED=1 -DNRN_ENABLE_THREADS=1 -DNRN_ENABLE_MECH_DLL_STYLE=1 -DLIB_INSTALL_DIR=$VIRTUAL_ENV/lib64 -DLIB_SUFFIX=64 -DMOD2C_ENABLE_LEGACY_UNITS=0 -DNRN_ENABLE_DOCS=ON ../nrn
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
            lib_sites=`${py_exec} -c "import sys, os; venv=os.getenv(\"VIRTUAL_ENV\"); print([p for p in sys.path if p.startswith(venv) and \"lib\" in p][0])"`
            lib64_sites=`${py_exec} -c "import sys, os; venv=os.getenv(\"VIRTUAL_ENV\"); print([p for p in sys.path if p.startswith(venv) and \"lib64\" in p][0])"`
#             lib_sites=`python -c "import sys, os; venv=os.getenv(\"VIRTUAL_ENV\"); print([p for p in sys.path if p.startswith(venv) and \"lib\" in p][0])"`
#             lib64_sites=`python -c "import sys, os; venv=os.getenv(\"VIRTUAL_ENV\"); print([p for p in sys.path if p.startswith(venv) and \"lib64\" in p][0])"`
  
            # try to see if neuron is in lib/site-packages/python3.10
            if [ ! -d ${lib_sites}/neuron ] ; then
                # not found => try to see if it is in lib64_sites
                if [ ! -d ${lib64_sites}/neuron ] ; then
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
# When the installer script is run as regular user, it will create 
# ${HOME}/.scipeynrc which allows activation of the virtual python environment
# used to run Scipyen.
#
#
# When the script is run as root, it will create a scipyact script in the 
# /usr/local/bin (which should be on PATH by default on linux)
# TODO/FIXME check for other UN*X platforms (e.g. BSD family)
# The ${HOME}/.scipyenrc defines a single bash function - 'scipyact' - which 
# when called, activates the virtual environment and optionally sets up a few 
# needed environment variables (see below in the code)
#
# The .scipyenrc script NEEDS TO BE SOURCED (in bash); this is done automatically
# by the Scipyen launch bash script ('scipyen'); for convenience, this script is
# also sourced from ${HOME}/.bashrc in order for the function 'scipyact' to be
# readily available to the user, at the console.
#

if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

dt=`date '+%Y-%m-%d_%H-%M-%s'`

if [[ `id -u` -eq 0 ]] ; then
py_exec="$VIRTUAL_ENV/bin/${python_exec}"
bindir=/usr/local/bin


if [ -r ${bindir}/scipyact ]; then
shopt -s lastpipe
echo "Copying ${bindir}/scipyact to ${bindir}/scipyact.$dt"
cp ${bindir}/scipyact ${bindir}/scipyact.$dt
fi
cat<<END > ${bindir}/scipyact
#! /bin/bash
scipyact () {
source ${VIRTUAL_ENV}/bin/activate
}
export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:$LD_LIBRARY_PATH
END
shopt -u lastpipe
    
else
py_exec=${python_exec}
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

fi
# scipyenvdir=${VIRTUAL_ENV} # not really needed, right?
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
shopt -u lastpipe
fi
}

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

function linkscripts () 
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
# branch=`git -C $scipyendir branch --show-current`
# RED='\033[0;31m'
# GREEN='\033[0;32m'
# BLUE='\033[0;34m'
# NC='\033[0m'

shopt -s lastpipe

# if [[ `id -u` -eq 0 ]] ; then
cat << END > ${target_dir}/scipyen 
#! /bin/sh
if [ -z ${VIRTUAL_ENV} ]; then
source ${install_dir}/${virtual_env}/bin/activate
fi
git -C $scipyendir rev-parse 2>/dev/null;
if [[ $? -eq 0 ]]; then
branch=( git -C $scipyendir branch --show-current )
echo -e "'${RED}'WARNING:'${NC}' Running '${GREEN}${branch}${NC}' branch of local scipyen git repository in ${BLUE}$scipyendir${NC} with status:"
git -C $scipyendir status --short --branch
fi
echo -e "\nUsing Python environment in ${VIRTUAL_ENV}\n"
if [ -z $BROWSER ]; then
if [ -a $VIRTUAL_ENV/bin/browser ]; then
source $VIRTUAL_ENV/bin/browser
fi
fi
export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:$LD_LIBRARY_PATH
export OUTDATED_IGNORE=1
a=`which xrdb` # do we have xrdb to read the X11 resources? (on Unix almost surely yes)
if [ $0 == 0 ] ; then
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

#### Execution starts here ###

# start_time=`date +%s`
SECONDS=0
get_pyver

# virtual_env="testenv"
virtual_env_pfx="scipyenv" #.$pyver"
# install_dir=$HOME
# pyqt5_version=5.15.9
# pyqt5_repo=https://files.pythonhosted.org/packages/source/P/PyQt5/
# pyqt5_src=PyQt5-$pyqt5_version.tar.gz
# NOTE: figure out is /where is dbus-python.h
# pcgconf (pkg-config) must be installed
# pkgconf --liat-all  | grep dbus => list of dbus-* packages including dbus-python
# qdbus_python_dir=


if [[ `id -u ` -eq 0 ]] ; then
install_dir="/usr/local"
else
install_dir=${HOME}
fi
realscript=`realpath $0`
installscriptdir=`dirname "$realscript"`
docdir=`dirname "$installscriptdir"`
scipyendir=`dirname "$docdir"`
scipyensrcdir=${scipyendir}/src/scipyen
using_python=""
install_neuron=0
use_pypi_neuron=1
use_core_neuron=0
njobs=4
reinstall_pyqt5=0
reinstall_vigra=0
reinstall_neuron=0
reinstall_pips=0
reinstall_desktop=0
refresh_git_repos=0
make_dist=0
# for_msys=0

# if [ -n $MSYSTEM_PREFIX ] ; then
#     for_msys=1
# fi

# if [[ `id -u` -eq 0 ]]; then 
#     echo "Running as root" 
#     install_dir="/usr/local"
# else 
# #     echo "Must be root"
#     install_dir=$HOME
#     
# fi

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
            vigra)
            reinstall_vigra=1
            ;;
            neuron)
            reinstall_neuron=1
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

# echo "python major": $major
# echo "python minor": $minor
# echo "python micro": $micro

virtual_env=${virtual_env_pfx}.$pyver
python_exec="python${major}.${minor}"

if [[ `id -u ` -eq 0 ]] ; then
#     echo "running as root"
    python_executable=`which ${python_exec}`;
else
    python_executable=${python_exec}
fi

echo -e "virtual_env is ${virtual_env} \n\twith full path ${install_dir}/${virtual_env}"
echo -e "python executable: ${python_executable}"


# makes a virtual environment and activates it
if ! [ -v VIRTUAL_ENV ] ; then
# NOTE: 2023-06-25 20:57:31 
# these two MUST be run
upgrade_virtualenv && makevirtenv
fi


if [[ $? -ne 0 ]] ; then
    echo -e "\nCould not create and/or activate a virtual environment. Goodbye!\n"
    exit 1
fi

# verify that the newly created virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

# exit

if [[ ( -n "$VIRTUAL_ENV" ) && ( -d "$VIRTUAL_ENV" ) ]] ; then
    echo -e "Creating 'src' directory inside $VIRTUAL_ENV ...\n"
    mkdir -p "$VIRTUAL_ENV/src" && cd "$VIRTUAL_ENV/src"
    
    # install pip requirements NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    installpipreqs
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Could not install pip requirements; check the console for messages. Goodbye!\n"
        exit 1
    fi
    
#     build Pyqt5 NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    dopyqt5
    
    
    # build vigra NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    dovigra
    
    # build neuron NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    if [ $install_neuron -ne 0 ] ; then
        doneuron
    fi
    
    # make scripts
    make_scipyenrc
    
    if [[ `id -u` -ne 0 ]] ; then
        # only update bashrc for regular users
        update_bashrc
    fi
    
    linkscripts
    
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




