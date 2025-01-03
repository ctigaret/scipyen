# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, pathlib, functools, itertools
from urllib.parse import urlparse, urlsplit
from collections import namedtuple
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class DeviceType:(IntEnum):
    """"""
    # NOTE: 2025-01-03 14:09:24 
    # Solid DeviceInterface::Type
    Unknown = 0,
    GenericInterface = 1,
    Processor = 2,
    Block = 3,
    StorageAccess = 4,
    StorageDrive = 5,
    OpticalDrive = 6,
    StorageVolume = 7,
    OpticalDisc = 8,
    Camera = 9,
    PortableMediaPlayer = 10,
    Battery = 12,
    NetworkShare = 14,
    Last = 0xffff,
