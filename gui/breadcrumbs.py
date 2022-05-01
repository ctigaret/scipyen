"""Almost direct port of breadcrumbs navigation code in kio
"""
import typing, pathlib
from urllib.parse import urlparse, urlsplit
from enum import Enum, IntEnum
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType

from core import desktoputils
import gui.pictgui as pgui
from iolib import pictio

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

class NavigatorButton(NavigatorButtonBase):
    #urlsDroppedOnNavButton = pyqtSignal(QtCore.QUrl, QtCore.QEvent, 
                                        #name="urlsDroppedOnNavButton")
                                        
    urlsDroppedOnNavButton = pyqtSignal(QtCore.QUrl, QtGui.QDropEvent, 
                                        name = "urlsDroppedOnNavButton")
    
    navigatorButtonActivated = pyqtSignal(QtCore.Qurl, QtCore.Qt.MouseButton, QtCore.Qt.KeyboardModifiers, 
                                          name = "navigatorButtonActivated")
    
    startedTextResolving = pyqtSignal(name = "startTextResolving")
    finishedTextResolving = pyqtSignal(name = "finishedTextResolving")
    
    
    def __init__(self, url:QtCore.QUrl, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self.threadpool = QtCore.QThreadPool.globalInstance()
        self._hoverArrow = False
        self._pendingTextChange = False
        self._replaceButton = False
        self._showMnemonic = False
        self._wheelSteps = 0
        self._url = url
        self._subDir = ""
        self._openSubDirsTimer = QtCore.QTimer(self)
        self._subDirsJob = None # not sure you need this here # KIO::ListJob
        
        
        self.setAcceptDrops(True)
        self.setUrl(url)
        self.setMouseTracking(True)
        
        self._openSubDirsTimer.setSingleShot(True)
        self._openSubDirsTimer.setInterval(300)
        
    def setUrl(self, url:QtCore.QUrl):
        self._url = url
        protocolBlacklist = {"nfs", "fish", "ftp", "sftp", "smb", "webdav", "mtp"}
        
        startTextResolving = self._url.isValid() and not self._url.isLocalFile() and self._url.scheme() not in protocolBlacklist
        
        if startTextResolving:
            self._pendingTextChange = True
            # TODO async code emulating KIO::StatJob
            self.startedTextResolving.emit()
            
        else:
            self.setText(self._url.fileName().replace("&", "&&"))
            
    def url(self) -> QtCore.QUrl:
        return self._url
    
    def setText(self, text:str):
        adjustedText = text
        if len(adjustedText) == 0:
            adjustedText = self._url.scheme()
            
        adjustedText = adjustedText.strip("\n")
        
        super().setText(adjustedText)
        
        self._pendingTextChange = False
            
        
    def setActiveSubDirectory(self, subDir:str):
        self._subDir = subDir
        
        self.updateGeometry()
        self.update()
        
    def activeSubDirectory(self) -> str:
        return self._subDir
    
    def sizeHint(self) -> QtCore.QSize:
        adjustedFont = QtGui.QFont(self.font())
        adjustedFont.setBold(len(self._subDir) == 0)
        width = QtGui.QFontMetrics(adjustedFont).size(QtCore.Qt.TextSingleLine, self.plainText()).width() + self.arrowWidth() + 4 * self.BorderWidth
        return QtCore.QSize(width, super().sizeHint().height())
    
    def setShowMnemonic(self, show:bool):
        if self._showMnemonic != show:
            self._showMnemonic = show is True
            update()
            
    def showMnemonic(self) -> bool:
        return self._showMnemonic
    
    def paintEvent(self, event:QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        
        adjustedFont = QtGui.QFont(self.font())
        adjustedFont.setBold(len(self._subDir) == 0)
        painter.setFont(adjustedFont)
        
        buttonWidth = self.width()
        preferredWidth = self.sizeHint().width()
        
        if preferredWidth < self.minimumWidth():
            preferredWidth = self.minimumWidth()
            
        if buttonWidth > preferredWidth:
            buttonWidth = preferredWidth
            
        buttonHeight = self.height()
        
        fgcolor = self.foregroundColor()
        self.drawHoverBackground(painter)
        
        textLeft = 0
        textWidth = buttonWidth
        
        leftToRight = self.layoutDirection() == QtCore.Qt.LeftToRight
        
        if len(self._subDir) == 0:
            arrowSize = self.arrowWidth()
            arrowX = buttonWidth - arrowSize - self.BorderWidth if leftToRight else self.BorderWidth
            arrowY = (buttonHeight - arrowSize) / 2
            
            option = QtWidgets.QStyleOption()
            option.initFrom(self)
            option.rect = QtCore.QRect(arrowX, arrowY, arrowSize, arrowSize)
            option.palette = self.palette()
            option.palette.setColor(QtGui.QPalette.Text, fgColor)
            option.palette.setColor(QtGui.QPalette.WindowText, fgColor)
            option.palette.setColor(QtGui.QPalette.ButtonText, fgColor)
            
            if self._hoverArrow:
                hoverColor = self.palette().color(QtGui.QPalette.HighlightedText)
                hoverColor.setAlpha(96)
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(hoverColor)
                
                hoverX = arrowX
                if not leftToRight:
                    hoverX -= self.BorderWidth
                    
                painter.drawRect(QtCore.QRect(hoverX, 0, arrowSize + self.BorderWidth, buttonHeight))
                
            if leftToRight:
                self.style().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowRight, option, painter)
            else:
                self.style().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowLeft, option, painter)
                textLeft += arrowSize + 2 * self.BorderWidth
                
            textWidth -= arrowSize + 2 * self.BorderWidth
            
        painter.setPen(fgColor)
        clipped = self.isTextClipped()
        textRect = QtCore.QRect(textLeft, 0, textWidth, buttonHeight)
        if clipped:
            bgColor = QtGui.QColor(fgColor)
            bgColor.setAlpha(0)
            gradient = QtGui.QLinearGradient(textRect.topleft(), textRect.topRight())
            if leftToRight:
                gradient.setColorAt(0.8, fgColor)
                gradient.setColorAt(1.0, bgColor)
            else:
                gradient.setColorAt(0.0, bgColor)
                gradient.setColorAt(0.2, fgColor)
                
            pen = QtGui.QPen()
            pen.setBrush(QtGui.QBrush(gradient))
            painter.setPen(pen)
            
        textFlags = QtCore.Qt.AlignVCenter if clipped else QtCore.Qt.AlignCenter
        
        if self._showMnemonic:
            textFlags |= QtCore.Qt.TextShowMnemonic
            painter.drawText(textRect, textFlags, self.text())
        else:
            painter.drawText(textRect, textFlags, self.plainText())
            
    #def enterEvent(self, event:QtGui.QEnterEvent)
    def enterEvent(self, event:QtCore.QEvent):
        super().enterEvent(event)
        if self.isTextClipped():
            self.setToolTip(self.plainText())
            
    def leaveEvent(self, event:QtCore.QEvent):
        super().leaveEvent(event)
        self.setToolTip("")
        
        if self._hoverArrow:
            self._hoverArrow = False
            update()
            
    def keyPressEvent(self, event:QtGui.QKeyEvent):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.navigatorButtonActivated.emit(self._url, QtCore.Qt.LeftButton,
                                               event.modifiers())
            
        elif event.key() in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Space):
            self.startSubDirsJob()
            
        else:
            super().keyPressEvent(event)
            
    def dropEvent(self, event:QtGui.QDropEvent):
        if event.mimeData().hasUrls():
            self.setDisplayHintEnabled(DisplayHint.DraggedHint, True)
            
            self.urlsDroppedOnNavButton.emit(self._url, event)
            
            self.setDisplayHintEnabled(DisplayHint.DraggedHint, False)
            self.update()
            
    def dragEnterEvent(self, event:QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            self.setDisplayHintEnabled(DisplayHint.DraggedHint, True)
            event.acceptProposedAction()
            self.update()
            
    def dragMoveEvent(self, event:QtGui.QDragMoveEvent):
        rect = event.answerRect()
        if self.isAboveArrow(rect.center().x()):
            self._hoverArrow = True
            self.update()
            
            if self._subDirsMenu is None:
                self.requestSubDirs()
            elif self._subDirsMenu.parent() is not self:
                self._subDirsMenu.close()
                self._subDirsMenu.deleteLater()
                self._subDirsMenu = None
                
                self.requestSubDirs()
            
        else:
            if self._openSubDirsTimer.isActive():
                self.cancelSubDirsRequest()
                
                
            self._subDirsMenu.deleteLater()
            self._subDirsMenu = None
            self._hoverArrow = False
            self.update()
            
    def dragLeaveEvent(self, event:QtGui.QDragLeaveEvent):
        super().dragLeaveEvent(event)
        self._hoverArrow = False
        self.setDisplayHintEnabled(DisplayHint.DraggedHint, False)
        self.update()
        
    def mousePressEvent(self, evet:QtGui.QMouseEvent):
        if self.isAboveArrow(event.x()) and event.button() == QtCore.Qt.LeftButton:
            self.startSubDirsJob()
            
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event:QtGui.QMouseEvent):
        if not self.isAboveArrow(event.x()) or event.button() != QtCore.Qt.LeftButton:
            self.navigatorButtonActivated.emit(self._url, event.button(), event.modifiers())
            self.cancelSubDirsRequest()
            
        super().mouseReleaseEvent(event)
        
    def mouseMoveEvent(self, event:QtGui.QMouseEvent):
        super().mouseMoveEvent(event)
        hoverArrow = self.isAboveArrow(event.x())
        if hoverArrow != self._hoverArrow:
            self._hoverArrow = hoverArrow
            self.update()
            
    def wheelEvent(self, event:QtGui.QWheelEvent):
        if event.angleDelta().y() != 0:
            self._wheelSteps = event.angleDelta().v() / 120
            self._replaceButton = True
            self.startSubDirsJob()
            
        super().wheelEvent(event)
        
    def requestSubDirs(self):
        if not self._openSubDirsTimer.isActive() and self._subDirsJob is None:
            self._openSubDirsTimer.start()
            
    def _listSubDirs(self, url:QtCore.QUrl, showHidden:typing.Optional[bool]=False) -> list:
        #url = upUrl(self._url) if self._replaceButton else self._url
        
        myPath = pathlib.Path(urlsplit(url.url()).path)
        
        if not showHidden:
            return sorted(list(p for p in myPath.iterdir() if p.is_dir() and not pio.is_hidden(p)))
        else:
            return sorted(list(p for p in myPath.iterdir() if p.is_dir()))
        
    @pyqtSlot
    def slot_subdirsJobFinished(self):
        job = self.sender()
        entries = getattr(job, "result", None)
        if isinstance(entries, list):
            self.addEntriesToSubDirs(job, entries)
        
    def startSubDirsJob(self):
        if self._subDirsJob is not None:
            return
        
        url = upUrl(self._url) if self._replaceButton else self._url
        
        if type(self.parent).__name__ == "Navigator" and type(self.parent()).__module__ == self.__class__.__module__:
            showHidden = self.parent()._showHidden
        
        self._subDirsJob = pgui.GuiWorker(self._listSubDirs, url, showHidden)
        
        self._subDirsJob.signal_finished.connect(self.slot_subdirsJobFinished)
        
        if self._replaceButton:
            self._subDirsJob.signal_result.connect(self.replaceButton)
        else:
            self._subDirsJob.signal_result.connect(self.openSubdirsMenu)
        
    def addEntriesToSubDirs(self, job:pgui.GuiWorker, entries:list):
        assert(job == self._subDirsJob)
        for entry in entries:
            name=entry.name
            displayName=
        
        
        
    

class Navigator(QtWidgets.QWidget):
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
            
        
    
