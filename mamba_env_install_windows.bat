echo OFF
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
rem Leave THIS LINE HERE; jus comment out or change the goto label
rem  goto make_desktop_shortcut
rem  set pip_reqs=%mydir%\setup_env\pip_requirements_win.txt
:create_env
set default_env_path="c:\scipyenv"
set /P env_path="Enter the full path name of the new environment (no spaces, please, default is: %default_env_path%): "
if [%env_path%] equ [] set env_path=%default_env_path%
echo Creating mamba environment %env_path%
call mamba create --prefix %env_path% --file mambaprojects\win32\scipyenv.yml || goto eof
rem  call mamba create -n "scipyenv" --file mambaprojects\win32\scipyenv.yml || goto eof
:activate_env
echo:
echo Activating mamba environment %env_path%
call conda deactivate
call mamba activate %env_path% || goto eof
rem  :install_pips - dealt with via the scipyenv.yml file
echo:
rem  echo Installing additional PyPI packages
rem  call pip install -r %pip_reqs% || goto eof
:install_own_console_styles
cd %mydir%\src\scipyen\gui\scipyen_console_styles || goto eof
call pip install .  || goto eof
cd %mydir%  || goto eof
:make_scripts
echo:
echo Creating batch scripts
powershell -ExecutionPolicy Bypass -File %mydir%\setup_env\make_scipyen_batch_scripts.ps1 || goto eof
:make_desktop_shortcut
echo:
echo Creating desktop link
powershell -ExecutionPolicy Bypass -File %mydir%\setup_env\make_link.ps1 %mydir%  || goto eof
echo:
echo Scipyen can now be launched from the desktop icon


:eof
rem  endlocal
