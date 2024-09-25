#! bash
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


echo -e "WARNING this script is NOT customized; edit before running"
echo -e "\tthen run from the root scipyen directory (i.e. root of the git tree)"

mamba create -y --prefix $HOME/scipyenv
mamba activate $HOME/scipyenv

mamba config --add channels conda-forge # not needed on recent miniforge versions

mamba install --prefix $HOME/scipyenv -y jupyter
mamba install --prefix $HOME/scipyenv -y jupyterthemes
mamba install --prefix $HOME/scipyenv -y numpy

mamba install --prefix $HOME/scipyenv -y matplotlib
echo Installing scipy
mamba install --prefix $HOME/scipyenv -y scipy
echo Installing sympy
mamba install --prefix $HOME/scipyenv -y sympy
echo Installing h5py
mamba install --prefix $HOME/scipyenv -y h5py
echo Installing pyqtgraph
mamba install --prefix $HOME/scipyenv -y pyqtgraph
echo Installing pywavelets
mamba install --prefix $HOME/scipyenv -y PyWavelets
echo Installing pandas
mamba install --prefix $HOME/scipyenv -y pandas
echo Installing quantities
mamba install --prefix $HOME/scipyenv -y quantities
echo Installing python-neo
mamba install --prefix $HOME/scipyenv -y python-neo
echo Installing vigra
mamba install --prefix $HOME/scipyenv -y -c conda-forge vigra
echo Installing cmocean
mamba install --prefix $HOME/scipyenv -y cmocean
echo Installing confuse
mamba install --prefix $HOME/scipyenv -y confuse
echo Installing inflect
mamba install --prefix $HOME/scipyenv -y inflect
echo Installing seaborn
mamba install --prefix $HOME/scipyenv -y seaborn
echo Installing pingouin
mamba install --prefix $HOME/scipyenv -y pingouin
echo Installing qimage2ndarray
mamba install --prefix $HOME/scipyenv -y qimage2ndarray
echo Installing pyxdg
mamba install --prefix $HOME/scipyenv -y pyxdg
# REM OPTIONAL PACKAGES FROM CONDA
# REM mamba install --prefix $HOME/scipyenv -y qdarkstyle
echo Installing bokeh
mamba install --prefix $HOME/scipyenv -y bokeh
echo Installing scikit-image
mamba install --prefix $HOME/scipyenv -y scikit-image
echo Installing scikit-learn
mamba install --prefix $HOME/scipyenv -y scikit-learn
echo Installing dill
mamba install --prefix $HOME/scipyenv -y dill
echo Installing libNeuroML
mamba install --prefix $HOME/scipyenv -y libNeuroML
echo Installing matlab kernel
mamba install --prefix $HOME/scipyenv -y matlab_kernel
echo Installing octave kernel
mamba install --prefix $HOME/scipyenv -y octave_kernel
echo Installing PyInstaller
mamba install --prefix $HOME/scipyenv -y pyinstaller

echo Installing additional PyPI packages
pip install -r doc/install/pip_requirements.txt

# powershell -ExecutionPolicy Bypass -File %mydir%\make_link.ps1 %mydir%
# echo Scipyen can now be launched from the desktop icon


# :eof
# rem  endlocal

