# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
import vigra
# NOTE: 2024-08-15 21:47:00 somehow `true_divide` is left out of vigra.ufunc
# module, but a dunction `divide` is present
# now, vigra.ufunc.true_divide is called by VigraArray.__truediv__, so 
# the following monkey patch hopefully solves this

vigra.ufunc.true_divide = vigra.ufunc.divide


