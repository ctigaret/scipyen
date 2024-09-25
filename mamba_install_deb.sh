# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# NOTE: the comments below are for my own benefit - do NOT use !!!
# Transaction finished
# 
# To activate this environment, use:
# 
#     micromamba activate /home/cezar/miniforge3
# 
# Or to execute a single command in this environment, use:
# 
#     micromamba run -p /home/cezar/miniforge3 mycommand
# 
# installation finished.
# Do you wish to update your shell profile to automatically initialize conda?
# This will activate conda on startup and change the command prompt when activated.
# If you'd prefer that conda's base environment not be activated on startup,
#    run the following command when conda is activated:
# 
# conda config --set auto_activate_base false
# 
# You can undo this by running `conda init --reverse $SHELL`? [yes|no]
# [no] >>> yes
# 
# # >>> conda initialize >>>
# # !! Contents within this block are managed by 'conda init' !!
# __conda_setup="$('/home/cezar/miniforge3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
# if [ $? -eq 0 ]; then
#     eval "$__conda_setup"
# else
#     if [ -f "/home/cezar/miniforge3/etc/profile.d/conda.sh" ]; then
#         . "/home/cezar/miniforge3/etc/profile.d/conda.sh"
#     else
#         export PATH="/home/cezar/miniforge3/bin:$PATH"
#     fi
# fi
# unset __conda_setup
# 
# if [ -f "/home/cezar/miniforge3/etc/profile.d/mamba.sh" ]; then
#     . "/home/cezar/miniforge3/etc/profile.d/mamba.sh"
# fi
# # <<< conda initialize <<<

# __env_create="$('mamba create -y --name scipyenv_test python=3.11 --file mamba_reqs.txt')"
#
# __env_evolve=

# mamba create -y --prefix $HOME/scipyenv python=3.11 --file mamba_reqs.txt

realscript=`realpath $0`

echo "$realscript"

scipyendir=`dirname "$realscript"`

echo "$scipyendir"

env_name="scipyenv"

mamba create -y --name "$env_name" python=3.11 --file mamba_reqs.txt
mamba init

if test $? -ne 0  ; then
echo -e "Could not create the mamba environment $env_name. Goodbye!"
exit 1
else
echo -e "The mamba environment $env_name was created successfully"

fi

bash ./mamba_post_install.sh



#mamba activate $HOME/scipyenv
#
#
# mamba install --prefix $HOME/scipyenv -y jupyter qtconsole jupyterthemes numpy \
#     matplotlib scipy sympy h5py pyqtgraph PyWavelets pandas quantities python-neo \
#     cmocean confuse inflect seaborn pingouin  qimage2ndarray pyxdg bokeh \
#     scikit-image scikit-learn dill pyinstaller dbus-python \
#     pyserial python-magic shapely pandas-flavor jupyter_qtconsole_colorschemes \
#     sphinx cmasher more-itertools termcolor termcolor2 inflect isodate ipyparallel
#
# mamba install --prefix $HOME/scipyenv -y -c conda-forge vigra

# mamba activate $HOME/scipyenv && pip install nixio pyabf imreg-dft modelspec

# BUG: this install in the base environment
# cd src/scipyen/gui/scipyen_console_styles/ && pip install .

