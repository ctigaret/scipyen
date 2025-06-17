#!/bin/bash
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# Installation script stub for scipyen 23c19
#
# Author: Cezar M. Tigaret <cezar.tigaret@gmail.com>
#
# Distributed under GNU GPL License v.2
#
#
# Changelog:
# 2025-03-13 10:45:35:
# • No more installation as root
# • uses Python 3.13
# • pip requirements for linux split in two batches
#   ∘ first one installs the mimimum packages necessary to build PyQt5 locally
#   ∘ second one installs the rest
# • builds PyQt5 locally (support for PyQt6 and/or Pyside6 is still being developed )
#   this requires some packages supplied by the distribution (including their
#   development counterparts where shown by ∗):
#   ∘ Qt5 (∗) and tools (e.g. designer, qmake)
#   ∘ tiff (∗)
#   ∘ png (∗)
#   ∘ zlib (∗)
#   ∘ gnu toolchain and cmake
# • vigra is built locally -- requires sphinx, and the following packages
#   supplied by your distribution (including their development counterparts, ∗):
#   ∘ python (>=3.13, ∗)
#   ∘ gnu toolchain and cmake
#   ∘ boost-python bindings (∗)
#   ∘ for a complete list please see 
#       https://ukoethe.github.io/vigra/doc-release/vigra/Installation.html

function showinstalldoc () 
{
    glowexec=`which glow`
    if [ -n $glowexec ] ; then
        glow -p $docdir/Install.md
    else
        cat $docdir/Install.md
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
    echo -e "Run 'sh $0' without options for a fully automated installation, using built-in defaults.\n"
    echo -e "Options:"
    echo -e "========\n"
    echo -e "--install_dir=DIR\tSpecify where the virtual environment will be created (default is ${HOME})\n"
    echo -e "--environment=NAME\tCustom name for the virtual environment (default is ${virtual_env})\n"
    echo -e "--with_neuron\t\tInstall binary neuron python distribution from PyPI\n"
    echo -e "--build_neuron\t\tBuild neuron python locally\n"
    echo -e "--with_coreneuron\twhen '--build_neuron' is passed, build local neuron with coreneuron; by default coreneuron is not used.\n"
    echo -e "--with_pyqt5\t\tInstall PyQt5 from PyPI\n"
    echo -e "--build_pyqt5\t\tBuild a PyQt5 wheel locally and install it (recommended)\n"
    echo -e "--with_pyside6\t\tInstall PySide6 ans Shiboken from PyPI (recommended)\n"
    echo -e "--build_pyside6\t\tBuild a PySide6 and Shiboken wheels locally and install them \n"
    echo -e "--refresh_repos\t When '--refresh_repos' is passed, local repository clones will be refreshed before rebuilding\n"
    echo -e "\tNOTE: This applies to vigra and to local neuron build only\n"
    echo -e "--jobs=N\t\tNumber of parallel tasks during building PyQt5 and neuron; default is 4; set to 0 to disable parallel build\n"
    echo -e "--reinstall=NAME\t\t\tRe-install/re-building NAME, where NAME is one of:\n"
    echo -e "\tpips, pyqt5, build_pyqt5, pyside6, build_pyside6, vigra, neuron, or desktopentry;\n"
    echo -e "\t(this option can be passed more than once)\n"
    echo -e "--install=NAME\t\t Alias to --reinstall option above; use it to "
    echo -e "\tinstall optional libraries AFTER building Scipyen's virtual environment\n "
    echo -e "--about\t\t\tDisplay Install.md at the console (requires the program 'glow')\n"
    echo -e "--dist\t\t\tCreates a binary Scipyen diwstribution using PyInstaller. Requires that a virtual environment has already been built using this script.\n"
    echo -e "-h | -? | --help \tShow this help message and quit\n"
    echo -e "\nFor details, execute $0 --about\n"
    echo -e "\n"
    echo -e "When run with the virtual Python environment already activated,\n"
    echo -e "the script will use the current virtual environment to perform \n"
    echo -e "(re)installations. WARNING: Make sure you activate the appropriate\n"
    echo -e "Python environment for this !\n"
   
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
        # virtual environment directory apparently found
        if [ -a $virtual_env/pyvenv.cfg ] ; then 
            # and has pyvenv.cfg => check if pyvenv.cfg is what is expected to be
            aa=`cat $virtual_env/pyvenv.cfg | grep "virtualenv"`
            if [ -n "$aa" ] ; then 
                # and pyvenv.cfg defines a vitualenv variable -> OK so far
                # => check for bin subdirerctory
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
        if [ -z ${uv_exec} ] ; then
            ${python_executable} -m virtualenv --python ${python_executable} $virtual_env
        else
            ${uv_exec} venv --python ${python_executable} $virtual_env 
        fi
        
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

function installpipreqs_part1 ()
{
    # installs pip packaged listed in pip_requirements
    # assumes (and therefore REQUIRES) that the virtual environment is active
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
#     if [[ ( $with_pyside6 -eq 1 ) || ( $build_pyside6 -eq 1 ) ]] ; then
    if [[ $with_pyside6 -eq 1 ]] ; then
        if [[ $build_pyside6 -eq 1 ]] ; then
            reqfile="$installscriptdir"/pip_requirements_linux_1_pyside6_build.txt
        else
            reqfile="$installscriptdir"/pip_requirements_linux_1_pyside6_pypi.txt
        fi
    else
        reqfile="$installscriptdir"/pip_requirements_linux_1.txt
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pips1_done ] || [[ $reinstall_pips -gt 0 ]] ; then
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
        
#         echo -e "Using ${python_executable} as `whoami` to install PyPI packages\n"
        
        if [ -z ${uv_exec} ] ; then
            ${python_executable} -m pip install -r "$reqfile"
        else
            ${uv_exec} pip install -r "$reqfile"
        fi
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Cannot install required packages from PyPI. Bailing out. Goodbye!\n"
            exit 1
        else
            echo "pip packages installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pips1_done
            echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
        fi
    fi
}
function installpipreqs_part2 ()
{
    # installs pip packaged listed in pip_requirements
    # assumes (and therefore REQUIRES) that the virtual environment is active
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pips2_done ] || [[ $reinstall_pips -gt 0 ]] ; then
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
        
#         echo -e "Using ${python_executable} as `whoami` to install PyPI packages\n"
        
        if [ -z ${uv_exec} ] ; then
            ${python_executable} -m pip install -r "$installscriptdir"/pip_requirements_linux_2.txt
        else
            ${uv_exec} pip install -r "$installscriptdir"/pip_requirements_linux_2.txt
        fi
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Cannot install required packages from PyPI. Bailing out. Goodbye!\n"
            exit 1
        else
            echo "pip packages installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pips2_done
            echo -e "\n\n=====================\n# PyPI packages installed.\n=====================\n\n"
        fi
    fi
}

function dopyqt5 ()
{
    # Builds, then installs a pyqt5 wheel locally - I chose this approach because
    # on Linux, ready-made wheels (e.g. from PyPI) do not integrate well with the
    # native platform look and feel (for example, they notoriously miss the Breeze
    # style plugins). This approach also offers the possibility to opt-in/out 
    # installation of various Qt modules.
    #
    # Obviously this depends on having installed the appropriate build toolchain
    # and Qt5 development package on the platform, and adds some extra lead time
    # for having a ready environment — a small price to pay, IMHO.
    #
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
#     if [ ! -r ${VIRTUAL_ENV}/.pyqt5done ] || [[ $reinstall_pyqt5 -gt 0 ]] || [[ $build_pyqt5 -gt 0 ]] ; then
    if [ ! -r ${VIRTUAL_ENV}/.pyqt5build_done ] || [[ $reinstall_pyqt5 -gt 0 ]] ; then
        if [[ $build_pyqt5 -gt 0 ]] ; then
            mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src
            
            # figure out which qmake there is on the host platform
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
            
            echo "Using ${py_exec} as user `whoami` to build PyQt5"
            
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
            else
                ${sip_wheel_exec} --qmake=${qmake_binary} --confirm-license --qt-shared --verbose --build-dir ../PyQt5-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
            fi

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
                    echo "PyQt5 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pyqt5build_done
                    echo -e "\n\n=====================\n# Pyqt5 installed!\n=====================\n\n"
                fi
            fi
        
        else 
            pip install pyqt5
        fi
    fi
}

function dopyqt6 ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pyqt6done ] || [[ $reinstall_pyqt6 -gt 0 ]]; then
        if [[ $build_pyqt6 -gt 0 ]] ; then
            mkdir -p ${VIRTUAL_ENV}/src && cd ${VIRTUAL_ENV}/src
            
            findqmake6
            
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
            
            echo "Using ${py_exec} as `whoami` to build PyQt6"
            
            # NOTE: locate_pyqt6_src.py uses distlib to locate the (latest) source 
            # archive (i.e., the sdist) of PyQt6 - its file name typically ends with
            # .tar.gz
            pyqt6_src_url=`${py_exec} $installscriptdir/locate_pyqt6_src.py`
            pyqt6_src=`basename $pyqt6_src_url`
            
            pyqt6_src_dir=${pyqt6_src%.tar.gz}
            
            echo "PyQt6 source is in "${pyqt6_src_dir}
            
            # NOTE: the sdist might have been downloaded alreay - so check this first
            # before actually downloading
            if [ ! -r ${pyqt6_src} ] ; then
                wget ${pyqt6_src_url} && tar xzf ${pyqt6_src} 

                if [[ $? -ne 0 ]] ; then
                echo -e "Cannot obtain the PyQt6 source. Bailing out. Goodbye!\n"
                exit 1
                fi
            else
                if [ -d ${pyqt6_src_dir} ] ; then
                    rm -fr ${pyqt6_src_dir}
                fi
                tar xzf ${pyqt6_src}
            fi
            
            # NOTE: good practice is to create an out-of-source build tree, » ...
            pyqt6_build_dir="PyQt6-build"
            
            # NOTE: clear build dir if it exists -- best to start fresh
            if [ -d ${pyqt6_build_dir} ] ; then
                rm -fr ${pyqt6_build_dir}
            fi
            mkdir -p ${pyqt6_build_dir}
            
            # NOTE: » ... but run the build process INSIDE the expanded sdist dir
            # this is because sip-wheel will get extra options from there :)
            cd ${pyqt6_src_dir}
            
            echo "Generating PyQt6 wheel in "$(pwd)"..."
            
            # NOTE: 2023-03-23 14:03:48 - enable parallel jobs - to change, either:
            # • change the value of the --jobs option (e.g. half the number of 
            # cores in your system seems to be a good choice), or
            # • remove the --jobs option altogether
            if [[ $njobs -gt 0 ]] ; then
                ${sip_wheel_exec} --qmake=${qmake6_binary} --confirm-license --jobs $njobs --qt-shared --verbose --build-dir ../PyQt6-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
            else
                ${sip_wheel_exec} --qmake=${qmake6_binary} --confirm-license --qt-shared --verbose --build-dir ../PyQt6-build --disable QtQuick3D --disable QtRemoteObjects --disable QtBluetooth --pep484-pyi
            fi

            if [[ $? -ne 0 ]] ; then
                echo -e "sip Cannot build a PyQt6 wheel. Bailing out. Goodbye!\n"
                echo -e "You might want to upgrade sip and PyQt6-sip in this environment\n"
                echo -e " by calling \n\n"
                echo -e "pip install --upgrade sip\n"
                echo -e "pip install --upgrade PyQt6-sip\n\n"
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
                    echo -e "Cannot install the PyQt6 wheel; check console output. Goodbye!\n"
                    exit 1
                else
                    echo "PyQt6 built and installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.pyqt6done
                    echo -e "\n\n=====================\n# Pyqt6 installed!\n=====================\n\n"
                    
    #                 echo -e "\n\n Installing PyQtDataVisualization\n\n"
    #                 # NOTE: WARNING: 2023-07-19 00:12:27 avoid this !!!! 
    #                 pip install PyQtDataVisualization
                fi
            fi
        else
            pip install pyqt6
        fi
    fi
}

function dopyside6 ()
{
    if [[ -z "$VIRTUAL_ENV" ]] ; then
        echo -e "Not in an active environment! Goodbye!\n"
        exit 1
    fi
    
    if [ ! -r ${VIRTUAL_ENV}/.pyside6done ] || [[ $reinstall_pyside6 -eq 1 ]] ; then
        if [[ $build_pyside6 -eq 1 ]]; then
            get_qtpaths
            cd ${VIRTUAL_ENV}
            mkdir -p src && cd src
            # create build directory
            mkdir pyside6-build && cd pyside6-build
            # pre-create build sub directory as expected by setup.py in pyside-setup
            # BUT: make sure install/lib and install/lib64 point to the same directory
            # i.e., make lib64 a symbolic link to lib
            build_venv_subdir=`basename ${VIRTUAL_ENV}`
            mkdir ${build_venv_subdir} && cd ${build_venv_subdir}
            mkdir -p install && cd install
            mkdir -p lib
            ln -s lib lib64
            base_build_dir=${VIRTUAL_ENV}/src/pyside6-build
            cd ${VIRTUAL_ENV}/src
            git clone https://code.qt.io/pyside/pyside-setup
            cd pyside-setup && git checkout 6.9
            if [ -z ${uv_exec} ] ; then
                pip install -r requirements.txt
                pip install -r requirements-doc.txt
                pip install -r requirements-coin.txt
            else
                ${uv_exec} pip install -r requirements.txt
                ${uv_exec} pip install -r requirements-doc.txt
                ${uv_exec} pip install -r requirements-coin.txt
            fi
            qtinfopatch=${installscriptdir}/pyside6/qtinfo.diff
            patch build_scripts/qtinfo.py ${qtinfopatch}

            if [ -z ${uv_exec} ] ; then
                python setup.py build --qtpaths=${full_path_to_qtpaths} --build-tests --build-base=${base_build_dir} --parallel=8
            else
                uv run setup.py build --qtpaths=${full_path_to_qtpaths} --build-tests --build-base=${base_build_dir} --parallel=8
            fi
            
            if [[ $? -ne 0 ]] ; then
                echo -e "\nCould not build PySide6. Goodbye!\n"
                exit 1
            fi
            build_dir=${base_build_dir}/`basename ${VIRTUAL_ENV}`
            python create_wheels.py --no-examples --build-dir=${build_dir}
            
            if [[ $? -ne 0 ]] ; then
                echo -e "\nCould not create PySide6 wheels. Goodbye!\n"
                exit 1
            fi
            
            if [ -z ${uv_exec} ] ; then
                pip install ${VIRTUAL_ENV}/src/pyside-setup/dist/*.whl
            else
                uv pip install ${VIRTUAL_ENV}/src/pyside-setup/dist/*.whl
            fi
            
            if [[ $? -ne 0 ]] ; then
                echo -e "\nCould not install PySide6 wheels. Goodbye!\n"
                exit 1
            else
                echo -e "\nPySide6 wheel have been successfully built and installed"
            fi
            
        else
            if [ -z ${uv_exec} ] ; then
                pip install PySide6
            else
                ${uv_exec} pip install PySide6
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
    
    if [ ! -r ${VIRTUAL_ENV}/.vigra_done ] || [[ $reinstall_vigra -gt 0 ]]; then
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
        
        make && make install
        
        if [[ $? -ne 0 ]] ; then
            echo -e "Cannot build vigra; check console output. Bailing out. Goodbye!\n"
            exit 1
        else
            echo "VIGRA installed on "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.vigra_done
            echo -e "\n\n=====================\n# Building vigra DONE!\n=====================\n\n"
        fi
    fi
    
    
}

function make_desktop_entry ()
{
target_dir=${HOME}/bin
if [[ $with_pyside6 -eq 1 ]] ; then
    desktopfile=Scipyen-pyside6-pypi.desktop
    scriptfile=${target_dir}/scipyen-pysid6-pypi
elif [[ $build_pyside6 -eq 1 ]] ; then
    desktopfile=Scipyen-pyside6-build.desktop
    scriptfile=${target_dir}/scipyen-pysid6-build
else 
    desktopfile=Scipyen.desktop
    scriptfile=${target_dir}/scipyen
fi

if [ ! -r ${VIRTUAL_ENV}/.desktop_done ] || [[ $reinstall_desktop -gt 0 ]] ; then
# if [[ `id -u` -eq 0 ]] ; then
# target_dir=/usr/local/bin
# else
# fi
tmpfiledir=$(mktemp -d)
# tmpfile=${tmpfiledir}/cezartigaret-Scipyen.desktop
# tmpfile=${tmpfiledir}/Scipyen.desktop
# script=${target_dir}/scipyen
tmpfile=${tmpfiledir}/${desktopfile}
script=${target_dir}/${scriptfile}
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
echo "Scipyen Desktop file has been installed "$(date '+%Y-%m-%d_%H-%M-%s') > ${VIRTUAL_ENV}/.desktop_done
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

if [[ -z "$VIRTUAL_ENV" ]] ; then
    echo -e "Not in an active environment! Goodbye!\n"
    exit 1
fi

dt=`date '+%Y-%m-%d_%H-%M-%s'`

if [[ $with_pyside6 -eq 1 ]] ; then
    if [[ $build_pyside6 -eq 1 ]] ; then
        rcfile=${HOME}/.scipyen_pyside6_build_rc
    else 
        rcfile=${HOME}/.scipyen_pyside6_pypi_rc
    fi
else
    rcfile=${HOME}/.scipyenrc
fi

echo -e "\nCreating ${rcfile}\n"

py_exec=${python_exec}
# if [ -r ${HOME}/.scipyenrc ] ; then
if [ -r ${rcfile} ] ; then
# make a backup copy of .scipyenrc
shopt -s lastpipe
# echo "Copying ${HOME}/.scipyenrc to ${HOME}/.scipyenrc.$dt"
# cp ${HOME}/.scipyenrc ${HOME}/.scipyenrc.$dt
echo "Copying ${rcfile} to ${rcfile}.$dt"
cp ${rcfile} ${rcfile}.$dt
fi
# cat<<END > ${HOME}/.scipyenrc
cat<<END > ${rcfile}
scipyact () {
source ${VIRTUAL_ENV}/bin/activate
export LD_LIBRARY_PATH=${VIRTUAL_ENV}/lib:${VIRTUAL_ENV}/lib64:$LD_LIBRARY_PATH
echo -e "The Python virtual environment in ${VIRTUAL_ENV} is now active.\nTo exit this environment call 'deactivate'"
}
END
shopt -u lastpipe
}

function update_bashrc () 
{
if [[ $with_pyside6 -eq 1 ]] ; then
    rcfile=${HOME}/.scipyen_pyside6_pypi_rc
elif [[ $build_pyside6 -eq 1 ]] ; then
    rcfile=${HOME}/.scipyen_pyside6_build_rc
else 
    rcfile=${HOME}/.scipyenrc
fi

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
# cat ${HOME}/.bashrc | grep "source ${HOME}/.scipyenrc" | read source_set
cat ${HOME}/.bashrc | grep "source ${rcfile}" | read source_set
# echo "source_set="$source_set
if [ -z "${source_set}" ]; then
# .scipyenrc not sourced from .bashrc => backup .bashrc, then append a line to
# source .scipyenrc in there
echo "Copying ${HOME}/.bashrc to ${HOME}/.bashrc.$dt"
cp ${HOME}/.bashrc ${HOME}/.bashrc.$dt
# echo "source ${HOME}/.scipyenrc" >> ${HOME}/.bashrc
echo "source ${rcfile}/" >> ${HOME}/.bashrc
echo ".bashrc has been modified in ${HOME}"
echo "Sourcing ${HOME}/.bashrc"
source ${HOME}/.bashrc
fi
shopt -u lastpipe
fi
# if [ ! -r ${HOME}/.bashrc ]; then
# cat<<END > ${HOME}/.bashrc
# source ${HOME}/.scipyenrc
# END
# echo ".bashrc has been created in ${HOME}"
# echo "Sourcing ${HOME}/.bashrc"
# source ${HOME}/.bashrc
# else
# shopt -s lastpipe
# # check if .scipyenrc is sourced from .bashrc
# cat ${HOME}/.bashrc | grep "source ${HOME}/.scipyenrc" | read source_set
# # echo "source_set="$source_set
# if [ -z "${source_set}" ]; then
# # .scipyenrc not sourced from .bashrc => backup .bashrc, then append a line to
# # source .scipyenrc in there
# echo "Copying ${HOME}/.bashrc to ${HOME}/.bashrc.$dt"
# cp ${HOME}/.bashrc ${HOME}/.bashrc.$dt
# echo "source ${HOME}/.scipyenrc" >> ${HOME}/.bashrc
# echo ".bashrc has been modified in ${HOME}"
# echo "Sourcing ${HOME}/.bashrc"
# source ${HOME}/.bashrc
# fi
# shopt -u lastpipe
# fi
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

function get_qtpaths ()
{
declare -a ver_array
qtpaths_exec=`which qtpaths`
ver_array=( `${qtpaths_exec} --qt-version` )
qtver=${ver_array}
oldifs=$IFS
IFS=-.
read major minor micro <<EOF
${qtver##*-}
EOF
IFS=$oldifs
if [[ ${major} -lt 6 ]] ; then
qtpaths_exec=`which qtpaths6`
ver_array=( `${qtpaths_exec} --qt-version` )
qtver=${ver_array}
oldifs=$IFS
IFS=-.
read major minor micro <<EOF
${qtver##*-}
EOF
IFS=$oldifs
fi
if [[ ${major} -ne 6 ]] ; then
# echo "Cannot find qtpaths for Qt6. Bailing out..."
exit 1
fi
full_path_to_qtpaths=`readlink -f ${qtpaths_exec}`
}

function make_launch_script () 
{
target_dir=${HOME}/bin

if [[ $with_pyside6 -eq 1 ]] ; then
    if [[ $build_pyside6 -eq 1 ]] ; then
        scriptfile=${target_dir}/scipyen-pyside6-build
        launchcmd="${scipyensrcdir}/scipyen.py pyside6"
        
    else 
        scriptfile=${target_dir}/scipyen-pyside6-pypi
        launchcmd="${scipyensrcdir}/scipyen.py pyside6"
    fi
else
    scriptfile=${target_dir}/scipyen
    launchcmd=${scipyensrcdir}/scipyen.py
fi


echo -e "\nCreating ${scriptfile} launch script \n"

mkdir -p ${target_dir}
# if [ -r ${target_dir}/scipyen ] ; then
#     dt=`date '+%Y-%m-%d_%H-%M-%s'`
#     mv ${target_dir}/scipyen ${target_dir}/scipyen.$dt
# fi
if [ -r ${scriptfile} ] ; then
    dt=`date '+%Y-%m-%d_%H-%M-%s'`
    mv ${scriptfile} ${scriptfile}.$dt
fi
shopt -s lastpipe

# cat <<END > ${target_dir}/scipyen 
cat <<END > ${scriptfile} 
#! /bin/sh
if [ -z \${VIRTUAL_ENV} ]; then
source ${virtual_env}/bin/activate
fi
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
END
if [[ ( $with_pyside6 -eq 1 ) || ( $build_pyside6 -eq 1 ) ]] ; then
cat <<END >> ${scriptfile} 
export QT_API="pyside6"
END
fi
cat <<END >> ${scriptfile} 
${python_executable} -Xfrozen_modules=off ${launchcmd} "\$*"
END
shopt -u lastpipe
# chmod +x ${target_dir}/scipyen 
chmod +x ${scriptfile}
echo -e "Scipyen startup script created in ${target_dir} \n"
}

#### BEGIN Main script action happens here ###
#

if [[ `id -u` -eq 0 ]] ; then
echo -e "This script MUST be run as regular user, NOT as root!"
exit 1
fi
# start_time=`date +%s`
SECONDS=0
get_pyver
uv_exec=`which uv`


virtual_env_pfx="scipyenv"
install_dir=${HOME}
realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
docdir=${scipyendir}/doc
installscriptdir=${scipyendir}/setup_env
scipyensrcdir=${scipyendir}/src/scipyen
using_python=""
install_neuron=0
use_pypi_neuron=1
use_core_neuron=0
with_pyqt5=1
build_pyqt5=1
reinstall_pyqt5=0
with_pyqt6=0
reinstall_pyqt6=0
build_pyqt6=0
with_pyside6=0
build_pyside6=0
reinstall_pyside6=0
install_fenicsx=0
njobs=4
reinstall_vigra=0
reinstall_neuron=0
reinstall_fenicsx=0
reinstall_pips=0
reinstall_desktop=0
refresh_git_repos=0
make_dist=0

target_dir=${HOME}/bin

rcfile=${HOME}/.scipyenrc
scriptfile=${target_dir}/scipyen
desktopfile=Scipyen.desktop

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
        --with_pyqt5)
        with_pyqt5=1
        build_pyqt5=0 
        with_pyqt6=0
        build_pyqt6=0
        with_pyside6=0
        build_pyside6=0
        shift
        ;;
        --with_pyqt6)
        with_pyqt6=1
        build_pyqt6=0 
        with_pyqt5=0
        build_pyqt5=0 
        with_pyside6=0
        build_pyside6=0
        shift
        ;;
        --with_pyside6)
        with_pyqt6=0
        build_pyqt6=0 
        with_pyqt5=0
        build_pyqt5=0 
        with_pyside6=1
        build_pyside6=0
        shift
        ;;
        --build_pyqt5)
        with_pyqt5=1
        build_pyqt5=1
        with_pyqt6=0
        build_pyqt6=0
        with_pyside6=0
        build_pyside6=0
        shift
        ;;
        --build_pyqt6)
        with_pyqt6=1
        build_pyqt6=1
        with_pyqt5=0
        build_pyqt5=0 
        with_pyside6=0
        build_pyside6=0
        shift
        ;;
        --build_pyside6)
        with_pyqt6=0
        build_pyqt6=0
        with_pyqt5=0
        build_pyqt5=0 
        with_pyside6=1
        build_pyside6=1
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
            build_pyqt5=0
            reinstall_pyqt6=0
            build_pyqt6=0
            reinstall_pyside6=0
            build_pyside6=0
            ;;
            build_pyqt5)
            reinstall_pyqt5=1
            build_pyqt5=1
            reinstall_pyqt6=0
            build_pyqt6=0
            reinstall_pyside6=0
            build_pyside6=0
            ;;
            pyqt6)
            reinstall_pyqt6=1
            build_pyqt6=0
            ;;
            build_pyqt6)
            reinstall_pyqt5=0
            build_pyqt5=0
            reinstall_pyqt6=1
            build_pyqt6=1
            reinstall_pyside6=0
            build_pyside6=0
            ;;
            pyside6)
            reinstall_pyqt5=0
            build_pyqt5=0
            reinstall_pyqt6=0
            build_pyqt6=0
            reinstall_pyside6=1
            build_pyside6=0
            ;;
            build_pyside6)
            reinstall_pyqt5=0
            build_pyqt5=0
            reinstall_pyqt6=0
            build_pyqt6=0
            reinstall_pyside6=1
            build_pyside6=1
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

# if  [[ ( $with_pyside6 -eq 1 ) || ( $build_pyside6 -eq 1 ) ]] ; then
if  [[ $with_pyside6 -eq 1 ]] ; then
    if [[  $build_pyside6 -eq 1 ]] ; then
        virtual_env_pfx=${virtual_env_pfx}_pyside6_build
    else
        virtual_env_pfx=${virtual_env_pfx}_pyside6_pypi
    fi
fi

if ! [ -v VIRTUAL_ENV ] ; then
    virtual_env=${install_dir}/${virtual_env_pfx}
    python_exec="python${major}.${minor}"
else
    virtual_env=$VIRTUAL_ENV
    python_exec=$VIRTUAL_ENV/bin/"python${major}"
fi

python_executable=${python_exec}
echo -e "virtual_env is ${virtual_env}"
echo -e "python executable: ${python_executable}"


# makes a virtual environment and activates it
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

# exit

if [[ ( -n "$VIRTUAL_ENV" ) && ( -d "$VIRTUAL_ENV" ) ]] ; then
    echo -e "Checking for, or making 'src' directory inside $VIRTUAL_ENV ...\n"
    mkdir -p "$VIRTUAL_ENV/src" && cd "$VIRTUAL_ENV/src"
    
    # install pip requirements NOTE: 2023-06-25 10:55:09 FIXME how to pass the virtualenv python to builder when run as root?
    installpipreqs_part1
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Could not install pip requirements (part 1); check the console for messages. Goodbye!\n"
        exit 1
    fi
    
    # NOTE: we need at least pyqt5; on Linux we build the wheel from scratch unless
    # specifically requested
    
    # NOTE/BUG 2025-03-12 00:37:03 FIXME
    # after upgrading platform OS (with full migration to python3.13)
    # the PyQt5 build has issues with xcb and wayland plugins (i.e., they're not found)
    #
    # NOTE: 2025-03-13 11:01:58 FIXED
    # • using python3.13 (took a while until PyPI packages migrated to this version)
    # may take a while until conda packages are also uptodate :)
    # • splitting pip package installation in two batches (installpipreqs_part1 & installpipreqs_part2
    # see changelog above)
    
    if  [[ ( $with_pyside6 -eq 1 ) || ( $build_pyside6 -eq 1 ) ]]  ; then
        dopyside6
    else
        doipyqt5 
    fi
    
    # NOTE: 2025-03-13 11:01:07 TODO/FIXME
#     dopyqt6 
#     dopyside6 # TODO

    installpipreqs_part2

    dovigra
    
    if [ $install_neuron -ne 0 ] ; then
        doneuron
    fi
    
    if  [ $install_fenicsx -ne 0 ] ; then
        dofenicsx
    fi
    
    # make scripts
    make_scipyenrc
    
    make_launch_script
    
    make_desktop_entry
    
    # NOTE: install console color schemes
    cd $scipyendir/src/scipyen/gui/scipyen_console_styles
    if [ -x ${uv_exec} ] ; then
        pip install .
    else
        ${uv_exec} pip install .
    fi
    cd $scipyendir
    
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
echo "Before using Scipyen, either restart the terminal, or call 'source ${rcfile}'"
echo "Scipyen can be launched by calling ${scriptfile}"

#
#### END   Main script action happens here ###



