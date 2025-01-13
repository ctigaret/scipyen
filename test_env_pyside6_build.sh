#!/bin/bash
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

function dopyqt6 ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    cd ${VIRTUAL_ENV}

    wget https://download.qt.io/development_releases/prebuilt/libclang/$libclang_arc
    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot retrieve prebult libclang. Bailing out. Goodbye!\n"
    exit 1
    fi
    
    7z x $libclang_arc
    
    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot extract prebult libclang. Bailing out. Goodbye!\n"
    exit 1
    fi
    
    export LLVM_INSTALL_DIR=${VIRTUAL_ENV}/libclang
    
    mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src
    
    git clone https://code.qt.io/pyside/pyside-setup
    
    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot clone pyqside6 repository. Bailing out. Goodbye!\n"
    exit 1
    fi
    
    cd pyside-setup && git checkout $pyside6_qtver
    
    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot checkout branch $pyside6_qtver. Bailing out. Goodbye!\n"
    exit 1
    fi
    
    pip install -r requirements.txt
    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot install pip requirements for PySide ($pyside6_qtver). Bailing out. Goodbye!\n"
    exit 1
    fi
    
    
    pip install -r requirements-doc.txt
    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot install pip documentation requirements for PySide ($pyside6_qtver). Bailing out. Goodbye!\n"
    exit 1
    fi
    
    mkdir -p ${VIRTUAL_ENV}/src/pyside-build
    
    py_includes=/usr/include/python${major}.${minor}
    
    cmake -B  ${VIRTUAL_ENV}/src/pyside-build -S  ${VIRTUAL_ENV}/src/pyside-setup -DCMAKE_INSTALL_PREFIX=${VIRTUAL_ENV} -DPython_EXECUTABLE=`which python` -DCMAKE_CXX_FLAGS=-I${py_includes} -DCMAKE_C_FLAGS=-I${py_includes}
#     cmake -B ../pyside-build -S ./ -DCMAKE_INSTALL_PREFIX=${VIRTUAL_ENV} -DPython_EXECUTABLE=`which python` -DCMAKE_CXX_FLAGS=-I/usr/include/python3.11 -DCMAKE_C_FLAGS=-I/usr/include/python3.11
    
    
    if [[ $? -ne 0 ]] ; then
    echo -e "Could not configure PySide6 build. Bailing out. Goodbye!\n"
    exit 1
    fi
    
    cmake --build ${VIRTUAL_ENV}/src/pyside-build --parallel ${njobs}
    
    if [[ $? -ne 0 ]] ; then
    echo -e "Could not build PySide6 Bailing out. Goodbye!\n"
    exit 1
    fi
    
    
#     if [[ $build_pyqt6 -gt 0 ]] ; then
#         
#         findqmake6
#         
#         if [ `pwd` != "$VIRTUAL_ENV"/src ]; then
#             echo -e "Not inside $VIRTUAL_ENV/src - goodbye\n"
#             exit 1
#         fi
#         
#         # NOTE: 2023-06-25 10:56:34 
#         # when we are root, make sure to use the virtual environment's python 
#         # executable here
#         if [[ `id -u` -eq 0 ]] ; then
#             py_exec="$VIRTUAL_ENV/bin/${python_exec}"
#             sip_wheel_exec="$VIRTUAL_ENV/bin/sip-wheel"
#         else
#             py_exec=${python_exec}
#             sip_wheel_exec=sip-wheel
#         fi
#         
#         echo "Using ${py_exec} as `whoami` to build PyQt6"
#         
#         # NOTE: locate_pyqt6_src.py uses distlib to locate the (latest) source 
#         # archive (i.e., the sdist) of PyQt6 - its file name typically ends with
#         # .tar.gz
#         pyqt6_src_url=`${py_exec} $installscriptdir/locate_pyqt6_src.py`
#         pyqt6_src=`basename $pyqt6_src_url`
#         
#         pyqt6_src_dir=${pyqt6_src%.tar.gz}
#         
#         echo "PyQt6 source is in "${pyqt6_src_dir}
#         
#         # NOTE: the sdist might have been downloaded alreay - so check this first
#         # before actually downloading
#         if [ ! -r ${pyqt6_src} ] ; then
#             wget ${pyqt6_src_url} && tar xzf ${pyqt6_src} 
# 
#             if [[ $? -ne 0 ]] ; then
#             echo -e "Cannot obtain the PyQt6 source. Bailing out. Goodbye!\n"
#             exit 1
#             fi
#         else
#             if [ -d ${pyqt6_src_dir} ] ; then
#                 rm -fr ${pyqt6_src_dir}
#             fi
#             tar xzf ${pyqt6_src}
#         fi
#         
#         # NOTE: good practice is to create an out-of-source build tree, » ...
#         pyqt6_build_dir="PyQt6-build"
#         
#         # NOTE: clear build dir if it exists -- best to start fresh
#         if [ -d ${pyqt6_build_dir} ] ; then
#             rm -fr ${pyqt6_build_dir}
#         fi
#         mkdir -p ${pyqt6_build_dir}
#         
#         # NOTE: » ... but run the build process INSIDE the expanded sdist dir
#         # this is because sip-wheel will get extra options from there :)
#         cd ${pyqt6_src_dir}
#         
#         echo "Generating PyQt6 wheel in "$(pwd)"..."
#         
#         # NOTE: 2023-03-23 14:03:48 - enable parallel jobs - to change, either:
#         # • change the value of the --jobs option (e.g. half the number of 
#         # cores in your system seems to be a good choice), or
#         # • remove the --jobs option altogether
#         if [[ $njobs -gt 0 ]] ; then
#             ${sip_wheel_exec} --qmake=${qmake6_binary} --confirm-license --jobs $njobs --qt-shared --verbose --build-dir ../PyQt6-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
#         else
#             ${sip_wheel_exec} --qmake=${qmake6_binary} --confirm-license --qt-shared --verbose --build-dir ../PyQt6-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
#         fi
# 
#         if [[ $? -ne 0 ]] ; then
#             echo -e "sip Cannot build a PyQt6 wheel. Bailing out. Goodbye!\n"
#             echo -e "You might want to upgrade sip and PyQt6-sip in this environment\n"
#             echo -e " by calling \n\n"
#             echo -e "pip install --upgrade sip\n"
#             echo -e "pip install --upgrade PyQt6-sip\n\n"
#             echo -e "Then run this script again"
#             exit 1
#         fi
#         
#         # NOTE: check is a wheel file has been produced; the filename typically
#         # ends in .whl » if found then call pip to install it inside the 
#         # environment ⟶ IT WORKS!
#         wheel_file=`ls | grep whl`
#         if [ -z ${wheel_file} ] ; then
#             echo -e "No wheel file found in "$(pwd)" - goodbye!\n"
#             exit 1
#         else
#             ${py_exec} -m pip install --force-reinstall ${wheel_file}
#             
#             if [[ $? -ne 0 ]] ; then
#                 echo -e "Cannot install the PyQt6 wheel; check console output. Goodbye!\n"
#                 exit 1
#             else
#                 echo "PyQt6 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pyqt6done
#                 echo -e "\n\n=====================\n# Pyqt6 installed!\n=====================\n\n"
#                 
# #                 echo -e "\n\n Installing PyQtDataVisualization\n\n"
# #                 # NOTE: WARNING: 2023-07-19 00:12:27 avoid this !!!! 
# #                 pip install PyQtDataVisualization
#             fi
#         fi
#     else
#         pip install pyqt6
#     fi
    
#     if [ ! -r ${VIRTUAL_ENV}/.pyqt6done ] || [[ $reinstall_pyqt6 -gt 0 ]]; then
#         if [[ $build_pyqt6 -gt 0 ]] ; then
#             mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src
#             
#             findqmake6
#             
#             if [ `pwd` != "$VIRTUAL_ENV"/src ]; then
#                 echo -e "Not inside $VIRTUAL_ENV/src - goodbye\n"
#                 exit 1
#             fi
#             
#             # NOTE: 2023-06-25 10:56:34 
#             # when we are root, make sure to use the virtual environment's python 
#             # executable here
#             if [[ `id -u` -eq 0 ]] ; then
#                 py_exec="$VIRTUAL_ENV/bin/${python_exec}"
#                 sip_wheel_exec="$VIRTUAL_ENV/bin/sip-wheel"
#             else
#                 py_exec=${python_exec}
#                 sip_wheel_exec=sip-wheel
#             fi
#             
#             echo "Using ${py_exec} as `whoami` to build PyQt6"
#             
#             # NOTE: locate_pyqt6_src.py uses distlib to locate the (latest) source 
#             # archive (i.e., the sdist) of PyQt6 - its file name typically ends with
#             # .tar.gz
#             pyqt6_src_url=`${py_exec} $installscriptdir/locate_pyqt6_src.py`
#             pyqt6_src=`basename $pyqt6_src_url`
#             
#             pyqt6_src_dir=${pyqt6_src%.tar.gz}
#             
#             echo "PyQt6 source is in "${pyqt6_src_dir}
#             
#             # NOTE: the sdist might have been downloaded alreay - so check this first
#             # before actually downloading
#             if [ ! -r ${pyqt6_src} ] ; then
#                 wget ${pyqt6_src_url} && tar xzf ${pyqt6_src} 
# 
#                 if [[ $? -ne 0 ]] ; then
#                 echo -e "Cannot obtain the PyQt6 source. Bailing out. Goodbye!\n"
#                 exit 1
#                 fi
#             else
#                 if [ -d ${pyqt6_src_dir} ] ; then
#                     rm -fr ${pyqt6_src_dir}
#                 fi
#                 tar xzf ${pyqt6_src}
#             fi
#             
#             # NOTE: good practice is to create an out-of-source build tree, » ...
#             pyqt6_build_dir="PyQt6-build"
#             
#             # NOTE: clear build dir if it exists -- best to start fresh
#             if [ -d ${pyqt6_build_dir} ] ; then
#                 rm -fr ${pyqt6_build_dir}
#             fi
#             mkdir -p ${pyqt6_build_dir}
#             
#             # NOTE: » ... but run the build process INSIDE the expanded sdist dir
#             # this is because sip-wheel will get extra options from there :)
#             cd ${pyqt6_src_dir}
#             
#             echo "Generating PyQt6 wheel in "$(pwd)"..."
#             
#             # NOTE: 2023-03-23 14:03:48 - enable parallel jobs - to change, either:
#             # • change the value of the --jobs option (e.g. half the number of 
#             # cores in your system seems to be a good choice), or
#             # • remove the --jobs option altogether
#             if [[ $njobs -gt 0 ]] ; then
#                 ${sip_wheel_exec} --qmake=${qmake6_binary} --confirm-license --jobs $njobs --qt-shared --verbose --build-dir ../PyQt6-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
#             else
#                 ${sip_wheel_exec} --qmake=${qmake6_binary} --confirm-license --qt-shared --verbose --build-dir ../PyQt6-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
#             fi
# 
#             if [[ $? -ne 0 ]] ; then
#                 echo -e "sip Cannot build a PyQt6 wheel. Bailing out. Goodbye!\n"
#                 echo -e "You might want to upgrade sip and PyQt6-sip in this environment\n"
#                 echo -e " by calling \n\n"
#                 echo -e "pip install --upgrade sip\n"
#                 echo -e "pip install --upgrade PyQt6-sip\n\n"
#                 echo -e "Then run this script again"
#                 exit 1
#             fi
#             
#             # NOTE: check is a wheel file has been produced; the filename typically
#             # ends in .whl » if found then call pip to install it inside the 
#             # environment ⟶ IT WORKS!
#             wheel_file=`ls | grep whl`
#             if [ -z ${wheel_file} ] ; then
#                 echo -e "No wheel file found in "$(pwd)" - goodbye!\n"
#                 exit 1
#             else
#                 ${py_exec} -m pip install --force-reinstall ${wheel_file}
#                 
#                 if [[ $? -ne 0 ]] ; then
#                     echo -e "Cannot install the PyQt6 wheel; check console output. Goodbye!\n"
#                     exit 1
#                 else
#                     echo "PyQt6 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pyqt6done
#                     echo -e "\n\n=====================\n# Pyqt6 installed!\n=====================\n\n"
#                     
#     #                 echo -e "\n\n Installing PyQtDataVisualization\n\n"
#     #                 # NOTE: WARNING: 2023-07-19 00:12:27 avoid this !!!! 
#     #                 pip install PyQtDataVisualization
#                 fi
#             fi
#         else
#             pip install pyqt6
#         fi
#     fi
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
    
    if [ -d $virtual_env ] ; then 
        # found putative virtual environment directory
        if [ -a $virtual_env/pyvenv.cfg ] ; then 
            # which contains a file named 'pyvenv.cfg' =>
            # check if pyvenv.cfg is what is expected to be
            aa=`cat $virtual_env/pyvenv.cfg | grep "virtualenv"`
            if [ -n "$aa" ] ; then 
                # and pyvenv.cfg defines a 'virtualenv' variable -> OK so far
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
                
                echo -e "Virtual environment found; activating it...\n"
                
                # so far so good; try and activate the virtual environment
                source $virtual_env/bin/activate
                
                if [[ -z ${VIRTUAL_ENV} ]]; then
                    # failed to activate => bail out
                    echo -r "Cannot activate a virtual environment from  $virtual_env . Goodbye!\n"
                    exit 1
                fi
                
                python_executable=`which python3`
                
                echo -e "Virtual environment activated and will use ${python_executable}\n"
                
            else
                echo -e "$virtual_env/ does not look like a virtual environment directory. Goodbye!\n"
                exit 1
            fi 
        fi
    else
        # putative virtual environment directory not found => need to generate one
        ${python_executable} -m virtualenv --python ${python_executable} $virtual_env
        
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



install_dir=${HOME}
virtual_env_pfx="scipyenv_pyside6_build" #.$pyver"
realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
docdir=${scipyendir}/doc
installauxdir=${scipyendir}/setup_env
pipreqsfile1="pip_requirements_pyside6_stage_1.txt"
pipreqsfile2="pip_requirements_pyside6_stage_2.txt"
scipyensrcdir=${scipyendir}/src/scipyen
pyside6_qtver="6.8"
njobs=4
install_dir=`realpath ${install_dir}`

libclang_arc=libclang-release_18.1.5-based-linux-Rhel8.6-gcc10.3-x86_64.7z


echo -e "Will install in ${install_dir}" 

if ! [ -v VIRTUAL_ENV ] ; then
    virtual_env=${install_dir}/${virtual_env_pfx}
    python_exec="python${major}.${minor}"
else
    virtual_env=$VIRTUAL_ENV
    python_exec=$VIRTUAL_ENV/bin/"python${major}"
fi

echo -e "virtual_env is ${virtual_env}"
echo -e "python executable: ${python_executable}"

if ! [ -v VIRTUAL_ENV ] ; then
# NOTE: 2023-06-25 20:57:31 
# these two MUST be run
makevirtenv
# upgrade_virtualenv && makevirtenv
else
    virtual_env=$VIRTUAL_ENV
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

if [[ ( -n "$VIRTUAL_ENV" ) && ( -d "$VIRTUAL_ENV" ) ]] ; then
    echo -e "Checking for, or making 'src' directory inside $VIRTUAL_ENV ...\n"
    mkdir -p "$VIRTUAL_ENV/src" && cd "$VIRTUAL_ENV/src"
    
    # install pip requirements NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    installpipreqs_stage1
    dopyqt6
    installpipreqs_stage2
    dovigra
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Could not install pip requirements; check the console for messages. Goodbye!\n"
        exit 1
    fi
    
