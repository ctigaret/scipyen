import typing, pathlib
from urllib.parse import urlparse, urlsplit
from enum import Enum, IntEnum
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType

from core import desktoputils

class DisplayHint(IntEnum):
    EnteredHint = 1
    DraggedHint = 2
    PopupActiveHint = 4
    

class NavigatorButtonBase(QtWidgets.QPushbutton):
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
        backgroundColor

class BreadCrumbsNavigator(QtWidgets.QWidget):
    def __init__(self, url:typing.Optional[typing.Union[str, pathlib.Path, QtCore.QUrl]]=None, 
                 parent:typing.optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0,0,0,0)
        
        if isinstance(url, QtCore.QUrl):
            if url.isLocalFile():
                self._url = url
            else:
                self._url = QtCore.QUrl() # only local files are supported
            
        elif isinstance(url, pathlib.Path):
            self._url = QtCore.QUrl(url.as_uri())
            
        elif isinstance(url, str):
            elements = urlsplit(url)
            if len(elements.scheme):
                self._url = QtCore.QUrl(url)
            else:
                p = pathlib.Path(elements.path)
                if not p.is_absolute():
                    self._url = QtCore.QUrl(pathlib.Path((os.sep,) + p.parts[1:]).as_uri())
                else:
                    self._url = QtCore.QUrl(p.as_uri())
                    
        else:
            self._url = QtCore.QUrl()
            
        self._pathBox = QtWidgets.QComboBox(self)
        self._pathBox.lineEdit().setClearButtonEnabled(True)
        
        self._removeRecentDirFromListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"), \
                                                        "Remove this path from list", \
                                                        self._pathBox.lineEdit())
        
        self._removeRecentDirFromListAction.setToolTip("Remove this path from history")
        
        self._removeRecentDirFromListAction.triggered.connect(self._slot_removeDirFromHistory)
        
        self._clearRecentDirListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("final_activity"), \
                                                        "Clear history of visited paths", \
                                                        self._pathBox.lineEdit())
        
        self._clearRecentDirListAction.setToolTip("Clear history of visited paths")
        
        self._clearRecentDirListAction.triggered.connect(self._slot_clearRecentDirList)
        
        self._pathBox.lineEdit().addAction(self._removeRecentDirFromListAction, \
                                                    QtWidgets.QLineEdit.TrailingPosition)
        
        self._pathBox.activated[str].connect(self._slot_chDirString)
        
        self._navButtons = list()
            
        self._setupComponents()
        
        
    def _setupComponents(self):
        is self._url.isEmpty():
            return
        
        urlpath = pathlib.Path(self._url.path())
        
        user_places = desktoputils.get_user_places()
        
        file_system_user_places = dict((k,v) for k,v in user_places.items() if urlsplit(v["url"]).scheme == "file" and v["app"] is None)
        
        candidate_places = [(len(urlsplit(v["url"]).path), k) for k,v in file_system_user_places.items() if str(urlpath).startswith(urlsplit(v["url"]).path)]
        
        longest_match = max(i[0] for i in candidate_places)
        
        place = [i[1] for i in candidate_places if i[0] == longest_match]
        
        if len(place):
            place = place[0]
            
        else:
            place = ""
            
        
    
