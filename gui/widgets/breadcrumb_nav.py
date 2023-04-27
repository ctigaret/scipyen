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
    sig_navigate = pyqtSignal(pathlib.Path, name="sig_navigate")
        
    def __init__(self, path:pathlib.Path, isBranch:bool=False, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        # if not path.is_absolute():
        path = path.resolve()
            
        if not path.is_dir():
            path = path.parent

        self.path=path

        self.name = self.path.name
        self._isBranch_ = isBranch
        
        # NOTE: 2023-04-27 08:38:31
        # defines the following members: 
        # self.fileSystemModel, self.rootIndex, self.dirButton, self.branchButton
        # self.branchIcon, self.iconSize, self.subDirsMenu
        self._configureUI_()
        
    def _configureUI_(self):
        print(f"{self.__class__.__name__}._configureUI_ path {self.path.as_posix()}")
        self.fileSystemModel = QtWidgets.QFileSystemModel(parent=self)
        self.fileSystemModel.setOption(QtWidgets.QFileSystemModel.DontWatchForChanges, True)
        self.fileSystemModel.setReadOnly(True)
        self.fileSystemModel.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.CaseSensitive | QtCore.QDir.NoDotAndDotDot)
        self.fileSystemModel.setRootPath(self.path.as_posix())
        self.rootIndex = self.fileSystemModel.index(self.fileSystemModel.rootPath())

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        # pathParts = self.path.parts
        # self.dirButton = QtWidgets.QPushButton(pathParts[-1])
        w,h = guiutils.get_text_width_and_height(self.name)
        self.dirButton = QtWidgets.QPushButton(self.name, self)
        self.dirButton.setFlat(True)
        self.dirButton.setMinimumSize(w,h)
        self.dirButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        self.dirButton.clicked.connect(self.dirButtonClicked)
        
        self.branchIcon = QtGui.QIcon.fromTheme("go-next")
        self.iconSize = self.branchIcon.actualSize(QtCore.QSize(16,16), state=QtGui.QIcon.On)
        
        self.branchButton = QtWidgets.QPushButton(self.branchIcon, "", self)
        self.branchButton.setFlat(True)
        self.branchButton.setMinimumSize(self.iconSize.width(), self.iconSize.height())
        self.branchButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum))
        self.branchButton.clicked.connect(self.branchButton.showMenu)
        
        self.layout.addWidget(self.dirButton)
        self.layout.addWidget(self.branchButton)
        
        self.subDirsMenu = QtWidgets.QMenu("", self.branchButton)
        print(f"{self.__class__.__name__}._configureUI_ rootIndex {self.fileSystemModel.data(self.rootIndex)}")
        if self.fileSystemModel.hasChildren(self.rootIndex):
            subDirs = [self.fileSystemModel.data(self.fileSystemModel.index(row, 0, self.rootIndex)) for row in range(self.fileSystemModel.rowCount(self.rootIndex))]
            action_0 = None
            if len(subDirs):
                for k, subDir in enumerate(subDirs):
                    action = self.subDirsMenu.addAction(subDir)
                    if k == 0:
                        action_0 = action
                    path = self.path.parent.join(subDir)
                    action.triggered.connect(self.sig_navigate.emit(path))
        
                self.branchButton.setMenu(self.subDirsMenu)
        
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
        
class Navigator(QtWidgets.QWidget):
    # def __init__(self, url:QtCore.QUrl, parent:typing.Optional[QtWidgets.QWidget] = None):
    def __init__(self, path:pathlib.Path, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        self.path=path
        self.crumbs = list()
        self._configureUI_()
        self._setupCrumbs_()
        
        for bc in self.crumbs:
            self.hlayout.addWidget(bc)
        
    def _configureUI_(self):
        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.setContentsMargins(0,0,0,0)
        self.setLayout(self.hlayout)
        
    def _setupCrumbs_(self):
        parts = self.path.parts
        partPaths = [pathlib.Path(*parts[0:k]) for k in range(1, len(parts))]
        nCrumbs = len(partPaths)
        for k, p in enumerate(partPaths):
            isBranch = k < nCrumbs-1
            b = BreadCrumb(p, isBranch)#, parent=self)
            b.sig_navigate.connect(self.slot_crumb_request)
            self.crumbs.append(BreadCrumb(p, isBranch, parent=self))
            # self.layout.addWidget(b)
            
    @pyqtSlot(pathlib.Path)
    def slot_crumb_request(self, path):
        print(f"{self.__class__.__name__} {path.as_posix()}")
        
        
        
        
    
