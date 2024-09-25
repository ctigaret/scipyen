# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

mamba install --prefix $HOME/scipyenv -y jupyter qtconsole jupyterthemes numpy \
    matplotlib scipy h5py pyqtgraph PyWavelets pandas quantities python-neo \
    cmocean confuse inflect seaborn pingouin  qimage2ndarray pyxdg bokeh \
    scikit-image scikit-learn dill pyinstaller dbus-python \
    pyserial python-magic shapely pandas-flavor jupyter_qtconsole_colorschemes \
    sphinx cmasher more-itertools termcolor termcolor2 inflect isodate ipyparallel
                     
mamba install --prefix $HOME/scipyenv -y -c conda-forge vigra

pip install nixio 
pip install pyabf
pip install imreg-dft
pip install modelspec
