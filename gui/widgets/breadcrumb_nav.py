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

class ArrowButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setArrowType(QtCore.Qt.RightArrow)
        self.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.icon = QtGui.QIcon.fromTheme("go-next")
        self.iconSize = self.icon.actualSize(QtCore.QSize(16,16), state=QtGui.QIcon.On)
        self.setMinimumSize(self.iconSize.width(), self.iconSize.height())
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum))
        opt = QtWidgets.QStyleOptionFrame()
        self.initStyleOption(opt)
        
    # def paintEvent(self, ev = QtGui.QPaintEvent):
    #     painter = QtGui.QPainter(self)
    #     style = self.style()
    #     super().paintEvent(ev)

    def initStyleOption(self, opt:QtWidgets.QStyleOptionFrame):
        """Required in all concrete subclasses of QWidget
        """
        opt.initFrom(self)
        # opt.state = QtWidgets.QStyle.State_Sunken if self.isDown() else QtWidgets.QStyle.State_Raised
        #  NOTE: 2021-05-14 21:52:32
        opt.features |= 0
        # if isinstance(self, QtWidgets.QPushButton) and self.isDefault():
        #     opt.features |= QtWidgets.QStyleOptionButton.DefaultButton
        # opt.text=""
        # opt.icon = QtGui.QIcon()
  
class BreadCrumb(QtWidgets.QWidget):
    sig_navigate = pyqtSignal(str, name="sig_navigate")
        
    def __init__(self, path:pathlib.Path, isBranch:bool=False, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        # if not path.is_absolute():
        path = path.resolve()
        print(f"{self.__class__.__name__}.__init__ path = {path}")
        if not path.is_dir():
            path = path.parent

        self.path=path

        self.name = self.path.name
        if len(self.name) == 0:
            self.name = self.path.parts[0]
            
        self._isBranch_ = isBranch
        self.subDirsMenu = None
        # NOTE: 2023-04-27 08:38:31
        # defines the following members: 
        # self.fileSystemModel, self.rootIndex, self.dirButton, self.branchButton
        # self.branchIcon, self.iconSize, self.subDirsMenu
        self._configureUI_()
        
    def _configureUI_(self):
        # print(f"{self.__class__.__name__}._configureUI_ path {self.path.as_posix()}")
        self.fileSystemModel = QtWidgets.QFileSystemModel(parent=self)
        # self.fileSystemModel.setOption(QtWidgets.QFileSystemModel.DontWatchForChanges, True)
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
        self.iconSize = self.branchIcon.actualSize(QtCore.QSize(16,h), state=QtGui.QIcon.On)
        
        # self.branchButton = QtWidgets.QPushButton(self.branchIcon, "", self)
        # self.branchButton = ArrowButton(self)
        self.branchButton = QtWidgets.QToolButton(self)
        self.branchButton.setArrowType(QtCore.Qt.RightArrow)
        # self.branchButton.setFlat(True)
        self.branchButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.branchButton.setMinimumSize(self.iconSize.width(), self.iconSize.height())
        self.branchButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum))
        self.branchButton.clicked.connect(self.branchButtonClicked)
        
        
        self.layout.addWidget(self.dirButton)
        self.layout.addWidget(self.branchButton)
        
        self.branchButton.setVisible(self.isBranch)
        
    # def painEvent(self)
    @property
    def isBranch(self):
        return self._isBranch_
    
    @isBranch.setter
    def isBranch(self, value):
        self._isBranch_ = value == True
        self.branchButton.setVisible(self._isBranch_)
        
    @pyqtSlot()
    def dirButtonClicked(self):
        # print(f"{self.__class__.__name__}.dirButtonClicked on {self.name}")
        self.sig_navigate.emit(self.path.as_posix())
        
    @pyqtSlot()
    def branchButtonClicked(self):
        if self.subDirsMenu is None:
            self.subDirsMenu = QtWidgets.QMenu("", self.branchButton)
            self.subDirsMenu.aboutToHide.connect(self.slot_menuHiding)
            
        self.subDirsMenu.clear()
        
        if self.fileSystemModel.hasChildren(self.rootIndex):
            subDirs = [self.fileSystemModel.data(self.fileSystemModel.index(row, 0, self.rootIndex)) for row in range(self.fileSystemModel.rowCount(self.rootIndex))]
            # print(f"rootIndex subDirs {subDirs}")
            if len(subDirs):
                for k, subDir in enumerate(subDirs):
                    # print(f"subDir {subDir}")
                    action = self.subDirsMenu.addAction(subDir)
                    action.setText(subDir)
                    action.triggered.connect(self.slot_subDirClick)
        
                self.branchButton.setMenu(self.subDirsMenu)
            self.branchButton.setArrowType(QtCore.Qt.DownArrow)
            self.branchButton.showMenu()
        
    @pyqtSlot()
    def slot_subDirClick(self):
        action = self.sender()
        ps = os.path.join(self.path.as_posix(), action.text())
        self.sig_navigate.emit(ps)
        self.branchButton.setArrowType(QtCore.Qt.RightArrow)
        
    @pyqtSlot()
    def slot_menuHiding(self):
        self.branchButton.setArrowType(QtCore.Qt.RightArrow)
        
        
class BreadCrumbsNavigator(QtWidgets.QWidget):
    # def __init__(self, url:QtCore.QUrl, parent:typing.Optional[QtWidgets.QWidget] = None):
    def __init__(self, path:pathlib.Path, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        if not path.is_dir():
            path = path.parent
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
        print(f"{self.__class__.__name__}._setupCrumbs_ parts = {parts}")
        partPaths = [pathlib.Path(*parts[0:k]) for k in range(1, len(parts))] # avoid this dir dot
        nCrumbs = len(partPaths)
        for k, p in enumerate(partPaths):
            print(f"k = {k}; p = {p}")
            # isBranch = k < nCrumbs-1
            b = BreadCrumb(p, True)#, parent=self)
            b.sig_navigate.connect(self.slot_crumb_request)
            self.crumbs.append(b)
            # self.layout.addWidget(b)
            
        b = BreadCrumb(self.path, False) # last dir in path = LEAF !!!
        b.sig_navigate.connect(self.slot_crumb_request)
        self.crumbs.append(b)
        self.navspot = QtWidgets.PushButton("", self)
        self.navspot.setFlat(True)
        self.navspot.clicked.connect(self.slot_editPath_request)
        self.crumbs.append(self.navspot)
            
    @pyqtSlot(str)
    def slot_crumb_request(self, path):
        print(f"{self.__class__.__name__}.slot_crumb_request {path}")
        
    @pyqtSlot()
    def slot_editPath_request(self):
        print("to switch to path editing mode")
        
        
class PathEditor(QtWidgets.QWidget):
    sig_chDirString = pyqtSignal(str, name = "sig_chDirString")
    sig_removeCurrentDirFromHistory = pyqtSignal(str, name = "sig_removeCurrentDirFromHistory")
    sig_clearRecentDirsList = pyqtSignal(str, name = "sig_clearRecentDirsList")
    sig_switchToNavigator = pyqtSignal(name="sig_switchToNavigator")
    
    def _init__(self, path:pathlib.Path, recentDirs:list = [], parent=None):
        super().__init__(parent=parent) 
        self._recentDirs_ = recentDirs
        self._path_ = path
       
    def _configureUI_(self):
        self.directoryComboBox = QtWidgets.QComboBox(parent=self)
        self.directoryComboBox.setEditable(True)
        self.directoryComboBox.lineEdit().setClearButtonEnabled(True)
        self.directoryComboBox.lineEdit().undoAvailable = True
        self.directoryComboBox.lineEdit().redoAvailable = True
        self.directoryComboBox.lineEdit().addAction(self.removeRecentDirFromListAction,
                                                    QtWidgets.QLineEdit.TrailingPosition)
       
        self.directoryComboBox.activated[str].connect(self.slot_newDir) 
       
        self.removeRecentDirFromListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"), \
                                                        "Remove this path from list", \
                                                        self.directoryComboBox.lineEdit())
        
        self.removeRecentDirFromListAction.setToolTip("Remove this path from history")
        
        self.removeRecentDirFromListAction.triggered.connect(self.slot_removeDirFromHistory)
        
        self.clearRecentDirListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("final_activity"), \
                                                        "Clear history of visited paths", \
                                                        self.directoryComboBox.lineEdit())
        
        self.clearRecentDirListAction.setToolTip("Clear history of visited paths")
        
        self.clearRecentDirListAction.triggered.connect(self.slot_clearRecentDirList)
        
        self.switchToBreadCrumbsAction=QtWidgets.QAction(QtGui.QIcon.fromTheme("checkbox"),
                                                         "Apply",
                                                         self.directoryComboBox.lineEdit())
        
        self.switchToBreadCrumbsAction.setToolTip("End editing and switch to navigation bar")
        self.switchToBreadCrumbsAction.triggered.connect(self.sig_switchToNavigator)
        
        
    @property
    def history(self):
        return self._recentDirs_
    
    @history.setter
    def history(self, value:list=list()):
        self._recentDirs_[:] = value
        if len(self._recentDirs_):
            self.directoryComboBox.clear()
            for item in self._recentDirs_:
                self.directoryComboBox.addItem(item)
                
        self.directoryComboBox.setCurrentIndex(0)
        
    @pyqtSlot()
    def slot_removeDirFromHistory(self):
        signalBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        currentNdx = self.directoryComboBox.currentIndex()
        self.directoryComboBox.removeItem(currentNdx)
        self.directoryComboBox.lineEdit().setClearButtonEnabled(True)
        
    @pyqtSlot()
    def slot_clearRecentDirList(self):
        signalBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        self.directoryComboBox.clear()
        
    @pyqtSlot(str)
    def slot_newDir(self, value):
        self.sig_chDirString.emit(value)
        
class Navigator(QtWidgets.QWidget):
    def __init__(self, path:pathlib.Path, parent=None):
        super().__init__(parent=parent)
        
        self.path = path
        self.bcNav = BreadCrumbsNavigator(path, self)
        self.editor = PathEditor(path,self)
        self.editor.sig_chDirString[str].connect(self.slot_newDir)
        
    @pytSlot(str)
    def slot_newDir(self, value):
        pass
        
    
