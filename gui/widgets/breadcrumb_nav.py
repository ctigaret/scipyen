import typing, pathlib, functools, os
from urllib.parse import urlparse, urlsplit
from enum import Enum, IntEnum
import sip # for sip.isdeleted() - not used yet, but beware
from traitlets.utils.bunch import Bunch
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType

from core import desktoputils
import gui.pictgui as pgui
from gui import guiutils
from iolib import pictio

# Root > dir > subdir

class BreadCrumb(QtWidgets.QWidget):
    def __init__(self, path:pathlib.Path, isBranch:bool=False, parent:typing.Optional[QtWidgets.QWidget]=None):
        sig_navigate = pyqtSignal(pathlib.Path, name="sig_navigate")
        
        super().__init__(self, parent=parent)
        if not path.is_absolute():
            path = path.resolve()
            
        if not path.is_dir():
            path = path.parent

        self.path=path

        self.fileSystemModel = QtWidgets.QFileSystemModel(parent=self)
        self.fileSystemModel.setOption(QtWidgets.QFileSystemModel.DontWatchForChanges, True)
        self.fileSystemModel.setReadOnly(True)
        self.fileSystemModel.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.CaseSensitive | QtCore.QDir.NoDotAndDotDot)
        self.fileSystemModel.setRootPath(self.path.as_posix())

        self.name = self.path.name
        self.branchIcon = QtGui.QIcon.fromTheme("go-next")
        self.iconSize = self.branchIcon.actualSize(QtCore.QSize(16,16), state=QtGui.QIcon.On)
        self._isBranch_ = isBranch
        
        # defined in _configureUI_
        # self.dirButton = None
        # self.branchButton = None
        
        self._configureUI_()
        
    def _configureUI_(self):
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        # pathParts = self.path.parts
        # self.dirButton = QtWidgets.QPushButton(pathParts[-1])
        w,h = guiutils.get_text_width_and_height(self.name)
        self.dirButton = QtWidgets.QPushButton(self.name)
        self.dirButton.setFlat(True)
        self.dirButton.setMinimumSize(w,h)
        self.dirButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        self.dirButton.clicked.connect(self.dirButtonClicked)
        
        self.branchButton = QtWidgets.QPushButton(branchIcon)
        self.branchButton.setFlat(True)
        self.branchButton.setMinimumSize(self.iconSize.width(), self.iconSize.height())
        self.branchButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum))
        self.layout.addWidget(self.dirButton)
        self.layout.addWidget(self.branchButton)
        self.branchButton.setVisible(self.isBranch)
        
    @property
    def isBranch(self):
        return self._isBranch_
    
    @isBranch.setter
    def isBranch(self, value):
        self._isBranch_ = value == True
        self.branchButton.setVisible(self._isBranch_)
        
    @pyqtSlot()
    def dirButtonClicked(self):
        self.sig_navigate.emit(self.path)
        
    @pyqtSlot()
    def branchButtonClicked(self):
        index = self.fileSystemModel.index(self.fileSystemModel.rootPath(), 0)
        if index.hasChildren():
            
        cm = QtWidgets.QMenu("", self)
        
        

class Navigator(QtWidgets.QWidget):
    # def __init__(self, url:QtCore.QUrl, parent:typing.Optional[QtWidgets.QWidget] = None):
    def __init__(self, path:pathlib.Path, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(self, parent=parent)
        self.path=path
        # self.crumbs = list()
        self._configureUI_()
        
    def _configureUI_(self):
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
    
    def _setupCrumbs_(self):
        parts = self.path.parts
        
        for k, p in enumerate(parts):
            if k == 0:
                if p == os.path.sep:
                    pass
        
        
        
    
