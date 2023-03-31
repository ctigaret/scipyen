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
call conda activate %env_name%
call conda config --add channels conda-forge
call conda install --prefix %env_name% -y --file %conda_reqs%
rem  call conda install --previx %env_name% -y jupyter
rem  call conda install --previx %env_name% -y jupyter_cms
rem  call conda install --previx %env_name% -y jupyter_qtconsole_colorschemes
rem  call conda install --previx %env_name% -y numpy
rem  call conda install --previx %env_name% -y matplotlib
rem  call conda install --previx %env_name% -y scipy
rem  call conda install --previx %env_name% -y sympy
rem  call conda install --previx %env_name% -y h5py
rem  call conda install --previx %env_name% -y pyqtgraph
rem  call conda install --previx %env_name% -y pandas
rem  call conda install --previx %env_name% -y quantities
rem  call conda install --previx %env_name% -y python-neo
rem  call conda install --previx %env_name% -y -c conda-forge vigra
rem  call conda install --previx %env_name% -y cmocean
rem  call conda install --previx %env_name% -y confuse
rem  call conda install --previx %env_name% -y inflect
rem  call conda install --previx %env_name% -y seaborn
rem  call conda install --previx %env_name% -y pingouin
rem  call conda install --previx %env_name% -y qimage2ndarray
rem  call conda install --previx %env_name% -y pyxdg
REM OPTIONAL PACKAGES FROM CONDA
REM call conda install --previx %env_name% -y qdarkstyle
rem  call conda install --previx %env_name% -y bokeh
rem  call conda install --previx %env_name% -y scikit-image
rem  call conda install --previx %env_name% -y scikit-learn
rem  call conda install --previx %env_name% -y dill
rem  call conda install --previx %env_name% -y jupyterthemes
rem  call conda install --previx %env_name% -y libNeuroML
rem  call conda install --previx %env_name% -y matlab_kernel
rem  call conda install --previx %env_name% -y octave-kernel




call pip install -r %pip_reqs%

rem  :eof
rem  endlocal
