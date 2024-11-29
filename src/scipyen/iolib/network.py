# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, collections, pathlib, tarfile, dataclasses
import inspect, functools, traceback
from dataclasses import MISSING
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
                 downloadSizeGetter:typing.Optional[typing.Callable] = None,
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
        # self._replyTextBuffer_ = QtCore.QTextStream()
        
        self._outputFileName_ = dataclasses.MISSING
        """This can be MISSING, None or a string:
        MISSING: let ScipyenNetworkManager decide (by calling self._setSaveFileName)
        None: do NOT download the file
        A string: download to a faile with path given by the string
        """
        
        
        self._removeOnFail_ = True
        self._replyText_ = None
        # self._dlSize_ = 0
        
        self._networkReply_ = None # cannot instantiate QNetworkReply (is abstract) # qt5ex
        self._downloadTime_ = QtCore.QTime() # ~qt5ex
        self._progressDialog_ = None # ~qt5ex
        self._progressBar_ = None # ~qt5ex
        self._content_length_ = 0
        self._downloadSizeGetter_ = downloadSizeGetter
        
        self._manager_ = QtNetwork.QNetworkAccessManager(self) # also qt5ex
        self._manager_.setTransferTimeout(_timeout_ms_)
        # self._manager_.finished[QtNetwork.QNetworkReply].connect(self.slot_replyFinished)
        # self._hasInternet_=False
        
    def getUrl(self, source:typing.Union[str, QtCore.QUrl, typing.Sequence[typing.Union[str, QtCore.QUrl]]],
                   destination:typing.Optional[typing.Union[str, type(MISSING)]]=MISSING,
                   removeOnFailure:bool=True) -> None:
        """Request a remote file
        Parameters:
        source: url string QUrl, or a sequence (tuple, list) of these
        
        fileName: destination file path (including the file name & extension if any)
            Optional, default is dataclasses.MISSING
        
            When MISSING, a file name will be generated from the url's basename;
                if such a file exists locally, then an integer counter will be 
                included in its name, just before the extension, such that:
                a) no existing file will be overwritten
                b) the file mime type contingent on the file name extension (or
                    suffix) will not be changed.
        
            When None, then no file will be saved; instead, the downloaded data
                contents will be stored in an internal cache.
        
            When a str, a file will be saved under this name, subject to the rules
                (a) and (b) listed above.
                
                In addition, when the 'source' parameter specifies a sequence of URLs,
                the fileName will automatically be modified subject to the above
        """
        self._totalCount_ = 0 # reset counter
        self._removeOnFail_ = removeOnFailure
        self._append(source, destination)
        
    @singledispatchmethod
    def _append(self, o:object, fileName:typing.Optional[str]=dataclasses.MISSING,
                save:bool=True):  # qt5ex
        raise NotImplementedError(f"Method is not implemented for {type(o).__name__} arguments")
        
    @_append.register(list)
    @_append.register(tuple)
    @_append.register(collections.deque)
    def _(self, urlList:typing.Sequence[typing.Union[str, QtCore.QUrl]], # qt5ex
          fileName:typing.Optional[typing.Union[str, type(MISSING)]]=MISSING) -> None:  
        for u in urlList:
            self._append(u, fileName)#, save)
            
        if len(self._downloadQueue_) == 0:
            QtCore.QTimer.singleShot(0, self.sig_finished)
            self._totalCount_ = 0
            
    @_append.register(str)
    @_append.register(QtCore.QUrl)
    def _(self, u: str | QtCore.QUrl, 
          fileName:typing.Optional[typing.Union[str, type(MISSING)]]=MISSING) -> None:  # qt5ex
        self._outputFileName_ = fileName
        # if save:
        #     self._outputFileName_ = fileName
        # else:
        #     self._outputFileName_ = None
            
        if len(self._downloadQueue_) == 0:
            QtCore.QTimer.singleShot(0, self._startNextDownload)
            
        url = u if isinstance(u, QtCore.QUrl) else QtCore.QUrl(u)
        
        self._downloadQueue_.append(url)
        self._totalCount_ += 1
        
    def _startNextDownload(self):  # qt5ex
        if len(self._downloadQueue_) == 0:
            print(f"{self._downloadedCount_}/{self._totalCount_} files downloaded")
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
        
        if self._outputFileName_ is not None:
            fileName = self._outputFileName_
            
            if fileName is dataclasses.MISSING:
                fileName = self._setSaveFileName(url)
            
            self._outputFile_.setFileName(fileName)
            
            if not self._outputFile_.open(QtCore.QIODevice.WriteOnly):
                scipywarn(f"Problem opening save file {fileName} for download from {url.url()}: {self._outputFile_.errorString()}")
                
                self._startNextDownload()
                return
            
        request = QtNetwork.QNetworkRequest(url)
        request.setRawHeader(b"User-Agent", b"Mozilla 5.0")
        self._networkReply_ = self._manager_.get(request)
        # if self._outputFileName_ is None:
        #     self._replyTextBuffer_.setDevice(self._networkReply_)
        self._networkReply_.downloadProgress["qint64", "qint64"].connect(self.slot_downloadProgress)
        if self._outputFileName_ is None:
            self._manager_.finished[QtNetwork.QNetworkReply].connect(self.slot_handleNetworkData)
        else:
            self._networkReply_.finished.connect(self.slot_downloadFinished)
        self._networkReply_.readyRead.connect(self.slot_downloadReadyRead)
        self._networkReply_.metaDataChanged.connect(self.slot_downloadHeaderChanged)
        
        msg = printStyled(f"")
        
        print(printStyled(f"Downloading {url.url()} ...", "green",True))
        self._downloadTime_.start()
        
    def _setSaveFileName(self, url:QtCore.QUrl) -> str:  # ~qt5ex
        from iolib import pictio as pio
        path = pathlib.Path(url.path())
        basename = path.name
        if len(basename.strip()) == 0:
            basename="download"
            
#         mimeFileType = pio.getMimeAndFileType(basename)
#         
#         if all(all(a in m for a in ("x-tar", "gzip")) for m in mimeFileType):
            
        path = pathlib.Path(basename)
        suffixes = path.suffixes
        
        # deal with tag.gz, tar.bz situations ...
        if len(suffixes) > 1:
            if suffixes[-2] == ".tar":
                suffix = "".join(suffixes[-2:])
                ndx = path.stem.index(suffixes[-2])
                stem = path.stem[0:ndx]
                
            else:
                suffix = suffixes[-1]
                stem = path.stem
        else:
            suffix = path.suffix
            stem = path.stem
        
        basename = stem
            
        if pathlib.Path(basename+suffix).exists():
            i = 0
            while(pathlib.Path(f"{basename}_{i}_{suffix}").exists()):
                i += 1
                
            basename += f"_{i}_"
            
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
            
        total = bytesTotal if bytesTotal >=0 else self._content_length_
        self._progressBar_.setRange(0, total)
        self._progressBar_.setValue(bytesReceived)
        
        print(f"bytes: {bytesReceived} / {bytesTotal} (speed: {speed} {units})")
        
    @Slot()
    def slot_downloadFinished(self)-> None: # ~qt5ex
        print(f"{self.__class__.__name__}.slot_downloadFinished: self._outputFileName_: {self._outputFileName_}")
        if self._outputFileName_ is None:
            pass
            # self._replyText_ = bytes(self._networkReply_.readAll()).decode()
            # self._replyText_ = self._replyTextBuffer_.readAll()
            # print(f"{self.__class__.__name__}.slot_downloadFinished: reply text = \n{self._replyText_}")
            
        else:
            self._outputFile_.close()
            self._progressBar_.reset() # clear progressbar
            self.scipyenWindow.statusBar().removeWidget(self._progressBar_)
            if self._networkReply_.error():
                scipywarn(f"{self.__class__.__name__}.show_downloadFinished Failed:\n {self._networkReply_.errorString()} ")
                if self._removeOnFail_:
                    if not self._outputFile_.remove():
                        scipywarn(f"{self.__class__.__name__}.show_downloadFinished Failed to remove incomplete download file:\n {self._outputFile_.fileName()} ")
                        
            else:
                print("Succeeded")
                self._downloadedCount_ += 1
            
        self._networkReply_.deleteLater()
        self._startNextDownload()
        
    @Slot(QtNetwork.QNetworkReply)
    def slot_handleNetworkData(self, reply:QtNetwork.QNetworkReply):
        print(f"{self.__class__.__name__}.slot_handleNetworkData")
        if not reply.error():
            self._replyText_ = bytes(reply.readAll()).decode()
            self._downloadedCount_ += 1
        
    @Slot()
    def slot_downloadHeaderChanged(self):
        # NOTE 2024-11-28 09:20:58
        # Won't work if content length is not supplied by the server, in the header.
        # For some sites a trick is to get the size of the downloaded file from
        # somewhere else - e.g., in BrainbGlobe atlases, to download the "src" page 
        # for a given atlas, and parse the (expected) size from there
        # 
        # However, that is just a particular case...
        #
        # TODO: 2024-11-28 09:43:20
        # So what I can do here is to use a Callable object defined elsewhere
        # that can deal with a particular case, and which is to be fed to the 
        # constructor of ScipyenNetworkManager instance as the "downloadSizeGetter"
        # parameter.
        #
        # Strategy:
        # 1) use another instance of ScipyenNetworkManager to download the content
        # of an appropriate web page detailing the content size, but storing the 
        # the content to an internal variable instead of saving it to disk
        # 2) parse the interval variable assigned at (1) to obtain the size of
        # the file being downloaded here
        #
        # Potential problems:
        # needs to be asynchronous; 
        # by the time the contents are parsed, some chunks may have already been 
        # downoaded
        #
        # For BrainbGlobe Id do something like:
        # URL to retrieve the file
        # url = bgbridge.brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base.format("example_mouse_100um_v1.2.tar.gz")
        #
        # URL to get file size:
        # src_url = url.replace("raw", "src")
        #
        
        print(f"{self.__class__.__name__}.slot_downloadHeaderChanged:")
        
        rawHeaders = self._networkReply_.rawHeaderPairs()
        for x in rawHeaders:
            print(f"{bytes(x[0]).decode()} ↦ {bytes(x[1]).decode()}")
        if self._networkReply_.hasRawHeader(b"content-length"):
            self._content_length_ = self._networkReply_.header(QtNetwork.QNetworkRequest.ContentLengthHeader)
        else:
            if isinstance(self._downloadSizeGetter_, typing.Callable):
                self._content_length_ = self._downloadSizeGetter_()
            else:
                self._content_length_ = 0
                
        print(f"{self._content_length_}")
    
    @Slot()
    def slot_downloadReadyRead(self) -> None: # qt5ex   
        print(f"{self.__class__.__name__}.slot_downloadReadyRead:")
        # if isinstance(self._outputFile_, QtCore.QIODevice) and self._outputFileName_ is not None:
        if isinstance(self._outputFile_, QtCore.QFile) and self._outputFile_.exists():
            self._outputFile_.write(self._networkReply_.readAll())
            
    def getDownloadSize(self, s:str) -> int:
        import re
        search_result = re.search("([0-9]+\.[0-9] [MGK]B)|([0-9]+ [MGK]B)", s)
        assert search_result is not None
        sz_str = search_result.group()
        assert sz_str is not None
        sz = float(sz_str[:-3])
        pfx = sz_str[-2]
        if pfx == "G":
            sz *= 1e9
        elif pfx == "M":
            sz *= 1e6
        elif pfx == "K":
            sz *= 1e3
        return int(sz)        
            
        # else:
        #     self._replyText_ = bytes(self._networkReply_.readAll()).decode()
            
#     def checkInternetConnection(self, url:typing.Union[str, QtCore.QUrl] = "http://www.google.com/", 
#                                   raise_error:bool=True):
#         
#         if isinstance(url, str):
#             url = QtCore.QUrl(url)
#         
#         request = QtNetwork.QNetworkRequest(url)
#         request.setRawHeader(b"User-Agent", b"Mozilla 5.0")
#         self._networkReply_ = self._manager_.get(request)
#         self._networkReply_.readyRead.connect(self.slot_checkConnectionReady)
#         self._networkReply_.finished.connect(self.slot_checkConnectionFinished)
#         self._networkReply_.errorOccurred.connect(self.slot_checkConnectionError)
#         self._networkReply_.sslErrors.connect(self.slot_checkConnectionSSLError)
#         # self._networkReply_.deleteLater()
        
#     def getTextFromUrl(self, url:typing.Union[str, QtCore.QUrl]):
#         if isinstance(url, str):
#             url = QtCore.QUrl(url)
#         
#         request = QtNetwork.QNetworkRequest(url)
#         request.setRawHeader(b"User-Agent", b"Mozilla 5.0")
#         self._replyText_ = None
#         self._networkReply_ = self._manager_.get(request)
#         self._networkReply_.readyRead.connect(self.slot_replyReady)
#         self._networkReply_.finished.connect(self.slot_replyFinished)
#         self._networkReply_.errorOccurred.connect(self.slot_replyConnectionError)
#         self._networkReply_.sslErrors.connect(self.slot_replySSLError)
        
    # @Slot()
    # def slot_replyReady(self):
    #     pass
        # self._replyText_ = bytes(self._networkReply_.readAll()).decode()
        
    # @Slot(QtNetwork.QNetworkReply)
    # def slot_replyFinished(self, reply:QtNetwork.QNetworkReply):
    # @Slot()
    # def slot_replyFinished(self):
    #     reply = self.sender()
    #     txt = bytes(reply.readAll()).decode()
    #     self.sig_textFromUrl.emit(txt)
        
        # self._replyText_ = bytes(reply.readAll()).decode()
        # self.sig_textFromUrl.emit(self._replyText_)
        
    # @Slot()
    # def slot_checkConnectionFinished(self):
    #     # reply = self.sender()
    #     rawHeaders = self._networkReply_.rawHeaderPairs()
    #     # for x in rawHeaders:
    #     #     print(f"{bytes(x[0]).decode()} ↦ {bytes(x[1]).decode()}")
    #     self._hasInternet_ = len(rawHeaders) > 0
    #     self.sig_hasInternet.emit(self._hasInternet_)
    #     if self._hasInternet_:
    #         self._sig_goAhead.emit()
    
    # @Slot()
    # def slot_checkConnectionReady(self):
    #     # reply = self.sender()
    #     data = bytes(self._networkReply_.readAll()).decode()
    #     # rawHeaders = self._networkReply_.rawHeaderPairs()
    #     # for x in rawHeaders:
    #     #     print(f"{bytes(x[0]).decode()} ↦ {bytes(x[1]).decode()}")
    #     self._hasInternet_ = len(data) > 0
    #     self.sig_hasInternet.emit(self._hasInternet_)
    
    # @Slot()
    # def slot_replyConnectionError(self):
    #     scipywarn("No internet connection available.")
    #     self._hasInternet_=False
    #     self.sig_hasInternet.emit(self._hasInternet_)
    
    # @Slot()
    # def slot_checkConnectionError(self):
    #     scipywarn("No internet connection available.")
    #     self._hasInternet_=False
    #     self.sig_hasInternet.emit(self._hasInternet_)
    
    # @Slot()
    # def slot_checkConnectionSSLError(self):
    #     scipywarn("No secure internet connection available.")
    #     self._hasInternet_=False
    #     self.sig_hasInternet.emit(self._hasInternet_)

    # @Slot()
    # def slot_replySSLError(self):
    #     scipywarn("No secure internet connection available.")
    #     self._hasInternet_=False
    #     self.sig_hasInternet.emit(self._hasInternet_)

    @property
    def networkReply(self) -> QtNetwork.QNetworkReply | None:
        return self._networkReply_
