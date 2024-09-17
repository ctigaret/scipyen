#!/bin/bash
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

function findqmake ()
{
    qmake_binary=`which qmake`
    if [ -z "$qmake_binary" ] ; then
        qmake_binary=`which qmake-qt5`
    fi
    
    if [ -z "$qmake_binary" ] ; then
        read -e -p "Enter a full path to qmake (or qmake-qt5): " qmake_binary
    fi
    
    if [ -z "$qmake_binary" ] ; then
        echo -e "Cannot build Pyqt5 without qmake. Goodbye!\n"
        exit 1
    fi
    
    echo "using qmake: ${qmake_binary}"
}

cp pyproject.toml pyproject.toml.original

project_qmake=$(cat pyproject.toml  | grep qmake)

if [ -z "${project_qmake}" ] ; then 
echo "not ok" ; 
findqmake
cat <<END >> pyproject.toml

[tool.sip.builder]
qmake = "${qmake_binary}"
jobs = 4

[tool.sip.project]
target-qt-dir = "Qt/lib"
END
else 
echo "ok" ; 
echo $project_qmake
fi



