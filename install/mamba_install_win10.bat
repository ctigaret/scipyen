rem  # -*- coding: utf-8 -*-
rem  # SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
rem  # SPDX-License-Identifier: GPL-3.0-or-later
rem  # SPDX-License-Identifier: LGPL-2.1-or-later
rem  
echo This script requires mambaforge installed from https://github.com/conda-forge/miniforge#mambaforge
echo run this from a mamba prompt launched as administrator
@echo off
rem  setlocal enabledelayedexpansion enableextensions
set mypath=%0
set mydir=%~dp0
set conda_reqs=%mydir%\conda_requirements_win.txt
set pip_reqs=%mydir%\pip_requirements_win.txt
set default_env_name="e:\scipyenv"
set /P env_name="Enter the full path name of the new environment (no spaces, please, e.g. %default_env_name%): "
if [%env_name%] equ [] set env_name=%default_env_name%
echo
echo Creating mamba environment %env_name%
call mamba create -y --prefix %env_name% python=3.11 || goto eof
echo
echo Activating mamba environment %env_name%
call mamba activate %env_name% || goto eof
call mamba config --add channels conda-forge || goto eof
rem  call mamba install --prefix %env_name% -y --file %conda_reqs%
rem  echo Installing PyQt5 and QtPy
rem  call mamba install --prefix %env_name% -y PyQt5 || goto eof
rem  call mamba install --prefix %env_name% -y PyQt5-sip || goto eof
rem  call mamba install --prefix %env_name% -y QtPy || goto eof
echo
echo Installing jupyter
call mamba install --prefix %env_name% -y jupyter || goto eof
rem  echo Installing jupyter_cms
rem  call mamba install --prefix %env_name% -y jupyter_cms || goto eof
echo
echo Installing color schemes for jupyter qtconsole
call mamba install --prefix %env_name% -y jupyter_qtconsole_colorschemes || goto eof
echo
echo Installing jupyter themes
call mamba install --prefix %env_name% -y jupyterthemes || goto eof
echo
echo Installing numpy
call mamba install --prefix %env_name% -y numpy || goto eof
echo
echo Installing matplotlib
call mamba install --prefix %env_name% -y matplotlib || goto eof
echo
echo Installing scipy
call mamba install --prefix %env_name% -y scipy || goto eof
echo
echo Installing sympy
call mamba install --prefix %env_name% -y sympy || goto eof
echo
echo Installing h5py
call mamba install --prefix %env_name% -y h5py || goto eof
echo
echo Installing pyqtgraph
call mamba install --prefix %env_name% -y pyqtgraph || goto eof
echo
echo Installing pywavelets
call mamba install --prefix %env_name% -y PyWavelets || goto eof
echo
echo Installing pandas
call mamba install --prefix %env_name% -y pandas || goto eof
echo
echo Installing quantities
call mamba install --prefix %env_name% -y quantities || goto eof
echo
echo Installing python-neo
call mamba install --prefix %env_name% -y python-neo || goto eof
echo
echo Installing vigra
call mamba install --prefix %env_name% -y -c conda-forge vigra || goto eof
echo
echo Installing cmocean
call mamba install --prefix %env_name% -y cmocean || goto eof
echo
echo Installing confuse
call mamba install --prefix %env_name% -y confuse || goto eof
echo
echo Installing inflect
call mamba install --prefix %env_name% -y inflect || goto eof
echo
echo Installing seaborn
call mamba install --prefix %env_name% -y seaborn || goto eof
echo
echo Installing pingouin
call mamba install --prefix %env_name% -y pingouin || goto eof
echo
echo Installing qimage2ndarray
call mamba install --prefix %env_name% -y qimage2ndarray || goto eof
echo
echo Installing pyxdg
call mamba install --prefix %env_name% -y pyxdg || goto eof
REM OPTIONAL PACKAGES FROM CONDA
REM call mamba install --prefix %env_name% -y qdarkstyle
echo
echo Installing bokeh
call mamba install --prefix %env_name% -y bokeh || goto eof
echo
echo Installing scikit-image
call mamba install --prefix %env_name% -y scikit-image || goto eof
echo
echo Installing scikit-learn
call mamba install --prefix %env_name% -y scikit-learn || goto eof
echo
echo Installing dill
call mamba install --prefix %env_name% -y dill || goto eof
echo
echo Installing libNeuroML
call mamba install --prefix %env_name% -y libNeuroML || goto eof
echo
echo Installing matlab kernel
call mamba install --prefix %env_name% -y matlab_kernel || goto eof
echo
echo Installing octave kernel
call mamba install --prefix %env_name% -y octave_kernel || goto eof
echo
echo Installing PyInstaller
call mamba install --prefix %env_name% -y pyinstaller || goto eof

echo
echo Installing additional PyPI packages
call pip install -r %pip_reqs% || goto eof
call pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip || goto eof

powershell -ExecutionPolicy Bypass -File %mydir%\make_link.ps1 %mydir%  || goto eof
echo Scipyen can now be launched from the desktop icon

powershell -ExecutionPolicy Bypass -File %mydir%\doc\install\make_scipyen_batch_scripts.ps1 %mydir%  || goto eof
echo Scipyen (git clone) can now be called from the command prompt by executing the `scipyen` command
echo Scipyen pyrthon environent can be activates from the command prompt by executing the `scipyact` command

:eof
rem  endlocal
