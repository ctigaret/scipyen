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

class StorageVolume(Block):
    from systems.devices.storagevolume import StorageVolume as FendStorageVolume
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def isIgnored(self) -> bool:
        pass
    
    @abstractmethod
    def usage(self) -> FendStorageVolume.UsageType:
        pass
    
    @abstractmethod
    def fsType(self) -> str:
        pass
    
    @abstractmethod
    def label(self) -> str:
        pass
    
    @abstractmethod
    def size(self) -> int:
        pass
    
    @abstractmethod
    def encryptedContainerUdi() -> str:
        pass
    
