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
from core.datatypes import TypeEnum

from systems.devices.errors import ErrorType
from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface)
from systems.devices.storagedrive import (_StorageDrive_, StorageDrive)

class IfaceOpticalDrive: pass

class _OpticalDrive_(_StorageDrive_):
    def __init__(self):
        super().__init__()

class OpticalDrive(StorageDrive):
    ejectPressed = Signal(str, name = "ejectPressed", arguments=["udi"])
    ejectDone = Signal(ErrorType, QtCore.QVariant, str, name = "ejectDone", arguments=["error", "errorData", "udi"])
    ejectRequested = Signal(str, name="ejectRequested", arguments=["udi"])
    
    class MediumType(TypeEnum):
        UnknownMediumType = 0x00000
        Cdr = 0x00001
        Cdrw = 0x00002
        Dvd = 0x00004
        Dvdr = 0x00008
        Dvdrw = 0x00010
        Dvdram = 0x00020
        Dvdplusr = 0x00040
        Dvdplusrw = 0x00080
        Dvdplusdl = 0x00100
        Dvdplusdlrw = 0x00200
        Bd = 0x00400
        Bdr = 0x00800
        Bdre = 0x01000
        HdDvd = 0x02000
        HdDvdr = 0x04000
        HdDvdrw = 0x08000
        
    MediumTypes = MediumType
        
    def __init__(self, backendObject:QtCore.QObject):
        super().__init__(_OpticalDrive_(), backendObject)
        self._supportedMedia_:self.MediumType = self.MediumType.UnknownMediumType
        self._readSpeed_:int = 0
        self._writeSpeed_:int = 0
        self._writeSpeeds_:list[int] = list()
        
        backendObject.ejectPressed[str].connect(self.ejectPressed)
        backendObject.ejectDone[ErrorType, QtCore.QVariant, str].connect(self.ejectDone)
        backendObejct.ejectRequested[str].connect(self.ejectRequested)
        

    
    @staticmethod
    def deviceInterfaceType() -> DeviceInterface.Type:
        return DeviceInterface.OpticalDrive
    
    def supportedMedia(self) -> MediumTypes:
        o = self._d_.backendObject()
        self._supportedMedia_ = o.supportedMedia() if isinstance(o, IfaceOpticalDrive) else self.MediumTypes.UnknownMediumType
        return self._supportedMedia_
    
    def readSpeed(self) -> int:
        o = self._d_.backendObject()
        self._readSpeed_ = o.readSpeed() if isinstance(o, IfaceOpticalDrive) else 0
        return self._readSpeed_
    
    def writeSpeed(self) -> int:
        o = self._d_.backendObject()
        self._writeSpeed_ = o.readSpeed() if isinstance(o, IfaceOpticalDrive) else 0
        return self._writeSpeed_
    
    def writeSpeeds(self) -> int[list]:
        o = self._d_.backendObject()
        self._writeSpeeds_ = o.writeSpeeds() if isinstance(o, IfaceOpticalDrive) else list()
        return self._writeSpeeds_
    
    def eject(self) -> bool:
        o = self._d_.backendObject()
        return o.eject if isinstance(o, IfaceOpticalDrive) else False
            
from systems.devices.interfaces.opticaldrive import OpticalDrive as IfaceOpticalDrive

        

    
    
    
    
    
    
    
