# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, collections, pathlib, tarfile
import inspect, functools, traceback
from functools import (singledispatch, singledispatchmethod)
from qtpy import QtCore, QtGui, QtWidgets, QtSvg, QtNetwork
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import (safeWrapper, scipywarn, printStyled)
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))


class ScipyenNetworkManager(QtCore.QObject):
    # NOTE: 2024-11-27 11:16:32
    # working towards a network manager for downloading remote data;
    # starting out with Qt 5 examples/network/downloadmanager a.k.a qt5ex
    #
    sig_hasInternet = Signal(bool, name="sig_hasInternet")
    sig_textFromUrl = Signal(object)
    sig_finished = Signal(name="sig_finished")
    _sig_goAhead = Signal(name="_sig_goAhead")
    
    def __init__(self, _timeout_ms_:int=QtNetwork.QNetworkRequest.DefaultTransferTimeoutConstant,
                 parent:typing.Optional[QtCore.QObject] = None):
        from core import workspacefunctions as wf
        super().__init__(parent=parent)
        
        ws = wf.user_workspace()
        if ws is not None:
            self.scipyenWindow = ws["mainWindow"]
        else:
            frame_records = inspect.getouterframes(inspect.currentframe())
            for (n,f) in enumerate(frame_records):
                if "ScipyenWindow" in f[0].f_globals:
                    self.scipyenWindow = f[0].f_globals["ScipyenWindow"].instance()
                    break
        
        self._timeout_ms_ = _timeout_ms_
        self._downloadQueue_ = collections.deque() # qt5ex
        self._downloadedCount_ = 0 # qt5ex
        self._totalCount_ = 0 # qt5ex
        self._outputFile_ = QtCore.QFile() # qt5ex
        self._outputFileName_ = None
        self._currentDownload_ = None # cannot instantiate QNetworkReply (is abstract) # qt5ex
        self._downloadTime_ = QtCore.QTime() # ~qt5ex
        self._progressDialog_ = None # ~qt5ex
        self._progressBar_ = None # ~qt5ex
        
        self._manager_ = QtNetwork.QNetworkAccessManager(self) # also qt5ex
        self._manager_.setTransferTimeout(_timeout_ms_)
        # self._manager_.finished[QtNetwork.QNetworkReply].connect(self.slot_replyFinished)
        self._hasInternet_=False
        self._networkReply_ = None # cannot instantiate QNetworkReply (is abstract)
        self._replyText_ = None
        
    def getFromUrl(self, o:typing.Union[str, QtCore.QUrl, typing.Sequence[typing.Union[str, QtCore.QUrl]]],
                   destination:typing.Optional[str]=None) -> None:
        self._append(o, destination)#, asText)
        
    @singledispatchmethod
    def _append(self, o:object, fileName:typing.Optional[str]=None):  # qt5ex
        """When passing a sequence of URLs AND a fileName, AND he fileName already
        exists, then each URL will be saved to fileNameStem<X>.fileNameSuffix where X is 0, 1, 2, etc
        Whe fileName is None, fileName will be generated from the basename  of the URL
        """
        raise NotImplementedError(f"Method is not implemented for {type(o).__name__} arguments")
        
    @_append.register(list)
    @_append.register(tuple)
    @_append.register(collections.deque)
    def _(self, urlList:typing.Sequence[typing.Union[str, QtCore.QUrl]], # qt5ex
          fileName:typing.Optional[str]=None) -> None:  
        for u in urlList:
            self._append(u, fileName)
            
        if len(self._downloadQueue_) == 0:
            QtCore.QTimer.singleShot(0, self.sig_finished)
            
    @_append.register(str)
    @_append.register(QtCore.QUrl)
    def _(self, u: str | QtCore.QUrl, fileName:typing.Optional[str]=None) -> None:  # qt5ex
        self._outputFileName_ = fileName
        if len(self._downloadQueue_) == 0:
            QtCore.QTimer.singleShot(0, self._startNextDownload)
            
        url = u if isinstance(u, QtCore.QUrl) else QtCore.QUrl(u)
        
        self._downloadQueue_.append(url)
        self._totalCount_ += 1
        
    def _startNextDownload(self):  # qt5ex
        if len(self._downloadQueue_) == 0:
            print(f"{self._downloadedCount_}/{self._totalCount_} files downloaded successfully")
            self.sig_finished.emit()
            return
        
        if self._progressBar_ is None:
            self._progressBar_ = QtWidgets.QProgressBar(parent = self.scipyenWindow)
            self.scipyenWindow.statusBar().addWidget(self._progressBar_)
        else:
            if not self._progressBar_.isVisible():
                self.scipyenWindow.statusBar().addWidget(self._progressBar_)
                self._progressBar_.show()
                
        url = self._downloadQueue_.popleft()
        
        fileName = self._outputFileName_
        
        if fileName is None:
            fileName = self._saveFileName(url)
        
        self._outputFile_.setFileName(fileName)
        
        if not self._outputFile_.open(QtCore.QIODevice.WriteOnly):
            scipywarn(f"Problem opening save file {fileName} for download from {url.url()}: {self._outputFile_.errorString()}")
            
            self._startNextDownload()
            return
        
        request = QtNetwork.QNetworkRequest(url)
        self._currentDownload_ = self._manager_.get(request)
        self._currentDownload_.downloadProgress["qint64", "qint64"].connect(self.slot_downloadProgress)
        self._currentDownload_.finished.connect(self.slot_downloadFinished)
        self._currentDownload_.readyRead.connect(self.slot_downloadReadyRead)
        
        msg = printStyled(f"")
        
        print(printStyled(f"Downloading {url.url()} ...", "green",True))
        self._downloadTime_.start()
        
    def _saveFileName(self, url:QtCore.QUrl) -> str:  # ~qt5ex
        path = pathlib.Path(url.path())
        basename = path.name
        if len(basename.strip()) == 0:
            basename="download"
        
        suffix = pathlib.Path(basename).suffix
        basename = pathlib.Path(basename).stem
            
        if pathlib.Path(basename+suffix).exists():
            i = 0
            basename += "."
            while(pathlib.Path(f"{basename}{i}{suffix}").exists()):
                i += 1
                
            basename += f"{i}"
            
        return basename+suffix
            
    # @Slot(int, int)
    @Slot("qint64", "qint64")
    def slot_downloadProgress(self, bytesReceived:int, bytesTotal:int) -> None: # qt5ex
        speed = bytesReceived * 1000. / self._downloadTime_.elapsed()
        
        units = ""
        
        if speed < 1024:
            units = "bytes/sec"
        elif speed < 1024*1024:
            speed /= 1024
            units = "kB/s"
        else:
            speed /= (1024 * 1024)
            units = "MB/s"
            
        self._progressBar_.setRange(0, bytesTotal)
        self._progressBar_.setValue(bytesReceived)
        
        print(f"bytes: {bytesReceived} / {bytesTotal} (speed: {speed} {units})")
        
    @Slot()
    def slot_downloadFinished(self)-> None: # ~qt5ex
        self._outputFile_.close()
        self._progressBar_.reset() # clear progressbar
        self.scipyenWindow.statusBar().removeWidget(self._progressBar_)
        if self._currentDownload_.error():
            scipywarn(f"Failed:\n {self._currentDownload_.errorString()} ")
        else:
            print("Succeeded")
            self._downloadedCount_ += 1
            
        self._currentDownload_.deleteLater()
        self._startNextDownload()
    
    @Slot()
    def slot_downloadReadyRead(self) -> None: # qt5ex
        self._outputFile_.write(self._currentDownload_.readAll())
        
        

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
