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

class DisplayHint(IntEnum):
    EnteredHint = 1
    DraggedHint = 2
    PopupActiveHint = 4
    
class NavigatorButtonBase(QtWidgets.QPushButton):
    """Common ancestor for NavigatorDropDownButton and NavigatorButton
    """
    BorderWidth = 2
    
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent)
        self._active=True
        self._displayHint = 0
        self.setFocusPolicy(QtCore.Qt.TabFocus)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, 
                           QtWidgets.QSizePolicy.Fixed)
        if isinstance(parent, QtWidgets.QWidget):
            self.setMinimumHeight(parent.minimumHeight())
        
        self.setAttribute(QtCore.Qt.WA_LayoutUsesWidgetRect)
        
        if hasattr(parent, "requestActivation"):
            self.pressed.connect(parent.requestActivation)
            
    def setActive(self, active:bool):
        if self._active != active:
            self._active = active is True
            self.update()
            
    def isActive(self) -> bool:
        return self._active
    
    @property
    def active(self) -> bool:
        return self._active
    
    @active.setter
    def active(self, value:bool):
        if self._active != value:
            self._active = value is True
            self.update()
    
    def setDisplayHintEnabled(self, hint:typing.Union[DisplayHint, int], enable:bool):
        if enable:
            self._displayHint = self._displayHint | hint
        else:
            self._displayHint = self._displayHint & ~hint
        update()

    def isDisplayHintEnabled(self, hint:typing.Union[DisplayHint, int]) -> bool:
        return (self._displayHint & hint) > 0
    
    def focusInEvent(self, event:QtGui.QFocusEvent):
        self.setDisplayHintEnabled(DisplayHint.EnteredHint, True)
        super().focusInEvent(event)
        
    def focusOutEvent(self, event:QtGui.QFocusEvent):
        self.setDisplayHintEnabled(DisplayHint.EnteredHint, False)
        super().focusOutEvent(event)
        
    #def enterEvent(self, event:QtGui.QEnterEvent):
    def enterEvent(self, event:QtCore.QEvent):
        super().enterEvent(event)
        self.setDisplayHintEnabled(DisplayHint.EnteredHint, True)
        self.update()
        
    def leaveEvent(self, event:QtCore.QEvent):
        super().leaveEvent(event)
        self.setDisplayHintEnabled(DisplayHint.EnteredHint,False)
        self.update()
        
    def drawHoverBackground(self, painter:QtGui.QPainter):
        isHighlighted = self.isDisplayHintEnabled(DisplayHint.EnteredHint) or self.isDisplayHintEnabled(DisplayHint.DraggedHint) or self.isDisplayHintEnabled(DisplayHint.PopupActiveHint)
        backgroundColor = self.palette().color(QtGui.QPalette.Highlight) if isHighlighted else QtCore.Qt.transparent
        if not self._active and isHighlighted:
            backgroundColor.setAlpha(128)
            
        if backgroundColor != QtCore.Qt.transparent:
            option = QtWidgets.QStyleOptionViewItem()
            option.initFrom(self)
            option.state = QtWidgets.QStyle.State_Enabled | QtWidgets.QStyle.State_Mouseover
            option.viewItemPosition = QtWidgets.QStyleOptionViewItem.OnlyOne
            self.style().drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, self)
            
    def foregroundColor(self) -> QtGui.QColor:
        isHighlighted = self.isDisplayHintEnabled(DisplayHint.EnteredHint) or self.isDisplayHintEnabled(DisplayHint.DraggedHint) or self.isDisplayHintEnabled(DisplayHint.PopupActiveHint)
        
        foregroundColor = self.palette().color(QtGui.QPalette.Foreground)
        
        alpha = 255 if self._active else 128
        
        if not self._active and not isHighlighted:
            alpha -= alpha/4
            
        foregroundColor.setAlpha(alpha)
        
        return foregroundColor
    
    def activate(self):
        self.active = True
        #self.setActive(true)
        
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
        
    def __init__(self, path:pathlib.Path, isBranch:bool=False, parentCrumb=None,parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        # if not path.is_absolute():
        path = path.resolve()
        # print(f"{self.__class__.__name__}.__init__ path = {path}")
        if not path.is_dir():
            path = path.parent

        self.path=path

        self.name = self.path.name
        
        self.parentCrumb = parentCrumb
        
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

        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.setContentsMargins(0,0,0,0)
        self.hlayout.setSpacing(0)
        self.setLayout(self.hlayout)
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
        
        
        self.hlayout.addWidget(self.dirButton)
        self.hlayout.addWidget(self.branchButton)
        
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
    sig_chDirString = pyqtSignal(str, name = "sig_chDirString")
    sig_switchToEditor = pyqtSignal(name = "sig_switchToEditor")
    # def __init__(self, url:QtCore.QUrl, parent:typing.Optional[QtWidgets.QWidget] = None):
    def __init__(self, path:pathlib.Path, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        if not path.is_dir():
            path = path.parent
        self._path_= path
        self.crumbs = list()
        self._configureUI_()
        self._setupCrumbs_()
        
    def _configureUI_(self):
        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.setContentsMargins(0,0,0,0)
        self.hlayout.setSpacing(0)
        self.setLayout(self.hlayout)
        
    def _setupCrumbs_(self):
        parts = self._path_.parts
        # print(f"{self.__class__.__name__}._setupCrumbs_ parts = {parts}")
        partPaths = [pathlib.Path(*parts[0:k]) for k in range(1, len(parts))] # avoid this dir dot
        nCrumbs = len(partPaths)

        # NOTE: 2023-04-28 21:52:31
        # when chaning the path it's easier to just remove all widgets and 
        # populate anew.
        if len(self.crumbs):
            self._clearCrumbs_()
                
        for k, p in enumerate(partPaths):
            # print(f"k = {k}; p = {p}")
            # isBranch = k < nCrumbs-1
            if k > 0:
                b = BreadCrumb(p, True, parentCrumb = self.crumbs[-1])#, parent=self)
            else:
                b = BreadCrumb(p, True)#, parent=self)
                
            b.sig_navigate.connect(self.slot_crumb_clicked)
            self.crumbs.append(b)
            
        b = BreadCrumb(self._path_, False, parentCrumb=self.crumbs[-1]) # last dir in path = LEAF !!!
        b.sig_navigate.connect(self.slot_crumb_clicked)
        self.crumbs.append(b)
        
        for bc in self.crumbs:
            self.hlayout.addWidget(bc)
                
        self.navspot = QtWidgets.QPushButton("", self)
        self.navspot.setFlat(True)
        self.navspot.clicked.connect(self.slot_editPath_request)
        self.hlayout.addWidget(self.navspot)
            
    def _clearCrumbs_(self):
        """
        Removes all BreadCrumbs from this BreadCrumbsNavigator/.
        Leaves the last Pushbutton bedinh (for switching to path editor)
        """
        for k, bc in enumerate(self.crumbs):
            bc.setParent(None)
            bc = None
            
        self.crumbs.clear()
        self.navspot = None

        for k in range(self.hlayout.count()):
            self.hlayout.takeAt(0)
            
    @pyqtSlot(str)
    def slot_crumb_clicked(self, path):
        self.sig_chDirString.emit(path)
        # print(f"{self.__class__.__name__}.slot_crumb_clicked {path}")
        
    @pyqtSlot()
    def slot_editPath_request(self):
        self.sig_switchToEditor.emit()
        # print("to switch to path editing mode")
        
    @property
    def path(self):
        return self._path_
    
    @path.setter
    def path(self, value:pathlib.Path):
        self._path_ = value
        self._setupCrumbs_()
        
        
class PathEditor(QtWidgets.QWidget):
    sig_chDirString = pyqtSignal(str, name = "sig_chDirString")
    sig_removeCurrentDirFromHistory = pyqtSignal(str, name = "sig_removeCurrentDirFromHistory")
    sig_clearRecentDirsList = pyqtSignal(str, name = "sig_clearRecentDirsList")
    sig_switchToNavigator = pyqtSignal(name="sig_switchToNavigator")
    
    def __init__(self, path:pathlib.Path, recentDirs:list = [], maxRecent:int=10, parent=None):
        super().__init__(parent=parent) 
        self._path_ = path
        self._recentDirs_ = recentDirs
        self._maxRecent_ = maxRecent
        self._configureUI_()
       
    def _configureUI_(self):
        self.directoryComboBox = QtWidgets.QComboBox(parent=self)
        self.directoryComboBox.setEditable(True)
        self.directoryComboBox.lineEdit().setClearButtonEnabled(True)
        self.directoryComboBox.lineEdit().undoAvailable = True
        self.directoryComboBox.lineEdit().redoAvailable = True
        
        for i in [self._path_.as_posix()] + self._recentDirs_:
            self.directoryComboBox.addItem(i)
            
        self.directoryComboBox.setCurrentIndex(0)
        
        self.directoryComboBox.activated[str].connect(self.slot_dirChange) 
       
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
        
        self.directoryComboBox.lineEdit().addAction(self.switchToBreadCrumbsAction,
                                                   QtWidgets.QLineEdit.TrailingPosition)
        
        self.directoryComboBox.lineEdit().addAction(self.clearRecentDirListAction,
                                                    QtWidgets.QLineEdit.TrailingPosition)
        
        self.directoryComboBox.lineEdit().addAction(self.removeRecentDirFromListAction,
                                                    QtWidgets.QLineEdit.TrailingPosition)
       
        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.addWidget(self.directoryComboBox)
        
    @property
    def path(self):
        return self._path_
    
    @path.setter
    def path(self, value:pathlib.Path):
        oldp = self._path_.as_posix()
        if oldp not in self.history:
            self.history.insert(0, oldp)
        self._path_ = value
        ps = self._path_.as_posix()
        
        signalBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        
        self.directoryComboBox.clear()
        
        for i in [ps] + self.history:
            self.directoryComboBox.addItem(i)
            
        self.directoryComboBox.setCurrentIndex(0)
        
    @property
    def history(self):
        return self._recentDirs_
    
    @history.setter
    def history(self, value:list=list()):
        sigBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        
        if len(value) > self._maxRecent_:
            value = value[0:self._maxRecent_]
            
        self._recentDirs_[:] = value
        if len(self._recentDirs_):
            self.directoryComboBox.clear()
            ps = self._path_.as_posix()
            for item in [ps] + self._recentDirs_:
                self.directoryComboBox.addItem(item)
                
        self.directoryComboBox.setCurrentIndex(0)
        
    @property
    def maxHistory(self):
        return self._maxRecent_
    
    @maxHistory.setter
    def maxHistory(self, value:int):
        self._maxRecent_ = value
        
        if len(self.history) > self._maxRecent_:
            self.history = self.history[0:self._maxRecent_]
        
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
    def slot_dirChange(self, value):
        hh = self.history
        if value not in hh:
            hh.insert(0, value)
            self.history = hh
            
        else:
            ndx = hh.index(value)
            del hh[ndx]
            hh.insert(0, value)
            self.history = hh

        self.sig_chDirString.emit(value)
        
class Navigator(QtWidgets.QWidget):
    def __init__(self, path:pathlib.Path, editMode:bool=False, recentDirs:list = list(), maxRecent:int=10,parent=None):
        super().__init__(parent=parent)
        self._path_ = path
        posixpathstr = self._path_.as_posix()
        self._recentDirs_ = [posixpathstr]
        if posixpathstr in recentDirs:
            rd = [i for i in recentDirs if i != posixpathstr]
        else:
            rd = recentDirs
        self._recentDirs_ = rd
        self._editMode_ = editMode==True
        self._configureUI_()
        
    def _configureUI_(self):
        self.bcnav = BreadCrumbsNavigator(self._path_, parent=self)
        self.bcnav.sig_chDirString[str].connect(self.slot_dirChange)
        self.bcnav.sig_switchToEditor.connect(self.slot_switchToEditor)
        self.editor = PathEditor(self._path_, self._recentDirs_, parent=self)
        self.editor.sig_chDirString[str].connect(self.slot_dirChange)
        self.editor.sig_switchToNavigator.connect(self.slot_switchToNavigator)
        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.setContentsMargins(0,0,0,0)
        self.hlayout.setSpacing(0)
        self.setLayout(self.hlayout)
        self.bcnav.setVisible(False)
        self.editor.setVisible(False)
        if self._editMode_:
            self.editor.setVisible(True)
            self.layout().addWidget(self.editor)
            self.bcnav.setVisible(False)
        else:
            self.bcnav.setVisible(True)
            self.layout().addWidget(self.bcnav)
            self.editor.setVisible(False)
        
    @property
    def recentDirs(self):
        return self._recentDirs_
    
    @recentDirs.setter
    def recentDirs(self, value:list):
        self._recentDirs_[:] = value
        
    @property
    def path(self):
        return self._path_
    
    @path.setter
    def path(self, value:pathlib.Path):
        self._path_ = value
        signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.bcnav, self.editor)]
        self.bcnav.path = value
        self.editor.path = value
        
    @property
    def editMode(self):
        return self._editMode_
    
    @editMode.setter
    def editMode(self, value:bool):
        self._editMode_ = value==True
        self.update()
    
    def update(self):
        if self.hlayout.count() > 0:
            self.hlayout.takeAt(0)
            
        if self._editMode_:
            self.bcnav.setVisible(False)
            self.hlayout.addWidget(self.editor)
            self.editor.setVisible(True)
            
            
        else:
            self.editor.setVisible(False)
            self.hlayout.addWidget(self.bcnav)
            self.bcnav.setVisible(True)
            
        
    @pyqtSlot(str)
    def slot_dirChange(self, value):
        print(f"{self.__class__.__name__}.slot_dirChange value: {value}" )
        
        self.path = pathlib.Path(value)
        
    @pyqtSlot()
    def slot_switchToNavigator(self):
        self.editMode = False
        
    @pyqtSlot()
    def slot_switchToEditor(self):
        self.editMode = True
