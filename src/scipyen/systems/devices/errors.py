# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

from core.datatypes import TypeEnum

class ErrorType(TypeEnum):
    NoError = 0
    UnauthorizedOperation = 1
    DeviceBusy = 2
    OperationFailed = 3
    UserCancelled = 4
    InvalidOption = 5
    MissingDriver = 6
    
    
