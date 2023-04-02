@echo off
rem  setlocal enabledelayedexpansion enableextensions
set mypath=%0
set mydir=%~dp0
set conda_reqs=%mydir%\conda_requirements_win.txt
set pip_reqs=%mydir%\pip_requirements_win.txt
set default_env_name="e:\scipyenv"
set /P env_name="Enter the full path name of the new environment (no spaces, please, e.g. %default_env_name%): "
if [%env_name%] equ [] set env_name=%default_env_name%
echo Creating conda environment %env_name%
call conda create -y --prefix %env_name% python=3.11 || exit
echo Activating conda environment %env_name%
call conda activate %env_name% || exit
call conda config --add channels conda-forge || exit
rem  call conda install --prefix %env_name% -y --file %conda_reqs%
echo Installing jupyter
call conda install --prefix %env_name% -y jupyter || exit
echo Installing jupyter_cms
call conda install --prefix %env_name% -y jupyter_cms || exit
echo Installing color schemes for jupyter qtconsole
call conda install --prefix %env_name% -y jupyter_qtconsole_colorschemes || exit
echo Installing jupyter themes
call conda install --prefix %env_name% -y jupyterthemes || exit
echo Installing numpy
call conda install --prefix %env_name% -y numpy || exit
echo Installing matplotlib
call conda install --prefix %env_name% -y matplotlib || exit
echo Installing scipy
call conda install --prefix %env_name% -y scipy || exit
echo Installing sympy
call conda install --prefix %env_name% -y sympy || exit
echo Installing h5py
call conda install --prefix %env_name% -y h5py || exit
echo Installing pyqtgraph
call conda install --prefix %env_name% -y pyqtgraph || exit
echo Installing pywavelets
call conda install --prefix %env_name% -y PyWavelets || exit
echo Installing pandas
call conda install --prefix %env_name% -y pandas || exit
echo Installing quantities
call conda install --prefix %env_name% -y quantities || exit
echo Installing python-neo
call conda install --prefix %env_name% -y python-neo || exit
echo Installing vigra
call conda install --prefix %env_name% -y -c conda-forge vigra || exit
echo Installing cmocean
call conda install --prefix %env_name% -y cmocean || exit
echo Installing confuse
call conda install --prefix %env_name% -y confuse || exit
echo Installing inflect
call conda install --prefix %env_name% -y inflect || exit
echo Installing seaborn
call conda install --prefix %env_name% -y seaborn || exit
echo Installing pingouin
call conda install --prefix %env_name% -y pingouin || exit
echo Installing qimage2ndarray
call conda install --prefix %env_name% -y qimage2ndarray || exit
echo Installing pyxdg
call conda install --prefix %env_name% -y pyxdg || exit
REM OPTIONAL PACKAGES FROM CONDA
REM call conda install --prefix %env_name% -y qdarkstyle
echo Installing bokeh
call conda install --prefix %env_name% -y bokeh || exit
echo Installing scikit-image
call conda install --prefix %env_name% -y scikit-image || exit
echo Installing scikit-learn
call conda install --prefix %env_name% -y scikit-learn || exit
echo Installing dill
call conda install --prefix %env_name% -y dill || exit
echo Installing libNeuroML
call conda install --prefix %env_name% -y libNeuroML || exit
echo Installing matlab kernel
call conda install --prefix %env_name% -y matlab_kernel || exit
echo Installing octave kernel
call conda install --prefix %env_name% -y octave-kernel || exit

echo Installing additional PyPI packages
call pip install -r %pip_reqs% || exit

powershell -ExecutionPolicy Bypass -File %mydir%\make_link.ps1 %mydir%  || exit
echo Scipyen can now be launched from the desktop icon


rem  :eof
rem  endlocal
