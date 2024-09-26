#! /bin/sh
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

realscript=`realpath $0`

# echo "$realscript"

scipyendir=`dirname "$realscript"`

# echo "$scipyendir"

if test -z "$CONDA_DEFAULT_ENV" ; then 
echo "Not in a conda environment"
exit -1
else 
# echo "$CONDA_DEFAULT_ENV"
if test "$CONDA_DEFAULT_ENV" = "base" ; then
eval "$(conda shell.bash hook)"
conda activate scipyenv
fi
# echo "OK" ;
fi


python -Xfrozen_modules=off "$scipyendir"/src/scipyen/scipyen.py
