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

from systems.devices.errors import ErrorType
from systems.devices.iterfaces.storagedrive import StorageDrive

class FendOpticalDrive: pass
class FendOpticalDriveMediumType: pass
class OpticalDrive(StorageDrive):
    ejectPressed = Signal(str, name="ejectPressed", arguments=["udi"])
    ejectDone = Signal(ErrorType, QtCore.QVariant, str, name="ejectDone", 
                       arguments = ["error", "errorData", "udi"])
    
    def __init__(self):
        super().__init__()
        
    @abstractmethod
    def readSpeed(self) -> int: pass

    @abstractmethod
    def writeSpeed(self) -> int: pass

    @abstractmethod
    def writeSpeeds(self) -> list[int]: pass

    @abstractmethod
    def eject(self) -> bool: pass
        
    



from systems.devices.opticaldrive import OpticalDrive as FendOpticalDrive
FendOpticalDriveMediumType = FendOpticalDrive.MediumType
