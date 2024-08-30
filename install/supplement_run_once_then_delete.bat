rem  # -*- coding: utf-8 -*-
rem  # SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
rem  # SPDX-License-Identifier: GPL-3.0-or-later
rem  # SPDX-License-Identifier: LGPL-2.1-or-later
rem  
powershell -ExecutionPolicy Bypass -File %mydir%\make_scipyen_batch_scripts.ps1 %mydir%  || goto eof
:eof

