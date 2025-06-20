# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import sys, os, typing, collections, pathlib, tarfile, dataclasses
import inspect, functools, traceback
from dataclasses import MISSING
from functools import (singledispatch, singledispatchmethod)
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
        
    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True
    
if __has_sip__:
    QtType = typing.TypeVar("QtType", bound = "sip.wrappertype")
else:
    QtType = typing.TypeVar("QtType", bound = "Shiboken.Object")
    

from core.prog import (safewrapper, scipywarn, print_styled)
from core.sysutils import adapt_ui_path
from gui.widgets.cancellableqprogressbar import CancellableQProgressBar
__module_path__ = os.path.abspath(os.path.dirname(__file__))

QtReplyNetworkErrors = dict((name, val) for name, val in vars(QtNetwork.QNetworkReply).items() if isinstance(val, QtNetwork.QNetworkReply.NetworkError))

QDefaultTransferTimeoutConstant = QtNetwork.QNetworkRequest.TransferTimeoutConstant.DefaultTransferTimeoutConstant
    
from core.prog import (safewrapper, scipywarn, print_styled)
from core.sysutils import adapt_ui_path
from gui.widgets.cancellableqprogressbar import CancellableQProgressBar

__module_path__ = os.path.abspath(os.path.dirname(__file__))

QtReplyNetworkErrors = dict((name, val) for name, val in vars(QtNetwork.QNetworkReply).items() if isinstance(val, QtNetwork.QNetworkReply.NetworkError))

class ScipyenNetworkManager(QtCore.QObject):
    # NOTE: 2024-11-27 11:16:32
    # working towards a network manager for downloading remote data;
    # starting out with Qt 5 examples/network/downloadmanager a.k.a qt5ex
    #
    sig_hasInternet = Signal(bool, name="sig_hasInternet")
    sig_replyFromUrl = Signal(object, name="sig_replyFromUrl")
    sig_finished = Signal(name="sig_finished)")
    sig_resultReady = Signal(object, name="sig_resultReady")
    sig_networkError = Signal(object,name="sig_networkError")
    defaultMaxDownloadSizeForProgressBar = 2147483647
    
    def __init__(self, timeout_ms:int = QDefaultTransferTimeoutConstant,
                 replyHandler:typing.Optional[typing.Callable] = None,
                 progressUIFactory:typing.Optional[QtType]=None,
                 parent:typing.Optional[QtCore.QObject] = None):
                 # verbose:bool=False,
                 # parent:typing.Optional[QtCore.QObject] = None):
        r"""Constructor for ScipyenNetworkManager
        Parameters:
        ----------
        timeout_ms:int = the underlying QNetworkAccessManager timeout (in ms)
            Optional; default is 3000 ms

        replyHandler:Callable (i.e. a function) with syntax:
            replyHandler(obj: object, manager: ScipyenNetworkManager) -> None
        
            This function is used to process downloaded data received from the 
            URL parameters to the getUrl(…) method.

            WARNING: When more than one URL is passed to getUrl (i.e. a sequential
            download of URLs) the SAME handler will be used !

            A workaround is to drive a sequential download indirectly, via the handler,
            see the example_sequential_download_handler(…) function in this module.

            ATTENTION: Any reply handler passed as parameter to the getUrl method
            will replace the one specified here.

            Optional; default is None

        verbose:bool. Turn on some informative messages at the console; default is
            False

        parent: parent Qt object; default is None
        
        """
        from core import workspacefunctions as wf
        super().__init__(parent=parent)
        
        self.scipyenWindow = wf.getMainScipyenWindow()
        
        # self._verbose_ = verbose
        self._timeout_ms_ = timeout_ms
        self._downloadQueue_ = collections.deque() # qt5ex
        self._downloadedCount_ = 0 # qt5ex
        self._totalCount_ = 0 # qt5ex
        self._outputFile_ = QtCore.QFile() # qt5ex
        self._tempFile_ = QtCore.QTemporaryFile()
        self._tempFile_.setAutoRemove(False)
        self._saveToFile_ = False
        self._networkError_ = QtNetwork.QNetworkReply.NoError
        self._urlToCheck_ = None
        # self._urlToDownload_ = None
        # self._replyTextBuffer_ = QtCore.QTextStream()
        
        # self._outputFileName_ = dataclasses.MISSING
        r"""This can be MISSING, None or a string:
        MISSING: let ScipyenNetworkManager decide (by calling self._setSaveFileName)
        None: does NOT download the reply to a file; useful to process it in memory
            (WARNING this can be very expensive)
        A string: download to a faile with path given by the string
        """
        
        
        self._removeOnFail_ = True
        self._replyInfo_ = None
        
        self._networkReply_ = None # cannot instantiate QNetworkReply (is abstract) # qt5ex
        self._downloadTime_ = QtCore.QTime() # ~qt5ex
        self._progressUI_ = None # ~qt5ex
        self._progressUIFactory_ = QtWidgets.QProgressBar

        self._userDefinedProgressUIFactory_ = progressUIFactory
            
        self._content_length_ = 0
        self._temp_download_size_ = None
        
        self._replyHandler_ = replyHandler
        self._maxDownloadSizeForProgressBar = int(5e6)
        
        self._manager_ = QtNetwork.QNetworkAccessManager(self) # also qt5ex
        self._manager_.setTransferTimeout(self._timeout_ms_)
        
        # this is OK here
        self.sig_replyFromUrl.connect(self.slot_processUrlReply)
        
        self._manager_.finished[QtNetwork.QNetworkReply].connect(self.slot_handleNetworkManagerFinished)
    
    @property
    def networkManager(self)-> QtNetwork.QNetworkAccessManager:
        return self._manager_
    
    def setNextDownloadSize(self, val:typing.Optional[int] = None):
        print(f"{self.__class__.__name__}.setNextDownloadSize: {val} bytes")
        self._progressUIFactory_ = self.getProgressUIFactory(val)
        if isinstance(val, int):
            self._temp_download_size_ = val
        else:
            self._temp_download_size_ = None
            
        # self._progressUIFactory_ = QtWidgets.QProgressBar if val < 2147483647 else QtWidgets.QProgressDialog
        
    @property
    def maximumDownloadSizeForProgressBar(self):
        return self._maxDownloadSizeForProgressBar
    
    @maximumDownloadSizeForProgressBar.setter
    def maximumDownloadSizeForProgressBar(self, val:int):
        if val > self.defaultMaxDownloadSizeForProgressBar:
            val = defaultMaxDownloadSizeForProgressBar
        elif val <= 0:
            val = int(5e6)
            
        self._maxDownloadSizeForProgressBar = val
        
    def getProgressUIFactory(self, downloadSize:int) -> QtType:
        factory = self._setUIFactory()
        print(f"{self.__class__.__name__}.getProgressUIFactory: factory = {factory}")
        ui_cancellable = self._isCancellableProgressUI(factory)
        if downloadSize >= self.maximumDownloadSizeForProgressBar and not ui_cancellable:
            factory = QtWidgets.QProgressDialog
        
        print(f"{self.__class__.__name__}.getProgressUIFactory: adjusted factory = {factory}")
        return factory
    
    @property
    def networkError(self) -> QtNetwork.QNetworkReply.NetworkError:
        return self._networkError_
    
    @property
    def networkErrorName(self) -> str:
        return getNetworkErrorName(self._networkError_)
    
    @property
    def replyHandler(self) -> typing.Callable | None:
        return self._replyHandler_
    
    @replyHandler.setter
    def replyHandler(self, val:typing.Optional[typing.Callable] = None):
        if val is not None and not isinstance(val, typing.Callable):
            scipywarn(f"In {self.__class__.__name__}.setReplyHandler: expecting a Callable or None; instead got {type(val).__name__}")
            return
        
        self._replyHandler_ = val
        
    def getUrl(self, source:typing.Union[str, QtCore.QUrl, typing.Sequence[typing.Union[str, QtCore.QUrl]]],
                   destination:typing.Optional[typing.Union[typing.Sequence[str], str, type(MISSING)]]=MISSING,
                   replyHandler:typing.Optional[typing.Union[typing.Callable, type(MISSING)]] = MISSING,
                   removeOnFailure:bool=True) -> None:
        r"""Request a remote file
        Parameters:
        source: url string QUrl, or a sequence (tuple, list) of these
        
        destination: destination file path where the data received from the URLs
            will be saved (including the file name & extension if any)
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
                the destination will automatically be modified subject to the above
                rules.
        
            When a sequence of str, it specifies a distinct destination for each
                URL in the sequesnce of URLs. Requires that bith the 'source' and 
                'destination' parameters are sequences with the same number of
                elements
                
        """
        self._totalCount_ = 0 # reset counters
        self._downloadedCount_ = 0 # reset counters
        self._removeOnFail_ = removeOnFailure
        
        if isinstance(destination, (tuple, list)):
            if not isinstance(source, (tuple, list)):
                raise TypeError("'destination' cannot be a seauence when only one URL is requested")
            if len(destination) != len(source):
                raise ValueError("Both 'source' and 'destination' must contain the same number of elements")
                
            if not all(isinstance(d, str) and len(d.strip()) for d in destination):
                raise ValueError("Invalid 'destination'")
            
        if isinstance(replyHandler, (type(None), typing.Callable)):
            self._replyHandler_ = replyHandler
            
        self._append(source, destination)
        
    @singledispatchmethod
    def _append(self, o:object, fileName:typing.Optional[str]=dataclasses.MISSING,
                save:bool=True):  # qt5ex
        raise NotImplementedError(f"Method is not implemented for {type(o).__name__} arguments")
        
    @_append.register(list)
    @_append.register(tuple)
    @_append.register(collections.deque)
    def _(self, urlList:typing.Sequence[typing.Union[str, QtCore.QUrl]], # qt5ex
          fileName:typing.Optional[typing.Union[typing.Sequence[str], str, type(MISSING)]]=MISSING) -> None:  
        
        if isinstance(fileName, (tuple, list)):
            for k,u in enumerate(urlList):
                self._append(u, fileName[k])
        else:
            for u in urlList:
                self._append(u, fileName)
            
        if len(self._downloadQueue_) == 0:
            QtCore.QTimer.singleShot(0, self.sig_finished)
            self._totalCount_ = 0
            
    @_append.register(str)
    @_append.register(QtCore.QUrl)
    def _(self, u: str | QtCore.QUrl, 
          fileName:typing.Optional[typing.Union[str, type(MISSING)]]=MISSING) -> None:  # qt5ex
        
        # if self._verbose_:
        #     print(f"In {self.__class__.__name__}._append(url= {u}, fileName = {fileName})")
        
        if len(self._downloadQueue_) == 0:
            QtCore.QTimer.singleShot(0, self._startNextDownload)
            
        url = u if isinstance(u, QtCore.QUrl) else QtCore.QUrl(u)
        
        self._downloadQueue_.append((url, fileName))
        self._totalCount_ += 1
        
    def _getRequest(self): # not used but keep ⌢
        if isinstance(self._request_, QtNetwork.QNetworkRequest):
            self._networkReply_ = self._manager_.get(self._request_)
        else:
            self._networkReply_ = None
            
    def _isCancellableProgressUI(self, factory:QtType) -> bool:
        cancel_sigs = list(filter(lambda x: x[0]=="canceled", inspect.getmembers_static(factory, predicate=lambda x: isinstance(x, QtCore.Signal))))
        return len(cancel_sigs)==1
            
    def _setUIFactory(self) -> QtType:
        if isinstance(self._userDefinedProgressUIFactory_, QtType):
            self._progressUIFactory_ = self._userDefinedProgressUIFactory_
            
        if self.scipyenWindow is None:
            if not any(c in inspect.getmro(self._progressUIFactory_) for c in (QtWidgets.QDialog, QtWidgets.QMainWindow)):
                factory = QtWidgets.QProgressDialog
            else:
                factory = self._progressUIFactory_
        else:
            factory = self._progressUIFactory_
            
        return factory
    
    def _initProgressUI(self):
        factory = self._setUIFactory()
        
        if self._progressUI_ is None:
            ui_cancellable = self._isCancellableProgressUI(factory)
            self._progressUI_ = factory(parent = self.scipyenWindow)
            if isinstance(self._progressUI_, (QtWidgets.QMainWindow, QtWidgets.QDialog)):
                self._progressUI_.setLabelText("Downloading...")
            else:
                self.scipyenWindow.statusBar().addPermanentWidget(self._progressUI_)
                
            if ui_cancellable:
                self._progressUI_.canceled.connect(self.slot_abortReply)
        else:
            ui_cancellable = self._isCancellableProgressUI(type(self._progressUI_))
            if not self._progressUI_.isVisible():
                if not isinstance(self._progressUI_, (QtWidgets.QMainWindow, QtWidgets.QDialog)):
                    if self._progressUI_ not in self.scipyenWindow.statusBar().children():
                        self.scipyenWindow.statusBar().addPermanentWidget(self._progressUI_)
                self._progressUI_.show()
                
    def _resetProgressUI_(self, remove:bool=False):
        if isinstance(self._progressUI_, (QtWidgets.QMainWindow, QtWidgets.QDialog)):
            self._progressUI_.reset() # clear progressbar
            self._progressUI_.close()
        elif self.scipyenWindow is not None and self._progressUI_:
            self._progressUI_.reset() # clear progressbar
            self.scipyenWindow.statusBar().removeWidget(self._progressUI_)
            self._progressUI_.close()
            
        if remove:
            self._progressUI_ = None
       
         
    def _startNextDownload(self): # qt5ex
        if len(self._downloadQueue_) == 0:
            print(f"{self._downloadedCount_}/{self._totalCount_} files downloaded")
            self._temp_download_size_ = None
            self._content_length_ = 0
            self._downloadedCount_ = 0
            if self._saveToFile_:
                if self._tempFile_.exists():
                    self.sig_resultReady.emit(self._tempFile_)
                elif self._outputFile_.exists():
                    self.sig_resultReady.emit(self._outputFile_.fileName())
            self.sig_finished.emit()
            return
        
        self._initProgressUI()
        
        url,fileName = self._downloadQueue_.popleft()
        
        if fileName is MISSING:
            fileName = self._setSaveFileName(url)
            
        if isinstance(fileName, str):
            self._saveToFile_ = True
            if fileName.lower() == "temp":
                if not self._tempFile_.open(QtCore.QIODevice.WriteOnly):
                    scipywarn(f"In {self.__class__.__name__}._startNextDownload: Problem opening temporary file {fileName} for saving from {url.url()}:\n{self._tempFile_.errorString()}")
                    self._startNextDownload() # NOTE: 2024-12-01 15:09:16 will reset counters if download quere is empty
                    return
            else:
                self._outputFile_.setFileName(fileName)
                if not self._outputFile_.open(QtCore.QIODevice.WriteOnly):
                    # NOTE: 2024-12-01 15:08:42
                    # This branch called when one could not open fileName for writing
                    scipywarn(f"In {self.__class__.__name__}._startNextDownload: Problem opening file {fileName} for saving from {url.url()}:\n{self._outputFile_.errorString()}")
                    self._startNextDownload() # NOTE: 2024-12-01 15:09:16 will reset counters if download quere is empty
                    return
            
        else:
            self._saveToFile_ = False
            
        request = QtNetwork.QNetworkRequest(url)
        request.setRawHeader(b"User-Agent", b"Mozilla 5.0")
        self._networkReply_ = self._manager_.get(request)
        
        self._networkReply_.downloadProgress["qint64", "qint64"].connect(self.slot_downloadProgress)
        
        # NOTE: 2024-12-01 15:09:49
        # The logic below is as follows:
        # 1) If fileName is None, this means that the downloaded data needs to 
        # be processed in memory (CAUTION, here!) using a reply handler, if supplied
        # either as parameter to getUrl or at the initalization of this instance
        # (WARNING: this last one is questionable, probably best to remove this option)
        #
        #   in this case we bypass the QNetworkReply's finished signal and just
        #   call the replyHandler to process the data — again CAUTION with processing
        #   in-memory - this can be very expensive!
        #
        # 2) if fileName is a str, then this mens there is an output file pointing
        # to it, in write mode -> just save the data to that file
        #

        if self._saveToFile_:
            self._networkReply_.finished.connect(self.slot_downloadFinished)
            
        self._networkReply_.readyRead.connect(self.slot_downloadReadyRead)
        self._networkReply_.metaDataChanged.connect(self.slot_downloadHeaderChanged)
        
        if self._saveToFile_:
            fName = self._tempFile_.fileName() if self._tempFile_.isOpen() else self._outputFile_.fileName() if (isinstance(self._outputFile_, QtCore.QFile) and self._outputFile_.isOpen()) else ""
            print(print_styled(f"Downloading {url.url()} to {fName} ...", "green",True))
        else:
            print(print_styled(f"Downloading {url.url()} ...", "green",True))
            # print(print_styled(f"Handler: {self._replyHandler_} ...", "green",True))
            
        self._downloadTime_.start()
        
    def checkUrl(self, url:typing.Union[str, QtCore.QUrl]) -> bool:
        self._networkError_ = QtNetwork.QNetworkReply.NoError
        if isinstance(url, str):
            url = QtCore.QUrl(url)
            
        self._urlToCheck_ = url
        QtCore.QTimer.singleShot(1000, self._startCheckUrl)
        
        
    def _startCheckUrl(self):
        if self._urlToCheck_ is None:
            return
        request = QtNetwork.QNetworkRequest(self._urlToCheck_)
        request.setRawHeader(b"User-Agent", b"Mozilla 5.0")
        self._networkReply_ = self._manager_.get(request)
        self._manager_.finished.connect(self.slot_handleNetworkData)
        
    def _setSaveFileName(self, url:QtCore.QUrl) -> str:  # ~qt5ex
        from iolib import pictio as pio
        path = pathlib.Path(url.path())
        basename = path.name
        if len(basename.strip()) == 0:
            basename="download"
            
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
            
    @Slot("qint64", "qint64")
    def slot_downloadProgress(self, bytesReceived:int, bytesTotal:int) -> None: # qt5ex
        reply = self.sender()
        netError = reply.error()
        self._networkError_ = netError
        if netError:
            print(print_styled(f"{self.__class__.__name__}._startNextDownload: {reply.request().url().url()}: {getNetworkErrorName(netError)}", "red"))
            self._resetProgressUI_(False)
            # self._progressUI_.reset() # clear progressbar
            # if isinstance(self._progressUI_, QtWidgets.QProgressBar) and self.scipyenWindow is not None:
            #     self.scipyenWindow.statusBar().removeWidget(self._progressUI_)
            # elif isinstance(self._progressUI_, QtWidgets.QProgressDialog):
            #     self._progressUI_.close()
                
            self.sig_networkError.emit((reply.request().url().url(), getNetworkErrorName(netError)))
            return
        
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
        try:
            self._progressUI_.setRange(0, total)
            self._progressUI_.setValue(bytesReceived)
        except:
            # when range exceeds -2147483648 to 2147483647:
            self._progressUI_.setRange(0, 100)
            self._progressUI_.setValue(int(bytesReceived*100/total))
            
    @Slot()
    def slot_abortReply(self):
        try:
            self._networkReply_.abort()
            self._networkReply_.close()
        except:
            traceback.print_exc()
            
        self._manager_.finished.emit(None)
            
    @Slot()
    def slot_downloadFinished(self)-> None: # ~qt5ex
        # print(f"In {self.__class__.__name__}.slot_downloadFinished:  output file name: {self._outputFile_.fileName()}, reply handler: {self._replyHandler_}")
        if self._saveToFile_:
            if self._tempFile_.isOpen():
                self._tempFile_.close()
                fName = self._tempFile_.fileName()
                
            elif self._outputFile_.isOpen():
                self._outputFile_.close()
                fName = self._outputFile_.fileName()
                
            netError = self._networkReply_.error()
                
            if netError:
                scipywarn(f"In {self.__class__.__name__}.slot_downloadFinished Failed downloading {fName}:\n {self._networkReply_.errorString()} ")
                if self._removeOnFail_:
                    if self._outputFile_.exists():
                        if not self._outputFile_.remove():
                            scipywarn(f"In {self.__class__.__name__}.slot_downloadFinished Failed to remove incomplete download file:\n {self._outputFile_.fileName()} ")
                    elif self._tempFile_.exists():
                        if not self._tempFile_.remove():
                            scipywarn(f"In {self.__class__.__name__}.slot_downloadFinished Failed to remove incomplete temporary file:\n {self._tempFile_.fileName()} ")
            else:
                print(print_styled("Succeeded", "green", True))
                self._downloadedCount_ += 1
                
        self._networkError_ = netError
        
        self._resetProgressUI_(False)
        
        # if isinstance(self._progressUI_, (QtWidgets.QMainWindow, QtWidgets.QDialog))
        #     self._progressUI_.reset() # clear progressbar
        #     self._progressUI_.close()
        # elif self.scipyenWindow is not None:
        #     self._progressUI_.reset() # clear progressbar
        #     self.scipyenWindow.statusBar().removeWidget(self._progressUI_)
        #     self._progressUI_.close()
        # if isinstance(self._progressUI_, QtWidgets.QProgressBar) and self.scipyenWindow is not None:
        #     self._progressUI_.reset() # clear progressbar
        #     self.scipyenWindow.statusBar().removeWidget(self._progressUI_)
        # elif isinstance(self._progressUI_, QtWidgets.QProgressDialog):
        #     self._progressUI_.reset() # clear progressbar
        
        self._networkReply_.deleteLater()
        # self._progressUI_ = None
        self._startNextDownload()
        
    @Slot(QtNetwork.QNetworkReply)
    def slot_handleURLCheck(self, reply:QtNetwork.QNetworkReply):
        url = reply.url()
        if isinstance(self._urlToCheck_, QtCore.Qurl) and url != self._urlToCheck_:
            scipywarn(f"{self.__class__.__name__}.slot_handleURLCheck: Expecting to check {self._urlToCheck_.url()}; insetad, got {url.url()}")
            return
        
        netError = reply.error()
        if netError:
            scipywarn(f"{print_styled(getNetworkErrorName(netError), 'yellow', True)} for {print_styled(url.url(), 'green', True)}")
            
        reply.deleteLater()
        self._networkError_ = netError
        self.sig_resultReady.emit([self._networkError_, url.url()])
        self._urlToCheck_ = None
        
        
    @Slot(QtNetwork.QNetworkReply)
    def slot_handleNetworkData(self, reply:QtNetwork.QNetworkReply):
        r"""Generic handler"""
        url = reply.url()
        netError = reply.error()
        if netError:
            scipywarn(getNetworkErrorName(netError))
            
        reply.deleteLater()
        self._networkError_ = netError
        
    @Slot(QtNetwork.QNetworkReply)
    def slot_handleNetworkManagerFinished(self, reply:QtNetwork.QNetworkReply):
        # print(f"In {self.__class__.__name__}.slot_handleNetworkManagerFinished")
        
        if isinstance(reply, QtNetwork.QNetworkReply):
            netError = reply.error()
            self._networkError_ = netError
            
            if not netError:
                if self._saveToFile_ and self._outputFile_.exists():
                    self._replyInfo_ = self._outputFile_.fileName()
                else:
                    self._replyInfo_ = reply.readAll()
                
                # The signal sig_replyFromUrl must be connected to a slot that
                # processes reply data `_replyInfo_` in-memory; this can be either:
                # • self.slot_processUrlReply
                #   which will call self._replyHandler_
                #
                # • a suitable slot in another QObject instance
                #   which takes care of the processing of `_replyInfo_`
                #
                # TODO: 2024-12-01 22:31:38
                # must find a way to pass other data if necessary, to the handle,
                # not just the _replyInfo_ !
                self.sig_replyFromUrl.emit(self._replyInfo_)
                
                # ### BEGIN DO NOT DELETE - this exmplains why we need to call the
                # replyHandler via a signal.slot mechanism!
                #
                # What if I call the processing function directly ?!?
                #
                # self.slot_processUrlReply(self._replyInfo_)
                #
                # Unfortunately, this won't work, in the sense that variables assigned
                # to by the processing code won't be seen by `self` by the time it 
                # carries out the next task; 
                #
                # The tasks NEED to be triggered via the signal.slot mechanism!!!
                
                # ### END DO NOT DELETE
                
                # self._downloadedCount_ += 1
                
            reply.deleteLater()
            
        self._resetProgressUI_(True)
        # if isinstance(self._progressUI_, (QtWidgets.QMainWindow, QtWidgets.QDialog))
        #     self._progressUI_.reset() # clear progressbar
        #     self._progressUI_.close()
        # elif self.scipyenWindow is not None:
        #     self._progressUI_.reset() # clear progressbar
        #     self.scipyenWindow.statusBar().removeWidget(self._progressUI_)
        #     self._progressUI_.close()

        # if isinstance(self._progressUI_, (QtWidgets.QProgressBar, QtWidgets.QProgressDialog)):
        #     self._progressUI_.reset()
        #     if isinstance(self._progressUI_, QtWidgets.QProgressBar) and self.scipyenWindow is not None:
        #         self.scipyenWindow.statusBar().removeWidget(self._progressUI_)
        #     else:
        #         self._progressUI_.close()
                
        # self._progressUI_ = None
            
    @Slot(object)
    def slot_processUrlReply(self, s:object):
        if isinstance(self._replyHandler_, typing.Callable):
            # print(f"{self.__class__.__name__}.slot_processUrlReply will call {self._replyHandler_}")
            try:
                self._replyHandler_(s, self)
            except:
                traceback.print_exc()
        
    @Slot()
    def slot_downloadHeaderChanged(self):
        r"""Use to retrieve the advertised expected download size using the reply's headers.
        This may not be available; in this case, the expected download size MAY be
        retrieved by other means...
        """
        # NOTE 2024-11-28 09:20:58
        # Won't work well if content length is not supplied in the header.
        # For some sites a trick is to get the size of the downloaded file from
        # somewhere else - e.g., in BrainbGlobe atlases, to download the "src" page 
        # for a given atlas, and parse the (expected) size from there
        # 
        # However, that is just a particular case...
        #
        #
        # For BrainGlobe I'd do something like:
        # URL to retrieve the file
        # url = bgbridge.brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base.format("example_mouse_100um_v1.2.tar.gz")
        #
        # URL to get file size:
        # src_url = url.replace("raw", "src")
        #
        netError = self._networkReply_.error()
        rawHeaders = self._networkReply_.rawHeaderPairs()
        # if self._verbose_:
        #     print(f"{self.__class__.__name__}.slot_downloadHeaderChanged:")
        #     for x in rawHeaders:
        #         print(f"{bytes(x[0]).decode()} ↦ {bytes(x[1]).decode()}")
            
        if not isinstance(self._temp_download_size_, int):
            if self._networkReply_.hasRawHeader(b"content-length"):
                self._content_length_ = self._networkReply_.header(QtNetwork.QNetworkRequest.ContentLengthHeader)
        else:
            self._content_length_ = self._temp_download_size_
            
        self._networkError_ = netError
        # if self._verbose_:
        #     print(f"In {self.__class__.__name__}.slot_downloadHeaderChanged: content length = {self._content_length_}")
    
    @Slot()
    def slot_downloadReadyRead(self) -> None: # qt5ex   
        netError = self._networkReply_.error()
        
        if not netError:
            if self._tempFile_.isOpen():
                self._tempFile_.write(self._networkReply_.readAll())
            elif isinstance(self._outputFile_, QtCore.QFile) and self._outputFile_.exists():
                self._outputFile_.write(self._networkReply_.readAll())
        else:
            scipywarn(getNetworkErrorName(netError))
            
        self._networkError_ = netError
                

    @property
    def networkReply(self) -> QtNetwork.QNetworkReply | None:
        return self._networkReply_

def example_get_download_size(s:str) -> int:
    import re
    search_result = re.search(r"([0-9]+\.[0-9] [MGK]B)|([0-9]+ [MGK]B)", s)
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

# ### BEGIN Module-level functions

def example_sequential_download_handler(info:QtCore.QByteArray,
                                          manager:ScipyenNetworkManager,
                                          url:typing.Union[str, QtCore.QUrl], 
                                          ) -> None:
    r"""Example of reply handler for sequential download of URLs using ScipyenNetworkManager.
        
        The handler accomplishes the task of calculating the expected download size
        of the specified URL, using information retrieved from a previous URL.
        
        This is applicable for the particular case of downloading a remote archive
        from a site that advertises the size of the archive on a distinct url.
        
        Example: 

        Suppose the archive url is "https://www.some_place.org/archive.tar.gz";
        also suppose that the file size of the archive is listed on the web page
        with url: "https://www.some_place.org/archive_sizes.html"
        
        Let: 
            # url of the archive file
            url = "https://www.some_place.org/archive.tar.gz"
            
            # url containing informtion about the size of the archive file
            url1= "https://www.some_place.org/archive_sizes.html"
        
        The problem: we want to know the expected size of "archive.tar.gz" file
        in order to properly update a progress message or widget while downloading
        this file.

        The solution proposed here is to calculate or retrieve the size of 
        "archive.tar.gz" using the information downloaded from `url1`, then 
        use this value in the progress message or widget, while downloading 
        "archive.tar.gz" from `url2`. 

        In this example, the size of the archive file is parsed using a simple 
        regular expression applied on the text retrieved form url1, using the 
        auxiliary function `example_get_download_size`. 

        The auxiliary function could have been def-ed nested inside this
        example function (see _parse_size, in the code).
        
        Implementation of the solution:
        1) Create a functools.partial of this function by "fixing" the 'url' parameter
            to the URL of the archive to be downloaded:

        handle = functools.partial(network.example_sequential_download_handler, url = url)
        
        2) Create an instance of the ScipyenNetworkManager
        
            manager = network.ScipyenNetworkManager(verbose=False)
        
        3) Make sure the ScipyenNetworkManager signal `sig_replyFromUrl` is connected
            to its slot `slot_processUrlReply`. This slot will actually call the handler
            pased to `manager` at (4) below.
        
            manager.sig_replyFromUrl.connect(manager.slot_processUrlReply)
        
        4) Now, use `manager` to retrieve `url1`, passing the `handle` as the
        reply handler; 
        
            manager.getUrl(url1, destination=None, replyHandler=handle)
        
    Applicability
    -------------
    Thus example function was designed specifically to replicate downloading
    brainglobe atlas data from their repository IN A NON UI-BLOCKING MANNER.
        
    The code in the brainglobe_atlas uses the `requests` package to donwload the 
    two URLs sequentially, which is fine when run directly in a regular 
    python console (where they also provide a cli progress bar via the `rich`
    package). However, these operations are executed in a synchronous mode, and
    hence they are blocking (i.e., no user interaction can take place while the 
    code is executed.) While this could in principle be made asynchronous, the 
    tools provided by Python standard library to achieve this cannot be (easily)
    used from within the Qt event loop that runs inside the main thread of Scipyen.
        
    NOTE that in this case, `url` would be, e.g.,
        
    bgbridge.brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas._remote_url_base.format("example_mouse_100um_v1.2.tar.gz")
        
    and `url1` would be
        
        url1 = url.replace("raw", "src")
        
    """
    def _parse_size(s:str) -> int:
        import re
        search_result = re.search(r"([0-9]+\.[0-9] [MGK]B)|([0-9]+ [MGK]B)", s)
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
    
    # use manager to download from url conditioned on prevInfo
    # pass a partial to it, fixing the url
    # in network manager, pass the info and manager parameters
    if not isinstance(info, QtCore.QByteArray):
        raise TypeError(f"Expecting a QByteArray; instead, got {type(info).__name__}")
    
    info = bytes(info).decode()
    
    if not isinstance(info, str) or len(info.strip()) == 0:
        scipywarn("example_sequential_download_handler received invalid data")
        return 
    sz = _parse_size(info)
    if isinstance(sz, int):
        manager.setNextDownloadSize(sz)
    else:
        scipywarn("example_sequential_download_handler: Could not get the size of the next download")
        
    manager.getUrl(url, replyHandler=example_generic_handler) 
    
def example_generic_handler(obj:object, manager:ScipyenNetworkManager) -> None:
    print(f"example_generic_handler(obj:{type(obj).__name__})")
    
def getNetworkErrorName(e:QtNetwork.QNetworkReply.NetworkError) -> str:
    found = [name for name in QtReplyNetworkErrors if QtReplyNetworkErrors[name] == e]
    if len(found):
        return found[0]
    return "Undefined network error"

# ### END Module-level functions
