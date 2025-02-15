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

class StorageAccess(DeviceInterface):
    from systems.devices.errors import ErrorType
    repairRequested = Signal(str, name="repairRequested", arguments=["udi"]) # emits an udi:str
    repairDone = Signal(ErrorType, object, str, name = "repairDone", arguments=["error", "resultData", "udi"])
    teardownRequested = Signal(str, name="teardownRequested", arguments=["udi"])
    setupRequested = Signal(str, name="setupRequested", arguments = ["udi"])
    teardownDone = Signal(ErrorType, object, str, name="teardownDone", arguments=["error", "resultData", "udi"])
    setupDone = Signal(ErrorType, object, str, name="setupDone", arguments=["error", "resultData", "udi"])
    accessibilityChanged = Signal(bool, str, name="accessibilityChanged", arguments=["accessible", "udi"])
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def isAccessible(self) -> bool:
        pass
    
    @abstractmethod
    def filePath(self) -> str:
        pass
    
    @abstractmethod
    def isIgnored(self) -> bool:
        pass
    
    @abstractmethod
    def isEncrypted(self) -> bool:
        pass
    
    @abstractmethod
    def setup(self) -> bool:
        pass
    
    @abstractmethod
    def teardown(self) -> bool:
        pass
    
    @abstractmethod
    def canCheck(self) -> bool:
        return False
    
    @abstractmethod
    def check(self) -> bool:
        return False
    
    @abstractmethod
    def canRepair(self) -> bool:
        return False
    
    @abstractmethod
    def repair(self) -> bool:
        return False
    
