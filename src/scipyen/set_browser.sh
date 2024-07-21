#!/bin/bash
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

realscript=`realpath $0`
scipyendir=`dirname $realscript`
scipyenvdir=`dirname $scipyendir`

if [ -z $1 ]; then
    echo "Resetting BROWSER to system's default"
    unset BROWSER
fi

echo "export BROWSER=$1" > $scipyenvdir/bin/browser


