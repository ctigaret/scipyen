rem  # -*- coding: utf-8 -*-
rem  # SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
rem  # SPDX-License-Identifier: GPL-3.0-or-later
rem  # SPDX-License-Identifier: LGPL-2.1-or-later
rem  
echo This script requires mambaforge installed from https://github.com/conda-forge/miniforge#mambaforge
echo and must be run from a mamba (Microforge) prompt launched as administrator
@echo off
rem  setlocal enabledelayedexpansion enableextensions
set mypath=%0
set mydir=%~dp0
rem  set conda_reqs=%mydir%\install\conda_requirements_win.txt
set pip_reqs=%mydir%\setup_env\pip_requirements_win.txt
set default_env_name="c:\scipyenv"
set /P env_name="Enter the full path name of the new environment (no spaces, please, default is: %default_env_name%): "
if [%env_name%] equ [] set env_name=%default_env_name%
echo Creating mamba environment %env_name%
call mamba create -y --prefix %env_name% python=3.11 || goto eof
echo Activating mamba environment %env_name%
call mamba activate %env_name% || goto eof
call mamba config --add channels conda-forge || goto eof
rem  call mamba install --prefix %env_name% -y --file %conda_reqs%
echo:
echo Installing jupyter qtconsole jupyterthemes matplotlib
call mamba install --prefix %env_name% -y jupyter qtconsole jupyterthemes || goto eof
echo:
echo Installing jupyter_cms
call mamba install --prefix %env_name% -y -c conda-forge jupyter_cms jupyter_qtconsole_colorschemes || goto eof
rem  echo Installing jupyter_cms
rem  call mamba install --prefix %env_name% -y jupyter_cms || goto eof
rem  echo:
rem  echo Installing jupyter qtconsole
rem  call mamba install --prefix %env_name% -y jupyter || goto eof
rem  echo:
rem  echo Installing color schemes for jupyter qtconsole
rem  call mamba install --prefix %env_name% -y jupyter_qtconsole_colorschemes || goto eof
rem  echo:
rem  echo Installing jupyter themes
rem  call mamba install --prefix %env_name% -y jupyterthemes || goto eof
rem  echo:
rem  echo Installing matplotlib
rem  call mamba install --prefix %env_name% -y matplotlib || goto eof
echo:
call mamba install --prefix %env_name% -y -c conda-forge biopython brainglobe-atlasapi napari brainglobe-napari-io brainglobe-segmentation brainrender-napari || goto eof
echo:
echo Installing vigra
call mamba install --prefix %env_name% -y -c conda-forge vigra researchpy pyserial termcolor termcolor2 colorama pickleshare shapely pywnb scikit-bio scikit-learn scikit-image|| goto eof
rem  rem  echo:
rem  rem  echo Installing numpy
rem  rem  call mamba install --prefix %env_name% -y numpy || goto eof
rem  echo:
rem  echo Installing scipy
rem  call mamba install --prefix %env_name% -y scipy || goto eof
echo:
echo Installing sympy pyqtgraph pywavelets qimage2ndarray
call mamba install --prefix %env_name% -y sympy pyqtgraph qimage2ndarray || goto eof
rem  echo:
rem  echo Installing h5py
rem  call mamba install --prefix %env_name% -y h5py || goto eof
rem  echo:
rem  echo Installing pyqtgraph
rem  call mamba install --prefix %env_name% -y pyqtgraph || goto eof
rem  echo:
rem  echo Installing pywavelets
rem  call mamba install --prefix %env_name% -y PyWavelets || goto eof
rem  echo:
rem  echo Installing pandas
rem  call mamba install --prefix %env_name% -y pandas || goto eof
echo:
echo Installing quantities and python-neo
call mamba install --prefix %env_name% -y quantities python-neo || goto eof
rem  echo:
rem  echo Installing python-neo
rem  call mamba install --prefix %env_name% -y python-neo || goto eof
echo:
echo Installing cmocean
call mamba install --prefix %env_name% -y cmocean confuse inflect seaborn pingouin || goto eof
rem  echo:
rem  echo Installing confuse
rem  call mamba install --prefix %env_name% -y confuse || goto eof
rem  echo:
rem  echo Installing inflect
rem  call mamba install --prefix %env_name% -y inflect || goto eof
rem  echo:
rem  echo Installing seaborn
rem  call mamba install --prefix %env_name% -y seaborn || goto eof
rem  echo:
rem  echo Installing pingouin
rem  call mamba install --prefix %env_name% -y pingouin || goto eof
rem  echo:
rem  echo Installing qimage2ndarray
rem  call mamba install --prefix %env_name% -y qimage2ndarray || goto eof
echo:
echo Installing pyxdg
call mamba install --prefix %env_name% -y pyxdg || goto eof
REM OPTIONAL PACKAGES FROM CONDA
REM call mamba install --prefix %env_name% -y qdarkstyle
rem  echo:
rem  echo Installing bokeh
rem  call mamba install --prefix %env_name% -y bokeh || goto eof
rem  echo:
rem  echo Installing scikit-image
rem  call mamba install --prefix %env_name% -y scikit-image || goto eof
rem  echo:
rem  echo Installing scikit-learn
rem  call mamba install --prefix %env_name% -y scikit-learn || goto eof
echo:
echo Installing dill libNeuroML
call mamba install --prefix %env_name% -y dill libNeuroML || goto eof
rem  echo:
rem  echo Installing libNeuroML
rem  call mamba install --prefix %env_name% -y libNeuroML || goto eof
echo:
echo Installing matlab & octave kernels
call mamba install --prefix %env_name% -y matlab_kernel octave_kernel || goto eof
rem  echo:
rem  echo Installing octave kernel
rem  call mamba install --prefix %env_name% -y octave_kernel || goto eof
echo:
echo Installing PyInstaller
call mamba install --prefix %env_name% -y pyinstaller || goto eof
echo:
echo Installing additional PyPI packages
call pip install -r %pip_reqs% || goto eof
echo:
echo Creating batch scripts
powershell -ExecutionPolicy Bypass -File %mydir%\install\make_scipyen_batch_scripts.ps1 || goto eof
echo:
echo Creating desktop link
powershell -ExecutionPolicy Bypass -File %mydir%\install\make_link.ps1 %mydir%  || goto eof
echo:
echo Scipyen can now be launched from the desktop icon


:eof
rem  endlocal
