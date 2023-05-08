import typing, pathlib, functools, os, itertools
from urllib.parse import urlparse, urlsplit
from collections import namedtuple
from enum import Enum, IntEnum
import sip # for sip.isdeleted() - not used yet, but beware
from traitlets.utils.bunch import Bunch
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg, sip)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType

from core import desktoputils as dutils
from core.desktoputils import PlacesModel
from core.prog import safeWrapper
import gui.pictgui as pgui
from gui import guiutils
from iolib import pictio

# TODO/FIXME: 2023-05-06 23:12:19
# Since this is only intended for use with local file system (i.e. file:// URI 
# protocol) I should use pathlib.Path instead of QtCore.QUrl

# Root > dir > subdir

archiveTypeStr = ("-compress", "arj", "zip", "rar", "zoo", "lha", "cab", "iso")

NetworkProtocols = ("fish", "ftp", "sftp", "smb", "webdav")

Protocols = ("file", "desktop")

SpecialProtocols = ("trash")

SupportedProtocols = Protocols

ArrowSize = 10

class Navigator:
    pass # fwd decl


class LocationData(typing.NamedTuple):
    """
    Encapsulates location data
    """
    # KCoreUrlNavigator API`
    url:str
    state:object = None
    def __repr__(self):
        return f"LocationData url = {self.url}, state = {self.state}"
    
class UrlNavigatorData(typing.NamedTuple):
    """
    Encapsulates UrlNavigator data
    """
    # KUrlNavigator API
    rootUrl: QtCore.QUrl
    pos: QtCore.QPoint
    state: bytes
    
class SubDirInfo(typing.NamedTuple):
    name:str
    displayName:str
        

def getSystemArchiveMimeTypes():
    mimebd = QtCore.QMimeDatabase()
    types = [m for m in mimedb.allMimeTypes() if any(v in m.name() for v in archiveTypeStr)]
    
    return types

def firstChildUrl(lastUrl:QtCore.QUrl, currentUrl:QtCore.QUrl):
    
    adjustedLastUrl = lastUrl.adjusted(QtCore.QUrl.StripTrailingSlash)
    adjustedCurrentUrl = currentUrl.adjusted(QtCore.QUrl.StripTrailingSlash)
    
    if not adjustedCurrentUrl.isParentOf(adjustedLastUrl):
        return QtCore.QUrl()
    
    childPath = adjustedLastUrl.path()
    parentPath = adjustedCurrentUrl.path()
    
    minIndex = 1 if parentPath == "/" else 2
    
    if len(childPath) < len(parentPath) + minIndex:
        return QtCore.QUrl()
    
    idx2 = childPath.find('/', len(parentPath) + minIndex)
    
    len2 = len(childPath) if idx2 < 0 else idx2
    
    path3 = childPath[:len2]
    
    res = QtCore.QUrl(url)
    res.setPath(path3)
    return res
    
def findProtocol(protocol:str):
    assert len(protocol) > 0
    assert ':' in protocol
    
def isAbsoluteLocalPath(path:str):
    if path.startwith(':'):
        return False
    plpath = pathlib.Path(path)
    return plpath.is_absolute()
    # NOTE: 2023-05-08 17:49:03 use pathlib
    # return not path.startwith(':') and QtCore.QDir.isAbsolutePath(path)

def appendSlash(path:str):
    if len(path) == 0:
        return path
    
    if not path.endswith('/'):
        path += '/'
        
    return path

def removeTrailingPath(path:str):
    if path.endswith('/'):
        path = path[:-1]
        
    return path

def trailingSlashRemoved(path:str):
    path = removeTrailingPath(path)
    return path

def appendSlashToPath(url:QtCore.QUrl):
    path = url.path()
    if len(path) and not path.endswith('/'):
        path = appendSlash(path)
        url.setPath(path)
        
    return url

def concatPaths(path1:str, path2:str):
    assert not path2.startswith('/')
    
    if len(path1) == 0:
        return path2
    
    path1 = appendSlash(path1)
    path1 += path2
    return path1

def isRegFileMask(mode):
    # TODO: use pathlib
    pass

def isDirMask(mode):
    # TODO: use pathlib
    pass

def isLinkMask(mode):
    # TODO: use pathlib
    pass

def upUrl(url:QtCore.QUrl):
    if not url.isValid() and url.isRelative():
        return QtCore.QUrl()
    
    u = QtCore.QUrl(url)
    
    if url.hasQuery():
        u.setQuery("")
        return u
    
    if url.hasFragment():
        u.setFragment("")
        
    u = u.adjusted(QtCore.QUrl.StripTrailingSlash)
    
    return u.adjusted(QtCore.QUrl.RemoveFilename)
    
class SchemeCategory(IntEnum):
    CoreCategory = 0
    PlacesCategory = 2
    DevicesCategory = 3
    SubversionCategory = 4
    OtherCategory = 5
    CategoryCount = 6 # mandatory last entry

class DisplayHint(IntEnum):
    EnteredHint = 1
    DraggedHint = 2
    PopupActiveHint = 4
    
class UrlComboItem(typing.NamedTuple):
    url:QtCore.QUrl
    icon: QtGui.QIcon
    text:str = ""
    
class UrlComboMode(IntEnum):
    Files = -1
    Directories = 1
    Both = 0
    
class UrlComboOverLoadResolving(IntEnum):
    RemoveTop = 0
    RemoveBottom = 1
    
class UrlComboBox(QtWidgets.QComboBox):
    urlActivated = pyqtSignal(QtCore.QUrl, name="urlActivated")
    
    def __init__(self, mode:UrlComboMode, rw:typing.Optional[bool]=False, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent)
        
        self._completer_ = QtWidgets.QCompleter(self)
        self._completer_.setModel(QtWidgets.QFileSystemModel(self._completer_))
        self._completer_.setModelSorting(QtWidgets.QCompleter.CaseSensitivelySortedModel)
        self._completer_.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        
        self.setEditable(rw==True)
        self.lineEdit().setCompleter(self._completer_)
        self._dirIcon_ = QtGui.QIcon.fromTheme("folder")
        self._opendirIcon_ = QtGui.QIcon.fromTheme("folder-open")
        self._mode_ = mode
        self._urlAdded_ = False
        self._maximum_ = 10
        self._dragPoint_ = QtCore.QPoint()
        self.itemList = list() # list of UrlComboItem
        self.defaultList = list()
        self.itemMapper = dict() # int ↦ UrlComboItem
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        
        if isinstance(self.completer(), QtWidgets.QCompleter):
            self.completer().setModelSorting(QtWidgets.QCompleter.CaseSensitivelySortedModel)
        
    def getIcon(self, url:QtCore.QUrl):
        if self._mode_ == UrlComboMode.Directories:
            return self._dirIcon_
        else:
            return QtGui.QIcon.fromTheme(dutils.iconNameForUrl(url))
    
    def textForItem(self, item:UrlComboItem):
        if len(item.text):
            return item.text
        
        url = item.url
        
        if self._mode_ == UrlComboMode.Directories:
            url = appendSlashToPath(url)
        else:
            url = url.adjusted(QtCore.QUrl.StripTrailingSlash)
            
        if url.isLocalFile():
            return url.toLocalFile()
        else:
            return url.toDisplayString()
        
    def insertUrlItem(self, item:UrlComboItem):
        ndx = self.count()
        self.insertItem(ndx, item.icon, self.textForItem(item))
        self.itemMapper[ndx] = item
        
    def updateItem(self, item:UrlComboItem, index:int, icon:QtGui.QIcon):
        self.setItemIcon(index, icon)
        self.setItemText(index, self.textForItem(item))
        
    def maxItems(self):
        return self._maximum_
    
    def setMaxItems(self, value:int):
        self._maximum_ = value
        
        if self.count() > self._maximum_:
            oldCurrent = self.currentIndex()
            
            self.setDefaults()
            
            offset = max(0, len(self.itemList) + self.defaultList - self._maximum_)
            
            for k in range(offset, len(self.itemList)):
                self.insertUrlItem(self.itemList[k])
                
            if self.count() > 0: # restore prev current item
                if oldCurrent >= self.count():
                    oldCurrent = self.count() - 1
                    
                self.setCurrentIndex(oldCurrent)
                
                
    def removeUrl(self, url:QtCore.QUrl, checkDefaultURLs:bool):
        for k, v in self.itemMapper.items():
            if url.toString(QtCore.QUrl.StripTrailingSlash) == v.url.toString(QtCore.QUrl.StripTrailingSlash):
                lst = [i for i in self.itemList if i != url]
                
                self.itemList[:] = lst
                
                if checkDefaultURLs:
                    self.defaultList[:] = lst
                    
        signalBlocker = QtCore.QSignalBlocker(self)
        
        self.setDefaults()
        
        for item in self.itemList:
            self.insertUrlItem(item)
    
    def urls(self):
        ulist = list()
        for i in range(len(self.defaultList), self.count()):
            url = self.itemText(i)
            if len(url):
                if isAbsoluteLocalPath(url):
                    ulist.append(QtCore.QUrl.fromLocalFile(url).toString())
                else:
                    ulist.append(url)
                    
        return ulist
    
    def addDefaultUrl(self, url:QtCore.QUrl, icon:typing.Optional[QtGui.QIcon] = None, text:str=""):
        if not isinstance(icon, QtGui.QIcon):
            icon = self.getIcon(url)
            
        self.defaultList.append(UrlComboItem(url, icon, text))
            
        
    def setDefaults(self):
        self.clear()
        self.itemMapper.clear()
        
        for item in self.defaultList:
            self.insertUrlItem(item)
            
    def setUrls(self, ulist:list, remove:UrlComboOverLoadResolving = UrlComboOverLoadResolving.RemoveBottom):
        self.setDefaults()
        self.itemList.clear()
        self._urlAdded_ = False
        
        if len(ulist) == 0:
            return
        
        urls = list()
        for u in ulist:
            if u not in urls:
                urls.append(u)
                
        Overload = len(urls) - self._maximum_ + len(self.defaultList)
        
        while Overload > 0:
            if remove == UrlComboOverLoadResolving.RemoveBottom:
                if len(urls):
                    urls = urls[:-1]
            else:
                if len(urls):
                    urls = urls[1:]
                    
            Overload = Overload - 1
            
        uu = QtCore.QUrl()
        
        for u in urls:
            if u.isEmpty():
                continue
            
            if isAbsoluteLocalPath(u):
                uu = QtCore.QUrl.fromLocalFile(u)
            else:
                uu.setUrl(u)
                
            if u.isLocalFile() and not QtCore.QFile.exists(u.toLocalFile()):
                continue
            ucon = self.getIcon(uu)
            item = UrlComboItem(uu, icon)
            self.insertUrlItem(item)
            self.itemList.append(item)
            
    def setUrl(self, url:QtCore.QUrl):
        if url.isEmpty():
            return
        
        signalBlocker = QtCore.QSignalBlocker(self)
        
        urlToInsert = url.toString(QtCore.QUrl.StripTrailingSlash)
        
        # checks for duplicates
        for k, v in self.itemMapper.items():
            if urlToInsert == v.toString(QtCore.QUrl.StripTrailingSlash):
                self.setCurrentItem(k)
                
                if self._mode_ == UrlComboMode.Directories:
                    self.updateItem(v, k, self._opendirIcon_)
                    
                return
        
        if self._urlAdded_:
            if len(self.itemList):
                self.itemList = self.itemList[:-1]
                self._urlAdded_ = False
                
        self.setDefaults()
        
        offset = max(0, len(self.itemList) + len(self.defaultList) - self._maximum_)
        
        for k in range(offset, len(self.itemList)):
            self.insertUrlItem(self.itemList[k])
        
        icon = self.getIcon(url)
        item = UrlComboItem(url, icon)
        
        ndx = self.count()
        text = self.textForItem(item)
        
        if self._mode_ == UrlComboMode.Directories:
            self.insertItem(ndx, self._opendirIcon_, text)
        else:
            self.insertItem(ndx, item.icon, text)
            
        self.itemMapper[ndx] = item
        
        self.itemList.append(item)
        
        self.setCurrentIndex(ndx)
        
        if len(self.itemList):
            self._urlAdded_ = True
            
    @pyqtSlot(int)
    def slot_activated(self, ndx:int):
        item = self.itemMapper.get(ndx, None)
        
        if isinstance(item, UrlComboItem):
            self.setUrl(item.url)
            self.urlActivated.emit(item.url)
            
    def mousePressEvent(self, evt:QtGui.QMouseEvent):
        comboOpt = QtWidgets.QStyleOptionComboBox()
        comboOpt.initFrom(self)
        x0 = QtWidgets.QStyle.visualRect(self.layoutDirection(), 
                                         self.rect(),
                                         self.style().subControlRect(QtWidgets.QStyle.CC_ComboBox,
                                                                     QtWidgets.QStyle.SC_ComboBoxEditField,
                                                                     self)).x()
        frameWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth,
                                              comboOpt, self)
        
        if evt.x() < (x0 + 16 + frameWidth):
            self._dragPoint_ = evt.pos()
        else:
            self._dragPoint_ = QtCore.QPoint()
            
        super().mousePressEvent(evt)
        
    def mouseMoveEvent(self, evt:QtGui.QMouseEvent):
        ndx = self.currentIndex()
        item = self.itemMapperget(ndx, None)
        
        if isinstance(item, UrlComboItem) and not self._dragPoint_.isNull() and evt.buttons() & QtCore.Qt.LeftButton and (evt.pos() - self._dragPoint_).manhattanLength() > QtWidgets.QApplication.startDragDistance():
            drag = QtGui.QDrag(self)
            mime = QtCore.QMimeData()
            mime.setUrls([item.url])
            mime.settext(self.itemText(ndx))
            if not self.itemIcon(ndx).isNull():
                # self.itemIcon inherited from QComboBox
                drag.setPixmap(self.itemIcon(ndx)).pixmap(32)
                
            drag.setMimeData(mime)
            drag.exec()
            
        super().mousemoveEvent(evt)
                        
    # TODO/FIXME ?
    # def setCompletionObject(self, compObj:QtWidgets.QCompleter, hsig:bool):
    #     compObj.setModelSorting(QtWidgets.QCompleter.CaseSensitivelySortedModel)
                    
    
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
    # FIXME/TODO 2023-05-07 23:34:55 finalize
    navigate = pyqtSignal(str, name="navigate")
    urlsDroppedOnNavButton = pyqtSignal(QtCore.QUrl, QtGui.QDropEvent, name = "urlsDroppedOnNavButton")
    navigatorButtonActivated = pyqtSignal(QtCore.QUrl, QtCore.Qt.MouseButton, QtCore.Qt.KeyboardModifiers, name = "navigatorButtonActivated")
    startedTextResolving = pyqtSignal(name = "startedTextResolving")
    finishedTextResolving = pyqtSignal(name = "finishedTextResolving")
    
    # def __init__(self, text:str, leaf:bool=False, parent=None):
    # def __init__(self, path:pathlib.Path, isBranch:bool=False, parentCrumb=None, parent=None):
    # def __init__(self, path:pathlib.Path, isBranch:bool=False, parent=None):
    def __init__(self, url.QtCore.QUrl, parent:typing.Optional[Navigator]=None):
        super().__init__(parent=parent)
        # self._isLeaf_ = not isBranch # CMT
        self._hoverArrow_ = False
        self._pressed_ = False
        self._pendingTextChange_ = False
        self._replaceButton_ = False
        self._showMnemonic_ = False
        self._wheelSteps_ = 0
        self._url_ = url
        self._subDir_ = "" # TODO
        self._openSubDirsTimer_ = None # QtCore.QTimer() # TODO
        self._subDirsJob_ = None # originally, a KIO.listDir → TODO: replace with Python logic (async?)
        self._subDirsMenu_ = None # NavigatorMenu # TODO
        self._subDirs_ = list() # of SubdirInfo
        
        self.setAcceptDrops(True)
        self.setUrl(url)
        self.setMouseTracking(True)
        
        self._openSubDirsTimer_ = QtCore.QTimer(self)
        self._openSubDirsTimer_.setSingleShot(True)
        self._openSubDirsTimer_.setInterval(300)
        self._openSubDirsTimer_.timeout.connect(self.startSubDirsJob)
        
        self.pressed.connect(self.requestSubDirs)
        
#         # ### BEGIN CMT 2023-05-08 17:56:23
#         
#         path = path.resolve()
#         
#         if not path.is_dir():
#             path = path.parent
#             
#         self.path = path
#         self.name = self.path.name
#         if len(self.name) == 0:
#             self.name = self.path.parts[0]
#     
#         self.setText(self.name)
#         
#         # self.parentCrumb = parentCrumb
#         
#         self.subDirsMenu = None
#         
#         # NOTE: 2023-05-07 23:42:42 
#         # use Qt file system model; does away with KIOJob etc (?!?)
#         self.fileSystemModel = QtWidgets.QFileSystemModel(parent=self)
#         self.fileSystemModel.setReadOnly(True)
#         self.fileSystemModel.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.CaseSensitive | QtCore.QDir.NoDotAndDotDot)
#         self.fileSystemModel.setRootPath(self.path.as_posix())
#         self.rootIndex = self.fileSystemModel.index(self.fileSystemModel.rootPath())
# 
#         # self.frameStyleOptions = QtWidgets.QStyleOptionFrame()
#         # self.frameStyleOptions.initFrom(self)
#         # self.frameStyleOptions.
#         
#         # ### END CMT 2023-05-08 17:56:23

    def setUrl(self, url:QtCore.QUrl): # FIXME/TODO: replace with a pythonic async protocol
        self._url_ = url
        
        # NOTE: 2023-05-08 18:06:14 KIO original
        protocolBlackList = {"nfs", "fish", "ftp", "sftp", "smb", "webdav", "mtp"}
        
        # protocolBlackList = {"nfs", "fish", "ftp", "sftp", "smb", "webdav", "mtp",
        #                      "http", "https", "man", "info", "gopher", "baloosearch", "filenamesearch", # CMT
        #                      "recoll", "rkward", "remote", "applications", "fonts"} # CMT
        
        startTextResolving = self._url_.isValid() and not self._url_.isLocalFile() and self._url_.scheme() is not in protocolBlackList
        
        if startTextResolving:
            # A-ha! whenever the protocol specified by the url scheme is not black-listed,
            # start aynchronous job to resolve it
            # This is for a url that IS NOT local, and , as per KIO original, the scheme
            # indicates:
            # • internet protocol (http, htpps, )
            # • special KDE frameworks protocol - WARNING these may be supplied by
            #  3ʳᵈ party KDE applications via KDE plugins framework (so-called
            #  KIO slaves); examples include Rkward, Recoll, Clementine, Amarok, etc.
            #
            # NOTE: A list of available protocols can be seen in KDE gui via the
            # file nmanager Dolphin: open a Dolphin window, click in the navigator
            # bar to show is as an editable field, clear the field ⇒ the leftmost
            # dropdown menu shows the available protocols in YOUR system 
            #
            # The 'special' ones are usually in an "Other" submenu
            #
            # TODO: contemplate calling kioexec5 for these !!!
            # TODO: filter these out so that they only show for sys.platform == "linux"
            #
            self._pendingTextChange_ = True
            # starts a KIO job via 
            # job = KIO.stat(self._url_, hide progress info)
            # then connects job.result to self.statFinished
            # finally, emit self.startedTextResolving
            
        else:
            self.setText(self._url_.fileName().replace('&', '&&'))
            
    def url(self):
        return self._url_
        
    def setText(self, text): 
        if len(text) == 0:
            text = self._url_.scheme()
            
        
        super().setText(text)
        
        self.updateMinimumWidth()
        
        self._pendingTextChange_ = False
        
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
            
    def showMnemonic(self):
        return self._showMnemonic_
        
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
        
    def enterEvent(self, evt:QtGui.QEnterEvent):
        super().enterEvent(evt)
        
        if self.isTextClipped():
            self.setToolTip(self.plainText())
            
    def leaveEvent(self, evt:QtCore.QEvent):
        super().leaveEvent(evt)
        
        self.setToolTip("")
        
        if self._hoverArrow_:
            self._hoverArrow_ = False
            self.update()
            
    def keyPressEvent(self, evt:QtGui.QKeyEvent):
        evtKey = evt.key()
        
        if evtKey == QtCore.Qt.Key_Enter:
            pass
        elif evtKey == QtCore.Qt.Key_Return:
            self.navigatorButtonActivated.emit(self._url, QtCore.Qt.LeftButton, evt.modifiers())
            return
        elif evtKey == QtCore.Qt.Key_Down:
            pass
        elif evtKey == QtCore.Qt.Key_Space:
            self.startSubDirsJob() # TODO 2023-05-08 13:18:48
            return
        
        else:
            super().keyPressEvent(evt)
            
    def dropEvent(self, evt:QtGui.QDropEvent):
        if evt.mimeData().hasUrls():
            self.setDisplayHintEnabled(DisplayHint.DraggedHint, True)
            self.urlsDroppedOnNavButton.emit(self._url_, evt)
            self.setDisplayHintEnabled(DisplayHint.DraggedHint, False)
            self.update()
            
    def dragEnterEvent(self, evt:QtGui.QDragEnterEvent):
        if evt.mimeData().hasUrls():
            self.setDisplayHintEnabled(DisplayHint.DraggedHint, True)
            evt.acceptProposedAction()
            self.update()
            
    def dragMoveEvent(self, QtGui.QDragMoveEvent):
        rect = evt.answerRect()
        if self.isAboveArrow(rect.center().x()):
            self._hoverArrow_ = True
            self.update()
            
            if self._subDirsMenu_ is None:
                self.requestSubDirs() # TODO: 2023-05-08 13:27:04
            elif self._subDirsMenu_.parent() != self:
                self._subDirsMenu_.close()
                self._subDirsMenu_.deleteLater()
                self._subDirsMenu_ = None
                
                self.requestSubDirs()
                
        else:
            if self._openSubDirsTimer_.isActive(): # TODO 2023-05-08 13:28:35 self._openSubDirsTimer_
                self.cancelSubDirsRequest() # TODO 2023-05-08 13:29:04
                
            self._subDirsMenu_.deleteLater()
            self._subDirsMenu_ = None
            self._hoverArrow_ = False
            self.update()
            
    def dragLeaveEvent(self, evt:QtGui.QDragLeaveEvent):
        super().dragLeaveEvent(evt)
        self._hoverArrow_ = False
        self.setDisplayHintEnabled(DisplayHint.DraggedHint, False)
        self.update()
        
    def mousePressEvent(self, evt:QtGui.QMouseEvent):
        super().mousePressEvent(evt)
        if self.isAboveArrow(round(evt.pos().x())):
            self._pressed_ = True
            self.update()
        
    def mouseReleaseEvent(self, evt:QtGui.QMouseEvent):
        if self.isAboveArrow(round(evt.pos().x())) or evt.button() != QtCore.Qt.LeftButton:
            self.subDirMenuRequested(evt)
        else:
            self.navigate.emit(self.path.as_posix())
            
        super().mouseReleaseEvent(evt)
        
    def mouseMoveEvent(self, evt:QtGui.QMouseEvent):
        super().mouseMoveEvent(evt)
        hoverArrow = self.isAboveArrow(round(evt.pos().x()))
        if hoverArrow != self._hoverArrow_:
            self._hoverArrow_ = hoverArrow
            self.update()
            
    def wheelEvent(self, QtGui.QWheelEvent):
        if evt.angleDelta().y() != 0:
            self._wheelSteps_ = evt.angleDelta().y() / 120
            self._replaceButton_ = True
            self.startSubDirsJob()
            
        super().wheelEvent(evt)
            
    def isTextClipped(self):
        availableWidth = self.width() - 2*self.BorderWidth
        adjustedFont = self.font()
        adjustedFont.setBold(self.isLeaf)
        return QtGui.QFontMetrics(adjustedFont).size(QtCore.Qt.TextSingleLine, self.text()).width() >= availableWidth
        
    def requestSubDirs(self): # TODO 2023-05-08 13:39:57 finalize
        if not self._openSubDirsTimer_.isActive() and self._subDirsJob_ is None:
            self._openSubDirsTimer_.start() # TODO/FIXME 2023-05-08 13:36:13 make sure you understand what this does
    
    def startSubDirsJob(self): # TODO/FIXME 2023-05-08 13:37:00 make sure you understand what this does
        if self._subDirsJob_ is None:
            return
        
        url = upUrl(self._url_) if self._replaceButton_ else self._url_
        
        # TODO 2023-05-08 13:19:49 create a listDir job iobject to work with QTimer
        pass
    
    
    def cancelSubDirsRequest(self):
        # TODO 2023-05-08 13:29:21
        pass
        
    @safeWrapper
    def subDirMenuRequested(self, evt:QtGui.QMouseEvent): # TODO/FIXME finalize
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
    def slot_subDirClick(self): # TODO/FIXME NOW - self.path not existent
        action = self.sender()
        ps = os.path.join(self.path.as_posix(), action.text())
        self.navigate.emit(ps)
        
    @pyqtSlot()
    def slot_menuHiding(self):
        self._pressed_ = False
        self.update()
        
    @property
    def isLeaf(self): # CMT - not used FIXME/TODO
        return self._isLeaf_
    
    @isLeaf.setter
    def isLeaf(self, value:bool): # CMT - not used FIXME/TODO
        self._isLeaf_ = value
        
# NOTE: 2023-05-06 22:30:40
# We only use the "file://" protocol, so this is not needed
#
# class NavigatorProtocolCombo(NavigatorButtonBase): # TODO
#     sig_activated = pyqtSignal()
#     def __init__(self, protocol:str, parent=None):
#         super().__init__(parent)
        
# NOTE: 2023-05-06 22:26:18
# By design we only use the 'file://' protocol hence this is NOT needed
#
# class NavigatorSchemeCombo(NavigatorButtonBase):
#     sig_activated = pyqtSignal(str, name="sig_activated")
#     
#     def __init__(self, scheme:str, parent:typing.Optional[Navigator]=None):
#         super().__init__(parent)
#         self._menu_ = QtWidgets.QMenu(self)
#         self._schemes_ = list()
#         self._categories_ = dict() # str ↦ SchemeCategory
#         
#         self._menu_.triggered.connect(self.setSchemeFromMenu)
#         self.setText(scheme)
#         self.setMenu(self._menu_)
#         
#     def _testProtocol_(self, scheme:str):
#         url = QtCore.QUrl()
#         url.setScheme(scheme)
#         return True
#         
#     @pyqtSlot()
#     def setSchemeFromMenu(self):
#         pass # TODO
#     
#     @pyqtSlot(str)
#     def setScheme(self, scheme:str):
#         self.setText(scheme)
#         
#     def currentScheme(self):
#         return self.text()
#     
#     def setSupportedSchemes(self, schemes:list):
#         self._schemes_ = schemes
#         self._menu_.clear()
#         for scheme in schemes:
#             action = self._menu_.addAction(scheme)
#             action.setData(scheme)
#             
#     def sizeHint(self):
#         size = super().sizeHint()
#         width = self.fontMetrics().boundingRect(dutils.removeAcceleratorMarker(self.text())).width()
#         width += (3 * self.BorderWidth) + ArrowSize
#         
#         return QtCore.QSize(width, size.height())
#     
#     def showEvent(self, evt:QtGui.QShowEvent):
#         super().showEvent(evt)
#         if not evt.spontaneous() and len(self._schemes_) == 0:
#             protocols = [p for p in ProtocolInfo.protocols() if self._testProtocol_(p)]
#             self._schemes_[:] = sorted(protocols)
            
            
            
        
class NavigatorPlacesSelector(NavigatorButtonBase): # TODO: 2023-05-07 23:07:25 finalize
    sig_placeActivated = pyqtSignal(str, name = "sig_activated")
    tabRequested = pyqtSignal()
    
    def __init__(self, placesModel:PlacesModel, parent:typing.Optional[QtWidgets.QWidget]=None):
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
        
    def selectedPlaceUrl(self): # TODO/FIXME finalize
        return QtCore.QUrl()
    
    def selectedPlaceText(self): # TODO/FIXME finalize
        return ""
        
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
            
class UrlNavigator(QtCore.QObject):
    currentUrlAboutToChange     = pyqtSignal(QtCore.QUrl, name = "currentUrlAboutToChange")
    currentLocationUrlChanged   = pyqtSignal(name = "currentLocationUrlChanged")
    urlSelectionRequested       = pyqtSignal(QtCore.QUrl, name = "urlSelectionRequested")
    historyIndexChanged         = pyqtSignal(name = "historyIndexChanged")
    historyChanged              = pyqtSignal(name = "historyChanged")
    historySizeChanged          = pyqtSignal(name = "historySizeChanged")
    
    def __init__(self, url:QtCore.QUrl = QtCore.QUrl(), parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        
        # NOTE: 2023-05-03 23:48:23
        # Originally, a list of LocationData structs.
        # Here, this is a NamedTuple with the fields "url" and "state"
        self._history_ = list() # of LocationData
        self._history_.insert(0, LocationData(url.adjusted(QtCore.QUrl.NormalizePathSegments), None))
        self._historyIndex_ = 0
        
    @property
    def historyIndex(self):
        return self._historyIndex_
    
    @historyIndex.setter
    def historyIndex(self, value:int):
        self._historyIndex_ = value
        self.historyIndexChanged.emit()
        
    @property
    def historySize(self):
        return len(self._history_)
    
    @property
    def currentLocationUrl(self):
        return self.locationUrl()
    
    @currentLocationUrl.setter
    def currentLocationUrl(self, newUrl:QtCore.QUrl):
        if newUrl == self.locationUrl():
            return
        
        url = newUrl.adjusted(QtCore.QUrl.NormalizePathSegments)
        
        firstUrlChild = firstChildUrl(self.locationUrl(), url)
        
        scheme = url.scheme()
        # NOTE: 2023-05-04 15:15:30
        # Scipyen's file manager does NOT use special protocols (which include
        # compressed archives)

        data = self._history_[self._historyIndex_]
        
        isUrlEqual = url.matches(self.locationUrl(), QtCore.QUrl.StripTrailingSlash) or (not url.isValid() and url.matches(data.url, QtCore.QUrl.StripTrailingSlash))
        
        if isUrlEqual:
            return
        
        self.currentUrlAboutToChange.emit(url)
        
        if self._historyIndex_ > 0:
            self._history_[0:self._historyIndex_] = []
            self._historyIndex_ = 0

        assert self._historyIndex_ == 0
        self._history_.insert(0, LocationData(url))
        
        historyMax = 100 # TODO make configurable -> link with mainWindow !!!
        
        if len(self._history_) > historyMax:
            self._history_[0:historyMax] = []
            
        self.historyIndexChanged.emit()
        self.historySizeChanged.emit()
        self.historyChanged.emit()
        self.currentLocationUrlChanged.emit()
        
    def setCurrentLocationUrl(self, newUrl:QtCore.QUrl):
        if newUrl == self.locationUrl():
            return
        self.currentLocationUrl = newUrl
            
    def isCompressedPath(self, path:QtCore.QUrl, archiveMimeTypes:list = list()):
        db = QtCore.QMimeDatabase()
        mime = db.mimeTypeForUrl(QtCore.QUrl(url.toString(QtCore.QUrl.StripTrailingSlash)))
        
        return any(mime.inherits(archiveType) for archiveType in archiveMimeTypes)
        
    def adjustedHistoryIndex(self, historyIndex:int):
        historySize = len(self._history_)
        if historyIndex < 0:
            historyIndex = self._historyIndex_
        elif historyIndex >= historySize:
            historyIndex = historySize - 1
            assert historyIndex >= 0
            
        return historyIndex
    
    def locationUrl(self, historyIndex:int = -1):
        historyIndex = self.adjustedHistoryIndex(historyIndex)
        return self._history_[historyIndex].url
    
    @safeWrapper
    def saveLocationState(self, state:object):
        oldLoc = self._history_[self._historyIndex_]
        newLoc = LocationData(oldLoc.url, state)
        self._history_[self._historyIndex_] = newLoc
        
    @safeWrapper
    def locationState(self, historyIndex:int = -1):
        historyIndex = self.adjustedHistoryIndex(historyIndex)
        return self._history_[historyIndex].state
    
    def goBack(self):
        count = len(self._history_)
        
        if self._historyIndex_ < count - 1:
            newUrl = self.locationUrl(self._historyIndex_ + 1)
            self.currentUrlAboutToChange.emit(newUrl)
            self._historyIndex_ += 1
            self.historyIndexChanged.emit()
            self.historyChanged.emit()
            self.currentLocationUrlChanged.emit()
            return True
        
        return False
    
    def goForward(self):
        if self._historyIndex_ > 0:
            newUrl = self.locationUrl(self._historyIndex_ - 1)
            self.currentUrlAboutToChange(newUrl)
            self._historyIndex_ -= 1
            self.historyIndexChanged.emit()
            self.historyChanged.emit()
            self.currentLocationUrlChanged.emit()
            return True
        
        return False
    
    def goUp(self):
        currentUrl = self.locationUrl()
        
        if not currentUrl.isValid() or currentUrl.isRelative():
            return QtCore.QUrl()
        
        u = QtCore.QUrl(currentUrl)
        if currentUrl.hasQuery():
            u.setQuery("")
            return u
        
        if currentUrl.hasFragment():
            u.setFragment("")
            
            u = u.adjusted(QtCore.QUrl.StripTrailingSlash)
            return u.adjusted(QtCore.QUrl.RemoveFilename)
        
        
class NavigatorPathSelectorEventFilter(QtCore.QObject):
    tabRequested = pyqtSignal(QtCore.QUrl, name="tabRequested")
    def __init__(self, parent:QtCore.QObject):
        super().__init__(parent)
        
    @safeWrapper
    def eventFilter(self, watched:QtCore.QObject, evt:QtCore.QEvent):
        if evt.type() == QtCore.QEvent.MouseButtonRelease:
            me = sip.cast(evt, QtGui.QMouseEvent)
            try:
                menu = sip.cast(watched, QtWidgets.QMenu)
                action = menu.activeAction()
                if action is not None:
                    url = QtCore.QUrl(action.data().toString())
                    if url.isValid():
                        menu.close()
                        self.tabRequested.emit(url)
                        return True
                    
        return QtCore.QObject.eventFilter(watched, evt)
        

class Navigator(QtWidgets.QWidget):
    # ### BEGIN signals
    activated           = pyqtSignal(name = "activated")
    urlChanged          = pyqtSignal(QtCore.QUrl, name="urlChanged")
    urlAboutToBeChanged = pyqtSignal(QtCore.QUrl, name = "urlAboutToBeChanged")
    editableStateChanged = pyqtSignal(bool, name = "editableStateChanged")
    historyChanged      = pyqtSignal(name = "historyChanged")
    urlsDropped         = pyqtSignal(QtCore.QUrl, QtGui.QDropEvent, name = "urlsDropped")
    returnPressed       = pyqtSignal(name = "returnPressed")
    
    # NOTE: 2023-05-07 22:03:17
    # Scipyen's file system viewer does not support tabs
    # tabRequested        = pyqtSignal(QtCore.QUrl, name = "tabRequested")
    # activeTabRequested  = pyqtSignal(QtCore.QUrl, name = "activeTabRequested")
    
    # NOTE: 2023-05-07 22:03:37
    # this should open the url in the system's default application
    newWindowRequested  = pyqtSignal(QtCore.QUrl, name = "newWindowRequested")
    urlSelectionRequested = pyqtSignal(QtCore.QUrl, name = "urlSelectionRequested")
    # ### END signals
    
    def __init__(self, placesModel:typing.Optional[PlacesModel]=None, url:typing.Optional[QtCore.QUrl]=None, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        
        # NOTE: 2023-05-06 22:27:36
        # We only suppoert "file:" protocol
        # self._supportedSchemes_ = list()
        
        # self._d_ = None # NavigatorPrivate
        
        # NOTE:2023-05-03 08:14:35 
        # ### BEGIN NavigatorPrivate API
        self._layout_ = QtWidgets.QHBoxLayout(self)
        self._layout_.setSpacing(0)
        self._layout_.setContentsMargins(0,0,0,0)
        self._toggleEditableMode_ = NavigatorToggleButton(self)
        self._dropWidget_ = None
        
        self._urlNavigator_ = UrlNavigator(url, self) # m_coreUrlNavigator
        self._urlNavigator_.currentLocationUrlChanged.connect(self._slot_urlNavigatorUrlChanged)
        self._urlNavigator_.currentUrlAboutToChange[QtCore.QUrl].connect(self._slot_urlNavigatorUrlAboutToBeChanged)
        self._urlNavigator_.historySizeChanged.connect(self.historyChanged)
        self._urlNavigator_.historyIndexChanged.connect(self.historyChanged)
        self._urlNavigator_.historyChanged.connect(self.historyChanged)
        
        self._navButtons_ = list() # list of "breadcrumb buttons" - instances of NavigatorButton
        self._customProtocols_ = list()
        self._homeUrl_ = QtCore.QUrl()
        
        if isinstance(placesModel, PlacesModel):
            self._placesSelector_ = NavigatorPlacesSelector(placesModel, self)
            self._placesSelector_.sig_placeActivated.connect(self.setLocationUrl)
            # self._placesSelector_.tabRequested.connect(self.tabRequested)
            self._placesModel_.rowsInserted.connect(self.updateContent)
            self._placesModel_.rowsRemoved.connect(self.updateContent)
            self._placesModel_.dataChanged.connect(self.updateContent)
            self._showPlacesSelector_ = True
        else:
            self._placesSelector_ = None
            self._showPlacesSelector_ = False
        
        self._subfolderOptions_ = Bunch({"showHidden":False, "sortHiddenLast": False})
        
        self._editable_ = False
        self._active_ = True
        self._showFullPath_ = False
        
        self.setAutoFillBackground(False)

        # NOTE: 2023-05-06 22:30:13
        # We only use "file://" protocol - hence only the file:// url scheme is
        # supported in Scipyen, see also NOTE: 2023-05-06 22:30:13 below
        # self._protocols_ = NavigatorProtocolCombo("", self)
        # self._protocols_.sig_activated.connect(self.slotProtocolChanged)
        self._protocols_ = None # I might revisit this
        
        # NOTE: 2023-05-06 22:25:07
        # by design we only support a file: protocol
        # hence we do NOT need self._schemes_
        # self._schemes_ = None # QComboBox (KUrlNavigatorSchemeCombo) # TODO ?!?
        # self._schemes_.activated.connect(self.slotSchemeChanged)
        self._schemes_ = None # I might revisit this
        
        # NOTE: 2023-05-07 22:59:49
        # drops down a menu of places or parent paths
        self._dropDownButton_ = NavigatorDropDownButton(self)
        self._dropDownButton_.setForegroundRole(QtGui.QPalette.WindowText)
        self._dropDownButton_.installEventFilter(self)
        self._dropDownButton_.clicked.connect(self.openPathSelectorMenu)
        
        # NOTE: 2023-05-07 23:16:43
        # the actual path combo box
        # TODO: Modify UrlComboBox code: to its QLineEdit, add exra tool buttons for:
        # • clearing history
        # • clear current text
        # • remove current text from history
        # • enable clear, undo, redo
        self._pathBox_ = UrlComboBox(UrlComboMode.Directories, False, self)
        # self._pathBox_.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
        self._pathBox_.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._pathBox_.installEventFilter(self)
        
        # NOTE: 2023-05-07 23:22:18
        # toggled between url combo box and bread crumbs
        self._toggleEditableMode_ = NavigatorToggleButton(self)
        self._toggleEditableMode_.installEventFilter(self)
        self._toggleEditableMode_.setMinimumWidth(20)
        self._toggleEditableMode_.toggled[bool].connect(self.slotTogleEditableButtonToggled)
        
        if self._placesSelector_ is not None:
            self._layout_.addwidget(self._placesSelector_)
            
        # self._layout_.addWidget(self._schemes_) # see NOTE: 2023-05-06 22:30:13
        
        self._layout_.addWidget(self._dropDownButton_)
        self._layout_.addWidget(self._pathBox_, 1)
        self._layout_.addWidget(self._toggleEditableMode_)
        
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.openContextMenu)
        
        # ### END NavigatorPrivate API
        
        self.setMinimumHeight(self._pathBox_.sizeHint().height())
        self.setMinimumWidth(100)
        self.updateContent()
        
    def __del__(self):
        self._dropDownButton_.removeEventFilter(self)
        self._pathBox_.removeEventFilter(self)
        self._toggleEditableMode_.removeEventFilter(self)
        
        for button in self._navButtons_:
            button.removeEventFilter(self)
        
    # ### BEGIN KUrlNavigatorPrivate API
            
    def switchView(self, editable:bool):
        # KUrlNavigatorPrivate
        self._toggleEditableMode_.setFocus()
        self._editable_ = editable
        self._toggleEditableMode_.setChecked(self._editable_)
        
        self.updateContent()
        
        if self.isUrlEditable():
            self._pathBox_.setFocus()
            
        self.requestActivation()
        self.editableStateChanged.emit(self._editable_)
        
    def dropUrls(self, destination:QtCore.QUrl, evt:QtGui.QDropEvent, dropButton:NavigatorButton):
        # KUrlNavigatorPrivate
        if evt.mimeData().hasUrls():
            self._dropWidget_ = dropButton
            self.urlsDropped.emit(destination, evt)
            
    def applyUncommittedUrl(self):
        # KUrlNavigatorPrivate
        text = self._pathBox_.currentText().strip()
        url = self.locationUrl()
        # if url.isEmpty() and len(text) > 0:
            # if self.slotCheckFilters(text):
            #     return
        
        if text.startswith('/'):
            url.setPath(text)
        else:
            url.setPath(concatPaths(url.path(), text))
            
        if os.path.isdir(url.path()):
            self.slotApplyUrl(url)
            return
        
        # NOTE: 2023-05-06 23:04:42
        # not sure we need this either...
        self.slotApplyUrl(QtCore.QUrl.fromUserInput(text))
        
    def appendWidget(self, widget:QtWidgets.QWidget, stretch:int=0):
        # KUrlNavigatorPrivate
        # NOTE: 2023-05-08 11:04:33
        # CAUTION: does NOT append to self._navButtons_!!!
        # this must eb done separately when appending a NavigatorButton, see
        # NOTE: 2023-05-08 11:05:23
        self._layout_.insertWidget(self._layout_.count()-1, widget, stretch)
        
    def retrievePlaceUrl(self): # TODO/FIXME: 2023-05-07 23:09:25
        # KUrlNavigatorPrivate
        currentUrl = self.locationUrl()
        currentUrl.setPath("")
        return currentUrl
    
    def switchToBreadcrumbMode(self):
        # KUrlNavigatorPrivate
        self.setUrlEditable(False)
        
    def buttonUrl(self, ndx:int):
        # KUrlNavigatorPrivate
        if ndx < 0:
            ndx = 0
            
        url = self.locationUrl()
        path = url.path()
        
        if len(path):
            if ndx == 0:
                if sys.platform == "win32":
                    path = path[:2] if len(path) > 1 else QtCore.QDir.rootPath()
                else:
                    path = "/"
                    
            else:
                pathParts = path.split("/")
                path = pathParts[:ndx]
                
        url.setPath(path)
        
        return url
    
    def deleteButtons(self):
        # KUrlNavigatorPrivate
        for button in self._navButtons_:
            button.hide()
            buttton.deleteLater()
            
        self._navButtons_.clear()
    
            
    def updateContent(self):
        # KUrlNavigatorPrivate  
        currentUrl = self.locationUrl()
        if self._placesSelector_ is not None:
            self._placesSelector_.updateSelection(currentUrl)
            
        if self._editable_:
            # self._schemes_.hide() # see NOTE: 2023-05-06 22:30:13
            self._dropDownButton_.hide()
            
            self.deleteButtons() # clear the breadcrumbs
            
            self._toggleEditableMode_.setsizePolicy(QtWidgets.QSizePolicy.Fixed,
                                                    QtWidgets.QSizePolicy.Preferred)
            self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                               QtWidgets.QSizePolicy.Fixed)
            
            self._pathBox_.show()
            self._pathBox_.setUrl(currentUrl)
            
        else:
            self._pathBox_.hide()
            # self._schemes_.hide() # see NOTE: 2023-05-06 22:30:13
            self._toggleEditableMode_.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                    QtWidgets.QSizePolicy.Preferred)
            
            self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                               QtWidgets.QSizePolicy.Fixed)
            
            placeUrl = QtCore.QUrl()
            if self._placesSelector_ is not None and not self._showFullPath_:
                placeUrl = self._placesSelector_.selectedPlaceUrl()
                
            if not placeUrl.isValid():
                placeUrl = self.retrievePlaceUrl()
                
            placePath = trailingSlashRemoved(placeUrl.path())
            
            startIndex = placePath.count('/')
            
            self.updateButtons(startIndex)
            
    def updateButtons(self, startIndex:int): # NOTE: 2023-05-08 11:05:23
        # KUrlNavigatorPrivate  
        currentUrl = self.locationUrl()
        if not currentUrl.isValid():
            return
        
        path = currentUrl.path()
        
        oldButtonCount = len(self._navButtons_)
        
        ndx = startIndex
        
        hasNext = True
        
        while hasNext:
            createButton = ((ndx - startIndex) >= oldButtonCount)
            isFirstButton = (ndx == startIndex)
            
            pathParts = pathlib.Path(path).parts
            if ndx >= len(pathParts) - 1:
                hasNext = False
                break
            
            dirName = pathParts[ndx]
            
            hasNext = isFirstButton or len(dirName) > 0
            
            if hasNext:
                button = None
                if createButton:
                    button = NavigatorButton(self.buttonUrl(ndx), self)
                    button.installEventFilter(self)
                    button.setForegroundRole(QtGui.QPalette.WindowText)
                    button.urlsDroppedOnNavButton.connect(self._slot_dropUrls) # CMT: wraps to dropUrls
                    button.navigatorButtonActivated.connect(self._slot_navigatorButtonActivated)
                    button.finishedTextResolving.connect(self.updateButtonVisibility)
                    
                    self.appendWidget(button)
                    
                else:
                    button = self._navButtons_[ndx-startIndex]
                    button.setUrl(self.buttonUrl(ndx))
                    
                if isFirstButton:
                    button.setText(self.firstButtonText())
                    
                button.setActive(self.isActive())
                
                if createButton:
                    if not isFirstButton:
                        self.setTabOrder(self._navButtons_[-1], button)
                        
                    self._navButtons_.append(button)
                    
            ndx += 1
            
            button.setActiveSubDirectory(pathParts[ndx])
        
            if not hasNext:
                break
            
        newButtonCount = ndx - startIndex
        
        if newButtonCount < oldButtonCount:
            for button in self._navButtons_[newButtonCount:]:
                button.hide()
                button.deleteLater()
                
            self._navButtons_ = self._navButtons_[:newButtonCount]
            
        self.setTabOrder(self._dropDownButton_, self._navButtons_[0])
        self.setTabOrder(self._navButtons_[-1], self._toggleEditableMode_)
        
        self.updateButtonVisibility()
            
    def updateButtonVisibility(self):
        # KUrlNavigatorPrivate
        if self._editable_:
            return
        
        buttonsCount = len(self._navButtons_)
        if buttonsCount == 0:
            self._dropDownButton_.hide()
            return
        
        availableWidth = self.width() - self._toggleEditableMode_.minimumWidth()
        
        if self._placesSelector_ is not None and self._placesSelector_.isVisible():
            availableWidth -= self._placesSelector_.width()
            
        if self._protocols_ is not None and self._protocols_.isVisible():
            availableWidth -= self._protocols_.width()
            
        requiredButtonWidth = sum(int(button.minimumWidth()) for button in self._navButtons_)
        
        if requiredButtonWidth > availableWidth:
            availableWidth -= self._dropDownButton_.width()
            
        # Hide buttons ...
        isLastButton = True
        hasHiddenButtons = False
        
        buttonsToShow = list()
        
        for button in self._navButtons_:
            availableWidth -= button.minimumWidth()
            if availableWidth <= 0 and not isLastButton:
                button.hide()
                hasHiddenButtons = True
                
            else:
                buttonsToShow.append(button)
                
            isLastButton = False
            
        for button in buttonsToShow:
            button.show()
            
        if hasHiddenButtons:
            self._dropDownButton_.show()
            
        else:
            url = self._navButtons_[0].url()
            
            visible = (not url.matches(upUrl(url), QtCore.QUrl.StripTrailingSlash)) and url.scheme() not in ("baloosearch", "filenamesearch")
            self._dropDownButton_.setVibisle(visible)
            
    def firstButtonText(self):
        # KUrlNavigatorPrivate
        text = ""
        
        if self._placesSelector_ is not None and not self._showFullPath_:
            text = self._placesSelector_.selectedPlaceText()
            
        currentUrl = self.locationUrl()
        
        if len(text) == 0:
            if currentUrl.isLocalFile():
                if sys.platform == "win32":
                    text = currentUrl.path()[:2] if len(currentUrl.path()) > 1 else QtCore.QDir.rootPath()
                else:
                    text = "/"
                    
        if len(text) == 0:
            if len(currentUrl.path()) == 0 or currentUrl.path() == '/':
                query = QtCore.QUrlQuery(currentUrl)
                text = query.queryItemValue("title")
                
        if len(text) == 0:
            text = currentUrl.scheme() + ':'
            if len(currentUrl.host()) > 0:
                text += " " + currentUrl.host()
        
        return  text
    
    # ### END KUrlNavigatorPrivate API
    
    def showFullPath(self):
        return self._showFullPath_
    
    def setShowFullPath(self, show:bool):
        if self._showFullPath_ != show:
            self._showFullPath_ = show
            self.updateContent()
            
    def setUrlEditable(self, editable:bool):
        if self._editable_ != editable:
            self.switchView(editable)
            
    def isUrlEditable(self):
        return self._editable_
    
    def locationUrl(self, historyIndex:int = -1):
        return self._urlNavigator_.locationUrl(historyIndex)
    
    @safeWrapper
    def saveLocationState(self, state):
        currentState = self._urlNavigator_.locationState()
        self._urlNavigator_.saveLocationState(currentState)
        
    @safeWrapper
    def locationState(self, historyIndex:int = -1):
        return self._urlNavigator_.locationState(historyIndex)
        
        
    def goBack(self):
        return self._urlNavigator_.goBack()
    
    def goForward(self):
        return self._urlNavigator_.goForward()
    
    def goUp(self):
        return self._urlNavigator_.goUp()
    
    def goHome(self):
        if self._homeUrl_.isEmpty() or not self._homeUrl_.isValid():
            self.setLocationUrl(QtCore.QUrl.fromLocalFile(QtCore.QDir.homePath()))
        else:
            self.setLocationUrl(self._homeUrl_)
            
    def setHomeUrl(self, url:QtCore.QUrl):
        self._homeUrl_ = url
        
    def homeUrl(self):
        return self._homeUrl_
    
    def setActive(self, active:bool):
        if active != self._active_:
            self._active_ = active
            
            self._dropDownButton_.setActive(active)
            
            for button in self._navButtons_:
                button.setActive(active)
                
            self.update()
            
            if active:
                self.activated.emit()
                
    def isActive(self):
        return self._active_
    
    def setPlacesSelectorVisible(self, visible:bool):
        if visible == self._showPlacesSelector_:
            return
        
        if visible and self._placesSelector_ is None:
            # places selector is None when no places model is available
            return
        
        self._showPlacesSelector_ = visible
        self._placesSelector_.setVisible(visible)
        
    def isPlacesSelectorVisible(self):
        return self._showPlacesSelector_
    
    def uncommittedUrl(self):
        pass # TODO/FIXME implement KUriFilter functionality
    
    def keyPressEvent(self, evt:QtGui.QKeyEvent):
        if self.isUrlEditable() and evt.key() == QtCore.Qt.Key_Escape:
            self.setUrlEditable(False)
            
        else:
            super().keyPressEvent(evt)
            
    def keyReleaseEvent(self, evt:QtGui.QKeyEvent):
        super().keyReleaseEvent(evt)
        
    def mousePressEvent(self, evt:QtGui.QMouseEvent):
        if evt.button() == QtCore.Qt.MiddleButton:
            self.requestActivation()
            
        super().mousePressEvent(evt)
        
    def mouseReleaseEvent(self, evt:QtGui.QMouseEvent):
        if evt.button() == QtCore.Qt.MiddleButton:
            bounds = self._toggleEditableMode_.geometry()
            if bounds.contains(evt.pos()):
                clipboard = QtWidgets.QApplication.clipboard()
                mimeData = clipboard.mimeData()
                if mimeData.hasText():
                    text = mimeData.text()
                    self.setLocationUrl(QtCore.QUrl.fromUserInput(text))
                    
        super().mouseReleaseEvent(evt)
        
    def resizeEvent(self, evt:QtGui.QResizeEvent):
        QtCore.QTimer.singleShot(0, self.updateButtonVisibility)
        
        super().resizeEvent(evt)
        
    def wheelEvent(self, evt:QtGui.QWheelEvent):
        self.setActive(True)
        super().wheelEvent(evt)
        
    def eventFilter(self, watched:QtCore.QObject, evt:QtCore.QEvent):
        eType = evt.type()
        
        if eType == QtCore.QEvent.FocusIn:
            if watched == self._pathBox_:
                self.requestActivation()
                self.setFocus()
                
            for button in self._navButtons_:
                button.setShowMnemonic(True)
                
        elif eType == QtCore.QEvent.FocusOut:
            for button in self._navButtons_:
                button.setShowMnemonic(False)
                
        return super().eventFilter(watched, evt)
    
    def historySize(self):
        return self._urlNavigator_.historySize()
    
    def historyIndex(self):
        return self._urlNavigator_.historyIndex()
    
    def editor(self):
        return self._pathBox_
    
    def setCustomProtocols(self, protocols:typing.List[str]):
        self._customProtocols_[:] = [protocols]
        # self._protocols_.setCustomProtocols(self._customProtocols_) # TODO/FIXME
        
    def customProtocols(self):
        return self._customProtocols_
    
    def dropWidget(self):
        return self._dropWidget_
    
    def setShowHiddenFolders(self, showHiddenFolders:bool):
        self._subfolderOptions_.showHidden = showHiddenFolders
        
    def setSortHiddenFoldersLast(self, sortHiddenFoldersLast:bool):
        self._subfolderOptions_.sortHiddenLast = sortHiddenFoldersLast
        
    def sortHiddenFoldersLast(self):
        return self._subfolderOptions_.sortHiddenLast
        
    
    # ### BEGIN KUrlNavigatorPrivate slots
    
    @pyqtSlot(QtCore.QPoint)
    def openContextMenu(self, p:QtCore.Qpoint):
        """Navigator's context menu
        Allows 
        • copy/paste of path, 
        • switching between edit mode and breadcrumb navigation mode, 
        • show path in full, or in places-reduced style (when in breadcrumb 
            navigation mode)
        """
        # KUrlNavigatorPrivate
        self.setActive(True)
        popup = QtWidgets.QMenu(self)
        
        copyAction = popup.addAction(QtGui.QIcon.fromTheme("edit-copy"), "Copy")
        
        pasteAction = popup.addAction(QtGui.QIcon.fromTheme("edit-paste"), "Paste")
        
        clipboard = QtWidgets.QApplication.clipboard()
        pasteAction.setEnabled(len(clipboard.text())> 0)
        
        popup.addSeparator()
        
        isWindowSignal = self.isSignalConnected(self.newWindowRequested)
        
        if isWindowSignal:
            for button in self._navButtons_:
                if button.geometry().contains(p):
                    url = button.url()
                    text = button.text()
                    
                    openInWindow = popup.addAction(QtGui.QIcon.fromTheme("window-new"), f"Open {text} in the system's file manager")
                    openInWindow.setData(url)
                    openInWindow.triggered.connect(self._slot_newWindowRequested_) # indirectly connects to signal newWindowRequested
                    
        editAction = popup.addAction("Edit")
        editAction.setCheckable(True)
        
        navigateAction = popup.addAction("Navigate")
        navigateAction.setCheckable(True)
        
        modeGroup = QtWidgets.QActionGroup(popup)
        modeGroup.addAction(editAction)
        modeGroup.addAction(navigateAction)
        
        if self.isUrlEditable():
            editAction.setChecked(True)
        else:
            navigateAction.setChecked(True)
            
        popup.addSeparator()
        
        showFullPathAction = popup.addAction("Show Full Path")
        showFullPathAction.setcheckable(True)
        showFullPathAction.setChecked(self.showFullPath())
        
        activatedAction = popup.exec(QtGui.QCursor.pos())
        
        if activatedAction  == copyAction:
            mimeData = QtCore.QMimeData()
            mimeData.setText(self.locationUrl().toDisplayString(QtCore.QUrl.PreferLocalFile))
            clipboard.setMimeData(mimeData)
            
        elif activatedAction == pasteAction:
            self.setLocationUrl(QtCore.QUrl.fromUserInput(clipboard.text()))
            
        elif activatedAction == editAction:
            self.setUrlEditable(True)
            
        elif activatedAction == navigateAction:
            self.setUrlEditable(False)
            
        elif activatedAction == showFullPathAction:
            self.setShowFullPath(showFullPathAction.isChecked())
            
            
        if popup is not None:
            popup.deleteLater()
            
    @pyqtSlot()
    def openPathSelectorMenu(self):
        # KUrlNavigatorPrivate
        if len(self._navButtons_) == 0:
            return
        
        firstVisibleUrl = self._navButtons_[0].url()
        
        spacer = ""
        
        dirName = ""
        
        popup = QtWidgets.QMenu(self)
        
        popupFilter = NavigatorPathSelectorEventFilter(popup)
        popupFilter.tabRequested.connect(self.tabRequested)
        popup.installEventFilter(popupFilter)
        
        placeUrl = self.retrievePlaceUrl()
        
        ndx = placeUrl.path().count('/')
        
        path = self._urlNavigator_.locationUrl(self._urlNavigator_.historyIndex()).path()
        pathParts = pathlib.Path(path).parts
        if ndx < len(pathParts):
            dirName = pathParts[ndx]
            
        if len(dirName) == 0:
            if placeUrl.isLocalFile():
                dirName = "/"
            else:
                dirName = placeUrl.toDisplayString()
                
        while len(dirName) > 0:
            text = spacer + dirName
            action = QtWidgets.QAction(text, popup)
            currentUrl = self.buttonUrl(ndx)
            
            if currentUrl == firstVisibleUrl:
                popup.addSeparator()
                
            action.setData(currentUrl.toString())
            ndx += 1
            
            spacer == "  "
            dirName = pathlib.Path(path).parts[ndx]
            
        pos = self.mapToGlobal(self._dropDownButton_.geometry().bottomRight())
        activatedAction = popup.exec(pos)
        if activatedAction is not None:
            url = QtCore.QUrl(activatedAction.data().toString())
            self.setLocationUrl(url)
            
        if popup is not None:
            popup.deleteLater() 
            
    @pyqtSlot(QtCore.QUrl, QtCore.Qt.MouseButton, QtCore.Qt.KeyboardModifiers)
    def slotNavigatorButtonClicked(self, url:QtCore.QUrl, button:QtCore.Qt.MouseButton, modifiers:QtCore.Qt.KeyboardModifiers):
        # KUrlNavigatorPrivate
        if ((button & QtCore.Qt.MiddleButton) and (modifiers & QtCore.Qt.ShiftModifier)) or ((button & QtCore.Qt.LeftButton) and (modifiers & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier))):
            self.activeTabRequested.emit(url) # TODO: to trigger navigation in MainWindow
            
        # NOTE: 2023-05-07 22:02:07
        # file system viewer does not support tabs
        # elif (button & QtCore.Qt.MiddleButton) or ((button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ControlModifier)):
        #     self.tabRequested.emit(url)
        #    
        # elif (button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ShiftModifier):
        #     self.newWindowRequested.emit(url)
            
        elif ((button & QtCore.Qt.MiddleButton) or ((button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ControlModifier)) or ((button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ShiftModifier)))
            self.newWindowRequested.emit(url)
            
        elif (button & QtCore.Qt.LeftButton):
            self.setLocationUrl(url)
    
    @pyqtSlot(bool)
    def slotTogleEditableButtonToggled(self, editable:bool):
        # KUrlNavigatorPrivate
        if self._editable_:
            self.applyUncommittedUrl()
            
        self.switchView(editable)
        
    @pyqtSlot(str)
    def slotPathBoxChanged(self, text:str):
        """
        This slot only deals with the situation where a scheme needs changing
        """
        # KUrlNavigatorPrivate
        if len(text) == 0:
            # NOTE: 2023-05-07 22:45:45
            # in the KIO framework this would trigger a selection of scheme from
            # the available schemes (e.g., from file:/ to desktop:/, or any other
            # scheme supported by the installed KDE frameworks plugins)
            #
            # scheme = self.locationUrl().scheme()
            # if len(self._supportedSchemes_) != 1:
            #     self._schemes_.show()
            #
            # This is outside Scipyen's scope therefore it is safe to restore
            # the current url here (for now).
            #
            # See also NOTE: 2023-05-06 22:30:13
            #
            # FIXME/TODO: 2023-05-07 22:52:54
            # the line editor of the url combo box will eventually contain 
            # editing tool buttons for example, to remove current text from
            # navigation history - in this case we DO NOT want to restore 
            # current url, but the next available one in the history.
            signalBlocker = QtCore.QSignalBlocker(self._pathBox_)
            url = QtCore.QUrl(os.path.getcwd())
            self.setLocationUrl(url)
            return
        # else:
            # self._schemes_.hide() # see NOTE: 2023-05-06 22:30:13
        
    @pyqtSlot(QtCore.QUrl)
    def slotApplyUrl(self, url:QtCore.QUrl):
        # KUrlNavigatorPrivate
        if not url.isEmpty() and len(url.path()) == 0:
            url.setPath("/")
            
        urlStr = url.toString()
        
        urls = [u for u in self._pathBox_.urls() if u != urlStr]
        urls.insert(0, urlStr)
        
        self.setLocationUrl(url)
        self._pathBox_.setUrl(self.locationUrl())
        
    @pyqtSlot(str)
    def slotCheckFilters(self, text:str):
        # KUrlNavigatorPrivate
        # TODO 2023-05-06 22:53:38
        # KIO used KUriFilterData
        # need to figure out what this does and replace with simpler pythonic code
        #
        # for now, just return False (i.e. not wasFiltered)
        return False
    
    @pyqtSlot()
    def slotReturnPressed(self):
        # KUrlNavigatorPrivate
        self.applyUncommittedUrl()
        self.returnPressed.emit()
        
        if QtWidgets.QApplication.KeyboardModifiers() & QtCore.Qt.ControlModifier:
            self.switchToBreadcrumbMode()
            
    
    # ### END KUrlNavigatorPrivate slots
    
    # ### BEGIN Slots
    @pyqtSlot(QtCore.QUrl, QtGui.QDropEvent) # CMT
    def _slot_dropUrls(self, url:QtCore.QUrl, evt:QtGui.QDropEvent):
        button = self.sender()
        if isinstance(button, NavigatorButton):
            self.dropUrls(url, evt, button)
            
    @pyqtSlot(QtCore.QUrl, QtCore.Qt.KeyboardModifiers)
    def _slot_navigatorButtonActivated(self, url:QtCore.QUrl, modifiers:QtCore.Qt.KeyboardModifiers):
        # button = self.sender()
        btn = QtWidgets.QApplication.mouseButtons()
        
        self.slotNavigatorButtonClicked(url, btn, modifiers)
        
    # @pyqtSlot(str)
    # def slotProtocolChanged(self, protocol:str):
    #     pass # TODO
    
    @pyqtSlot()
    def _slot_newWindowRequested_(self):
        action = self.sender()
        url = QtCore.QUrl(action.data().toString())
        if url.isValid():
            self.newWindowRequested.emit(url)
    
    @pyqtSlot(QtCore.QUrl)
    def setLocationUrl(self, url:QtCore.QUrl):
        self._urlNavigator_.setCurrentLocationUrl(url)
        self.updateContent()
        self.requestActivation()
    
    @pyqtSlot()
    def requestActivation(self):
        self.setActive(True)
    
    @pyqtSlot()
    def setFocus(self):
        if self.isUrlEditable():
            self._pathBox_.setFocus()
        else:
            super().setFocus()
    
#     @pyqtSlot(QtCore.QUrl)
#     def setUrl(self, url:QtCore.QUrl):
#         pass # TODO DEPRECATED
#     
#     @pyqtSlot(QtCore.QUrl)
#     def saveRootUrl(self, url:QtCore.QUrl):
#         pass # TODO DEPRECATED
#     
#     @pyqtSlot(int, int)
#     def savePosition(self, x:int, y:int):
#         pass # TODO DEPRECATED
    
    @pyqtSlot()
    def _slot_urlNavigatorUrlChanged(self):
        self.urlChanged.emit(self._urlNavigator_.currentLocationUrl)
        
    @pyqtSlot(QtCore.QUrl)
    def _slot_urlNavigatorUrlAboutToBeChanged(self, url):
        self.urlAboutToBeChanged.emit(url)
    
    @pyqtSlot(str)
    def slotSchemeChanged(self, scheme:str):
        # TODO ?!?
        pass
        
    
    # ### END Slots

   
        
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
