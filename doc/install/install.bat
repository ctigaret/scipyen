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
rem  call conda install --prefix %env_name% -y --file %conda_reqs%
call conda install --prefix %env_name% -y jupyter
call conda install --prefix %env_name% -y jupyter_cms
call conda install --prefix %env_name% -y jupyter_qtconsole_colorschemes
call conda install --prefix %env_name% -y numpy
call conda install --prefix %env_name% -y matplotlib
call conda install --prefix %env_name% -y scipy
call conda install --prefix %env_name% -y sympy
call conda install --prefix %env_name% -y h5py
call conda install --prefix %env_name% -y pyqtgraph
call conda install --prefix %env_name% -y PyWavelets
call conda install --prefix %env_name% -y pandas
call conda install --prefix %env_name% -y quantities
call conda install --prefix %env_name% -y python-neo
call conda install --prefix %env_name% -y -c conda-forge vigra
call conda install --prefix %env_name% -y cmocean
call conda install --prefix %env_name% -y confuse
call conda install --prefix %env_name% -y inflect
call conda install --prefix %env_name% -y seaborn
call conda install --prefix %env_name% -y pingouin
call conda install --prefix %env_name% -y qimage2ndarray
call conda install --prefix %env_name% -y pyxdg
REM OPTIONAL PACKAGES FROM CONDA
REM call conda install --prefix %env_name% -y qdarkstyle
call conda install --prefix %env_name% -y bokeh
call conda install --prefix %env_name% -y scikit-image
call conda install --prefix %env_name% -y scikit-learn
call conda install --prefix %env_name% -y dill
call conda install --prefix %env_name% -y jupyterthemes
call conda install --prefix %env_name% -y libNeuroML
call conda install --prefix %env_name% -y matlab_kernel
call conda install --prefix %env_name% -y octave-kernel




call pip install -r %pip_reqs%

rem  :eof
rem  endlocal
