#!/bin/bash
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# WARNING 2025-01-12 21:09:06 IF YOU WANT TO BUILD PySide6 FROM SOURCES ON LINUX:
# -------------------------------------------------------------------------------
#
# Operating System: openSUSE Tumbleweed 20250109
# KDE Plasma Version: 6.2.5
# KDE Frameworks Version: 6.9.0
# Qt Version: 6.8.1
#
# to build pyside6 from sources (Linux):
# 1. install ALL development packages for Qt6, including those providing private
# heders and the -devel-static packages
#
# 2. Install Shiboken & Ninja
#
# 3. Create the virtual environment (python3, ideally >= 3.10)
#
# 4. Activate the environment, cd to its top directory
#
# 5. Set up clang as described here:
#  https://doc.qt.io/qtforpython-6/building_from_source/linux.html#setting-up-clang
#
#   NOTE:  even though you may find your own distro is providing clang, there
#   might be issues with Shiboken's cmake files that prevent locating the 
#   appropriate (system-provided) libclang.so library. Therefore, best stick with
#   the instructions provided at the web link above.
#
# 
# 6. create a 'src' subdirectory, clone the pyside6 repo as described here:
# https://doc.qt.io/qtforpython-6/building_from_source/linux.html#getting-the-source
#
# at configuration stage remember to pass the python headers for YOUR python version, e.g.:
# /usr/include/python3.11
#
# cmake -B ../pyside-build -S ./ -DCMAKE_INSTALL_PREFIX=${VIRTUAL_ENV} -DPython_EXECUTABLE=`which python` -DCMAKE_CXX_FLAGS=-I/usr/include/python3.11 -DCMAKE_C_FLAGS=-I/usr/include/python3.11
#
# also remember to pip install shiboken6 module in the virtual environment - not really ?!?


function dopyside6 ()
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
    
    # NOTE 2025-01-13 16:34:26 trying setuptools - WARNING use qtpaths6 below, on
    # Tumbleweed!!!
    qtpaths_exec=`which qtpaths6`
    python setup.py build --qtpaths=${qtpaths_exec} --build-tests --ignore-git --parallel=8
    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot build PySide6 for Qt $pyside6_qtver. Bailing out. Goodbye!\n"
    exit 1
    fi
    
    python setup.py install --prefix=${VIRTUAL_ENV} --qtpaths=${qtpaths_exec} --build-tests --ignore-git --parallel=8
    
    if [[ $? -ne 0 ]] ; then
    echo -e "Cannot install PySide6 for Qt $pyside6_qtver. Bailing out. Goodbye!\n"
    exit 1
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


#### Execution starts here ###

SECONDS=0
get_pyver

install_dir=${HOME}
virtual_env_pfx="scipyenv_pyside6_build" #.$pyver"
realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
docdir=${scipyendir}/doc
installauxdir=${scipyendir}/setup_env
docdir=${scipyendir}/doc
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

if [[ `id -u ` -eq 0 ]] ; then
#     echo "running as root"
    python_executable=`which ${python_exec}`;
else
    python_executable=${python_exec}
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
#     installpipreqs_stage1
    dopyside6
#     installpipreqs_stage2
#     dovigra
    
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
echo "Before using Scipyen, either restart the terminal, or call 'source ~/.$virtual_env_pfx'"

