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
    sig_hasInternet = Signal(bool, name="sig_hasInternet")
    sig_textFromUrl = Signal(object)
    _sig_goAhead = Signal(name="_sig_goAhead")
    
    def __init__(self, _timeout_ms_:int=QtNetwork.QNetworkRequest.DefaultTransferTimeoutConstant,
                 parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._timeout_ms_ = _timeout_ms_
        self._manager_ = QtNetwork.QNetworkAccessManager(self)
        self._manager_.setTransferTimeout(_timeout_ms_)
        # self._manager_.finished[QtNetwork.QNetworkReply].connect(self.slot_replyFinished)
        self._hasInternet_=False
        self._networkReply_ = None
        self._replyText_ = None

    def checkInternetConnection(self, url:typing.Union[str, QtCore.QUrl] = "http://www.google.com/", 
                                  raise_error:bool=True):
        
        if isinstance(url, str):
            url = QtCore.QUrl(url)
        
        request = QtNetwork.QNetworkRequest(url)
        request.setRawHeader(b"User-Agent", b"Mozilla 5.0")
        self._networkReply_ = self._manager_.get(request)
        self._networkReply_.readyRead.connect(self.slot_checkConnectionReady)
        self._networkReply_.finished.connect(self.slot_checkConnectionFinished)
        self._networkReply_.errorOccurred.connect(self.slot_checkConnectionError)
        self._networkReply_.sslErrors.connect(self.slot_checkConnectionSSLError)
        # self._networkReply_.deleteLater()
        
    def getTextFromUrl(self, url:typing.Union[str, QtCore.QUrl]):
        if isinstance(url, str):
            url = QtCore.QUrl(url)
        
        request = QtNetwork.QNetworkRequest(url)
        request.setRawHeader(b"User-Agent", b"Mozilla 5.0")
        self._replyText_ = None
        self._networkReply_ = self._manager_.get(request)
        self._networkReply_.readyRead.connect(self.slot_replyReady)
        self._networkReply_.finished.connect(self.slot_replyFinished)
        self._networkReply_.errorOccurred.connect(self.slot_replyConnectionError)
        self._networkReply_.sslErrors.connect(self.slot_replySSLError)
        
    @Slot()
    def slot_replyReady(self):
        pass
        # self._replyText_ = bytes(self._networkReply_.readAll()).decode()
        
    # @Slot(QtNetwork.QNetworkReply)
    # def slot_replyFinished(self, reply:QtNetwork.QNetworkReply):
    @Slot()
    def slot_replyFinished(self):
        reply = self.sender()
        txt = bytes(reply.readAll()).decode()
        self.sig_textFromUrl.emit(txt)
        
        # self._replyText_ = bytes(reply.readAll()).decode()
        # self.sig_textFromUrl.emit(self._replyText_)
        
    @Slot()
    def slot_checkConnectionFinished(self):
        # reply = self.sender()
        rawHeaders = self._networkReply_.rawHeaderPairs()
        # for x in rawHeaders:
        #     print(f"{bytes(x[0]).decode()} ↦ {bytes(x[1]).decode()}")
        self._hasInternet_ = len(rawHeaders) > 0
        self.sig_hasInternet.emit(self._hasInternet_)
        if self._hasInternet_:
            self._sig_goAhead.emit()
    
    @Slot()
    def slot_checkConnectionReady(self):
        # reply = self.sender()
        data = bytes(self._networkReply_.readAll()).decode()
        # rawHeaders = self._networkReply_.rawHeaderPairs()
        # for x in rawHeaders:
        #     print(f"{bytes(x[0]).decode()} ↦ {bytes(x[1]).decode()}")
        self._hasInternet_ = len(data) > 0
        self.sig_hasInternet.emit(self._hasInternet_)
    
    @Slot()
    def slot_replyConnectionError(self):
        scipywarn("No internet connection available.")
        self._hasInternet_=False
        self.sig_hasInternet.emit(self._hasInternet_)
    
    @Slot()
    def slot_checkConnectionError(self):
        scipywarn("No internet connection available.")
        self._hasInternet_=False
        self.sig_hasInternet.emit(self._hasInternet_)
    
    @Slot()
    def slot_checkConnectionSSLError(self):
        scipywarn("No secure internet connection available.")
        self._hasInternet_=False
        self.sig_hasInternet.emit(self._hasInternet_)

    @Slot()
    def slot_replySSLError(self):
        scipywarn("No secure internet connection available.")
        self._hasInternet_=False
        self.sig_hasInternet.emit(self._hasInternet_)

    @property
    def networkReply(self) -> QtNetwork.QNetworkReply | None:
        return self._networkReply_
