# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Work in progress, DO NOT USE
"""
import sys, os, typing, pathlib, functools, itertools, traceback
from urllib.parse import urlparse, urlsplit
from collections import namedtuple
from abc import abstractmethod
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property

from systems.devices.interfaces.block import Block

class StorageDrive(Block):
    from systems.devices.storagedrive import StorageDrive as FendStorageDrive
    def __init__(self):
        super().__init__()
        
    @abstractmethod
    def bus(self) -> FendStorageDrive.Bus:
        pass
    
    @abstractmethod
    def driveType(self) -> FendStorageDrive.DeviceType:
        pass
    
    @abstractmethod
    def isRemovable(self) -> bool:
        pass
    
    @abstractmethod
    def isHotPluggable(self) -> bool:
        pass
    
    @abstractmethod
    def size(self) -> int:
        pass
    
    @abstractmethod
    def timeDetected(self) -> QtCore.QDateTime:
        pass
    
    @abstractmethod
    def timeMediaDetected(self) -> QtCore.QDateTime:
        pass
    
