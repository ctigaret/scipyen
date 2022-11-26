"""Almost direct port of breadcrumbs navigation code in kio
"""
import typing, pathlib, functools
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

def upUrl(url:QtCore.QUrl) -> QtCore.QUrl:
    if not url.isValid() or url.isRelative():
        return QtCore.QUrl()
    
    u = QtCore.QUrl(url)
    
    if url.hasQuery():
        u.setQuery("")
        return u
    
    if url.hasFragment():
        u.setFragment("")
        
    u = u.adjusted(QtCore.QUrl.StripTrailingSlash)
    return u.adjusted(QtCore.QUrl.RemoveFilename)

class DisplayHint(IntEnum):
    EnteredHint = 1
    DraggedHint = 2
    PopupActiveHint = 4
    
class CoreUrlNavigator(QtCore.QObject):
    pass
    
# NOTE: 2022-05-02 15:18:54
# placeholders for use by _NavigatorPrivate; redefined below
class Navigator 
class PlacesModel # TODO consider defining it in desktoputils

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
        
class NavigatorMenu(QtWidgets.QMenu):
    urlsDropped = pyqtSignal(QtWidgets.QAction, QtGui.QDropEvent, 
                             name="urlsDropped")
    mouseButtonClicked = pyqtSignal(QtWidgets.QAction, QtCore.Qt.MouseButton,
                                    name = "mouseButtonClicked")
    
    def __init__(self, parent:QtWidgets.QWidget):
        # NOTE: 2022-05-02 11:53:13
        # this is a QPoint; the static pos() method gets the position of the 
        # mouse cursor on screen, at the time of initialization
        # see NOTE: 2022-05-02 12:02:24 for a nice trick use
        self._initialMousePosition = QtGui.QCursor.pos() 
        self._mouseMoved = False
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
    
    def dragEnterEvent(self, event:QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event:QtGui.QDragMoveEvent):
        # NOTE: 2022-05-02 11:55:15
        # create a mouse move event on left mouse button, than we then handle
        # with self.mouseMoveEvent
        mouseEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, event.pos(),
                                       QtCore.Qt.LeftButton, event.mouseButtons(),
                                       event.keyboardModifiers())
        
        self.mouseMoveEvent(mouseEvent)
    
    def dropEvent(self, event:QtGui.QDropEvent):
        # NOTE: 2022-05-02 11:58:07
        # get action at event position; if found then emit urlsDropped with it
        action = self.actionAt(event.pos())
        if action is not None:
            self.urlsDropped.emit(action, event)
    
    def mouseMoveEvent(self, event:QtGui.QMouseEvent):
        # NOTE: 2022-05-02 12:04:57
        # check if mouse has moved
        if not self._mouseMoved:
            # NOTE: 2022-05-02 12:02:24
            # nice trick !!!
            moveDistance = self.mapToGlobal(event.pos()) - self._initialMousePosition
            self._mouseMoved = moveDistance.manhattanLength() >= QtWidgets.QApplication.startDragDistance()
            
        if self._mouseMoved:
            # if mouse has moved, handle it with the super's handler
            super().mouseMoveEvent(event) # avoid infinite recursion, call super's method
    
    def mouseReleaseEvent(self, event:QtGui.QMouseEvent):
        btn = event.button()
        if self._mouseMoved or btn != QtCore.Qt.LeftButton:
            action = self.actionAt(event.pos())
            if action is not None:
                self.mouseButtonClicked.emit(action, btn)
                self.setActiveAction(None) # would this work?!?
                
            super().mouseReleaseEvent(event)
            
        self._mouseMoved = True
    
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
        self._subDir = "" # active subdirectory
        self._subDirs = list() # of tuples (name, display name)
        self._subDirsJob = None 
        
        self._openSubDirsTimer = QtCore.QTimer(self, timeout=self.startSubDirsJob)
        self._openSubDirsTimer.setSingleShot(True)
        self._openSubDirsTimer.setInterval(300)
        
        
        # NOTE: 2022-05-02 11:09:04 
        # we use a GuiWorker instead of KIO::ListJob
        
        
        self.setAcceptDrops(True)
        self.setUrl(url)
        self.setMouseTracking(True)
        
        
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
        
    @pyqtSlot()
    def requestSubDirs(self):
        if not self._openSubDirsTimer.isActive() and self._subDirsJob is None:
            self._openSubDirsTimer.start()
            
    def _listSubDirs(self, url:QtCore.QUrl, showHidden:typing.Optional[bool]=False) -> typing.List[pathlib.Path]:
        
        # NOTE: 2022-05-02 11:33:39
        # KIO uses struct FolderNameNaturalLessThan (see kurlnavigatorbutton.cpp)
        # to sort folder names using a custom QCollator.
        # We don't use this here (KISS!)
        #url = upUrl(self._url) if self._replaceButton else self._url
        
        myPath = pathlib.Path(urlsplit(url.url()).path)
        
        if not showHidden:
            return sorted(list(p for p in myPath.iterdir() if p.is_dir() and not pio.is_hidden(p)))
        else:
            return sorted(list(p for p in myPath.iterdir() if p.is_dir()))
        
    @pyqtSlot(object)
    def slotSubDirsJobFinished(self, result:typing.Sequence[pathlib.Path]):
        job = self.sender()
        #entries = getattr(job, "result", None)
        if isinstance(result, list) and all(isinstance(p, pathlib.Path) for p in result):
            self.addEntriesToSubDirs(job, result)
        
    @pyqtSlot
    def startSubDirsJob(self):
        """Connected to self._openSubDirsTimer timeout signal
        """
        if self._subDirsJob is not None:
            return
        
        url = upUrl(self._url) if self._replaceButton else self._url
        
        if type(self.parent()).__name__ == "Navigator" and type(self.parent()).__module__ == self.__class__.__module__:
            showHidden = self.parent()._showHidden
        
        self._subDirsJob = pgui.GuiWorker(self._listSubDirs, url, showHidden)
        self._subDirs.clear()
        
        # NOTE: 2022-05-02 11:18:07
        # GuiWorker signal_Result is connected to self.slotSubDirsJobFinished,
        # which then calls self.addEntriesToSubDirs
        #self._subDirsJob.signal_Finished.connect(self.slotSubDirsJobFinished)
        self._subDirsJob.signal_Result.connect(self.slotSubDirsJobFinished)
        
        if self._replaceButton:
            self._subDirsJob.signal_Finished.connect(self.replaceButton)
        else:
            self._subDirsJob.signal_Finished.connect(self.openSubdirsMenu)
            
        self.threadpool.start(self._subDirsJob)
            
    @pyqtSlot
    def addEntriesToSubDirs(self, job:pgui.GuiWorker, entries:list):
        if not (type(self.parent()).__name__ == "Navigator" and type(self.parent()).__module__ == self.__class__.__module__):
            return
        
        assert(job == self._subDirsJob)
        for entry in entries:
            name=entry.name
            displayName=self.parent()._getDisplayName(entry)
            
            if name not in (".", ".."):
                self._subDirs.append(name, displayName)
        
    @pyqtSlot
    def slotUrlsDropped(self, action:QtWidgets.QAction, event:QtGui.QDropEvent):
        ndx = action.data().toInt()
        url = QtCore.QUrl(self._url)
        url.setPath(pio.concatPaths(url.path(), self._subDirs[ndx][0])) # the "name"
        self.urlsDroppedOnNavButton.emit(url, event)
        
    @pyqtSlot
    def slotMenuActionClicked(self, action: QtWidgets.QAction, button:QtCore.Qt.MouseButton):
        ndx = action.data().toInt()
        url = QtCore.QUrl(self._url)
        url.setPath(pio.concatPaths(url.path(), self._subDirs[ndx][0])) # the "name"
        self.navigatorButtonActivated.emit(url, button, QtCore.Qt.NoModifier)
        
    def statFinished(self, job):
        # TODO: 2022-05-02 11:36:42
        pass # not sure we can translate this here
    
    @pyqtSlot()
    def openSubDirsMenu(self, job):
        assert(job is self._subDirsJob)
        self._subDirsJob = None # bye bye job!
        
        if len(self._subDirs) == 0:
            return
        
        parent = self.parent()
        
        if not (type(parent).__name__ == "Navigator" and type(parent).__module__ == self.__class__.__module__):
            return
        
        # NOTE: 2022-05-02 11:41:47 self.m_subDirs should already be sorted,
        # see NOTE: 2022-05-02 11:33:39
        self.setDisplayHintEnabled(DisplayHint.PopupActiveHint, True)
        self.update()
        
        if isinstance(self._subDirsMenu, NavigatorMenu):
            self._subDirsMenu.close()
            self._subDirsMenu.deleteLater()
            self._subDirsMenu = None
            
        self._subDirsMenu = NavigatorMenu(self)
        self.initMenu(self._subDirsMenu, 0)
        
        
        leftToRight = self.layoutDirection() == QtCore.Qt.LeftToRight
        popupX = self.width() - self.arrowWidth() - self.BorderWidth if leftToRight else 0
        popupPos = self.parentWidget().mapToGlobal(self.geometry().bottomLeft() + QtCore.QPoint(popupX, 0))
        
        self._subDirsMenu.exec(popupPos)
        
        self._subDirs.clear()
        
        # NOTE: 2022-05-02 12:15:31 WARNING
        # lookout for the possibility for self to be deleted in the menu's nested 
        # event loop
        # see kurlnavigatorbutton.cpp
        
        self._subDirs.clear()
        self._subDirsMenu = None
        
        self.setDisplayHintEnabled(DisplayHint.PopupActiveHint, False)
        
    @pyqtSlot
    def replaceButton(self):
        job = self.sender() # the result should have been sent to self.slotSubDirsJobFinished
        assert(job is self._subDirsJob)
        self._subDirsJob = None # bye bye subdirs job
        self._replaceButton = False
        
        if len(self._subDirs) == 0:
            return
        
        # NOTE: self._subDirs should be already sorted
        # see NOTE: 2022-05-02 11:33:39
        
        currentDir = self._url.fileName()
        currentIndex = 0
        subDirsCount = len(self._subDirs)
        while currentIndex < subDirsCount:
            if self._subDirs[currentIndex][0] == currentDir:
                break
            
            currentIndex += 1
            
        targetIndex = currentIndex - self._wheelSteps
        if targetIndex < 0:
            targetIndex = 0
            
        elif targetIndex >= subDirsCount:
            targetIndex = subDirsCount - 1
            
        url = upUrl(self._url)
        
        url.setPath(pio.concatPaths(url.path(), self._subDirs[targetIndex][0]))
        self.navigatorButtonActivated.emit(url, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        
        self._subDirs.clear()
        
    @pyqtSlot
    def cancelSubDirsRequest(self):
        self._openSubDirsTimer.stop()
        if self._subDirsJob is not None:
            # self._subDirsjob.kill() # NOTE: 2022-05-02 13:01:11 CANNOT KILL!
            self._subDirsJob = None

    def plainText(self) -> str:
        return self.text().replace("&","")
    
    def arrowWidth(self) -> int:
        width = 0
        if len(self._subDir) == 0:
            width = self.height()/2
            if width < 4:
                width = 4
                
        return width
    
    def isAboveArrow(self, x:int) -> bool:
        leftToRight = self.layoutDirection() == QtCore.Qt.LeftToRight
        
        return x >= (self.width() - self.arrowWidth()) if leftToRight else x < self.arrowWidth()
    
    def isTextClipped(self) -> bool:
        availableWidth = self.width() - 2 * self.BorderWidth
        
        if len(self._subDir) == 0:
            availableWidth -= (self.arrowWidth() - self.BorderWidth)
            
        adjustedFont = QtGui.QFont(self.font())
        
        adjustedFont.setBold(len(self._subDir) == 0)
        
        return QtGui.QFontMetrics(adjustedFont).size(QtCore.Qt.TextSingleLine, self.plainText()).width() >= availableWidth
 
    def updateMinimumWidth(self):
        oldMinWidth = self.minimumWidth()
        minWidth = self.sizeHint().width()
        if minWidth < 40:
            minWidth = 40
        elif minWidth > 150:
            minWidth = 150
            
        if oldMinWidth != minWidth:
            self.setMinimumWidth(minWidth)
            
    def initMenu(self, menu:NavigatorMenu, startIndex:int):
        menu.mouseButtonClicked.connect(self.slotMenuActionClicked)
        menu.urlsDropped.connect(self.slotUrlsDropped)
        menu.triggered.connect(functools.partialmethod(self.slotMenuActionClicked, button=QtCore.Qt.LeftButton))
        
        menu.setLayoutDirection(QtCore.Qt.LeftToRight)

        maxIndex = startIndex + 30 # show at most 30 items
        lastIndex = min((len(self._subDirs)-1, maxIndex))
        
        for i in range(startIndex, lastIndex+1):
            subDirName = self._subDirs[i][0]
            subDirDisplayName = self._subDirs[i][1]
            text = guiutils.csqueeze(subDirDisplayName, 60)
            text.replace("&", "&&")
            action = QtWidgets.QAction(text, self)
            if self._subDir == subDirName:
                font = QtGui.QFont(action.font())
                font.setBold(True)
                action.setFont(font)
                
            action.setData(i)
            menu.addAction(action)
            
        if len(self._subDirs) > maxIndex:
            # move extra items to submenu
            menu.addSeparator()
            subDirsMenu = NavigatorMenu(menu)
            subDirsMenu.setTitle("More")
            self.initMenu(subDirsMenu, maxIndex)
            menu.addSubMenu(subDirsMenu)
        
class UrlComboBox(QtWidgets.QComboBox):
    pass

class NavigatorData:
    rootUrl = QtCore.QUrl()
    pos = QtCore.QPoint()
    state = bytearray()
    
    
class _NavigatorPrivate(QCore.QObject):
    def __init__(self, url:QtCore.QUrl, qq:Navigator, placesModel:PlacesModel=None):
        self.q = qq
        self._layout = QtWidgets.QHBoxLayout(self.q)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0,0,0,0)
        
        # TODO: connect KCoreUrlNavigator signals to q's slots
        
        self._navButtons = list() # of NavigatorButtons
        self._placesSelector = None # a KUrlNavigatorPlacesSelector -> not needed?
        self._pathBox = None # UrlComboBox
        self._protocols = None # KUrlNavigatorProtocolCombo -> no needed?
        self._dropDownButton = None # KUrlNavigatorDropDownbutton - needed - TODO?
        self._toggleEditableMode = None # NavigatorButtonBase
        self._dropWidget = None # QWidget
        self._customProtocols = list() # of str; not really needed in Scipyen?
        self._homeUrl = QtCore.QUrl()
        
        self._editable = False
        self._active = True
        self._showPlacesSelector = isinstance(placesModel, PlacesModel)
        self._showFullPath = False
        
        # originally a struct
        self._subfolderOptions = Bunch({"showHidden": False, "sortHiddenLast": False})
        
        pass
    
    def __del__(self):
        self._dropDownButton.removeEventFilter(self.q)
        self._pathBox.removeEventFilter(self.q)
        self._toggleEditableMode.removeEventFilter(self.q)
        
        for button in self._navButtons:
            button.removeEventFilter(self.q)
            
    def applyUncommittedUrl(self):
        # NOTE: 2022-05-02 21:55:31
        # unlike KIO code, we only support local protocols urls (i.e. file scheme):
        # no remote:/, trash:/, or anything other than local:/
        #
        # TODO: 2022-05-02 22:51:17
        # check in self.q if QUrl.fromUserInput is a valid local url!!!
        def __applyUrl__(url, pathbox, q):
            if url.scheme() != "file":
                return
            
            if not url.isEmpty() and url.path().isEmpty():
                url.setPath("/")
                
            urlStr = url.toString()
            # TODO/FIXME: 2022-05-02 22:04:39
            # use logic in ScipyenWindow or just move it here instead of below
            urls = pathbox.urls() # a list
            
            if urlStr in urls:
                urls.remove(urlStr)
                
            urls.insert(0, urlStr)
            pathbox.setUrls(urls, UrlComboBox.RemoveBottom)

            q.setLocationUrl(url)
            pathbox.setUrl(self.q.locationUrl())
        
        text = self._pathBox.currentText().strip()
        q_url = self.q.locationUrl()
        path = q_url.path()
        if not path.endswith("/"):
            path += "/"
            
            
        q_url.setPath(path + text)
        
        if pathlib.Path(q_url.path()).is_dir():
            __applyUrl__(q_url, self._pathBox, self.q)
        else:
            __applyUrl(QtCore.QUrl.fromUserInput(text))
        
        
        
        #__applyUrl__(url, self._pathBox, self.q)
        
        
    @pyqtSlot
    def slotReturnPressed(self):
        pass
    
    @pyqtSlot
    def slotProtocolChanged(self, s:str):
        pass
    
    def openPathSelectorMenu(self):
        pass
    
    def appendWidget(self, widget:QtWidgets.QWidget, stretch:int = 0):
        self._layout.insertWidget(self._layout.count()-1, widget, stretch)
    
    @pyqtSlot
    def slotToggleEditableButtonPressed(self):
        pass
    
    def switchView(self):
        pass
    
    def dropUrls(self, destination:QtCore.QUrl, event:QtGui.QDropEvent,
                 dropButton:NavigatorButton)
    
    @pyqtSlot
    def slotNavigatorButtonClicked(self, utl:QtCore.QUrl, button:QtCore.Qt.MouseButton,
                                   modifiers:QtCore.Qt.KeyboardModifiers):
        pass
    
    def openContextMenu(self, p:QtCore.QPoint):
        pass
    
    @pyqtSlot
    def slotPathBoxChanged(self, text:str):
        pass
    
    def updateContent(self):
        pass
    
    def updateButtons(self, startIndex:int):
        pass
    
    def updateButtonVisibility(self):
        pass
    
    def firstButtonText(self) -> str:
        pass
    
    def buttonUrl(self, index:int) -> QtCore.QUrl:
        pass
    
    def switchToBreadcrumbMode(self):
        pass
    
    def deleteButtons(self):
        pass
    
    def retrievePlaceUrl(self) -> QtCore.QUrl:
        pass
    
    def removeTrailingSlash(self, url:str):
        pass
    
    
    
    
    

class Navigator(QtWidgets.QWidget):
    activated = pyqtSignal(name="activated")
    urlChanged = pyqtSignal(QtCore.QUrl, name="urlChanged")
    urlAboutToBeChanged = pyqtSignal(QtCore.QUrl, name="urlAboutToBeChanged")
    editableStateChanged = pyqtslot(bool, name="editableStateChanged")
    historyChanged = pyqtSignal(name="historyChanged")
    urlsDropped = pyqtSignal(QtCore.QUrl, QtGui.QDropEvent, name="urlsDropped")
    returnPressed = pyqtSignal(name="returnPressed")
    urlSelectionRequested = pyqtSignal(QtCore.QUrl, name="urlSelectionRequested")
    
    # not needed in Scipyen!
    tabRequested = pyqtSignal(QtCore.QUrl, name="tabRequested")
    activeTabRequested = pyqtSignal(QtCore.QUrl, name="activeTabRequested")
    newWindowRequested = pyqtSignal(QtCore.QUrl, name="newWindowRequested")
    
    # NOTE: 2022-05-02 14:05:54
    # no file places model yet!
    
    def __init__(self, url:QtCore.QUrl, parent:typing.Optional[QtWidgets.QWidget] = None):
        # NOTE: 2022-05-02 14:47:02
        # doing away with KCoreUrlNavigator
        
        
        pass
    
    #def __init__(self, url:typing.Optional[typing.Union[str, pathlib.Path, QtCore.QUrl]]=None, 
                 #parent:typing.optional[QtWidgets.QWidget]=None):
        #super().__init__(parent=parent)
        #self._layout = QtWidgets.QHBoxLayout(self)
        #self._layout.setSpacing(0)
        #self._layout.setContentsMargins(0,0,0,0)
        
        #if isinstance(url, QtCore.QUrl):
            #if url.isLocalFile():
                #self._url = url
            #else:
                #self._url = QtCore.QUrl() # only local files are supported
            
        #elif isinstance(url, pathlib.Path):
            #self._url = QtCore.QUrl(url.as_uri())
            
        #elif isinstance(url, str):
            #elements = urlsplit(url)
            #if len(elements.scheme):
                #self._url = QtCore.QUrl(url)
            #else:
                #p = pathlib.Path(elements.path)
                #if not p.is_absolute():
                    #self._url = QtCore.QUrl(pathlib.Path((os.sep,) + p.parts[1:]).as_uri())
                #else:
                    #self._url = QtCore.QUrl(p.as_uri())
                    
        #else:
            #self._url = QtCore.QUrl()
            
        #self._pathBox = QtWidgets.QComboBox(self)
        #self._pathBox.lineEdit().setClearButtonEnabled(True)
        
        #self._removeRecentDirFromListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"), \
                                                        #"Remove this path from list", \
                                                        #self._pathBox.lineEdit())
        
        #self._removeRecentDirFromListAction.setToolTip("Remove this path from history")
        
        #self._removeRecentDirFromListAction.triggered.connect(self._slot_removeDirFromHistory)
        
        #self._clearRecentDirListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("final_activity"), \
                                                        #"Clear history of visited paths", \
                                                        #self._pathBox.lineEdit())
        
        #self._clearRecentDirListAction.setToolTip("Clear history of visited paths")
        
        #self._clearRecentDirListAction.triggered.connect(self._slot_clearRecentDirList)
        
        #self._pathBox.lineEdit().addAction(self._removeRecentDirFromListAction, \
                                                    #QtWidgets.QLineEdit.TrailingPosition)
        
        #self._pathBox.activated[str].connect(self._slot_chDirString)
        
        #self._navButtons = list()
            
        #self._setupComponents()
        
    def _getDisplayName(self, p:pathlib.Path) -> str:
        user_places = desktoputils.get_user_places()
        file_system_places = dict((k,v) for k,v in user_places.items() if urlsplit(v["url"]).scheme == "file" and v["app"] is None)
        
        place_found = [k for k,v in file_system_places.items() if p == urlsplit(v["url"]).path]
        
        if len(place_found):
            return place_found[0]
        
        return str(p)

    def locationUrl(self, historyIndex:int = -1) -> QtCore.QUrl:
        pass
    
    def saveLocationState(self, state:bytearray):  # uses QByteArray
        pass
    
    def locationState(self, historyIndex:int = -1) -> bytearray: # uses QByteArray
        pass
    
    def goBack(self) -> bool:
        pass
    
    def goForward(self) -> bool:
        pass
    
    def goUp(self) -> bool:
        pass
    
    def goHome(self) -> bool:
        pass
    
    def setHomeUrl(self, url:QtCore.QUrl):
        pass
    
    def homeUrl(self) -> QtCore.QUrl:
        pass
    
    def setUrlEditable(self, editable:bool):
        pass
    
    def isUrlEditable(self) -> bool:
        pass
    
    def setShowFullPath(self, show:bool):
        pass
    
    def showFullPath(self) -> bool:
        pass
    
    def setActive(self, active:bool):
        pass
    
    def isActive(self) -> bool:
        pass
    
    def setPlacesSelectorVisible(self, visible:bool):
        pass
    
    def isPlacesSelectorVisible(self) -> bool:
        pass
    
    def uncommittedUrl(self) -> QtCore.QUrl:
        pass
    
    def historySize(self) -> int:
        pass
    
    def historyIndex(self) -> int:
        pass
    
    def editor(self) -> UrlComboBox:
        pass
    
    def setCustomProtocols(self, protocols:typing.Sequence[str]):
        pass
    
    def customProtocols(self) -> typing.List[str]:
        pass
    
    def dropWidget(self) -> QtWidgets.QEidget:
        pass
    
    def setShowHiddenFolders(self, showHiddenFolders:bool):
        pass
    
    def showHiddenFolders(self) -> bool:
        pass
    
    def setSortHiddenFoldersLast(self, setSortHiddenFoldersLast:bool):
        pass
    
    def sortHiddenFoldersLast(self) -> bool:
        pass
    
    @pyqtSlot(QtCore.QUrl)
    def setLocationUrl(self, url:QtCore.QUrl):
        pass
    
    @pyqtSlot
    def requestActivation(self):
        pass
    
    @pyqtSlot
    def setfocus(self):
        pass
    
    def keyPressEvent(self, event:QtGui.QKeyEvent):
        pass
    
    def keyReleaseEvent(self, event:QtGui.QKeyEvent):
        pass
    
    def mouseReleaseEvent(self, event:QtGui.QMouseEvent):
        pass
    
    def mousePressEvent(self, event:QtGui.QMouseEvent):
        pass
    
    def resizeEvent(self, event:QtGui.QResizeEvent):
        pass
    
    def wheelEvent(self, QtGui.QWheelEvent):
        pass
    
    def eventFilter(self, watched: QtCore.QObject, event:QtCore.QEvent):
        pass
        
    #def _setupComponents(self):
        #is self._url.isEmpty():
            #return
        
        #urlpath = pathlib.Path(self._url.path())
        
        #user_places = desktoputils.get_user_places()
        
        #file_system_places = dict((k,v) for k,v in user_places.items() if urlsplit(v["url"]).scheme == "file" and v["app"] is None)
        
        #candidate_places = [(len(urlsplit(v["url"]).path), k) for k,v in file_system_places.items() if str(urlpath).startswith(urlsplit(v["url"]).path)]
        
        #longest_match = max(i[0] for i in candidate_places)
        
        #place = [i[1] for i in candidate_places if i[0] == longest_match]
        
        #if len(place):
            #place = place[0]
            
        #else:
            #place = ""
            
        
    
