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

from systems.devices.deviceinterface import (_DeviceInterface_, DeviceInterface)

class _NetworkShare_(_DeviceInterface_):
    def __init__(self):
        super().__init__()
        
class NetworkShare(DeviceInterface):
    ShareType = TypeEnum("ShareType", ["Unknown", "Nfs", "Cifs", "Smb3"])
    def __init__(self, backendObject:QtCore.Qobject):
        super().__init__(_NetworkShare_(), backendObject)
        self._type_:self.ShareType = self.ShareType.Unknown
        self._url_:QtCore.QUrl = QtCore.QUrl()
        
    @staticmethod
    def deviceInterfaceType(self) -> DeviceInterface.Type:
        return DeviceInterface.Type.NetworkShare
    
    def type(self) -> ShareType:
        from systems.devices.interfaces.networkshare import NetworkShare as IfaceNetworkShare
        o = self._d_.backendObject()
        self._type_ = o.type() if isinstance(o, IfaceNetworkShare) else self.ShareType.Unknown
        return self._type_
        
    def url(self) -> QtCore.QUrl:
        from systems.devices.interfaces.networkshare import NetworkShare as IfaceNetworkShare
        o = self._d_.backendObject()
        self._url_ = o.url() if isinstance(o, IfaceNetworkShare) else QtCore.QUrl()
        return self._url_
    
    
        
        
