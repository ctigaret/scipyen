#! bash
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


echo -e "WARNING this script is NOT customized; edit before running"
echo -e "\tthen run from the root scipyen directory (i.e. root of the git tree)"

realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
docdir=${scipyendir}/doc
installscriptdir=${scipyendir}/setup_env
scipyensrcdir=${scipyendir}/src/scipyen
mambaenv=$HOME/scipyenv


function make_launch_script ()
{
    # force the use of XCB platform abstraction plugin in Qt
target_dir=${HOME}/bin

mkdir -p ${target_dir}
if [ -r ${target_dir}/scipyen ] ; then
    dt=`date '+%Y-%m-%d_%H-%M-%s'`
    mv ${target_dir}/scipyen ${target_dir}/scipyen.$dt
fi
shopt -s lastpipe

# if [[ `id -u` -eq 0 ]] ; then
cat <<END > ${target_dir}/scipyen
#! /bin/sh
mamba activate ${mambaenv}
export OUTDATED_IGNORE=1
python3 -Xfrozen_modules=off ${scipyensrcdir}/scipyen.py "\$*"
END
shopt -u lastpipe
chmod +x ${target_dir}/scipyen
echo -e "Scipyen startup script created in ${target_dir} \n"
}


mamba create -y --prefix $mambaenv

mamba activate $mambaenv

mamba config --add channels conda-forge # not needed on recent miniforge versions

conda install conda-forge::pyqt
mamba install --prefix $mambaenv -y qtpy
mamba install --prefix $mambaenv -y jupyter
mamba install --prefix $mambaenv -y jupyterthemes
mamba install --prefix $mambaenv -y numpy

mamba install --prefix $mambaenv -y matplotlib
echo Installing scipy
mamba install --prefix $mambaenv -y scipy
echo Installing sympy
mamba install --prefix $mambaenv -y sympy
echo Installing h5py
mamba install --prefix $mambaenv -y h5py
echo Installing pyqtgraph
mamba install --prefix $mambaenv -y pyqtgraph
echo Installing pywavelets
mamba install --prefix $mambaenv -y PyWavelets
echo Installing pandas
mamba install --prefix $mambaenv -y pandas
echo Installing quantities
mamba install --prefix $mambaenv -y quantities
echo Installing python-neo
mamba install --prefix $mambaenv -y python-neo
echo Installing vigra
#mamba install --prefix $mambaenv -y -c conda-forge vigra
conda install conda-forge::vigra
echo Installing cmocean
mamba install --prefix $mambaenv -y cmocean
echo Installing confuse
mamba install --prefix $mambaenv -y confuse
echo Installing inflect
mamba install --prefix $mambaenv -y inflect
echo Installing seaborn
mamba install --prefix $mambaenv -y seaborn
echo Installing pingouin
mamba install --prefix $mambaenv -y pingouin
echo Installing qimage2ndarray
mamba install --prefix $mambaenv -y qimage2ndarray
echo Installing pyxdg
mamba install --prefix $mambaenv -y pyxdg
# REM OPTIONAL PACKAGES FROM CONDA
# REM mamba install --prefix $mambaenv -y qdarkstyle
echo Installing bokeh
mamba install --prefix $mambaenv -y bokeh
echo Installing scikit-image
mamba install --prefix $mambaenv -y scikit-image
echo Installing scikit-learn
mamba install --prefix $mambaenv -y scikit-learn
echo Installing dill
mamba install --prefix $mambaenv -y dill
echo Installing libNeuroML
mamba install --prefix $mambaenv -y libNeuroML
echo Installing matlab kernel
mamba install --prefix $mambaenv -y matlab_kernel
echo Installing octave kernel
mamba install --prefix $mambaenv -y octave_kernel
echo Installing PyInstaller
mamba install --prefix $mambaenv -y pyinstaller

echo Installing additional PyPI packages
pip install -r setup_env/pip_requirements_macos.txt

make_launch_script

