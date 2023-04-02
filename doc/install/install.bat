@echo off
rem  setlocal enabledelayedexpansion enableextensions
set mypath=%0
set mydir=%~dp0
set conda_reqs=%mydir%\conda_requirements_win.txt
set pip_reqs=%mydir%\pip_requirements_win.txt
set default_env_name="e:\scipyenv"
set /P env_name=Enter the full path name of the new environment (no spaces, please, e.g. %default_env_name%):
if [%env_name%] equ [] set env_name=%default_env_name%
echo "Creating conda environment " %env_name%
call conda create --prefix %env_name%
echo "Activating conda environment " %env_name%
call conda activate %env_name%
call conda config --add channels conda-forge
rem  call conda install --prefix %env_name% -y --file %conda_reqs%
echo "Installing jupyter"
call conda install --prefix %env_name% -y jupyter
echo "Installing jupyter_cms"
call conda install --prefix %env_name% -y jupyter_cms
echo "Installing jupyter_qtconsole_colorschemes"
call conda install --prefix %env_name% -y jupyter_qtconsole_colorschemes
echo "Installing jupyterthemes"
call conda install --prefix %env_name% -y jupyterthemes
echo "Installing numpy"
call conda install --prefix %env_name% -y numpy
echo "Installing matplotlib"
call conda install --prefix %env_name% -y matplotlib
echo "Installing scipy"
call conda install --prefix %env_name% -y scipy
echo "Installing sympy"
call conda install --prefix %env_name% -y sympy
echo "Installing h5py"
call conda install --prefix %env_name% -y h5py
echo "Installing pyqtgraph"
call conda install --prefix %env_name% -y pyqtgraph
echo "Installing pywavelets"
call conda install --prefix %env_name% -y PyWavelets
echo "Installing pandas"
call conda install --prefix %env_name% -y pandas
echo "Installing quantities"
call conda install --prefix %env_name% -y quantities
echo "Installing python-neo"
call conda install --prefix %env_name% -y python-neo
echo "Installing vigra"
call conda install --prefix %env_name% -y -c conda-forge vigra
echo "Installing cmocean"
call conda install --prefix %env_name% -y cmocean
echo "Installing confuse"
call conda install --prefix %env_name% -y confuse
echo "Installing inflect"
call conda install --prefix %env_name% -y inflect
echo "Installing seaborn"
call conda install --prefix %env_name% -y seaborn
echo "Installing pingouin"
call conda install --prefix %env_name% -y pingouin
echo "Installing qimage2ndarray"
call conda install --prefix %env_name% -y qimage2ndarray
echo "Installing pyxdg"
call conda install --prefix %env_name% -y pyxdg
REM OPTIONAL PACKAGES FROM CONDA
REM call conda install --prefix %env_name% -y qdarkstyle
echo "Installing bokeh"
call conda install --prefix %env_name% -y bokeh
echo "Installing scikit-image"
call conda install --prefix %env_name% -y scikit-image
echo "Installing scikit-learn"
call conda install --prefix %env_name% -y scikit-learn
echo "Installing dill"
call conda install --prefix %env_name% -y dill
echo "Installing libNeuroML"
call conda install --prefix %env_name% -y libNeuroML
echo "Installing matlab kernel"
call conda install --prefix %env_name% -y matlab_kernel
echo "Installing octave kernel"
call conda install --prefix %env_name% -y octave-kernel

echo "Installing additional PyPI packages"
call pip install -r %pip_reqs%

powershell -ExecutionPolicy Bypass -File %mydir%\make_link.ps1 %mydir%


rem  :eof
rem  endlocal
