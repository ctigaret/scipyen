# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing
from qtpy import QtCore, QtGui, QtWidgets, QtSvg, QtNetwork
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import (safeWrapper, scipywarn)
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))


class ScipyenNetworkManager(QtCore.QObject):
    def __init__(self, timeout_ms:int=QtNetwork.QNetworkRequest.DefaultTransferTimeoutConstant,
                 parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self.timeout_ms = timeout_ms
        self.manager = QtNetwork.QNetworkAccessManager(self)
        self.manager.setTransferTimeout(timeout_ms)
        self.hasInternet=False

    def check_internet_connection(self, url:str = "http://www.google.com/", 
                                  raise_error:bool=True):
        request = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
        request.setRawHeader(b"User-Agent", b"Mozilla 5.0")
        reply = self.manager.get(request)
        reply.readyRead.connect(self.slot_checkConnectionReady)
        reply.finished.connect(self.slot_checkConnectionFinished)
        reply.errorOccurred.connect(self.slot_checkConnectionError)
        reply.sslErrors.connect(self.slot_checkConnectionSSLError)
        reply.deleteLater()
        
    @Slot()
    def slot_readyRead(self):
        pass
    
    @Slot()
    def slot_checkConnectionFinished(self):
        reply = self.sender()
        rawHeaders = reply.rawHeaderPairs()
        for x in rawHeaders:
            print(f"{bytes(x[0]).decode()} ↦ {bytes(x[1]).decode()}")
        self.hasInternet = True
    
    @Slot()
    def slot_checkConnectionReady(self):
        reply = self.sender()
        rawHeaders = reply.rawHeaderPairs()
        for x in rawHeaders:
            print(f"{bytes(x[0]).decode()} ↦ {bytes(x[1]).decode()}")
        self.hasInternet = True
    
    @Slot()
    def slot_Error(self):
        scipywarn("No internet connection available.")
    
    @Slot()
    def slot_checkConnectionError(self):
        scipywarn("No internet connection available.")
        self.hasInternet=False
    
    @Slot()
    def slot_checkConnectionSSLError(self):
        scipywarn("No secure internet connection available.")
        self.hasInternet=False
