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

# Do you wish to update your shell profile to automatically initialize conda?
# This will activate conda on startup and change the command prompt when activated.
# If you'd prefer that conda's base environment not be activated on startup,
#    run the following command when conda is activated:
# 
# conda config --set auto_activate_base false
# 
# You can undo this by running `conda init --reverse $SHELL`? [yes|no]
# [no] >>> no
# 
# You have chosen to not have conda modify your shell scripts at all.
# To activate conda's base environment in your current shell session:
# 
# eval "$(/home/cezar/miniforge3/bin/conda shell.YOUR_SHELL_NAME hook)" 
# 
# To install conda's shell functions for easier access, first activate, then:
# 
# conda init
# 
# Thank you for installing Miniforge3!
# 
realscript=`realpath $0`

echo "$realscript"

scipyendir=`dirname "$realscript"`

echo "$scipyendir"

env_name="scipyenv"

if test -z "$CONDA_DEFAULT_ENV" ; then 

read -e -p "Enter the miniforge directory (no spaces, please): "

my_miniforge=$(printf %s "$REPLY" | envsubst)

if test -d $my_miniforge ; then
my_conda=${my_miniforge}/bin/conda

eval "$($my_conda shell.bash hook)" 
else
echo "You did not provide a valid path to miniforge. Bailing out "
exit -1
fi

fi

mamba create -y --name "$env_name" python=3.11 --file "$scipyendir"/setup_env/conda_reqs.txt
mamba init

if test $? -ne 0  ; then
echo "Could not create the mamba environment $env_name. Goodbye!"
exit 1
else
echo "Now, restart the shell (or, better, open a new shell) then:"
fi


if test "$CONDA_DEFAULT_ENV" = "base" ; then
eval "$(conda shell.bash hook)"
conda activate scipyenv
fi

if test "$CONDA_DEFAULT_ENV" = "$env_name" ; then
pip install "$scipyendir"/setup_env/conda_pip_reqs.txt
cd "$scipyendir"/src/scipyen/gui/scipyen_console_styles
pip install .
else
echo "Cannot activate the $env_name environment. You must continue the installation manually"
echo ""
echo "1. Restart the shell (or, better, open a new shell)"
echo "2. Activate the environment: mamba activate scipyenv"
echo "3. Change to directory to $scipyendir"
echo "4. Run: pip install -r $scipyendir/setup_env/conda_pip_reqs.txt"
echo "5. Change to directory $scipyendir/src/scipyen/gui/scipyen_console_styles"
echo "6. Run: pip install ."
echo ""
fi

echo "To run Scipyen, open a new shell, then execute the following script according to your platform:"
echo "   Linux: Execute 'mamba activate scipyenv' then 'sh $scipyendir/scipyen_conda.sh'"



