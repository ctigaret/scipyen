#!/bin/bash
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# Installation script stub for scipyen 23c19
#
# Author: Cezar M. Tigaret <cezar.tigaret@gmail.com>
#
# Distributed under GNU GPL License v.2
#

function define_vars()
{
    get_pyver
    virtual_env_stem="scipyenv"
    virtual_env_qt_binding="pyside6"
    virtual_env_qt_binding_source="pypi_pip"
    virtual_env_bnd=${virtual_env_qt_binding}_${virtual_env_qt_binding_source}
    virtual_env_pfx=${virtual_env_stem}_${virtual_env_bnd}
    activate_cmd="scipyact_"${virtual_env_bnd}
    launch_script="scipyen"_${virtual_env_bnd}
    desktop_file="Scipyen".$virtual_env_bnd".desktop"
    rcfile=${HOME}/.${virtual_env_pfx}_rc
    install_dir=${HOME}
    realscript=`realpath $0`
    scipyendir=`dirname "$realscript"`
    docdir=${scipyendir}/doc
    installauxdir=${scipyendir}/setup_env
    scipyensrcdir=${scipyendir}/src/scipyen
    pipreqsfile1="pip_requirements_pyside6_stage_1.txt"
    pipreqsfile2="pip_requirements_pyside6_stage_2.txt"
    using_python=""
    install_neuron=0
    use_pypi_neuron=1
    use_core_neuron=0
    install_fenicsx=0
    njobs=4
    reinstall_vigra=0
    reinstall_neuron=0
    reinstall_fenicsx=0
    reinstall_pips=0
    reinstall_desktop=0
    refresh_git_repos=0
    make_dist=0
    pyside6_qtver_major="6"
    pyside6_qtver_minor="8"
    pyside6_qtver_micro="0"
    libclang_arc=libclang-release_18.1.5-based-linux-Rhel8.6-gcc10.3-x86_64.7z



    must_create_env=1
}

function dofenicsx ()
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
    
    if [ ! -r ${VIRTUAL_ENV}/.fenicsxdone ] || [[ $reinstall_fenicsx -gt 0 ]]; then
        mkdir -p ${VIRTUAL_ENV}/src && cd $VIRTUAL_ENV/src
        
        findcmake
        
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

function dopyside6()
{
    pip install pyside6
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
        
        $cmake_binary -DPython_INCLUDE_DIRS=$(python -c "import sysconfig; print(sysconfig.get_paths()['include'])") \
                      -DPython_LIBRARIES=$(python -c "import distutils.sysconfig as sysconfig; print(sysconfig.get_config_var('LIBDIR'))") \
                      -DPython_EXECUTABLE:FILEPATH=`which python` \
                      -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DWITH_BOOST_GRAPH=1 -DWITH_BOOST_THREAD=1 -DWITH_HDF5=1 -DWITH_OPENEXR=1 -DWITH_VIGRANUMPY=1 -DLIB_SUFFIX=64 ../vigra
#         $cmake_binary -DPYTHON_INCLUDE_DIRS=$(python -c "import sysconfig; print(sysconfig.get_paths()['include'])") \
#                       -DPYTHON_LIBRARIES=$(python -c "import distutils.sysconfig as sysconfig; print(sysconfig.get_config_var('LIBDIR'))") \
#                       -DPYTHON_EXECUTABLE:FILEPATH=`which python` \
#                       -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DWITH_BOOST_GRAPH=1 -DWITH_BOOST_THREAD=1 -DWITH_HDF5=1 -DWITH_OPENEXR=1 -DWITH_VIGRANUMPY=1 -DLIB_SUFFIX=64 ../vigra
#         $cmake_binary -DPYTHON_INCLUDE_DIR=$(python -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") -DPYTHON_LIBRARY=$(python -c "import distutils.sysconfig as sysconfig; print(sysconfig.get_config_var('LIBDIR'))") -DPYTHON_EXECUTABLE:FILEPATH=`which python` -DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV -DCMAKE_SKIP_INSTALL_RPATH=1 -DCMAKE_SKIP_RPATH=1 -DWITH_BOOST_GRAPH=1 -DWITH_BOOST_THREAD=1 -DWITH_HDF5=1 -DWITH_OPENEXR=1 -DWITH_VIGRANUMPY=1 -DLIB_SUFFIX=64 ../vigra
        
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

function findcmake ()
{
    cmake_binary=`which cmake`
    if [ -z "$cmake_binary" ] ; then
        echo -e "Cannot build vigra without cmake. Goodbye!\n"
        exit 1
    fi
    
}

function findqmake ()
{
    # Identifes which qmake is there available on the platform.
    # 
    # Since Linux dsitributions currently provide both Qt5 and Qt6, their respective
    # qmake tools bear different names.
    #
    # Not sure this is as generic as possible across the Linux distributions...
    #
    
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

function installpipreqs_stage1 ()
{
    # installs pip packaged listed in pip_requirements
    # assumes (and therefore REQUIRES) that the virtual environment is active
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    # NOTE: since around Jan 2023 sklearn has been deprecated in favour of 
    # scikit-learn, such that an error message is issued whenever pip tries
    # to install sklearn.
    # HOWEVER, a LARGE number of packages still list sklearn among their 
    # dependencies, yet pip has no way to check this BEFORE installing them.
    #
    # Until all of them catch up with this, we circumvent the error message
    # by setting up the environment variable below
    # For details please see https://pypi.org/project/sklearn/
    #
    export SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True 
    
    echo -e "Using ${python_executable} as `whoami` to install PyPI packages\n"
    
    ${python_executable} -m pip install -r "$installauxdir"/"$pipreqsfile1"
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot install required packages from PyPI (stage 1). Bailing out. Goodbye!\n"
        exit 1
    else
        echo "pip packages installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pipdone
        echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
    fi
    
#     if [ ! -r ${VIRTUAL_ENV}/.pipdone ] || [[ $reinstall_pips -gt 0 ]] ; then
#         # NOTE: since around Jan 2023 sklearn has been deprecated in favour of 
#         # scikit-learn, such that an error message is issued whenever pip tries
#         # to install sklearn.
#         # HOWEVER, a LARGE number of packages still list sklearn among their 
#         # dependencies, yet pip has no way to check this BEFORE installing them.
#         #
#         # Until all of them catch up with this, we circumvent the error message
#         # by setting up the environment variable below
#         # For details please see https://pypi.org/project/sklearn/
#         #
#         export SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True 
#         
#         echo -e "Using ${python_executable} as `whoami` to install PyPI packages\n"
#         
#         ${python_executable} -m pip install -r "$installauxdir"/"$pipreqsfile"
#         
#         if [[ $? -ne 0 ]] ; then
#             echo -e "Cannot install required packages from PyPI. Bailing out. Goodbye!\n"
#             exit 1
#         else
#             echo "pip packages installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pipdone
#             echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
#         fi
#     fi
}

function installpipreqs_stage2()
{
    ${python_executable} -m pip install -r "$installauxdir"/"$pipreqsfile2"
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Cannot install required packages from PyPI (stage 2). Bailing out. Goodbye!\n"
        exit 1
    else
        echo "pip packages installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pipdone
        echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
    fi
}

function installpipreqs ()
{
    # installs pip packaged listed in pip_requirements
    # assumes (and therefore REQUIRES) that the virtual environment is active
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pipdone ] || [[ $reinstall_pips -gt 0 ]] ; then
        # NOTE: since around Jan 2023 sklearn has been deprecated in favour of 
        # scikit-learn, such that an error message is issued whenever pip tries
        # to install sklearn.
        # HOWEVER, a LARGE number of packages still list sklearn among their 
        # dependencies, yet pip has no way to check this BEFORE installing them.
        #
        # Until all of them catch up with this, we circumvent the error message
        # by setting up the environment variable below
        # For details please see https://pypi.org/project/sklearn/
        #
        export SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True 
        
        echo -e "Using ${python_executable} as `whoami` to install PyPI packages\n"
        
        ${python_executable} -m pip install -r "$installauxdir"/pip_requirements_pyside6.txt
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Cannot install required packages from PyPI. Bailing out. Goodbye!\n"
            exit 1
        else
            echo "pip packages installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pipdone
            echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
        fi
    fi
}

function main()
{

# makes a virtual environment and activates it
if ! [ -v VIRTUAL_ENV ] ; then
# NOTE: 2023-06-25 20:57:31 
# these two MUST be run
    overwrite_env=1
    makevirtenv
    if [[ $? -ne 0 ]] ; then
        echo -e "\nCould not create and/or activate a virtual environment. Goodbye!\n"
        exit 1
    fi
else
    virtual_env=$VIRTUAL_ENV
fi




# verify that the newly created virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

# exit

if [[ ( -n "$VIRTUAL_ENV" ) && ( -d "$VIRTUAL_ENV" ) ]] ; then
    echo -e "Checking for, or making 'src' directory inside $VIRTUAL_ENV ...\n"
    mkdir -p "$VIRTUAL_ENV/src" && cd "$VIRTUAL_ENV/src"
    
    # install pip requirements NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    dopyside6
#     installpipreqs_stage1
#     installpipreqs_stage2
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Could not install pip requirements; check the console for messages. Goodbye!\n"
        exit 1
    fi
    
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
    
#     update_bashrc
    
#     make_desktop_entry
    
    # NOTE: install console color schemes
    cd $scipyendir/src/scipyen/gui/scipyen_console_styles
    pip install .
    cd $scipyendir
    
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

function make_launch_script () 
{
    # force the use of XCB platform abstraction plugin in Qt
if [[ `id -u` -eq 0 ]] ; then
    target_dir=/usr/local/bin
else
    target_dir=${HOME}/bin
fi
    
mkdir -p ${target_dir}
if [ -r ${target_dir}/${launch_script} ] ; then
    dt=`date '+%Y-%m-%d_%H-%M-%s'`
    mv ${target_dir}/${launch_script} ${target_dir}/${launch_script}.$dt
fi
shopt -s lastpipe

# if [[ `id -u` -eq 0 ]] ; then
cat <<END > ${target_dir}/${launch_script}
#! /bin/sh
if [ -z \${VIRTUAL_ENV} ]; then
source ${virtual_env}/bin/activate
fi
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
echo -e "\nUsing Python environment in ${VIRTUAL_ENV}\n"
if [ -z \$BROWSER ]; then
if [ -a \$VIRTUAL_ENV/bin/browser ]; then
source \$VIRTUAL_ENV/bin/browser
fi
fi
export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:\${LD_LIBRARY_PATH}
export OUTDATED_IGNORE=1
a=\`which xrdb\` # do we have xrdb to read the X11 resources? (on Unix almost surely yes)
if [ \$0 == 0 ] ; then
if [ -r $scipyensrcdir/neuron_python/app-defaults/nrniv ] ; then
xrdb -merge $scipyensrcdir/neuron_python/app-defaults/nrniv
fi
fi
export QT_API="PySide6"
${python_executable} -Xfrozen_modules=off ${scipyensrcdir}/scipyen.py "\$*"
END
shopt -u lastpipe
chmod +x ${target_dir}/${launch_script}
echo -e "Scipyen (PySide6) startup script created in ${target_dir} \n"
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


echo -e "\nCreating ${rcfile} file... \n"

if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

dt=`date '+%Y-%m-%d_%H-%M-%s'`

py_exec=${python_exec}
if [ -r ${rcfile} ] ; then
# make a backup copy of .scipyenrc_pyside6
shopt -s lastpipe
echo "Copying ${rcfile} to ${rcfile}.$dt"
cp ${rcfile} ${rcfile}.$dt
fi
cat<<END > ${rcfile}
${activate_cmd} () {
source ${VIRTUAL_ENV}/bin/activate
export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:$LD_LIBRARY_PATH
export QT_API="PySide6"
echo -e "The Python virtual environment in ${VIRTUAL_ENV} is now active.\nTo exit this environment call 'deactivate'"
}
END
# # # # cat<<END > ${rcfile}
# # # # scipyact_pyside6 () {
# # # # source ${VIRTUAL_ENV}/bin/activate
# # # # export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:$LD_LIBRARY_PATH
# # # # export QT_API="PySide6"
# # # # echo -e "The Python virtual environment in ${VIRTUAL_ENV} is now active.\nTo exit this environment call 'deactivate'"
# # # # }
# # # # END
shopt -u lastpipe
}

function makevirtenv ()
{
    # Generates if necessary, then activates the virtual environment for Scipyen.
    #
    echo -e "Trying to create/use virtual environment ${virtual_env} in ${install_dir} using ${using_python}\n"
    
    # Checks if the environment directory exists and that it does belong to a
    # virtual python environment:
    # 1) it contains a file named "pyenv.cfg" defining a "virtualenv" variable
    # 2) contains a "bin" directory with "activate" script which can be sourced 
    #   to generate — among other things — a VIRTUAL_ENV environment variable
    # If such directory does NOT exist then tries to create a virtual environment
    # using virtualenv package (NOT python's standard library venv !!!)
    # 
    # If either was successful then activates the environment for the script to
    # proceed with installation of dependencies in this environment
    #
    
#     must_create_env=1

    if [ -d $virtual_env -a $overwrite_env -eq 0 ] ; then 
        echo -e "Found putative virtual environment directory: ${virtual_env}\n"
        echo -e "Checking if the directory hosts a virtual python evironment..."
        if [ -a $virtual_env/pyvenv.cfg ] ; then 
            echo -e "The file pyvenv.cfg was found in ${virtual_env} — OK\n"
            # which contains a file named 'pyvenv.cfg' =>
            # check if pyvenv.cfg is what is expected to be
            echo -e "Checking if pyvenv.cfg defines a virtual environment..."
            aa=`cat $virtual_env/pyvenv.cfg | grep "virtualenv"`
            if [ -n "$aa" ] ; then 
                echo -e "pyvenv.cfg looks OK\n"
                # and pyvenv.cfg defines a 'virtualenv' variable -> OK so far
                echo -r "Checking for environment activation script..."
                # => check for bin subdirectory
                if [ ! -d $virtual_env/bin ] ; then
                    # bin subdirectory missing -> BAD!!!
                    echo -e "$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                    exit 1
                fi
                if [ ! -r $virtual_env/bin ] ; then
                    # bin subdirectory not readable -> BAD!!!
                    echo -e "$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                    exit 1
                fi
                
                echo -e "Activation script found; sourcing it...\n"
                
                # so far so good; try and activate the virtual environment
                source $virtual_env/bin/activate
                
                if [[ -z ${VIRTUAL_ENV} ]]; then
                    # failed to activate => bail out
                    echo -r "Cannot activate a virtual environment from  $virtual_env . Goodbye!\n"
                    exit 1
                fi
                
                python_executable=`which python3`
                
                echo -e "Virtual environment ${virtual_env} is activated and will use ${python_executable}\n"
                
                must_create_env=0
                
#                 usesyssite=`cat $virtual_env/pyvenv.cfg | grep "include-system-site-packages = true"`
#                 echo -e "Checking if the evironment is using system-site packages..."
#                 if [ -n "$usesyssite" ] ; then
#                     echo -e "The evironment appears to use system-site packages...\n"
#                 
#                 else
#                     echo -e "The environment DOES NOT use system site packages; must recreate it"
#                     must_create_env=1
#                 fi
            else
                echo -e "$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                exit 1
            fi 
        fi
        
    fi
    
    if [ $must_create_env -eq 1 ] ; then
        ${python_executable} -m virtualenv --clear --python ${python_executable} $virtual_env
#         ${python_executable} -m virtualenv --clear --system-site-packages --python ${python_executable} $virtual_env
        
        if [[ $? -ne 0 ]] ; then
            # the above attempt failed => bail out
            echo -e "Could NOT create a virtual environment at ${virtual_env}. Bailing out...\n"
            exit 1
        fi

        echo -e "Virtual environment created at ${virtual_env}\n"
        echo -e "Activating the virtual environment\n"

        # so far so good:  virtual environment directory tree created, now try
        # to activate it
        source $virtual_env/bin/activate
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Could NOT activate the virtual environment at ${virtual_env}. Bailing out...\n"
            exit 1
        fi
        
        # just cache this for the rest of this script
        python_executable=`which python3`
        
        echo -e "Virtual environment at ${VIRTUAL_ENV} activated; python executable is ${python_executable}\n"
        
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
    echo -e "Run 'sh install.sh' without options for a fully automated installation, using built-in defaults.\n"
    echo -e "Options:"
    echo -e "========\n"
    echo -e "--install_dir=DIR\tSpecify where the virtual environment will be created (default is ${HOME})\n"
    echo -e "--environment=NAME\tCustom name for the virtual environment (default is ${virtual_env})\n"
    echo -e "--with_neuron\t\tInstall binary neuron python distribution from PyPI\n"
    echo -e "--build_neuron\t\tBuild neuron python locally\n"
    echo -e "--with_coreneuron\twhen '--build_neuron' is passed, build local neuron with coreneuron; by default coreneuron is not used.\n"
    echo -e "--refresh_repos\t When '--refresh_repos' is passed, local repository clones will be refreshed before rebuilding\n"
    echo -e "\tNOTE: This applies to vigra and to local neuron build only\n"
    echo -e "--jobs=N\t\tNumber of parallel tasks during building PyQt and neuron; default is 4; set to 0 to disable parallel build\n"
    echo -e "--reinstall=NAME\t\t\tRe-install/re-building NAME, where NAME is one of:\n"
    echo -e "\tpips, vigra, neuron, or desktopentry;\n"
    echo -e "\t(this option can be passed more than once)\n"
    echo -e "--install=NAME\t\t Alias to --reinstall option above; use it to "
    echo -e "\tinstall optional libraries AFTER building Scipyen's virtual environment\n "
    echo -e "--about\t\t\tDisplay Install.md at the console (requires the program 'glow')\n"
    echo -e "--dist\t\t\tCreates a binary Scipyen diwstribution using PyInstaller. Requires that a virtual environment has already been built using this script.\n"
    echo -e "-h | -? | --help \tShow this help message and quit\n"
    echo -e "\nFor details, execute install.sh --about\n"
    echo -e "\n"
    echo -e "When run with the virtual Python environment already activated,\n"
    echo -e "the script will use the current virtual environment to perform \n"
    echo -e "(re)installations. WARNING: Make sure you activate the appropriate\n"
    echo -e "Python environment for this !\n"
   
}

function showinstalldoc () 
{
    glowexec=`which glow`
    if [ -n $glowexec ] ; then
        glow -p $docdir/Install.md
    else
        cat $docdir/Install.md
    fi
}

function update_bashrc () 
{
dt=`date '+%Y-%m-%d_%H-%M-%s'`
if [ ! -r ${HOME}/.bashrc ]; then
cat<<END > ${HOME}/.bashrc
source ${rcfile}
END
echo ".bashrc has been created in ${HOME}"
echo "Sourcing ${HOME}/.bashrc"
source ${HOME}/.bashrc
else
shopt -s lastpipe
# check if .scipyenrc is sourced from .bashrc
cat ${HOME}/.bashrc | grep "source ${rcfile}" | read source_set
# echo "source_set="$source_set
if [ -z "${source_set}" ]; then
# ${rcfile} not sourced from .bashrc => backup .bashrc, then append a line to
# source ${rcfile} in there
echo "Copying ${HOME}/.bashrc to ${HOME}/.bashrc.$dt"
cp ${HOME}/.bashrc ${HOME}/.bashrc.$dt
echo "source ${rcfile}" >> ${HOME}/.bashrc
echo ".bashrc has been modified in ${HOME}"
echo "Sourcing ${HOME}/.bashrc"
source ${HOME}/.bashrc
fi
shopt -u lastpipe
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


#### Execution starts here ###

# start_time=`date +%s`
SECONDS=0
define_vars

# virtual_env="testenv"

# virtual_env_pfx="scipyenv_test" #.$pyver"
# install_dir=$HOME
# pyqt5_version=5.15.9
# pyqt5_repo=https://files.pythonhosted.org/packages/source/P/PyQt5/
# pyqt5_src=PyQt5-$pyqt5_version.tar.gz
# NOTE: figure out is /where is dbus-python.h
# pcgconf (pkg-config) must be installed
# pkgconf --list-all  | grep dbus => list of dbus-* packages including dbus-python
# qdbus_python_dir=



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
#         --with_pyqt5)
#         with_pyqt5=1
#         build_pyqt5=0 
#         shift
#         ;;
#         --with_pyqt6)
#         with_pyqt6=1
#         build_pyqt6=0 
#         shift
#         ;;
#         --build_pyqt5)
#         with_pyqt5=1
#         build_pyqt5=1
#         shift
#         ;;
#         --build_pyqt6)
#         with_pyqt6=1
#         build_pyqt6=1
#         shift
#         ;;
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
#             pyqt5)
#             reinstall_pyqt5=1
#             build_pyqt5=0
#             ;;
#             build_pyqt5)
#             reinstall_pyqt5=1
#             build_pyqt5=1
#             ;;
#             pyqt6)
#             reinstall_pyqt6=1
#             build_pyqt6=0
#             ;;
#             build_pyqt6)
#             reinstall_pyqt6=1
#             build_pyqt6=1
#             ;;
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
        --install=*)
        reinstall="${i#*=}"
        shift
        case $reinstall in
#             pyqt5)
#             reinstall_pyqt5=1
#             build_pyqt5=1
#             ;;
#             PyQt5)
#             reinstall_pyqt5=1
#             build_pyqt5=1
#             ;;
#             pyqt6)
#             reinstall_pyqt6=1
#             build_pyqt6=1
#             ;;
#             PyQt6)
#             reinstall_pyqt6=1
#             build_pyqt6=1
#             ;;
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
#         ;;
#         --dist)
#         make_dist=1
#         shift
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

if ! [ -v VIRTUAL_ENV ] ; then
    virtual_env=${install_dir}/${virtual_env_pfx}
    python_exec="python${major}.${minor}"
else
    virtual_env=$VIRTUAL_ENV
    python_exec=$VIRTUAL_ENV/bin/"python${major}"
fi

python_executable=${python_exec}

# if [[ `id -u ` -eq 0 ]] ; then
# #     echo "running as root"
#     python_executable=`which ${python_exec}`;
# else
#     python_executable=${python_exec}
# fi

echo -e "virtual_env is ${virtual_env}"
echo -e "python executable: ${python_executable}"

main



t=$SECONDS

days=$(( t/86400 ))
t=$(( t%(24*3600) ))
hours=$(( t/3600 ))
t=$(( t%3600 ))
minutes=$(( t/60 ))
t=$(( t % 60))
seconds=$(( t ))

echo "Execution time was $days days, $hours hours, $minutes minutes and $seconds seconds"
echo "Before using Scipyen, either restart the terminal, or call 'source ${rcfile}'"




