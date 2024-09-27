#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

realscript=`realpath $0`

# echo "$realscript"

scipyendir=`dirname "$realscript"`
env_name="scipyenv"

# echo "$scipyendir"

if test -z "$CONDA_DEFAULT_ENV" ; then 
    eval "$($HOME/miniforge3/bin/conda shell.bash hook)"
    if [[ $? -ne 0 ]]; then
        echo "Where is conda/miniforge installed?"
    fi
fi
if test "$CONDA_DEFAULT_ENV" = "base" ; then
    eval "$(conda shell.bash hook)"
    conda activate $env_name
elif [ ${CONDA_DEFAULT_ENV} -ne ${env_name} ]; then
    echo "You're in the wrong conda environment: $CONDA_DEFAULT_ENV  - goodbye!"
    exit -1

fi


python -Xfrozen_modules=off "$scipyendir"/src/scipyen/scipyen.py
