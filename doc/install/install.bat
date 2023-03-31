@echo off
rem  setlocal enabledelayedexpansion enableextensions
set mypath=%0
set mydir=%~dp0
set conda_reqs=%mydir%\conda_requirements_win.txt
set pip_reqs=%mydir%\pip_requirements_win.txt
set default_env_name="e:\scipyenv_conda"
set /P env_name=Enter the full path name of the new environment (no spaces, please, e.g. %default_env_name%):
if [%env_name%] equ [] set env_name=%default_env_name%
echo %env_name%
call conda create --prefix %env_name%
call conda install --prefix %env_name% -y --file %conda_reqs%
call conda activate %env_name%
call pip install -r %pip_reqs%

rem  :eof
rem  endlocal
