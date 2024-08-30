# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Used for importing modules from site-package.
Unless Scipyen is among those, import statements for Scipyen's modules won't
work here.
"""
has_hdf5 = False

try:
    import h5py
    h5py.enable_ipython_completer()
    has_hdf5 = True
except ImportError as e:
    pass

