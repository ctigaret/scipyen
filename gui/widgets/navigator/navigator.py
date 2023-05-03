import typing, pathlib, functools, os
from urllib.parse import urlparse, urlsplit
from enum import Enum, IntEnum
import sip # for sip.isdeleted() - not used yet, but beware
from traitlets.utils.bunch import Bunch
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType

from core import desktoputils as dutils
from core.desktoputils import PlacesModel
from core.prog import safeWrapper
import gui.pictgui as pgui
from gui import guiutils
from iolib import pictio

# Root > dir > subdir

class DisplayHint(IntEnum):
    EnteredHint = 1
    DraggedHint = 2
    PopupActiveHint = 4
    
class Navigator:
    pass # fwd decl
    
class NavigatorButtonBase(QtWidgets.QPushButton):
    """Common ancestor for breadcrumbs buttons
    """
    BorderWidth = 2
    
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent)
        self._isLeaf_=False
        self._isDown_ = False
        self._active_=True
        self._displayHint_ = 0
        
        self.setFocusPolicy(QtCore.Qt.TabFocus)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, 
                           QtWidgets.QSizePolicy.Fixed)
        if isinstance(parent, QtWidgets.QWidget):
            self.setMinimumHeight(parent.minimumHeight())
        
        self.setAttribute(QtCore.Qt.WA_LayoutUsesWidgetRect)
        
        if hasattr(parent, "requestActivation"):
            self._pressed_.connect(parent.requestActivation)
            
    def setActive(self, active:bool):
        self.active = value == True
            
    def isActive(self):
        return self._active_
    
    @property
    def active(self):
        return self._active_
    
    @active.setter
    def active(self, value:bool):
        if self._active_ != value:
            self._active_ = value is True
            self.update()
    
    def setDisplayHintEnabled(self, hint:typing.Union[DisplayHint, int], enable:bool):
        if enable:
            self._displayHint_ = self._displayHint_ | hint
        else:
            self._displayHint_ = self._displayHint_ & ~hint
            
        self.update()

    def isDisplayHintEnabled(self, hint:typing.Union[DisplayHint, int]):
        return (self._displayHint_ & hint) > 0
    
    def focusInEvent(self, event:QtGui.QFocusEvent):
        self.setDisplayHintEnabled(DisplayHint.EnteredHint, True)
        super().focusInEvent(event)
        
    def focusOutEvent(self, event:QtGui.QFocusEvent):
        self.setDisplayHintEnabled(DisplayHint.EnteredHint, False)
        super().focusOutEvent(event)
        
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
        
        if not self._active_ and isHighlighted:
            backgroundColor.setAlpha(128)
            
        if backgroundColor != QtCore.Qt.transparent:
            option = QtWidgets.QStyleOptionViewItem()
            option.initFrom(self)
            option.state = QtWidgets.QStyle.State_Enabled | QtWidgets.QStyle.State_MouseOver
            option.viewItemPosition = QtWidgets.QStyleOptionViewItem.OnlyOne
            self.style().drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, self)
            
    def foregroundColor(self):
        isHighlighted = self.isDisplayHintEnabled(DisplayHint.EnteredHint) or self.isDisplayHintEnabled(DisplayHint.DraggedHint) or self.isDisplayHintEnabled(DisplayHint.PopupActiveHint)
        
        foregroundColor = self.palette().color(QtGui.QPalette.Foreground)
        
        alpha = 255 if self._active_ else 128
        
        if not self._active_ and not isHighlighted:
            alpha -= alpha/4
            
        foregroundColor.setAlpha(alpha)
        
        return foregroundColor
    
    def activate(self):
        self.active = True
        #self.setActive(true)

class NavigatorToggleButton(NavigatorButtonBase):
    _iconSize_ = 16
    def __init__(self, parent:Navigator=None):
        super().__init__(parent=parent)
        self._pixmap_ = None
        self.setCheckable(True)
        self.toggled.connect(self.updateToolTip)
        self.clicked.connect(self.updateCursor)
        
        self.updateToolTip()
        
    def sizeHint(self):
        size = super().sizeHint()
        size.setWidth(max(self._iconSize_, self.iconSize().width()) + 4)
        
        return size
    
    def enterEvent(self, evt:QtGui.QEnterEvent):
        super().enterEvent(evt)
        self.updateCursor()
    
    def leaveEvent(self, evt:QtCore.QEvent):
        super().leaveEvent(evt)
        self.setCursor(QtCore.Qt.ArrowCursor)
    
    def paintEvent(self, evt:QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setClipRect(evt.rect())
        buttonWidth = int(self.width())
        buttonHeight = int(self.height())
        
        if self.isChecked():
            self.drawHoverBackground(painter)
            
            if self._pixmap_ is None:
                self._pixmap_ = QtGui.QIcon.fromTheme("dialog-ok").pixmap(QtCore.QSize(self._iconSize_, self._iconSize_)).expandedTo(self.iconSize())
                
            self.style().drawItemPixmap(painter, self.rect(), QtCore.Qt.AlignCenter, self._pixmap_)
            
        elif self.isDisplayHintEnabled(DisplayHint.EnteredHint):
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(self.palette().color(self.foregroundRole()))
            
            verticalGap = 4
            caretWidth = 2
            x = 0 if self.layoutDirection() == QtCore.Qt.LeftToRight else buttonWidth - caretWidth
            
            painter.drawRect(x, verticalGap. caretWidth, buttonHeight - 2 * verticalGap)
    
    @pyqtSlot()
    def updateToolTip(self):
        if self.isChecked():
            self.setToolTip("Click for Navigation")
        else:
            self.setToolTip("Click to Edit Location")
    
    @pyqtSlot()
    def updateCursor(self):
        if self.isChecked():
            self.setCursor(QtCore.Qt.ArrowCursor)
        else:
            self.setCursor(QtCore.Qt.IBeamCursor)

class NavigatorButton(NavigatorButtonBase):
    sig_navigate = pyqtSignal(str, name="sig_navigate")
    
    # def __init__(self, text:str, leaf:bool=False, parent=None):
    # def __init__(self, path:pathlib.Path, isBranch:bool=False, parentCrumb=None, parent=None):
    def __init__(self, path:pathlib.Path, isBranch:bool=False, parent=None):
        super().__init__(parent=parent)
        self._isLeaf_ = not isBranch
        self._hoverArrow_ = False
        self._pressed_ = False
        path = path.resolve()
        if not path.is_dir():
            path = path.parent
            
        self.path = path
        self.name = self.path.name
        if len(self.name) == 0:
            self.name = self.path.parts[0]
    
        self.setText(self.name)
        
        # self.parentCrumb = parentCrumb
        
        self.subDirsMenu = None
        
        # NOTE: 2023-04-29 15:57:58
        # defines self.fileSystemModel, self.rootIndex
        self._configureUI_()

        # self.frameStyleOptions = QtWidgets.QStyleOptionFrame()
        # self.frameStyleOptions.initFrom(self)
        # self.frameStyleOptions.
        
    def _configureUI_(self):
        self.fileSystemModel = QtWidgets.QFileSystemModel(parent=self)
        self.fileSystemModel.setReadOnly(True)
        self.fileSystemModel.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.CaseSensitive | QtCore.QDir.NoDotAndDotDot)
        self.fileSystemModel.setRootPath(self.path.as_posix())
        self.rootIndex = self.fileSystemModel.index(self.fileSystemModel.rootPath())
        # self.clicked.connect(self.dirButtonClicked)
        
    def setText(self, text):
        super().setText(text)
        self.updateMinimumWidth()
        
    def plainText(self):
        source = self.text()
        sourceLength = len(source)
        
        dest = list()
        
        for c in source:
            if c == '&':
                continue
            
            dest.append(c)
            
        return "".join(dest)
        
    def arrowWidth(self):
        width = 0
        if not self.isLeaf:
            width = self.height()/2
            if width < 4:
                width = 4
        
        return width
    
    def isAboveArrow(self, x:int):
        leftToRight = self.layoutDirection() == QtCore.Qt.LeftToRight
        if x >= self.width() - self.arrowWidth():
            return leftToRight
        else:
            return x < self.arrowWidth()
        
    def updateMinimumWidth(self):
        oldMinWidth = self.minimumWidth()
        minWidth = self.sizeHint().width()
        
        if minWidth < 40:
            minWidth = 40
            
        elif minWidth > 150:
            minWidth = 150
            
        if oldMinWidth != minWidth:
            self.setMinimumWidth(minWidth)
            
    def paintEvent(self, evt:QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        
        adjustedFont = QtGui.QFont(self.font())
        adjustedFont.setBold(self.isLeaf)
        painter.setFont(adjustedFont)
        
        buttonWidth = self.width()
        preferredWidth = self.sizeHint().width()
        
        if preferredWidth < self.minimumWidth():
            preferredWidth = self.minimumWidth()
            
        if buttonWidth > preferredWidth:
            buttonWidth = preferredWidth
            
        buttonHeight = self.height()
        
        fgColor = self.foregroundColor()
        
        self.drawHoverBackground(painter)
        
        textLeft = 0
        textWidth = buttonWidth
        
        leftToRight = self.layoutDirection() == QtCore.Qt.LeftToRight
        
        if not self.isLeaf:
            arrowSize = self.arrowWidth()
            arrowX = int((buttonWidth - arrowSize) - self.BorderWidth) if leftToRight else int(self.BorderWidth)
            arrowY = int((buttonHeight - arrowSize) / 2)
            
            option = QtWidgets.QStyleOption()
            option.initFrom(self)
            option.rect = QtCore.QRect(int(arrowX), int(arrowY), int(arrowSize), int(arrowSize))
            option.palette = self.palette()
            option.palette.setColor(QtGui.QPalette.Text, fgColor)
            option.palette.setColor(QtGui.QPalette.WindowText, fgColor)
            option.palette.setColor(QtGui.QPalette.ButtonText, fgColor)
            
            if self._hoverArrow_:
                hoverColor = self.palette().color(QtGui.QPalette.HighlightedText)
                hoverColor.setAlpha(96)
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(hoverColor)
                
                hoverX = arrowX
                
                if not leftToRight:
                    hoverX -= self.BorderWidth
                    
                painter.drawRect(QtCore.QRect(hoverX, 0, arrowSize + self.BorderWidth, buttonHeight))
            
            arrow = QtWidgets.QStyle.PE_IndicatorArrowDown if self._pressed_ else QtWidgets.QStyle.PE_IndicatorArrowRight if leftToRight else QtWidgets.QStyle.PE_IndicatorArrowLeft

            self.style().drawPrimitive(arrow, option, painter, self)
        
        painter.setPen(fgColor)
        
        clipped = self.isTextClipped()
        textRect = QtCore.QRect(textLeft, 0, textWidth, buttonHeight)
        
        if clipped:
            bgColor = fgColor
            bgColor.setAlpha(0)
            gradient = QtGui.QLinearGradient(textRect.topLeft(), textRect.topRight())
            if leftToRight:
                gradient.setColorAt(0.8, fgColor)
                gradient.setColorAt(1.0, bgColor)
            else:
                gradient.setColorAt(0.8, bgColor)
                gradient.setColorAt(0.2, fgColor)
                
            pen = QtGui.QPen()
            pen.setBrush(QtGui.QBrush(gradient))
            painter.setPen(pen)
            
        textFlags = QtCore.Qt.AlignVCenter if clipped else QtCore.Qt.AlignCenter
        painter.drawText(textRect, textFlags, self.text())
        
    def isTextClipped(self):
        availableWidth = self.width() - 2*self.BorderWidth
        adjustedFont = self.font()
        adjustedFont.setBold(self.isLeaf)
        return QtGui.QFontMetrics(adjustedFont).size(QtCore.Qt.TextSingleLine, self.text()).width() >= availableWidth
        
    def mouseReleaseEvent(self, evt:QtGui.QMouseEvent):
        if self.isAboveArrow(round(evt.pos().x())) or evt.button() != QtCore.Qt.LeftButton:
            self.subDirMenuRequested(evt)
        else:
            self.sig_navigate.emit(self.path.as_posix())
            
        super().mouseReleaseEvent(evt)
        
    def mousePressEvent(self, evt:QtGui.QMouseEvent):
        super().mousePressEvent(evt)
        if self.isAboveArrow(round(evt.pos().x())):
            self._pressed_ = True
            self.update()
        
    def mouseMoveEvent(self, evt:QtGui.QMouseEvent):
        super().mouseMoveEvent(evt)
        hoverArrow = self.isAboveArrow(round(evt.pos().x()))
        if hoverArrow != self._hoverArrow_:
            self._hoverArrow_ = hoverArrow
            self.update()
        
    @safeWrapper
    def subDirMenuRequested(self, evt:QtGui.QMouseEvent):
        if self.subDirsMenu is None:
            self.subDirsMenu = QtWidgets.QMenu("", self)
            self.subDirsMenu.aboutToHide.connect(self.slot_menuHiding)
            
        self.subDirsMenu.clear()
        
        if self.fileSystemModel.hasChildren(self.rootIndex):
            subDirs = [self.fileSystemModel.data(self.fileSystemModel.index(row, 0, self.rootIndex)) for row in range(self.fileSystemModel.rowCount(self.rootIndex))]
            # print(f"{self.__class__.__name__}.subDirMenuRequested rootIndex subDirs {subDirs}")
            if len(subDirs):
                for k, subDir in enumerate(subDirs):
                    # print(f"subDir {subDir}")
                    action = self.subDirsMenu.addAction(subDir)
                    action.setText(subDir)
                    action.triggered.connect(self.slot_subDirClick)
        
                self.subDirsMenu.popup(self.mapToGlobal(evt.pos()))
    
    @pyqtSlot()
    def slot_subDirClick(self):
        action = self.sender()
        ps = os.path.join(self.path.as_posix(), action.text())
        self.sig_navigate.emit(ps)
        
    @pyqtSlot()
    def slot_menuHiding(self):
        self._pressed_ = False
        self.update()
        
    @property
    def isLeaf(self):
        return self._isLeaf_
    
    @isLeaf.setter
    def isLeaf(self, value:bool):
        self._isLeaf_ = value
        
class NavigatorProtocolCombo(NavigatorButtonBase):
    sig_activated = pyqtSignal()
    def __init__(self, protocol:str, parent=None):
        super().__init__(parent)
        
        
        
class NavigatorPlacesSelector(NavigatorButtonBase):
    sig_placeActivated = pyqtSignal(str, name = "sig_activated")
    sig_tabRequested = pyqtSignal()
    
    def __init__(self, parent, placesModel):
        super().__init__(parent=parent)
        
        self._selectedItem_ = -1
        self._placesModel_ = placesModel
        
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._placesMenu_ = QtWidgets.QMenu(self)
        self._placesMenu_.installEventFilter(self)
        self._selectedUrl_ = QtCore.QUrl()
        
        self.updateMenu()
        
        self._placesModel_.reloaded.connect(self.updateMenu)
        # self._placesMenu_.triggered.connect() ### use updateMenu to connect each action
        
        self.setMenu(self._placesMenu_)
        
        self.setAcceptDrops(True)
        
    def updateMenu(self):
        for obj in self._placesMenu_.children():
            obj.deleteLater()
            
        self._placesMenu_.clear()
        
        self.updateSelection(self._selectedUrl_)
        
        previousGroup = ""
        subMenu = None
        
        rowCount = self._placesModel_.rowCount()
        
        for i in range(rowCount):
            index = self._placesModel_.index(i, 0)
            if self._placesModel_.ishidden(index):
                continue
            
            placeAction = QtWidgets.QAction(self._placesModel_.icon(index),
                                           self._placesModel_.text(index),
                                           self._placesMenu_)
            
            placeAction.setData(i)
            
            groupName = index.data(desktoputils.AdditionalRoles.GroupRole).toString()
            
            if len(previousGroup) == 0:
                previousGroup = groupName
                
            if previousGroup != groupName:
                subMenuAction = QtWidgets.QAction(groupName, self._placesMenu_)
                subMenu = QtWidgets.QMenu(self._placesMenu_)
                subMenu.installEventFilter(self)
                subMenuAction.setMenu(subMenu)
                
                self._placesMenu_.addAction(subMenuAction)
                
                previousGroup = groupName
                
            if isinstance(subMenu, QtWidgets.QMenu):
                subMenu.addAction(placeAction)
            else:
                self._placesMenu_.addAction(placeAction)
                
            if i == self._selectedItem_:
                self.setIcon(self._placesModel_.icon(index))
                
        self.updateTeardownAction()
        
    def updateTeardownAction(self):
        teardownActionId = "teardownAction"
        
        actions = self._placesMenu_.actions()
        
        for action in actions:
            if action.data() == teardownActionId:
                action.deleteLater()
                action = None
                
        index = self._placesModel_.index(self._selectedItem_, 0)
        
        teardown = self._placesModel_.teardownActionForIndex(index)
        
class NavigatorDropDownButton(NavigatorButtonBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        # self._isDown_ = False # def'ed in NavigatorButtonBase
        
        
    def sizeHint(self):
        size = super().sizeHint()
        size.setWidth(size.height() / 2)
        return size
    
    def keyPressEvent(evt:QtGui.QKeyEvent):
        if evt.key() == QtCore.Qt.Key_Down:
            self.clicked.emit()
            
        else:
            super().keyPressEvent(evt)
    
    def paintEvent(evt:QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        self.drawHoverBackground(painter)
        fgColor = QtGui.QColor(self.foregroundColor())
        
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        option.rect = QtCore.QRect(0,0, int(self.width()), int(self.height()))
        option.palette = self.palette()
        option.palette.setColor(QtGui.QPalette.Text, fgColor)
        option.palette.setColor(QtGui.QPalette.WindowText, fgColor)
        option.palette.setColor(QtGui.QPalette.ButtonText, fgColor)
        
        if self._isDown_:
            # self._isDown_ def'ed in superclass
            self.style().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowDown, option, painter, self)
        else:
            if self.layoutDirection() == QtCore.Qt.Left:
                self.style().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowRight, option, painter, self)
            else:
                self.style().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowLeft, option, painter, self)
            
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
        isLeaf = not self._isBranch_
        # self.dirButton = NavigatorButton(self.name, isLeaf, self)
        self.dirButton.setFlat(True)
        self.dirButton.setMinimumSize(w,h)
        # self.dirButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        # self.dirButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed))
        self.dirButton.clicked.connect(self.dirButtonClicked)
        
        # self.branchIcon = QtGui.QIcon.fromTheme("go-next")
        # self.iconSize = self.branchIcon.actualSize(QtCore.QSize(16,h), state=QtGui.QIcon.On)
        
        # self.branchButton = QtWidgets.QPushButton(self.branchIcon, "", self)
        # self.branchButton = ArrowButton(self)
        self.branchButton = QtWidgets.QToolButton(self)
        self.branchButton.setArrowType(QtCore.Qt.RightArrow)
        # self.branchButton.setFlat(True)
        self.branchButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        # self.branchButton.setMinimumSize(self.iconSize.width(), self.iconSize.height())
        # self.branchButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum))
        self.branchButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed))
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
            if k > 0:
                # b = BreadCrumb(p, True, parentCrumb = self.crumbs[-1])#, parent=self)
                b = NavigatorButton(p, True)#, parentCrumb = self.crumbs[-1])
            else:
                # b = BreadCrumb(p, True)#, parent=self)
                b = NavigatorButton(p, True)#, parent=self)
                
            b.sig_navigate.connect(self.slot_crumb_clicked)
            self.crumbs.append(b)
            
        # b = BreadCrumb(self._path_, False, parentCrumb=self.crumbs[-1]) # last dir in path = LEAF !!!
        b = NavigatorButton(self._path_, False)#, parentCrumb=self.crumbs[-1]) # last dir in path = LEAF !!!
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
        Leaves the last Pushbutton behind (for switching to path editor)
        """
        for k, b in enumerate(self.crumbs):
            b.hide()
            b.deleteLater()
            b = None
            
        self.crumbs.clear()
        
        self.navspot.destroy()
        self.navspot = None

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
        print(f"{self.__class__.__name__}.path = {value}")
        self._path_ = value
        self._setupCrumbs_()
        
        
class PathEditor(QtWidgets.QWidget):
    sig_chDirString = pyqtSignal(str, name = "sig_chDirString")
    sig_removeCurrentDirFromHistory = pyqtSignal(str, name = "sig_removeCurrentDirFromHistory")
    sig_clearRecentDirsList = pyqtSignal(str, name = "sig_clearRecentDirsList")
    sig_switchToNavigator = pyqtSignal(name="sig_switchToNavigator")
    
    def __init__(self, path:pathlib.Path, recentDirs:list = [], maxRecent:int=10, parent=None):
        super().__init__(parent=parent) 
        self._path_ = path.resolve()
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
        self._path_ = value.resolve()
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
        self.history.clear()
        self.history = [self.path.as_posix()]
        self.directoryComboBox.clear()
        for i in self.history:
            self.directoryComboBox.addItem(i)
            
        self.directoryComboBox.setCurrentIndex(0)
        
    @pyqtSlot(str)
    def slot_dirChange(self, value):
        hh = self.history
        p = pathlib.Path(value).resolve().as_posix()
        
        if p not in hh:
            hh.insert(0, p)
            self.history = hh
            
        else:
            ndx = hh.index(p)
            del hh[ndx]
            hh.insert(0, p)
            self.history = hh

        self.sig_chDirString.emit(value)
        
# class NavigatorPrivate:
#     pass

class UrlNavigator:
    pass

class Navigator(QtWidgets.QWidget):
    # NOTE: 2023-05-03 08:16:42
    # NavigatorPrivate API
    sig_urlChanged = pyqtSignal(object)
    sig_urlAboutToBeChanged = pyqtSignal()
    sig_historyChanged = pyqtSignal()
    
    def __init__(self, placesModel:typing.Optional[PlacesModel]=None, url:typing.Optional[QtCore.QUrl]=None, parent:typing.Optional[QtWidgets.QWidget] = None):
        
        super().__init__(parent=parent)
        self._supportedSchemes_ = list()
        self._schemes_ = None # QComboBox (KUrlNavigatorSchemeCombo) # TODO ?!?
        # self._d_ = None # NavigatorPrivate
        
        # NOTE:2023-05-03 08:14:35 
        # ### BEGIN NavigatorPrivate API
        self._navButtons_ = list()
        self._customProtocols_ = list()
        self._homeUrl = QtCore.QUrl()
        # self._coreUrlNavigator = None # TODO ?!?
        self._pathBox_ = None # QComboBox (KUrlComboBox)
        self._layout_ = QtWidgets.QHBoxLayout(self)
        self._layout_.setSpacing(0)
        self._layout_.setContentsMargins(0,0,0,0)
        self._toggleEditableMode_ = NavigatorToggleButton(self)
        self._dropWidget_ = None
        
        self._protocols_ = None # QComboBox (KUrlNavigatorProtocolCombo) # TODO
        
        self._subfolderOptions_ = Bunch({"showHidden":False, "showHiddenLast": False})
        
        self._showPlacesSelector_ = isinstance(placesModel, PlacesModel) # FIXME not needed
        self._editable_ = False
        self._active_ = True
        self._showFullPath_ = False
        
        self.setAutoFillBackground(False)
        
        if isinstance(placesModel, PlacesModel):
            self._placesSelector_ = NavigatorPlacesSelector(self, placesModel)
            self._placesSelector_.sig_placeActivated.connect(self.setLocationUrl)
            self._placesSelector_.sig_tabRequested.connect(self.tabRequested)
            self._placesModel_.rowsInserted.connect(self.updateContent)
            self._placesModel_.rowsRemoved.connect(self.updateContent)
            self._placesModel_.dataChanged.connect(self.updateContent)
        else:
            self._placesSelector_ = None
            
        self._protocols_ = NavigatorProtocolCombo("", self)
        self._protocols_.sig_activated.connect(self.slotProtocolChanged)
        
        self._dropDownButton_ = NavigatorDropDownButton(self)
        self._dropDownButton_.setForegroundRole(QtGui.QPalette.WindowText)
        self._dropDownButton_.installEventFilter(self)
        self._dropDownButton_.clicked.connect(self.openPathSelectorMenu)
        # ### END NavigatorPrivate API
        
        
    def __del__(self):
        self._dropDownButton_.removeEventFilter(self)
        self._pathBox_.removeEventFilter(self)
        self._toggleEditableMode_.removeEventFilter(self)
        
        for button in self._navButtons_:
            button.removeEventFilter(self)
            
    @pyqtSlot(str)
    def slotProtocolChanged(self, protocol:str):
        pass # TODO
    
    @pyqtSlot()
    def openPathSelectorMenu(self):
        pass
        
# class Navigator_old(QtWidgets.QWidget):
#     def __init__(self, path:pathlib.Path, editMode:bool=False, recentDirs:list = list(), maxRecent:int=10,parent=None):
#         super().__init__(parent=parent)
#         self._path_ = path.resolve()
#         posixpathstr = self._path_.as_posix()
#         self._recentDirs_ = [posixpathstr]
#         if posixpathstr in recentDirs:
#             rd = [i for i in recentDirs if pathlib.Path(i) != self._path_]
#         else:
#             rd = recentDirs
#         self._recentDirs_ = rd
#         self._editMode_ = editMode==True
#         self._configureUI_()
#         
#     def _configureUI_(self):
#         self.bcnav = BreadCrumbsNavigator(self._path_, parent=self)
#         self.bcnav.sig_chDirString[str].connect(self.slot_dirChange)
#         self.bcnav.sig_switchToEditor.connect(self.slot_switchToEditor)
#         self.editor = PathEditor(self._path_, self._recentDirs_, parent=self)
#         self.editor.sig_chDirString[str].connect(self.slot_dirChange)
#         self.editor.sig_switchToNavigator.connect(self.slot_switchToNavigator)
#         self.hlayout = QtWidgets.QHBoxLayout(self)
#         self.hlayout.setContentsMargins(0,0,0,0)
#         self.hlayout.setSpacing(0)
#         self.setLayout(self.hlayout)
#         self.bcnav.setVisible(False)
#         self.editor.setVisible(False)
#         if self._editMode_:
#             self.editor.setVisible(True)
#             self.layout().addWidget(self.editor)
#             self.bcnav.setVisible(False)
#         else:
#             self.bcnav.setVisible(True)
#             self.layout().addWidget(self.bcnav)
#             self.editor.setVisible(False)
#         
#     @property
#     def recentDirs(self):
#         return self._recentDirs_
#     
#     @recentDirs.setter
#     def recentDirs(self, value:list):
#         self._recentDirs_[:] = value
#         
#     @property
#     def path(self):
#         return self._path_
#     
#     @path.setter
#     def path(self, value:pathlib.Path):
#         self._path_ = value.resolve()
#         signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.bcnav, self.editor)]
#         print(f"{self.__class__.__name__}.path = {self._path_}")
#         self.bcnav.path = value
#         self.editor.path = value
#         
#     @property
#     def editMode(self):
#         return self._editMode_
#     
#     @editMode.setter
#     def editMode(self, value:bool):
#         self._editMode_ = value==True
#         self.update()
#     
#     def update(self):
#         if self.hlayout.count() > 0:
#             self.hlayout.takeAt(0)
#             
#         if self._editMode_:
#             self.bcnav.setVisible(False)
#             self.hlayout.addWidget(self.editor)
#             self.editor.setVisible(True)
#             
#             
#         else:
#             self.editor.setVisible(False)
#             self.hlayout.addWidget(self.bcnav)
#             self.bcnav.setVisible(True)
#             
#         
#     @pyqtSlot(str)
#     def slot_dirChange(self, value):
#         print(f"{self.__class__.__name__}.slot_dirChange value: {value}" )
#         
#         self.path = pathlib.Path(value)
#         
#     @pyqtSlot()
#     def slot_switchToNavigator(self):
#         self.editMode = False
#         
#     @pyqtSlot()
#     def slot_switchToEditor(self):
#         self.editMode = True
