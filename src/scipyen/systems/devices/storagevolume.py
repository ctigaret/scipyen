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
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path
from core.datatypes import TypeEnum

from systems.devices import device
from systems.devices.device import DeviceInterface as DevIFace
from systems.devices.device import DeviceInterfaceType as DevIFaceType

class UsageType(TypeEnum):
    Other = 0
    Unused = 1
    FileSystem = 1
    PartitionTable = 3
    Raid = 4
    encrypted = 5
    
class StorageVolume(DevIFace):
    def __init__(self, dd:typing.Optional[_StorageVolume_]=None,
                 backendObject:typing.Optional[QtCore.QObject] = None):
        if not isinstance(dd, _StorageVolume_):
            dd = _StorageVolume_()
            
        if isinstance(backendObject, QtCore.QObject):
            super().__init__(dd, backendObject)
        else:
            super().__init__()

    def isIgnored(self) -> bool:
        # Q_D(const StorageVolume);
        #                   Type,                   Object,             Default, Method        
        # return_SOLID_CALL(Ifaces::StorageVolume *, d->backendObject(), true, isIgnored());
        # casts d->backendObject() to a Ifaces::StorageVolume, calls its isIgnored() and returns the result
        # if casting fails, returns True (i.e., is ignored)
        #
        # Now, self._d_ is devices.device._DeviceInterface_, and its 
        # backend object (QObject) is cast to a devices.interfaces.DeviceInterface
        o = self._d_.backendObject()
        
        if isinstance(o, DevIFace:
            return o.isIgnored()
                
        return False
        
        
    @staticmethod
    def deviceInterfaceType() -> DevIFaceType:
        return DevIFaceType.StorageVolume
    
    
    
    
