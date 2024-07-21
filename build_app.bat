rem  # -*- coding: utf-8 -*-
rem  # SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
rem  # SPDX-License-Identifier: GPL-3.0-or-later
rem  # SPDX-License-Identifier: LGPL-2.1-or-later

echo This script must be run with Scipyen's virtual python environment properly installed and activated
echo and from the cloned Scipyen git repository (top directory).
echo The Python environment can be activated with the `scipyact` command.
set mypath=%0
set mydir=%~dp0

set default_destination="c:\scipyen_app"
set /P destination="Enter the full path name of the directory where the frozen Scipyen app will be created (no spaces, please, default is: %default_destination%): "

if [%destination%] equ [] set destination=%default_destination%

mkdir %destination%

set workdir=%destination%\build

set distdir=%destination%\dist

pyinstaller --distpath %distdir% --workpath %workdir% --clean --noconfirm %mydir%\scipyen.spec

