# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# TODO 2025-02-05 14:49:07
# when show full path is OFF show places panel (prepend to the navigator buttons)
# hide when show full path is ON
# -- make this an option (checkable menu item) & and Gui configurable one
# -- aslo make showing full path a configurable option

# BUG 2025-02-05 14:50:50 FIXME - FIXED see NOTE: 2025-02-05 15:06:38
# toggling show full path to ON shows only the crumb for the root file system 
# instead of creating the full array of crumbs (yet when editing, the correc
# path is shown); toggling back to OFF reverts to the expected behaviour
#


"""
About special protocols (KIO slaves) in KDE:
NOTE: A list of available protocols can be seen in KDE gui via the Dolphin file
manager open a Dolphin window, click in the navigator bar to show is as an 
editable field, then clear the field ⇒ the leftmost dropdown menu that appears
before the (now empty) editable field shows the protocols available on YOUR system 

On my machine :
    Operating System: openSUSE Tumbleweed 20241226
    KDE Plasma Version: 6.2.4
    KDE Frameworks Version: 6.9.0
    Qt Version: 6.8.1
    Kernel Version: 6.12.6-1-default (64-bit)
    Graphics Platform: Wayland

these protocol are as follows (<sep> is a menu separator): 

file - file system navigation
fish - file system navigation (possibly remote) over ssh
ftp - 
sftp - "secure" ftp"
smb - "samba" (i.e. Windows "network")
webdav 
<sep> 
desktop - navigates to the platform specific "Desktop" - NB this may be an actual
            file system directory e.g. ~/Desktop or a virtual folder (Windows)
fonts - two virtual folders - collect fonts installed in the user account or machine-wide
    fonts:/Personal
    fonts:/System
programs - the virtual folder of all applications installed
    on Linux with XDG-compliant desktops, programs:/ contains the full application menu
        and its submenus; the "files" are the *.desktop files (application launchers)
trash - the "Wastebin" - should point to the same file "recycling" system on XDG-compliant desktops
        (KDE, GNOME, XFCE, COSMIC and variants) - virtual folder (trash:/)
        NB this is supported by an actual file system directory (e.g. ~/.local/share/Trash)
        the contents of which shuold not be directly accessible, and containing three objects: "files" - a directory of trashed filw system items;
        "info" - a directory with *.trashinfo files; "directorysizes"
        

<sep>
Devices has a submenu as it may be served by more than one protocol (unlike fonts:/)
    On this machine it provides
        camera:/
        remote:/ - the "Network" virtual folder i, ncluding all network links that are
            configured on the machin. (NB these are NOT the same things as network connections,
            but are defined via "desktop" files and when executed instantiate various
            network protocols listed above, (e.g. smb, ftp, fish) as well as any of
            the protocols listed under "Other" (e.g., recoll:/, buetooth:/, etc), see
            below
Other
    a collection of "KIO slaves" - depends on what has been installed - one entry for each, e.g. 
    activities:/ (KDE only)
    afc:/ (Apple devices)
    akonadi:/ (KDE only)
    aplications:/ - the same as programs:/ (see above)
    ar:/, sevenz:/ tar:/ zip:/ - protocols for opening archive files as a folder (sevenz = 7zip)
    audiocd:/ videodvd:/ - protocols for accessing media (audio CD, video disks, DVD)
    baloosearch:/ (KDE only)
    bluetooth:/ - virtual folder with the configured blutetooth connections
    bup:/ -- ?
    cifs:/ - virtual folder with configured printers (Linux only, and only when using CIFS)
    mtp:/ - virtual folder with configured connections using the MTP protocol (media transfer protocol)
        i.e. mp3 players, cell (smart) phones
    dav:/, davs:/
    filenamesearch:/ 
    gdrive:/ - virtual folder with the configured connections to your google drive accounts
    kdeconnect:/ (KDE only) - virtual folder with connection to Android phones and tablets
    ldap:/, ldaps:/ - virtual folders -- lightweight directory access protocol
    man:/ - virtual folder with unix manual pages (KDE only, as it is useful only in konqueror)
    obexftp:/ -- file transfer over bluetooth (OBject EXchange)
    perldoc:/ (PERL documentation ?)
    recentlyused:/ (KDE only ?) -- virtual folder with the history of file system navigation inlcuding opened files
        only useful in KDE as it relies on the applcation to align with KDE philosophy & frameworks
    tags:/ virtual folder with defines file tags (UNIX/Linux only, and it depends on the file system used 
        e.g. btrfs, xfs, etc)
    timeline:/ - variant of recentlyused - virtual folder organized by calendar - see recentlyused:/
    webdavs:/ 
    zeroconf:/ (zero configration networking - never used this - Linux only, I guess)
    
Which of these are useful to implement in Scipyen?

file - definitely
desktop - maybe (as in "should"), gives quick access to "that" place in a platform compliant way
trash - maye (as in potentially useful, but only if Scipyen's file manager allows removing and restoring files,
    which would mean implementing file operations -- currently, Scipyen's file manager is read-only,
    although objects can be written to files in the current directory)
    The problem with implementing this is that the code will be "tied" to a specific
    set of platforms KDE, GNOME, as I am not sure these are working on Windows or MacOS
fish, smb - maybe, if one wants to access remote machines over TCP/IP or Windows 
    shares, but I won't recommend it
nfs
    
anything else -- definitely NOT!

A potential useful thing would be to implement the "Places" protocol (not really a 
KIO slave protocol but a layer that interfaces with KIO slaves) -- useful to access "bookmarked"
places. At its most basic, it is NOT platform--specific (in fact, it is , but Qt provides
some very basic standardisation here).

Implementation:
a) there would be a lot of code to port - not my cup of tea... - OR
b) use KDE framework - this would "tie" Scipyen into KDE too much:
    TODO: contemplate calling kioclient OR kioclient5 (depends on the XDG_DESKTOP_SESSION)
            /usr/libexec/kf5/kioexec OR
            /usr/libexec/kf6/kioexec
    (filter these out so that they only show for sys.platform.startswith("linux"))




"""

# TODO: 2025-01-09 21:07:03
# Completion -> UrlCompletion


import typing, pathlib, functools, os, itertools, sys, traceback
from functools import singledispatch, singledispatchmethod
from urllib.parse import urlparse, urlsplit
from collections import namedtuple, deque
from dataclasses import MISSING
from enum import Enum, IntEnum
try:
    from qtpy import sip as sip # for sip.cast
    has_sip = True
except:
    has_sip = False
# import sip # for sip.isdeleted() - not used yet, but beware
from traitlets.utils.bunch import Bunch
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg)
from qtpy.QtCore import (Signal, Slot, Property,)
# from qtpy.uic import loadUiType

from core import desktoputils as dutils
from core import qtutils
from iolib.navigation import placesmodel

# NOTE: 2025-01-24 21:25:12 CMT
# to reinstante when PlacesModel/PlacesSelector are finalized
# from iolib.navigation.placesmodel import PlacesModel
from iolib.navigation.protocols import ProtocolInfo # TODO
from core.prog import (safeWrapper, printStyled)
# import gui.pictgui as pgui
from gui import guiutils
from iolib import pictio

# TODO finalize this
# TODO/FIXME: 2023-05-06 23:12:19
# Since this is only intended for use with local file system (i.e. file:// URI 
# protocol) I should use pathlib.Path instead of QtCore.QUrl

# Root > dir > subdir

archiveTypeStr = ("-compress", "arj", "zip", "rar", "zoo", "lha", "cab", "iso")

NetworkProtocols = ("fish", "ftp", "sftp", "smb", "webdav")

Protocols = ("file", )

SpecialProtocols = ("desktop", "trash")

SupportedProtocols = Protocols

ArrowSize = 10

class PlacesModel: pass # NOTE: 2025-01-24 21:26:32 remove this when placesmodel module is finalized

class ListDirsJob(QtCore.QThread):
    sig_entries = Signal(list, name="sig_entries")
    # sig_result = Signal(name="sig_result")
    
    def __init__(self, path:typing.Union[pathlib.Path, QtCore.QUrl, str], showHidden:bool=False,
                 parent:typing.Optional[QtCore.QObject]=None):
        
        if isinstance(path, QtCore.QUrl):
            path = dutils.urlToPath(path)
            # path = pathlib.Path(path.path())
            
        elif isinstance(path, str):
            path = pathlib.Path(path)
        
        if not path.is_absolute():
            p = path.absolute()
        else:
            p = pathlib.Path(path)
        
        if not p.exists():
            raise ValueError(f"Path {path} does not exist")
            
        if not p.is_dir():
            self.path = p.parent
        else:
            self.path = p
            
        self.entries = list() # of pathlib.Path objects
        
        self.showHidden = showHidden is True
        
        QtCore.QThread.__init__(self, parent=parent)
        
    def run(self):
        # print(f"{self.__class__.__name__}.run called; self.path = {self.path}")
        filters = QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot | QtCore.QDir.CaseSensitive
        if self.showHidden:
            filters |= QtCore.QDir.Hidden

        p = self.path.as_posix()

        if sys.platform.startswith("win32"):
            p += "\\"

        # qDir = QtCore.QDir(self.path.as_posix(), "*",
        qDir = QtCore.QDir(p, "*",
                           QtCore.QDir.Name | QtCore.QDir.DirsFirst, filters)
        if sys.platform.startswith("win32"):
            self.entries = list(map(lambda x: pathlib.Path(os.path.join(p, x)), qDir.entryList()))
        else:
            self.entries = list(map(lambda x: self.path / x, qDir.entryList()))
        # print(f"\tentries: {self.entries}")
        self.sig_entries.emit(self.entries)
        
    
class ApplyUrlMethod(IntEnum):
    Apply = 1
    Tab = 2
    ActiveTab = 4
    NewWindow = 8
        

class UrlNavigator: pass # fwd decl

# class LocationData(typing.NamedTuple):
class LocationData:
    """
    Encapsulates location data
    """
    # KCoreUrlNavigator API
    def __init__(self, url:QtCore.QUrl, state:typing.Optional[typing.Any] = None):
        self.url:QtCore.QUrl = url
        self.state:object = state
        # print(f"{self.__class__.__name__}.__init__ url = {self.url}, state = {self.state}")
        
    def __repr__(self):
        return f"LocationData url = {self.url}, state = {self.state}"
    
    def __eq__(self, other:typing.Self):
        # ret = self.url.matches(other.url, QtCore.QUrl.StripTrailingSlash)
        ret = self.hasSameUrl(other)
        
        if ret:
            ret &= self.state == other.state
            
        return ret
    
    def hasSameUrl(self, other:typing.Self):
        return self.url.adjusted(QtCore.QUrl.StripTrailingSlash) == other.url.adjusted(QtCore.QUrl.StripTrailingSlash)
    
class UrlNavigatorData(typing.NamedTuple):
    """
    Encapsulates KCoreUrlNavigator data
    """
    # KUrlNavigator API
    rootUrl: QtCore.QUrl
    pos: QtCore.QPoint
    state: bytes
    
class SubDirInfo(typing.NamedTuple):
    name:str
    displayName:str
        

def getSystemArchiveMimeTypes():# TODO
    mimedb = QtCore.QMimeDatabase()
    types = [m for m in mimedb.allMimeTypes() if any(v in m.name() for v in archiveTypeStr)]
    
    return types

def firstChildUrl(lastUrl:QtCore.QUrl, currentUrl:QtCore.QUrl):
    # NOTE: 2025-01-02 14:53:22
    # TODO consider a more pythonic alernative
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
    
    res = QtCore.QUrl(lastUrl)
    res.setPath(path3)
    return res
    
@singledispatch
def pathToLocation(o:typing.Any, state:typing.Optional[QtCore.QByteArray]=None):
    raise NotImplementedError

@pathToLocation.register(str)
def _(o:str, state:typing.Optional[QtCore.QByteArray]=None) -> LocationData:
    path = pathlib.Path(o)
    return LocationData(QtCore.QUrl(path.as_uri()), state)
    # if path.is_dir() and path.is_absolute():
    #     return LocationData(QtCore.QUrl(path.as_uri()), state)
    # else:
    #     raise ValueError(f"{o} is not an absolute path to existing directory")
    
@pathToLocation.register(pathlib.Path)
def _(o:pathlib.Path, state:typing.Optional[QtCore.QByteArray]=None) -> LocationData:
    return LocationData(QtCore.QUrl(path.as_uri()), state)
    # if o.is_dir() and o.is_absolute():
    #     return LocationData(QtCore.QUrl(path.as_uri()), state)
    # else:
    #     raise ValueError(f"{o} is not an absolute path to existing directory")

@pathToLocation.register(QtCore.QUrl)
def _(o:QtCore.QUrl, state:typing.Optional[QtCore.QByteArray]=None) -> LocationData:
    # if not url.isLocalFile() or url.isRelative() or not pathlib.Path(o.path()).is_dir():
    #     raise ValueError(f"{o} is not an absolute path to existing directory")
    
    return LocationData(o, state)
    
def findProtocol(protocol:str):
    assert len(protocol) > 0
    assert ':' in protocol
    
def isAbsoluteLocalPath(path:str):
    if path.startswith(':'):
        return False
    plpath = pathlib.Path(path)
    return plpath.is_absolute()
    # NOTE: 2023-05-08 17:49:03 use pathlib
    # return not path.startswith(':') and QtCore.QDir.isAbsolutePath(path)

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
    # if sys.platform.startswith("win32"):
    #     if path.startswith("/"):
    #         path = path[1:]
    return path

def appendSlashToPath(url:QtCore.QUrl):
    path = url.path()
    if len(path) and not path.endswith('/'):
        path = appendSlash(path)
        url.setPath(path)
        
    return url

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
    if not url.isValid() or url.isRelative():
        return QtCore.QUrl()
    
    u = QtCore.QUrl(url)
    
    if url.hasQuery():
        u.setQuery("")
        return u
    
    if url.hasFragment():
        u.setFragment("")
#         
#     if url.isRelative():
#         u = QtCore.QUrl(upPath(pathlib.Path(u.path())).as_posix())
    
    return u.adjusted(QtCore.QUrl.StripTrailingSlash).adjusted(QtCore.QUrl.RemoveFilename)
    
    # return u.adjusted(QtCore.QUrl.RemoveFilename)

def upPath(path:pathlib.Path) -> pathlib.Path:
    # NOTE: 2024-12-30 19:36:35
    # this below would resolve the current path - not what I want
    # # if not path.is_absolute():
    # #     return path.parent.absolute()
    
    # in reality I want to resolve the parent path (i.e. the ".." in "../somepath")
    # therefore see the False branch below
    if path.is_absolute():
        return pathlib.Path(path.parent)
    else:
        p = pathlib.Path("..") / path
        return p.parent.absolute()
    
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
    """Implementation of KIO KUrlComboBox"""
    # TODO/FIXME: 2025-01-20 22:48:00
    # finalize completer - currently not working
    # TODO/FIXME: 2025-01-21 23:27:58
    # finalize merging with recent directories from ScipyenWindow - currently not working
    # see attempts at:
    # NOTE/FIXME 2025-01-21 23:28:51 TODO
    urlActivated = Signal(QtCore.QUrl, name="urlActivated")
    returnPressed = Signal(name="returnPressed")
    
    def __init__(self, mode:UrlComboMode, rw:typing.Optional[bool]=False, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent)
        
        self._completer_ = QtWidgets.QCompleter(self)
        self._completer_.setModel(QtWidgets.QFileSystemModel(self._completer_))
        self._completer_.setModelSorting(QtWidgets.QCompleter.CaseSensitivelySortedModel)
        self._completer_.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        
        self.setEditable(rw==True)
        self.lineEdit().setCompleter(self._completer_)
        self.lineEdit().setClearButtonEnabled(True)
        self.lineEdit().undoAvailable=True
        self.lineEdit().redoAvailable=True
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
            # if u.isEmpty():
            if len(u)==0:
                continue
            
            if isAbsoluteLocalPath(u):
                uu = QtCore.QUrl.fromLocalFile(u)
            else:
                uu.setUrl(u)
                
            if uu.isLocalFile() and not QtCore.QFile.exists(uu.toLocalFile()):
                continue
            
            icon = self.getIcon(uu)
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
            # if urlToInsert == v.toString(QtCore.QUrl.StripTrailingSlash):
            # WARNING: 2025-01-19 20:20:46
            # v is a UrlComboItem huich , here is a namedtuple
            if urlToInsert == v.url.toString(QtCore.QUrl.StripTrailingSlash):
                # self.setCurrentItem(k)
                self.setCurrentIndex(k) # NOTE: 2025-01-19 20:22:50 self inherits QComboBox !!!
                
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
            
    @Slot(int)
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
                                                                     comboOpt,
                                                                     # None,
                                                                     QtWidgets.QStyle.SC_ComboBoxEditField,
                                                                     self)).x()
        frameWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth,
                                              comboOpt, self)
        
        if evt.x() < (x0 + 16 + frameWidth):
            self._dragPoint_ = evt.pos()
        else:
            self._dragPoint_ = QtCore.QPoint()
            
        super().mousePressEvent(evt)
        
    def keyPressEvent(self, evt:QtGui.QKeyEvent):
        if evt.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.returnPressed.emit()
        evt.accept()
        super().keyPressEvent(evt)
        
        
    def mouseMoveEvent(self, evt:QtGui.QMouseEvent):
        ndx = self.currentIndex()
        item = self.itemMapper.get(ndx, None)
        
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
            
        super().mouseMoveEvent(evt)
                        
    # TODO/FIXME ? see TODO 2025-01-09 21:05:56
    # def setCompletionObject(self, compObj:QtWidgets.QCompleter, hsig:bool):
    #     compObj.setModelSorting(QtWidgets.QCompleter.CaseSensitivelySortedModel)
                    
class UrlNavigatorMenu(QtWidgets.QMenu):
    sig_urlDropped = Signal(QtWidgets.QAction, QtGui.QDropEvent, 
                            name="sig_urlDropped")
    mouseButtonClicked = Signal(QtWidgets.QAction, QtCore.Qt.MouseButton, 
                                    name="mouseButtonClicked")
    def __init__(self, title:typing.Optional[str] = None, parent:typing.Optional[QtWidgets.QWidget] = None):
        if isinstance(title, QtWidgets.QWidget):
            parent = title
            title = None
        if isinstance(title, str):
            super().__init__(title, parent)
        else:
            assert(isinstance(parent, (QtWidgets.QWidget, type(None))))
            super().__init__(parent=parent)
        self._initialMousePosition = QtGui.QCursor.pos()
        self._mouseMoved_ = False
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        
    def dragEnterEvent(self, evt:QtGui.QDragEnterEvent):
        if evt.mimeData().hasUrls():
            evt.acceptProposedAction()
    
    def dragMoveEvent(self, evt:QtGui.QDragMoveEvent):
        eventPosition = evt.position()
        globalEventPosition = self.mapToGlobal(eventPosition)
        newEvt = QtGui.QMouseEvent(QtGui.QMouseEvent(QtCore.QEvent.MouseMove, 
                                                     eventPosition, globalEventPosition,
                                                     QtCore.Qt.LeftButton, 
                                                     evt.button(), 
                                                     evt.modifiers()))
        
        self.mouseMoveEvent(newEvt)
    
    def dropEvent(self, evt:QtGui.QDropEvent):
        action = self.actionAt(evt.position().toPoint())
        if action is not None:
            self.sig_urlDropped.emit(action, evt)
    
    def mouseMoveEvent(self, evt:QtGui.QMouseEvent):
        if not self._mouseMoved_:
            moveDistance = self.mapToGlobal(evt.pos()) - self._initialMousePosition
            self._mouseMoved_ = moveDistance.manhattanLength() >= QtWidgets.QApplication.startDragDistance()
            
        if self._mouseMoved_:
            super().mouseMoveEvent(evt)
    
    def mouseReleaseEvent(self, evt:QtGui.QMouseEvent):
        btn = evt.button()
        
        if self._mouseMoved_ or btn != QtCore.Qt.LeftButton:
            action = self.actionAt(evt.pos())
            if action is not None:
                self.mouseButtonClicked.emit(action, btn)
                self.setActiveAction(None)
                
            super().mouseReleaseEvent(evt)
            
        self._mouseMoved_ = True
        
class UrlNavigatorButtonBase(QtWidgets.QPushButton):
    """Common ancestor for breadcrumbs buttons
    """
    BorderWidth = 2
    
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent)
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
            self.pressed.connect(parent.requestActivation)
            
    def setActive(self, value:bool):
        if self._active_ != value:
            self._active_ = value is True
            self.update()
            
    def isActive(self):
        return self._active_
    
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

class UrlNavigatorToggleButton(UrlNavigatorButtonBase):
    _iconSize_ = 16
    def __init__(self, parent:UrlNavigator=None):
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
                self._pixmap_ = QtGui.QIcon.fromTheme("dialog-ok").pixmap(QtCore.QSize(self._iconSize_, self._iconSize_).expandedTo(self.iconSize()))
                
            self.style().drawItemPixmap(painter, self.rect(), QtCore.Qt.AlignCenter, self._pixmap_)
            
        elif self.isDisplayHintEnabled(DisplayHint.EnteredHint):
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(self.palette().color(self.foregroundRole()))
            
            verticalGap = 4
            caretWidth = 2
            x = 0 if self.layoutDirection() == QtCore.Qt.LeftToRight else buttonWidth - caretWidth
            
            painter.drawRect(x, verticalGap, caretWidth, buttonHeight - 2 * verticalGap)
    
    @Slot()
    def updateToolTip(self):
        if self.isChecked():
            self.setToolTip("Click for Navigation")
        else:
            self.setToolTip("Click to Edit Location")
    
    @Slot()
    def updateCursor(self):
        if self.isChecked():
            self.setCursor(QtCore.Qt.ArrowCursor)
        else:
            self.setCursor(QtCore.Qt.IBeamCursor)

class UrlNavigatorButton(UrlNavigatorButtonBase): 
    # TODO: 2024-12-30 19:01:04 finalise me!
    # FIXME/TODO 2023-05-07 23:34:55 finalize
    navigate = Signal(str, name="navigate")
    urlsDroppedOnNavButton = Signal(QtCore.QUrl, QtGui.QDropEvent, 
                                    name = "urlsDroppedOnNavButton")
    navigatorButtonActivated = Signal(QtCore.QUrl, QtCore.Qt.MouseButton, 
                                      QtCore.Qt.KeyboardModifiers, 
                                      name = "navigatorButtonActivated")
    startedTextResolving = Signal(name = "startedTextResolving")
    finishedTextResolving = Signal(name = "finishedTextResolving")
    _sig_siblingsDone_ = Signal(name="_sig_siblingsDone_")
    
    # def __init__(self, url:typing.Union[QtCore.QUrl, pathlib.Path],
    def __init__(self, url:QtCore.QUrl,
                 model:typing.Optional[QtWidgets.QFileSystemModel] = None,
                 parent:typing.Optional[UrlNavigator]=None):
        super().__init__(parent=parent)
        self._hoverArrow_ = False
        # self._pressed_ = False # NOTE: 2025-01-02 01:20:39 by CMT for use in paintEvent
        self._pendingTextChange_ = False
        self._replaceButton_ = False
        self._showMnemonic_ = False
        self._wheelSteps_:int = 0
        # self._mousePressPos_ = QtCore.QPoint()
        
        self._url_ = None
        self._subDir_ = ""  # NOTE: 2025-01-02 00:21:29 this is to be set, actually,
                            # by code in UrlNavigator
                            # this is set when the navigator button does NOT
                            # show the active directory in the navigator!
                            
        self._subDirsJob_ = None # originally, a KIO::ListJob → here, a QThread
        self._subDirs_ = list() # of SubdirInfo → here, a list of pathlib.Path objects
        self._subDirsMenu_ = None # UrlNavigatorMenu 
        
        self._openSubDirsTimer = QtCore.QTimer(self)
        self._openSubDirsTimer.setSingleShot(True)
        self._openSubDirsTimer.setInterval(1000)
        self._openSubDirsTimer.timeout.connect(self.slot_startSubDirsJob)
        
        self.setAcceptDrops(True)
        self.setUrl(url)
        # self.setUrl(QtCore.QUrl(url.as_uri()) if isinstance(url, pathlib.Path) else url)
        self.setMouseTracking(True)
        
        self.pressed.connect(self.slot_requestSubDirs)
        
        # NOTE: 2023-05-07 23:42:42 
        # use Qt file system model; does away with KIOJob etc (?!?)
        # NOTE: 2024-12-30 19:20:27
        # allow the use of an external file system model (e.g. the one used by 
        # Scipyen's MainWindow)
        if not isinstance(model, QtWidgets.QFileSystemModel):
            self._fileSystemModel_ = QtWidgets.QFileSystemModel(parent=self)
            self._fileSystemModel_.setReadOnly(True)
            self._fileSystemModel_.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.CaseSensitive | QtCore.QDir.NoDotAndDotDot)
            self._fileSystemModel_.setRootPath(self.path().as_posix())
            self._fileSystemModelIndex_ = self._fileSystemModel_.index(self._fileSystemModel_.rootPath())
        else:
            self._fileSystemModel_ = model
            self._fileSystemModelIndex_ = self._fileSystemModel_.index(self.path.as_posix())
# # 
# #         # self.frameStyleOptions = QtWidgets.QStyleOptionFrame()
# #         # self.frameStyleOptions.initFrom(self)
# #         # self.frameStyleOptions.
# #         
# #         # ### END CMT 2023-05-08 17:56:23

    # def setUrl(self, url:typing.Union[QtCore.QUrl, pathlib.Path]):
    def setUrl(self, url:QtCore.QUrl):
        # print(f"{self.__class__.__name__}.setUrl({url})")
        self._url_ = url

        # NOTE: 2023-05-08 18:06:14 KIO original
        # protocolBlackList = {"nfs", "fish", "ftp", "sftp", "smb", "webdav", "mtp", "http", "https"}
        
        # protocolBlackList = {"nfs", "fish", "ftp", "sftp", "smb", "webdav", "mtp",
        #                      "http", "https", "man", "info", "gopher", "baloosearch", "filenamesearch", # CMT
        #                      "recoll", "rkward", "remote", "applications", "fonts"} # CMT
        
        # supportedProtocols = {"file", "desktop"}
        
        startTextResolving = self._url_.isValid() and not self._url_.isLocalFile() and self._url_.scheme() in SupportedProtocols
        # startTextResolving = self._url_.isValid() and not self._url_.isLocalFile() and self._url_.scheme() not in SupportedProtocols
        
        if startTextResolving:
            # NOTE: 2024-12-30 17:31:41
            # This branch would be active if KIO was implemented in Scipyen...
            # ... but it is not ...
            raise NotImplementedError(f"Unsupported URI scheme {self._url_.scheme()}")
            # # ### BEGIN
            # # A-ha! whenever the protocol specified by the url scheme is not black-listed,
            # # start aynchronous job to resolve it
            # # indicates:
            # # • internet protocol (http, htpps, )
            # # • special KDE frameworks protocol - WARNING these may be supplied by
            # #  3ʳᵈ party KDE applications via KDE plugins framework (so-called
            # #  KIO slaves); examples include Rkward, Recoll, Clementine, Amarok, etc.
            # #
            # # The 'special' ones are usually in an "Other" submenu
            # # TODO: If going ahead with implementing these in Scipyen:
            # # a) there would be a lot of code to port - not my cup of tea... - OR
            # # b) use KDE framework - this would "tie" Scipyen into KDE too much:
            # #   TODO: contemplate calling kioclient OR kioclient5 (depends on the XDG_DESKTOP_SESSION)
            # #           /usr/libexec/kf5/kioexec OR
            # #           /usr/libexec/kf6/kioexec
            # #   TODO: filter these out so that they only show for sys.platform.startswith("linux")
            # #
            # self._pendingTextChange_ = True
            # # starts a KIO job via 
            # # job = KIO.stat(self._url_, hide progress info)
            # # then connects job.result to self.statFinished
            # # finally, emit self.startedTextResolving
            # # This is for a url that IS NOT local, and , as per KIO original, the scheme
            # # ### END
            
        else:
            # btnText = self._url_.fileName().replace('&', '&&')
            btnPath = dutils.urlToPath(self._url_)
            btnText = btnPath.parts[-1]
            # print(f"\tbtnPath: {btnPath} -> btnText = {btnText}")
            if sys.platform.startswith("win32"):
                pass
            self.setText(btnText)
            # self.setText(self._url_.fileName().replace('&', '&&'))
            
    def url(self) -> QtCore.QUrl:
        return self._url_
    
    def path(self) -> typing.Optional[pathlib.Path]:
        return dutils.urlToPath(self.url()) if self.url().isLocalFile else None
        # return pathlib.Path(self.url().path()) if self.url().isLocalFile else None
        
    def setText(self, text):
        adjustedText = text
        if len(adjustedText) == 0:
            adjustedText = self._url_.scheme()
            
        adjustedText.replace("\n", " ")
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
        if len(self._subDir_) > 0:
            width = int(self.height()/2)
            if width < 4:
                width = 4
        
        return width
    
    def isAboveArrow(self, x:int) -> bool:
        leftToRight = self.layoutDirection() == QtCore.Qt.LeftToRight
        if leftToRight:
            return x >= self.width() - self.arrowWidth()
        else:
            return x < self.arrowWidth()
        
    def setShowMnemonic(self, val:bool):
        val = val is True
        if self._showMnemonic_ != val:
            self._showMnemonic_ = val
            
    def showMnemonic(self) -> bool:
        return self._showMnemonic_
        
    def updateMinimumWidth(self):
        oldMinWidth = self.minimumWidth()
        minWidth = self.sizeHint().width()
        
        if minWidth < 40:
            minWidth = 40
            
        elif minWidth > 150:
            minWidth = 150
            
        if oldMinWidth != minWidth:
            self.setMinimumWidth(minWidth)
            
    def initMenu(self, menu: QtWidgets.QMenu, startIndex:int):
        """Populates the subdirectories menu
        """
        # print(f"{self.__class__.__name__}<{self.plainText()}>.initMenu({menu}, {startIndex})")
        
        # NOTE: 2025-01-21 08:59:29
        # set up menu Signal connections;
        # in Python it is hard to overload a Slot (i.e. define Slots with the same
        # name but diffferent signatures);
        # therefore I need two slots: 
        #   • one for mouse activation of a menu entry (see NOTE: 2025-01-21 09:06:45)
        #   • the other for the activation of a menu entry using the keyboard
        #
        menu.mouseButtonClicked.connect(self.slot_menuActionClicked) # mouse activation of menu entry
        menu.triggered.connect(self.slot_menuActionTriggered) # keybard activation of menu entry
        menu.sig_urlDropped.connect(self.slot_urlsDropped) # drag'ndrop not yet implemented
        menu.setLayoutDirection(QtCore.Qt.LeftToRight)
        
        # NOTE: 2025-01-21 09:01:43
        # allow a maximum og 30 entries per menu; if there are > 30 entries, place
        # them in a submenu (overspill)
        #
        maxIndex = startIndex + 30  # (max 30 items shown in the menu)

        subDirs = sorted(self._subDirs_)

        nSubDirs = len(self._subDirs_)


        # print(f"\tnSubDirs = {nSubDirs}")
        # lastIndex = min(nSubDirs - 1, maxIndex)
        lastIndex = min(nSubDirs, maxIndex)
        
        subDirsNames = list(map(lambda x: x.name, self._subDirs_[startIndex : lastIndex]))
        
        subDirsActions = list(map(lambda x: QtWidgets.QAction(guiutils.csqueeze(x.replace('&', '&&'), 60), self), subDirsNames))

        if self._subDir_ in subDirsNames:
            currentIndex = subDirsNames.index(self._subDir_)
            font = QtGui.QFont(subDirsActions[currentIndex].font())
            font.setBold(True)
            subDirsActions[currentIndex].setFont(font)
            
        for k, i in enumerate(range(startIndex, lastIndex)):
            # NOTE: 2025-01-21 09:04:14
            # action carries <int> data which is the index of the subdirectory 
            # pointed to by this action, in self._subDirs_ !!!
            subDirsActions[k].setData(i) 
            menu.addAction(subDirsActions[k])
            
        if nSubDirs > maxIndex: # NOTE: 2025-01-21 09:03:03 generates the overspill menu
            menu.addSeparator()
            subDirsMenu = UrlNavigatorMenu("More", menu)
            self.initMenu(subDirsMenu, maxIndex)
            menu.addMenu(subDirsMenu)
        
    def paintEvent(self, evt:QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        
        adjustedFont = QtGui.QFont(self.font())
        adjustedFont.setBold(len(self._subDir_) == 0)
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
        
        # if not self.isLeaf:
        if len(self._subDir_) > 0:
            # draws arrow
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
            
            # arrow = QtWidgets.QStyle.PE_IndicatorArrowDown if self._pressed_ else QtWidgets.QStyle.PE_IndicatorArrowRight if leftToRight else QtWidgets.QStyle.PE_IndicatorArrowLeft
            arrow = QtWidgets.QStyle.PE_IndicatorArrowRight if leftToRight else QtWidgets.QStyle.PE_IndicatorArrowLeft
            self.style().drawPrimitive(arrow, option, painter, self)
            
            if not leftToRight:
                textLeft += arrowSize + 2 * self.BorderWidth

            textWidth -= arrowSize + 2 * self.BorderWidth
        
        painter.setPen(fgColor)
        
        clipped = self.isTextClipped()
        # print(f"{self.__class__.__name__}<{self.plainText()}> clipped: {clipped}")
        textRect = QtCore.QRect(textLeft, 0, textWidth, buttonHeight)
        
        if clipped:
            bgColor = QtGui.QColor(fgColor)
            bgColor.setAlpha(0)
            gradient = QtGui.QLinearGradient(textRect.topLeft(), textRect.topRight())
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
        if self._showMnemonic_:
            textFlags |= QtCore.Qt.TextShowMnemonic
            painter.drawText(textRect, textFlags, self.text())
        else:
            painter.drawText(textRect, textFlags, self.plainText())
        
    def enterEvent(self, evt:QtGui.QEnterEvent):
        super().enterEvent(evt)
        # print(f"{self.__class__.__name__}<'{self.plainText()}' sizeHint: {self.sizeHint()}, width: {self.width()}, arrowWidth: {self.arrowWidth()}>.enterEvent : {evt.pos()}")

        if self.isTextClipped():
            self.setToolTip(self.plainText())
            
        # evt.accept()
            
    def leaveEvent(self, evt:QtCore.QEvent):
        # if self.__class__.__name__ == "UrlNavigatorButton":
        #     print(f"{self.__class__.__name__}.enterEvent: {evt.pos()}")
        
        super().leaveEvent(evt)
        
        self.setToolTip("")
        # self.setDisplayHintEnabled(DisplayHint.EnteredHint, False)
        
        if self._hoverArrow_:
            self._hoverArrow_ = False
            self.update()
            
        # self.update()
        # evt.accept()
            
    def keyPressEvent(self, evt:QtGui.QKeyEvent):
        evtKey = evt.key()
        
        if evtKey == QtCore.Qt.Key_Enter:
            pass
        elif evtKey == QtCore.Qt.Key_Return:
            self.navigatorButtonActivated.emit(self._url, QtCore.Qt.LeftButton, evt.modifiers())
            super().keyPressEvent(evt)
            return
        elif evtKey == QtCore.Qt.Key_Down:
            pass
        elif evtKey == QtCore.Qt.Key_Space:
            self.slot_startSubDirsJob()
            super().keyPressEvent(evt)
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
            
    def dragMoveEvent(self, evt:QtGui.QDragMoveEvent):
        rect = evt.answerRect()
        if self.isAboveArrow(rect.center().x()):
            self._hoverArrow_ = True
            self.update()
            
            if not isinstance(self._subDirsMenu_, UrlNavigatorMenu) or not qtutils.isQObjectAlive(self._subDirsMenu_):
                self.slot_requestSubDirs()
                
            elif self._subDirsMenu_.parent() != self:
                self._subDirsMenu_.close()
                self._subDirsMenu_.deleteLater()
                self._subDirsMenu_ = None
                
                self.slot_requestSubDirs()
                
        else:
            if self._openSubDirsTimer.isActive(): 
                self.cancelSubDirsRequest() 
                
            if isinstance(self._subDirsMenu_, UrlNavigatorMenu) and qtutils.isQObjectAlive(self._subDirsMenu_):
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
        if self.isAboveArrow(evt.pos().x()) and evt.button() == QtCore.Qt.LeftButton:
            self.slot_startSubDirsJob()
        
        super().mousePressEvent(evt)
        
    def mouseReleaseEvent(self, evt:QtGui.QMouseEvent):
        if not self.isAboveArrow(round(evt.pos().x())) or evt.button() != QtCore.Qt.LeftButton:
            # self._pressed_ = False # NOTE: 2025-01-02 01:18:34 by CMT, used in paintEvent
            # self.update()
            self.navigatorButtonActivated.emit(self._url_, evt.button(), evt.modifiers())
            self.cancelSubDirsRequest()

        super().mouseReleaseEvent(evt)
        
    def mouseMoveEvent(self, evt:QtGui.QMouseEvent):
        super().mouseMoveEvent(evt)
        # hoverArrow = self.isAboveArrow(round(evt.pos().x()))
        hoverArrow = self.isAboveArrow(evt.pos().x())
        if hoverArrow != self._hoverArrow_:
            self._hoverArrow_ = hoverArrow
            self.update()
            
    def wheelEvent(self, evt:QtGui.QWheelEvent):
        if evt.angleDelta().y() != 0:
            self._wheelSteps_ = evt.angleDelta().y() // 120
            self._replaceButton_ = True
            self.slot_startSubDirsJob()
            # self.getSiblingDirs()
            
        super().wheelEvent(evt)
            
    def isTextClipped(self):
        availableWidth = self.width() - 2 * self.BorderWidth
        if len(self._subDir_) > 0:
            availableWidth -= self.arrowWidth() - self.BorderWidth
        adjustedFont = self.font()
        adjustedFont.setBold(len(self._subDir_) == 0)
        return QtGui.QFontMetrics(adjustedFont).size(QtCore.Qt.TextSingleLine, self.text()).width() >= availableWidth
        
    def sizeHint(self) -> QtCore.QSize:
        adjustedFont = self.font()
        adjustedFont.setBold(len(self._subDir_) == 0)
        fontMetric = QtGui.QFontMetrics(adjustedFont)
        width = fontMetric.size(QtCore.Qt.TextSingleLine,self.plainText()).width() + self.arrowWidth() + 4 * self.BorderWidth
        return QtCore.QSize(width, super().sizeHint().height())
    
    def activeSubDirectory(self) -> str:
        return self._subDir_
    
    def setActiveSubDirectory(self, val:str):
        self._subDir_ = val
        self.updateGeometry()
        self.update()
        
    def cancelSubDirsRequest(self):
        self._openSubDirsTimer.stop()
        if isinstance(self._subDirsJob_, ListDirsJob) and qtutils.isQObjectAlive(self._subDirsJob_):
            if self._subDirsJob_.isRunning():
                # self._subDirsJob_.requestInterruption()
                self._subDirsJob_.quit()
            self._subDirsJob_.deleteLater()
            self._subDirsJob_ = None
        # pass

    @Slot()
    def slot_startSubDirsJob(self):
        # print(f"{self.__class__.__name__}.slot_startSubDirsJob invoked")
        
        # NOTE: 2024-12-30 23:48:13
        # this is the slot_startSubDirsJob in KIO
        #
        # in KIO:
        # • if _replaceButton_ is True, the directory that this button
        # points to will have changed to one of its siblings; typically this
        # is triggered by a wheel event, which should result in "scrolling" 
        # through the sibling directories
        #
        # • if _replaceButton_ is False, then a menu with the subdirectories of
        # the current path of the button will open.
        #
        # • instantiates a KIO::ListJob by calling KIO::listDir(…)
        #   ∘ this indirectly constructs a ListJob by calling the static method 
        #       ListJobPrivate::newJob(…)
        #       ▷ ListJob c'tor (protected) in fact instantiates a ListJobPrivate 
        #           which actually represents the "job"
        #       ▷ the ListJobPrivate instance is a SimpleJobPrivate with CMD_LISTDIR
        #           macro (commands_p.h defines the internal commands that can be
        #           invoked by a job)
        #
        # Now, the Job emits two signals:
        # • entries -> connected to self.addEntriesToSubdirs (here, this is 
        #   slot_addEntriesToSubdirs)
        # • result -> connected to:
        #   ∘ self.replaceButton if _replaceButton_ is True
        #   ∘ self.openSubDirMenu otherwise
        
        # I don't use a KIO Job here because there is no Python port for it, and
        # even if there was one, it would "tie" Scipyen too much to KDE frameworks
        # -- sorry, KDE folks ⌣... 
        
        path = self.path()
        if not isinstance(path, pathlib.Path) or not path.is_dir() or not path.exists():
            return
    
        if isinstance(self._subDirsJob_, QtCore.QThread) and qtutils.isQObjectAlive(self._subDirsJob_) and self._subDirsJob_.isRunning():
            return
    
        url = upUrl(self._url_) if self._replaceButton_ else self._url_
        
        navigator = self.parent()
        assert qtutils.isQObjectAlive(navigator), f"Parent object was deleted"
        
        self._subDirsJob_ = ListDirsJob(url, self)
        self._subDirs_.clear()
        
        self._subDirsJob_.sig_entries.connect(self.slot_addEntriesToSubdirs)
        if self._replaceButton_:
            self._subDirsJob_.finished.connect(self.slot_replaceButton)
        else:
            self._subDirsJob_.finished.connect(self.slot_openSubDirsMenu)
            
        self._subDirsJob_.start()
        
    @Slot(QtWidgets.QAction, QtGui.QDropEvent)
    def slot_urlsDropped(self, action:QtWidgets.QAction, event:QtGui.QDropEvent):
        result = action.data().toInt()
        path = self._subDirs_[result]
        url = QtCore.QUrl(path.as_uri())
        self.urlsDroppedOnNavButton.emit(url, event)
    
    @Slot(QtWidgets.QAction)
    def slot_menuActionTriggered(self, action:QtWidgets.QAction):
        # mouseButtons = QtWidgets.QApplication.mouseButtons()
        # result = action.data().toInt()    
        # NOTE: 2025-01-20 21:36:48
        # in PyQt5 this is already an int, see also
        #   NOTE: 2025-01-21 09:04:14 (UrlNavigatorButton.initMenu)
        #   NOTE: 2025-01-21 16:43:02
        #   NOTE: 2025-01-21 16:45:50
        result = action.data()              
        path = self._subDirs_[result]
        url = QtCore.QUrl(path.as_uri())
        self.navigatorButtonActivated.emit(url, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    
    @Slot(QtWidgets.QAction, QtCore.Qt.MouseButton)
    def slot_menuActionClicked(self, action:QtWidgets.QAction, button:QtCore.Qt.MouseButton):
        """Invoked by mouse clicking on a subdirectories menu entry.
        """
        # NOTE: 2025-01-21 09:06:45 see NOTE: 2025-01-21 08:59:29
        # result = action.data().toInt()
        # NOTE: 2025-01-20 22:12:33 see 
        #   NOTE: 2025-01-20 21:36:48 
        #   NOTE: 2025-01-21 09:04:14
        #   NOTE: 2025-01-21 16:45:50
        #
        # this is the index of the subirectory (pointed to by the action) in the
        # self._subDirs_ list
        result = action.data() 
        buttonPath = self.path()
        path = pictio.concatPaths(buttonPath, self._subDirs_[result])   # the path to the subdirectory pointed to by the action
        # print(f"{self.__class__.__name__}.slot_menuActionClicked: path = {path}")
        print()
        url = QtCore.QUrl(path.absolute().as_uri())
        self.navigatorButtonActivated.emit(url, button, QtCore.Qt.NoModifier)

    @Slot()
    def slot_statFinished(self):
        # print(f"{self.__class__.__name__}.slot_statFinished invoked")
        # NOTE: 2025-01-02 00:14:19
        # in KIO this is triggered by the result signal of a KIO::stat job
        # part of the mechanism for resolving uris with special schemes/protocols
        # (i.e., in relation with special KIO slaves see this module docstring)
        # not used here (yet ?!?)
        pass
        
#     @safeWrapper
#     def subDirMenuRequested(self, evt:QtGui.QMouseEvent): # TODO/FIXME finalize
#         if self._subDirsMenu_ is None:
#             self._subDirsMenu_ = QtWidgets.QMenu("", self)
#             self._subDirsMenu_.aboutToHide.connect(self.slot_menuHiding)
#             
#         self._subDirsMenu_.clear()
#         
#         if self._fileSystemModel_.hasChildren(self._fileSystemModelIndex_):
#             subDirs = [self._fileSystemModel_.data(self._fileSystemModel_.index(row, 0, self._fileSystemModelIndex_)) for row in range(self._fileSystemModel_.rowCount(self._fileSystemModelIndex_))]
#             # print(f"{self.__class__.__name__}.subDirMenuRequested rootIndex subDirs {subDirs}")
#             if len(subDirs):
#                 for k, subDir in enumerate(subDirs):
#                     # print(f"subDir {subDir}")
#                     action = self._subDirsMenu_.addAction(subDir)
#                     action.setText(subDir)
#                     action.triggered.connect(self.slot_subDirClick)
#         
#                 self._subDirsMenu_.popup(self.mapToGlobal(evt.pos()))
    
    @Slot()
    def slot_requestSubDirs(self):
        # print(f"{self.__class__.__name__}.slot_requestSubDirs invoked")
        if not self._openSubDirsTimer.isActive() and (not isinstance(self._subDirsJob_, ListDirsJob) or not qtutils.isQObjectAlive(self._subDirsJob_)):
            self._openSubDirsTimer.start()
        
    @Slot()
    def slot_replaceButton(self):
        if isinstance(self._subDirsJob_, ListDirsJob):
            if qtutils.isQObjectAlive(self._subDirsJob_) and self._subDirsJob_.isRunning():
                self._subDirsJob_.quit()
                self._subDirsJob_.wait()
                
            self._subDirsJob_.deleteLater()
            
        self._subDirsJob_ = None
        self._replaceButton_ = False
        if len(self._subDirs_) == 0:
            return
        
        path = self.path()
        
        if path not in self._subDirs_:
            print(f"{path} not in _subDirs_")
            return
        
        currentIndex = self._subDirs_.index(path)
        
        navigator = self.parent()
        assert qtutils.isQObjectAlive(navigator), f"Parent object was deleted"
        targetIndex = currentIndex - self._wheelSteps_
        if targetIndex < 0:
            targetIndex = 0
        elif targetIndex >= len(self._subDirs_):
            targetIndex = len(self._subDirs_)-1
            
        newUrl = QtCore.QUrl(self._subDirs_[targetIndex].as_uri())
        self.navigatorButtonActivated.emit(newUrl, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        
        # NOTE: 2025-01-01 12:20:49 
        # in KIO the text of the button and its underlying URI are not modified here 
        # (i.e. they are not set to the new directory) - to find out if this is 
        # happening AFTER the navigator has successfully navigated to the new directory
        # (my guess is that this is what actually happens)
        
        self._subDirs_.clear()
        
    @Slot()
    def slot_openSubDirsMenu(self):
        """Creates a menu with subdirectories of this button's directory.
        """
        # NOTE: 2025-01-21 08:49:34
        # Connected to (and called by) ListDirsJob.finished Signal. The connection
        # is established from within slot_startSubDirsJob when self._replaceButton_ 
        # is False; see NOTE: 2024-12-30 23:48:13
        
        # print(f"{self.__class__.__name__}<{self.plainText()}>.slot_openSubDirsMenu invoked")
        self._subDirsJob_ = None
        if len(self._subDirs_) == 0:
            return
        navigator = self.parent()
        assert qtutils.isQObjectAlive(navigator), f"Parent object was deleted"
        
        # updates the button looks
        self.setDisplayHintEnabled(DisplayHint.PopupActiveHint, True)
        self.update()
        
        # there is ONE subdirectories menu per button, so let's make sure we
        # deal with it correctly (?!?)
        if isinstance(self._subDirsMenu_, QtWidgets.QMenu) and qtutils.isQObjectAlive(self._subDirsMenu_):
            self._subDirsMenu_.close()
            self._subDirsMenu_.deleteLater()
            self._subDirsMenu_ = None
            
        self._subDirsMenu_ = UrlNavigatorMenu(parent=self)
        
        # NOTE: 2025-01-21 08:58:06
        # populates the menu with subdirectory entries
        self.initMenu(self._subDirsMenu_, 0)
        
        self._subDirsMenu_.popup(self.mapToGlobal(QtCore.QPoint(0,0)))
    
    @Slot(list)
    def slot_addEntriesToSubdirs(self, entries:list[pathlib.Path]):
        """Populates the list of subdirectories for this button.
        The subdirectories are entries generated asynchronously by a ListDirsJob.
        """
        # NOTE: 2025-01-21 08:53:03
        # Connected to the  ListDirsJob.sig_entries Signal.
        
        # print(f"{self.__class__.__name__}.slot_addEntriesToSubdirs")

        if len(entries) == 0:
            return
        assert all(isinstance(v, pathlib.Path) for v in entries), "Expecting a list of Path objects"
        
        dirEntries = list(filter(lambda x: x.is_dir() and x.exists(), entries))
        if len(dirEntries) == 0:
            return
        
        self._subDirs_[:] = sorted(dirEntries[:])
        # print(f"\tsubDirs: {self._subDirs_}")

    
# NOTE: 2023-05-06 22:26:18
# By design we only use the 'file://' protocol hence this is not needed, for now...
# NOTE: 2025-01-02 16:02:17 but this may change
#
class UrlNavigatorSchemeCombo(UrlNavigatorButtonBase):
    """Implementation of KIO KUrlNavigatorSchemeCombo
    """
    # NOTE: 2025-01-21 16:34:28
    # was UrlNavigatorProtocolCombo
    
    activated = Signal(str, name="activated")
    
    def __init__(self, scheme:str, parent:typing.Optional[UrlNavigator]=None):
        super().__init__(parent)
        self._menu_ = QtWidgets.QMenu(self)
        self._schemes_ = list()
        self._categories_ = dict() # str ↦ SchemeCategory
        
        self._menu_.triggered.connect(self.setSchemeFromMenu)
        self.setText(scheme)
        self.setMenu(self._menu_)
        
    def _testProtocol_(self, scheme:str):
        url = QtCore.QUrl()
        url.setScheme(scheme)
        return True
        
    @Slot()
    def setSchemeFromMenu(self):
        pass # TODO
    
    @Slot(str)
    def setScheme(self, scheme:str):
        self.setText(scheme)
        
    def currentScheme(self):
        return self.text()
    
    def setSupportedSchemes(self, schemes:list):
        self._schemes_ = schemes
        self._menu_.clear()
        for scheme in schemes:
            action = self._menu_.addAction(scheme)
            action.setData(scheme)
            
    def sizeHint(self):
        size = super().sizeHint()
        width = self.fontMetrics().boundingRect(dutils.removeAcceleratorMarker(self.text())).width()
        width += (3 * self.BorderWidth) + ArrowSize
        
        return QtCore.QSize(width, size.height())
    
    def showEvent(self, evt:QtGui.QShowEvent):
        super().showEvent(evt)
        if not evt.spontaneous() and len(self._schemes_) == 0:
            protocols = [p for p in ProtocolInfo.protocols() if self._testProtocol_(p)]
            self._schemes_[:] = sorted(protocols)

class UrlNavigatorPlacesSelector(UrlNavigatorButtonBase): # TODO: 2023-05-07 23:07:25 finalize
    placeActivated = Signal(str, name = "placeActivated")
    tabRequested = Signal()
    
    def __init__(self, parent:UrlNavigator, placesModel:PlacesModel):
        super().__init__(parent=parent)
        
        self._selectedItem_:int = -1
        self._placesModel_:PlacesModel = placesModel
        # NOTE: 2025-01-02 22:55:20 next line performs the C++ code 
        # connect(m_placesModel, &KFilePlacesModel::reloaded, this, [this] {
        # updateSelection(m_selectedUrl);
        # });
        # i.e. passing a dynamically-created slot out of updateSelection(m_selectedUrl)
        # not sure I can do that in Python, so I define the intervening Slot placeModelReloaded
        #
        self._placesModel_.reloaded.connect(self.placeModelReloaded)
        
        self._placesMenu_ = QtWidgets.QMenu(self)
        self._placesMenu_.installEventFilter(self)
        self._placesMenu_.aboutToShow.connect(self.updateMenu)
        self._placesMenu_.triggered[QtWidgets.QAction].connect(self.placeActionActivated)
        self.setMenu(self._placesMenu_)
        self.setAcceptDrops(True)
        
#         self.setFocusPolicy(QtCore.Qt.NoFocus)
#         self._selectedUrl_ = QtCore.QUrl()
#         
#         self.updateMenu()
        
        # self._placesMenu_.triggered.connect() ### use updateMenu to connect each action

    # ### BEGIN Slots by CMT - TODO: 2025-01-21 17:25:38 revisit this
    @Slot()
    def placeModelReloaded(self):
        self.updateSelection(self._selectedUrl_)
        
    @Slot(QtWidgets.QAction)
    def placeActionActivated(self, action:QtWidgets.QAction):
        self.activatePlace(action, self.placeActivated)
        
    # ### END Slots by CMT
    
    @Slot()
    def updateMenu(self):
        # NOTE: 2025-01-02 23:02:58
        # CMT - facilitate garbage collection
        # see also in KIO:
        # // Submenus have to be deleted explicitly (QTBUG-11070)
        # for (QObject *obj : QObjectList(m_placesMenu->children())) {
        #     delete qobject_cast<QMenu *>(obj); // Noop for nullptr
        # }
        # but we cannot do it after calling clear()
        #
        for obj in self._placesMenu_.children():
            obj.deleteLater()
            
        self._placesMenu_.clear()
        
        self.updateSelection(self._selectedUrl_)
        
        previousGroup:str = ""
        subMenu:typing.Optional[QtWidgets.QMenu] = None
        
        rowCount = self._placesModel_.rowCount()
        
        for i in range(rowCount):
            # NOTE: 2025-01-02 23:07:04
            # here and throughout, don't mind my type annotations
            index:QtCore.QModelIndex = self._placesModel_.index(i, 0)
            if self._placesModel_.ishidden(index):
                continue
            
            placeAction:QtWidgets.QAction = QtWidgets.QAction(self._placesModel_.icon(index),
                                           self._placesModel_.text(index),
                                           self._placesMenu_)
            
            placeAction.setData(i)
            
            groupName:str = index.data(placesmodel.AdditionalRoles.GroupRole).toString()
            
            if len(previousGroup) == 0:
                previousGroup = groupName
                
            if previousGroup != groupName:
                subMenuAction:QtWidgets.QAction = QtWidgets.QAction(groupName, self._placesMenu_)
                subMenu:QtWidgets.QMenu = QtWidgets.QMenu(self._placesMenu_)
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
                
        # NOTE: 2025-01-02 23:17:54
        # replaces C++ code
        # const QModelIndex index = m_placesModel->index(m_selectedItem, 0);
        # if (QAction *teardown = m_placesModel->teardownActionForIndex(index)) {
        #     m_placesMenu->addSeparator();
        # 
        #     teardown->setParent(m_placesMenu);
        #     m_placesMenu->addAction(teardown);
        # }
        self.updateTeardownAction()
        
    def updateTeardownAction(self): # CMT
        teardownActionId:str = "teardownAction"
        actions:list[QtWidgets.QAction] = self._placesMenu_.actions()
        
        for action in actions:
            if action.data() == teardownActionId:
                action.deleteLater()
                action = None
                
        index:QtCore.QModelIndex = self._placesModel_.index(self._selectedItem_, 0)
        
        teardown:typing.Optional[QtWidgets.QAction] = self._placesModel_.teardownActionForIndex(index)
        
        if isinstance(teardown, QtQidgets.QAction):
            self._placesMenu_.addSeparator()
            self._placesMenu_.addAction(teardown)
        
    def selectedPlaceUrl(self): # TODO/FIXME finalize
        return QtCore.QUrl()
    
    def selectedPlaceText(self): # TODO/FIXME finalize
        return ""
        
class UrlNavigatorDropDownButton(UrlNavigatorButtonBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        # self._isDown_ = False # def'ed in UrlNavigatorButtonBase
        
        
    def sizeHint(self):
        size = super().sizeHint()
        size.setWidth(int(size.height() / 2))
        return size
    
    def keyPressEvent(evt:QtGui.QKeyEvent):
        if evt.key() == QtCore.Qt.Key_Down:
            self.clicked.emit()
            
        else:
            super().keyPressEvent(evt)
    
    def paintEvent(self, evt:QtGui.QPaintEvent):
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
            if self.layoutDirection() == QtCore.Qt.LeftToRight:
                self.style().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowRight, option, painter, self)
            else:
                self.style().drawPrimitive(QtWidgets.QStyle.PE_IndicatorArrowLeft, option, painter, self)
            
class CoreUrlNavigator(QtCore.QObject):
    """Implementation of KIO KCoreUrlNavigator"""
    currentUrlAboutToChange     = Signal(QtCore.QUrl, name = "currentUrlAboutToChange")
    currentLocationUrlChanged   = Signal(name = "currentLocationUrlChanged")
    urlSelectionRequested       = Signal(QtCore.QUrl, name = "urlSelectionRequested")
    historyIndexChanged         = Signal(name = "historyIndexChanged")
    historyChanged              = Signal(name = "historyChanged")
    historySizeChanged          = Signal(name = "historySizeChanged")
    
    def __init__(self, url:QtCore.QUrl = QtCore.QUrl(), parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        if not isinstance(url, QtCore.QUrl):
            url = QtCore.QUrl()
        adjUrl = QtCore.QUrl(url.adjusted(QtCore.QUrl.NormalizePathSegments))
        # NOTE: 2023-05-03 23:48:23
        # Originally, a list of LocationData structs.
        # Here, this is a NamedTuple with the fields "url" and "state"
        self._history_ = list() # of LocationData # NOTE: KIO KCoreUrlNavigatorPrivate API
        self._oldSessionsHistory_ = list() # CMT 2025-01-21 22:47:42
        self._history_.insert(0, LocationData(adjUrl, None))
        # self._history_.insert(0, LocationData(url, None))
        self._historyIndex_ = 0 # NOTE: KIO KCoreUrlNavigatorPrivate API
        # print(f"{self.__class__.__name__}.__init__: url = {url}, adjUrl = {adjUrl}, history: {self._history_}")
        
    def historyIndex(self):
        return self._historyIndex_
    
    def setHistoryIndex(self, value:int):
        self._historyIndex_ = value
        self.historyIndexChanged.emit()
        
    def historySize(self):
        return len(self._history_)
    
    def currentLocationUrl(self):
        return self.locationUrl()
    
    def setCurrentLocationUrl(self, newUrl:QtCore.QUrl):
        # print(f"{self.__class__.__name__}.setCurrentLocationUrl({newUrl})")
        if newUrl == self.locationUrl():
            return
        
        url = newUrl.adjusted(QtCore.QUrl.NormalizePathSegments)
        
        firstUrlChild = firstChildUrl(self.locationUrl(), url)
        
        scheme = url.scheme()
        # NOTE: 2023-05-04 15:15:30
        # Scipyen's file manager does NOT use special protocols (which include
        # compressed archives)
        
        if len(scheme):
            # NOTE: 2025-01-02 15:20:15
            # until a ProtocolInfo is implemented, use "getSystemArchiveMimeTypes"
            # defined in this module
            # archiveMimetypes = ProtocolInfo.archiveMimeTypes(scheme)
            archiveMimeTypes = list(map(lambda x: x.name(), getSystemArchiveMimeTypes()))
            
            if len(archiveMimeTypes):
                insideCompressedPath = self.isCompressedPath(url)
                if not insideCompressedPath:
                    prevUrl = url
                    parentUrl = upUrl(url)
                    while parentUrl != prevUrl:
                        if self.isCompressedPath(parentUrl, archiveMimeTypes):
                            insideCompressedPath = True
                            break;
                        prevUrl = parentUrl
                        parentUrl = upUrl(parentUrl)
                if not insideCompressedPath:
                    url.setScheme("file")
                    firstUrlChild.setScheme("file")
                    

        # this is a LocationData
        data = self._history_[self._historyIndex_]
        
        isUrlEqual = url.matches(self.locationUrl(), QtCore.QUrl.StripTrailingSlash) or (not url.isValid() and url.matches(data.url, QtCore.QUrl.StripTrailingSlash))
        
        if isUrlEqual:
            return
        
        self.currentUrlAboutToChange.emit(url)
        
        if self._historyIndex_ > 0:
            self._history_[0:self._historyIndex_] = []
            self._historyIndex_ = 0

        assert self._historyIndex_ == 0
        self._history_.insert(0, LocationData(url.adjusted(QtCore.QUrl.StripTrailingSlash), None)) # CAUTION: is it OK for state to be None ?!?
        
        historyMax = 100 # TODO make configurable -> link with mainWindow !!!
        
        if len(self._history_) > historyMax:
            self._history_[historyMax:] = []
            
        self.historyIndexChanged.emit()
        self.historySizeChanged.emit()
        self.historyChanged.emit()
        self.currentLocationUrlChanged.emit()
        
        if firstUrlChild.isValid():
            self.urlSelectionRequested.emit(firstUrlChild)
        
    def isCompressedPath(self, url:QtCore.QUrl, archiveMimeTypes:list = list()):
        # NOTE: KIO KCoreUrlNavigatorPrivate API
        db = QtCore.QMimeDatabase()
        mime = db.mimeTypeForUrl(QtCore.QUrl(url.toString(QtCore.QUrl.StripTrailingSlash)))
        
        return any(mime.inherits(archiveType) for archiveType in archiveMimeTypes)
        
    def adjustedHistoryIndex(self, historyIndex:int):
        # NOTE: KIO KCoreUrlNavigatorPrivate API
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
    def locationState(self, historyIndex:int = -1) -> object:
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
            self.currentUrlAboutToChange.emit(newUrl)
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
        
        upUrl_ = upUrl(currentUrl)
        
        if not currentUrl.matches(upUrl_, QtCore.QUrl.StripTrailingSlash):
            self.setCurrentLocationUrl(upUrl_)
            return True
        
        return False
        
class UrlNavigatorPathSelectorEventFilter(QtCore.QObject):
    tabRequested = Signal(QtCore.QUrl, name="tabRequested")
    def __init__(self, parent:QtCore.QObject):
        super().__init__(parent)
        
    @safeWrapper
    def eventFilter(self, menu:QtCore.QObject, evt:QtCore.QEvent):
        if isinstance(menu, QtWidgets.QMenu) and evt.type() == QtCore.QEvent.MouseButtonRelease and evt.button() == QtCore.Qt.MiddleButton:
            action = menu.activeAction()
            if action is not None:
                url = QtCore.QUrl(action.data().toString())
                print(f"{self.__class__.__name__}.eventFilter: url = {url}")
                if url.isValid():
                    menu.close()
                    self.tabRequested.emit(url)
                    return True
    
        return super().eventFilter(menu, evt)
    
class _UrlNavigator_(QtCore.QObject):
    # KUrlNavigatorPrivate
    # _sig_switchToBreadCrumbMode = Signal(name="_sig_switchToBreadCrumbMode")
    def __init__(self, url:QtCore.QUrl, qq: UrlNavigator, 
                 placesModel:typing.Optional[PlacesModel]=None):
        # print(f"{self.__class__.__name__}.__init__: url = {url}")
        super().__init__()
        self._supportedSchemes_:list[str] = list()
        self._homeUrl_:typing.Optional[QtCore.QUrl] = None # do not initialize here -> 'tis the work of _coreUrlNavigator_
        self._customProtocols_:list = list()
        self._editable_:bool = False
        self._active_:bool = True
        self._showFullPath_:bool = False
        
        # NOTE: 2025-01-24 21:21:11 CMT
        self._closestPlace_:typing.Optional[DEPlace] = None
        # self._placePathStr_:str = str()
        
        # self._sig_switchToBreadCrumbMode.connect(self.switchToBreadcrumbMode)
        
        # TODO: 2025-01-09 21:43:54 ?!? why Bunch ?!? - can also use a namespace
        # but Bunch ( in traitlets package ) most closely fits a struct
        self._subfolderOptions_:Bunch = Bunch({"showHidden":False, "sortHiddenLast": False})
        
        # ### BEGIN UI Components of self._nav_:UrlNavigator
        
        self._nav_:UrlNavigator = qq
        self._nav_.setAutoFillBackground(False)

        self._layout_:QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self._nav_)
        self._layout_.setSpacing(0)
        self._layout_.setContentsMargins(0,0,0,0)

        # print(f"\tconstructing self._coreUrlNavigator_ on {url}")
        self._coreUrlNavigator_:CoreUrlNavigator = CoreUrlNavigator(url, self._nav_) # m_coreUrlNavigator
        self._coreUrlNavigator_.currentLocationUrlChanged.connect(self._nav_.slot_coreUrlNavigatorUrlChanged)
        self._coreUrlNavigator_.currentUrlAboutToChange[QtCore.QUrl].connect(self._nav_.slot_coreUrlNavigatorUrlAboutToBeChanged)
        self._coreUrlNavigator_.historySizeChanged.connect(self._nav_._slot_historyChanged)
        self._coreUrlNavigator_.historyIndexChanged.connect(self._nav_._slot_historyChanged)
        self._coreUrlNavigator_.historyChanged.connect(self._nav_._slot_historyChanged)
        self._coreUrlNavigator_.urlSelectionRequested[QtCore.QUrl].connect(self._nav_.slot_coreUrlNavigatorUrlSelectionRequested)
        
        self._placesSelector_:typing.Optional[UrlNavigatorPlacesSelector] = None
        
        # ### BEGIN CMT reinstate this once placesmodel module is finalized
        # if isinstance(placesModel, PlacesModel):
        #     self._placesSelector_ = UrlNavigatorPlacesSelector(placesModel, self._nav_)
        #     self._placesSelector_.placeActivated.connect(self._nav_.setLocationUrl)
        #     self._placesSelector_.tabRequested.connect(self._nav_.tabRequested)
        #     self._placesModel_.rowsInserted.connect(self._nav_.updateContent)
        #     self._placesModel_.rowsRemoved.connect(self._nav_.updateContent)
        #     self._placesModel_.dataChanged.connect(self._nav_.updateContent)
            
        # self._showPlacesSelector_:bool = isinstance(self._placesSelector_, PlacesModel)
        # ### END   CMT reinstate this once placesmodel module is finalized

        # ### BEGIN _schemes_: UrlNavigatorSchemeCombo (was UrlNavigatorProtocolCombo)
        # NOTE: 2023-05-06 22:25:07
        # by design we only support a file: protocol
        # hence not sure I need self._schemes_
        # ### BEGIN _protocols_:UrlNavigatorProtocolCombo
        # NOTE: 2023-05-06 22:30:13
        # We only use "file://" protocol - hence only the file:/// url scheme is
        # supported in Scipyen, see also NOTE: 2023-05-06 22:30:13 below
        # NOTE: 2025-01-19 09:58:19
        # in kf6 KIO renamed to _schemes_
        # self._protocols_:typing.Optional[UrlNavigatorProtocolCombo] = None # TODO: revisit this
        # self._protocols_ = UrlNavigatorProtocolCombo("", self._nav_)
        # self._protocols_.sig_activated.connect(self.slotProtocolChanged)
        # ### END   _protocols_:UrlNavigatorProtocolCombo
        self._schemes_:UrlNavigatorSchemeCombo = UrlNavigatorSchemeCombo(str(), self._nav_)
        self._schemes_.activated[str].connect(self._nav_.slotSchemeChanged)
        
        # FIXME: 2025-01-21 14:40:32 temporary
        # TODO: finish up UrlNavigatorSchemeCombo
        self._schemes_.setVisible(False) 
        
        # ### END   _schemes_: UrlNavigatorSchemeCombo
        
        # ### BEGIN _navButtons_
        self._navButtons_:list = list() # list of "breadcrumb buttons" - instances of UrlNavigatorButton
        # ### END   _navButtons_
        
        
        # ### BEGIN drop down button - for "upward overspill" path elements
        # NOTE: 2023-05-07 22:59:49
        # drops down a menu of places or parent paths when they're not to be
        # shown directly as breadcrumbs
        self._dropDownButton_:UrlNavigatorDropDownButton = UrlNavigatorDropDownButton(self._nav_)
        self._dropDownButton_.setForegroundRole(QtGui.QPalette.WindowText)
        self._dropDownButton_.installEventFilter(self._nav_)
        self._dropDownButton_.clicked.connect(self.openPathSelectorMenu)
        # ### END   drop down button - for "upward overspill" path elements
        
        # ### BEGIN _pathBox_:UrlComboBox
        # NOTE: 2023-05-07 23:16:43
        # the actual path combo box
        # TODO: Modify UrlComboBox code: to its QLineEdit, add extra tool buttons for:
        # • clearing history
        # • clear current text
        # • remove current text from history
        # • enable clear, undo, redo
        self._pathBox_:UrlComboBox = UrlComboBox(UrlComboMode.Directories, True, self._nav_)
        self._pathBox_.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
        # self._pathBox_.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._pathBox_.installEventFilter(self._nav_)
        
        # ### BEGIN TODO 2025-01-09 21:05:56 implement completion
        # UrlCompletion <- Completion (KCompletion in KCompletion framework)
        # self._urlCompletion = ...
        # self._pathBox_.setCompletionObject(self._urlCompletion)
        # self._pathBox_.setAutoDeleteCompletionObject(true)
        # ### END   TODO
        
        # self._pathBox_.returnPressed.connect(self.slotReturnPressed)
        self._pathBox_.returnPressed.connect(self._nav_.slot_returnPressed)
        self._pathBox_.urlActivated.connect(self._nav_.setLocationUrl)
        self._pathBox_.editTextChanged[str].connect(self.slotPathBoxChanged)
        
        # ### END   _pathBox_:UrlComboBox
        
        # ### BEGIN _badgeWidgetContainer_:QtGui.QWidget - what's that for ?!?
        self._badgeWidgetContainer_:QtWidgets.QWidget = QtWidgets.QWidget(self._nav_)
        badgeLayout:QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self._badgeWidgetContainer_)
        badgeLayout.setContentsMargins(0,0,0,0)
        # ### END   _badgeWidgetContainer_:QtGui.QWidget
        
        # ### BEGIN _toggleEditableMode_:UrlNavigatorButton
        # NOTE: 2023-05-07 23:22:18
        # toggles between url combo box and bread crumbs
        self._toggleEditableMode_:UrlNavigatorToggleButton = UrlNavigatorToggleButton(self._nav_)
        self._toggleEditableMode_.installEventFilter(self._nav_)
        self._toggleEditableMode_.setMinimumWidth(20)
        self._toggleEditableMode_.clicked.connect(self.slotToggleEditableButtonPressed)
        # ### END   _toggleEditableMode_:UrlNavigatorButton
        
        # ### BEGIN _dropWidget_ - what's that for ?!?
        self._dropWidget_:typing.Optional[QtCore.QWidget] = None # TODO - dynamic stuff
        # ### END   _dropWidget_
        
        # ### BEGIN CMT 2025-01-24 21:28:34 reinstate this when placesmodel module is finalized
        # if isinstance(self._placesSelector_, UrlNavigatorPlacesSelector):
        #     self._layout_.addWidget(self._placesSelector_)
        # ### END   CMT 2025-01-24 21:28:34 reinstate this when placesmodel module is finalized
            
        self._layout_.addWidget(self._schemes_)
        self._layout_.addWidget(self._dropDownButton_)
        self._layout_.addWidget(self._pathBox_, 1)
        self._layout_.addWidget(self._badgeWidgetContainer_)
        self._layout_.addWidget(self._toggleEditableMode_)
        
        self._nav_.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._nav_.customContextMenuRequested[QtCore.QPoint].connect(self.openContextMenu)
        
        # ### END   UI Components of self._nav_:UrlNavigator
        
        
    # ### BEGIN KUrlNavigatorPrivate API
            
    @Slot(QtCore.QUrl)
    def slotApplyUrl(self, url:QtCore.QUrl):
        # TODO 2025-01-18 11:10:53 ProtocolInfo
        # if (!url.isEmpty() && url.path().isEmpty() && KProtocolInfo::protocolClass(url.scheme()) == QLatin1String(":local")) {
        #     url.setPath(QStringLiteral("/"));
        # }
        if not url.isEmpty() and len(url.path()) == 0:
            url.setPath("/")
            
        urlStr:str = url.toString()
        
        urls:list[str] = [u for u in self._pathBox_.urls() if u != urlStr]
        urls.insert(0, urlStr)
        # ### BEGIN NOTE/FIXME 2025-01-21 23:28:51 TODO
        # oldUrls = list(filter(lambda x: x not in urls, map(lambda x: x.url.path(), self._coreUrlNavigator_._oldSessionsHistory_)))
        oldUrls = list(filter(lambda x: x not in urls, map(lambda x: x.url.toString(QtCore.QUrl.StripTrailingSlash), self._coreUrlNavigator_._oldSessionsHistory_)))
        urls.extend(oldUrls)
        # ### END   NOTE/FIXME 2025-01-21 23:28:51 TODO
            
        self._pathBox_.setUrls(urls) # TODO: use flag KUrlComboBox::RemoveBottom
        self._nav_.setLocationUrl(url)
        self._pathBox_.setUrl(self._nav_.locationUrl())
        
    @Slot(str)
    def checkFilters(self, text:str): # TODO 2023-05-06 22:53:38
        # KIO uses KUriFilterData
        # need to figure out what this does and replace with simpler pythonic code
        #
        # for now, just return None
        return 
    
    @Slot()
    def slotReturnPressed(self):
        # NOTE: 2025-01-17 23:21:55 no support for Tabs
        # therefore either apply url here or open platform's default appliuation
        keyboardModifiers = QtWidgets.QApplication.keyboardModifiers()
        
        if int(keyboardModifiers & QtCore.Qt.ShiftModifier):
            self.applyUncommittedUrl(ApplyUrlMethod.NewWindow) # -> open in application
            
        elif int(keyboardModifiers & QtCore.Qt.ControlModifier):
            self._sig_switchToBreadCrumbMode.emit()
            
        else:
            self.applyUncommittedUrl(ApplyUrlMethod.Apply) # navigate here
            self._nav_.returnPressed.emit()
            
        # if int(leyboardModifiers & QtCore.Qt.AltModifier):
        #     if int(keyboardModifiers & QtCore.Qt.ShiftModifier):
        #         self.applyUncommittedUrl(ApplyUrlMethod.Tab)
        #     else:
        #         self.applyUncommittedUrl(ApplyUrlMethod.ActiveTab)
        # elif int(keyboardModifiers & QtCore.Qt.ShiftModifier):
        #     self.applyUncommittedUrl(ApplyUrlMethod.NewWindow)
        # else:
        #     self.applyUncommittedUrl(ApplyUrlMethod.Apply)
                
    @Slot(str)
    def slotSchemeChanged(self, scheme:str):
        from protocols import ProtocolInfo
        if not self._editable_:
            return
        url = QtCore.QUrl()
        url.setScheme(scheme)
        
        # TODO: 2025-01-18 10:12:51
        # they use KProtocolInfo.protocolClass(scheme) - factory for a ProtocolInfo
        # currently, my implementation ALWAYS returns ":local"
        if ProtocolInfo.protocolClass(scheme) == ":local":
            url.setPath("/")
        else:
            url.setAuthority("")
        
        self._pathBox_.setEditUrl(url)
    
    @Slot()
    def openPathSelectorMenu(self):
        # KUrlNavigatorPrivate
        # NOTE: 2025-03-01 17:25:21
        # called by navigator drop down button
        if len(self._navButtons_) == 0:
            return
        print(f"{self.__class__.__name__}.openPathSelectorMenu")

        firstVisibleUrl = self._navButtons_[0].url()
        print(f"\tfirstVisibleUrl = {firstVisibleUrl}")

        spacer = ""

        dirName = ""

        placeUrl = self.retrievePlaceUrl()
        print(f"\tplaceUrl = {placeUrl}")


        ndx = placeUrl.path().count('/')

        myPath = self._coreUrlNavigator_.locationUrl(self._coreUrlNavigator_.historyIndex()).path()
        print(f"\tmyPath = {myPath}")
        pathParts = pathlib.Path(myPath).parts
        # BUG 2025-03-01 17:35:21 FIXME
        # on windows this si something like
        #  pathParts = ('\\', 'C:', 'Users')
        print(f"\tpathParts = {pathParts}")
        if ndx < len(pathParts):
            dirName = pathParts[ndx]

        print(f"\t dirName = {dirName}")

        if len(dirName) == 0:
            if placeUrl.isLocalFile():
                dirName = "This PC" if sys.platform.startswith("win32") else "/"
            else:
                dirName = placeUrl.toDisplayString()

        print(f"\t dirName = {dirName}")

        dirActionsDataMap = dict()
        
        k = 0
        while len(dirName) > 0:
            text = spacer + dirName
            # action = QtWidgets.QAction(text, popup)
            currentUrl = self.buttonUrl(ndx)
            dirActionsDataMap[text] = currentUrl
            
            if currentUrl == firstVisibleUrl:
                dirActionsDataMap[MISSING] = None
                # popup.addSeparator()
                
            # action.setData(currentUrl.toString())
            ndx += 1
            # if ndx >= len(pathParts):
            #     break
            
            k+=2
            spacer = " " * k
            
            if ndx < len(pathParts):
                dirName = pathParts[ndx]
            else:
                dirName = ""
                
        # print(f"{self.__class__.__name__}.openPathSelectorMenu: dirActionsDataMap = {dirActionsDataMap}")
        
        popup = QtWidgets.QMenu(self._nav_)
        
        popupFilter = UrlNavigatorPathSelectorEventFilter(popup) # FIXME
        popupFilter.tabRequested.connect(self._nav_.slot_pathSelectorEventFilterTabRequested) # FIXME -- ? we don't use tab navigation
        popup.installEventFilter(popupFilter)
        
        for key, val in dirActionsDataMap.items():
            if key is MISSING:
                popup.addSeparator()
            else:
                action = QtWidgets.QAction(key, popup)
                # NOTE: 2025-01-21 16:45:50
                # val is a QtCore.QUrl;
                # the action stores its string in data (in Qt a QVariant, but in
                # PyQt5 the conversion is done "behind the scenes")
                action.setData(val.toString()) 
                popup.addAction(action)
            
        pos = self._nav_.mapToGlobal(self._dropDownButton_.geometry().bottomRight())
        # print(f"{self.__class__.__name__}.openPathSelectorMenu: pos = {pos}")
        activatedAction = popup.exec(pos)
        if activatedAction is not None:
            # NOTE: 2025-01-21 16:43:02
            # in PyQt5, action data is NOT a QVariant (or rather the QVariant on
            # Qt side is already converted to the python type behind the scenes;
            # see also:
            #   NOTE: 2025-01-20 21:36:48 
            #   NOTE: 2025-01-21 16:45:50
            url = QtCore.QUrl(activatedAction.data()) 
            # url = QtCore.QUrl(activatedAction.data().toString())
            self._nav_.setLocationUrl(url)
            
        if popup is not None:
            popup.deleteLater() 
            
    def switchView(self, editable:typing.Optional[bool]=None):
        self._toggleEditableMode_.setFocus()
        self._editable_ = editable if isinstance(editable, bool) else not self._editable_
        self._toggleEditableMode_.setChecked(self._editable_)
        
        self.updateContent()
        
        if self._nav_.isUrlEditable():
            self._pathBox_.setFocus()
            
        self._nav_.requestActivation()
        self._nav_.editableStateChanged.emit(self._editable_)
        
    @Slot()
    def slotToggleEditableButtonPressed(self):
        if self._editable_:
            self.applyUncommittedUrl(ApplyUrlMethod.Apply)
            
        self.switchView()
        # NOTE: 2025-01-21 16:09:08
        # looks like I need to call this again, here...
        self.updateButtonVisibility()
        
    def dropUrls(self, destination:QtCore.QUrl, evt:QtGui.QDropEvent, dropButton:UrlNavigatorButton):
        # KUrlNavigatorPrivate
        if evt.mimeData().hasUrls():
            self._dropWidget_ = dropButton
            self._nav_.urlsDropped.emit(destination, evt)
            
    def applyUncommittedUrl(self, method:ApplyUrlMethod):
        # print(f"\{self.__class__.__name__}.applyUncommittedUrl")
        # KUrlNavigatorPrivate
        # NOTE: 2025-01-17 23:19:20
        # About method - we don't support Tabs in filesystem viewer
        # but we can launch the platform's file manager when method is NewWindow,
        # or "Tab"# do nothing for ActiveTab
        text = self._pathBox_.currentText().strip()
        # print(f"\ttext = {text}")
        url = self._nav_.locationUrl()

        # print(f"\tcurrent url = {url}, text = {text}")
        if text.startswith('/'):
            url.setPath(text)
        else:
            # url.setPath(pictio.concatPaths(url.path(), text).as_posix())
            newPath = pictio.concatPaths(dutils.urlToPath(url).as_posix(), text)
            # print(f"\tnewPath = {newPath}")
            if sys.platform.startswith("win32") and not newPath.is_absolute() and dutils.pathLen(newPath) == 1:
                drive = newPath.drive
                url.setPath("file://" + drive + "/")
            else:
                url.setPath(newPath.as_uri())

        # print(f"\tnew url = {url}")
        if os.path.isdir(url.path()):
            self.slotApplyUrl(url)
            return
        
        # NOTE: 2023-05-06 23:04:42
        # not sure we need this either...
        self.slotApplyUrl(QtCore.QUrl.fromUserInput(text))
        
    @Slot(QtCore.QUrl, QtCore.Qt.MouseButton, QtCore.Qt.KeyboardModifiers)
    def slotNavigatorButtonClicked(self, url:QtCore.QUrl, button:QtCore.Qt.MouseButton, modifiers:QtCore.Qt.KeyboardModifiers):
        # KUrlNavigatorPrivate
#         if ((button & QtCore.Qt.MiddleButton) and (modifiers & QtCore.Qt.ShiftModifier)) or ((button & QtCore.Qt.LeftButton) and (modifiers & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier))):
#             self._nav_.activeTabRequested.emit(url) # TODO: to trigger navigation in MainWindow
#             
#         # NOTE: 2023-05-07 22:02:07
#         # file system viewer does not support tabs
#         # elif (button & QtCore.Qt.MiddleButton) or ((button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ControlModifier)):
#         #     self._nav_.tabRequested.emit(url)
#         #    
#         # elif (button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ShiftModifier):
#         #     self._nav_.newWindowRequested.emit(url)
#             
#         elif ((button & QtCore.Qt.MiddleButton) or ((button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ControlModifier)) or ((button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ShiftModifier))):

        if ((button & QtCore.Qt.MiddleButton) or ((button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ControlModifier)) or ((button & QtCore.Qt.LeftButton) and (modifiers & QtCore.Qt.ShiftModifier))):
            self._nav_.newWindowRequested.emit(url) # TODO: 2025-01-19 09:08:04 open in platform app
            
        elif (button & QtCore.Qt.LeftButton):
            self._nav_.setLocationUrl(url)
    
    @Slot(QtCore.QPoint)
    def openContextMenu(self, p:QtCore.QPoint):
        """UrlNavigator's context menu
        Allows 
        • copy/paste of path, 
        • switching between edit mode and breadcrumb navigation mode, 
        • show path in full, or in places-reduced style (when in breadcrumb 
            navigation mode)
        """
        # KUrlNavigatorPrivate
        self._nav_.setActive(True)
        popup = QtWidgets.QMenu(self._nav_)
        
        copyAction = popup.addAction(QtGui.QIcon.fromTheme("edit-copy"), "Copy")
        
        pasteAction = popup.addAction(QtGui.QIcon.fromTheme("edit-paste"), "Paste")
        
        clipboard = QtWidgets.QApplication.clipboard()
        pasteAction.setEnabled(len(clipboard.text())> 0)
        
        popup.addSeparator()
        
        # // We are checking whether the signal is connected because it's odd to have a tab entry even
        # // if it's not supported, like in the case of the open dialog
        # const bool isTabSignal = q->isSignalConnected(QMetaMethod::fromSignal(&KUrlNavigator::tabRequested));
        # const bool isWindowSignal = q->isSignalConnected(QMetaMethod::fromSignal(&KUrlNavigator::newWindowRequested));

        # NOTE: QMetaMethod.fromSignal is NOT implemented in PyQt5
        # isTabSignal = self._nav_.isSignalConnected(QtCore.QMetaMethod.fromSignal(self._nav_.tabRequested)) # not used
        # isWindowSignal = self._nav_.isSignalConnected(QtCore.QMEtaMethod.fromSignal(self._nav_.newWindowRequested)) # not used
        
        isTabSignal = self._nav_.receivers(self._nav_.tabRequested) > 0
        isWindowSignal = self._nav_.receivers(self._nav_.newWindowRequested) > 0
        
        if isTabSignal or isWindowSignal:
            for button in self._navButtons_:
                if button.geometry().contains(p):
                    url = button.url()
                    text = button.text()
                    
                    if isTabSignal:
                        pass
                    
                    if isWindowSignal:
                        openInWindow = popup.addAction(QtGui.QIcon.fromTheme("window-new"), f"Open {text} in the system's file manager")
                        openInWindow.setData(url)
                        openInWindow.triggered.connect(self._nav_._slot_newWindowRequested_) # indirectly connects to signal newWindowRequested
                    
        editAction = popup.addAction("Edit")
        editAction.setCheckable(True)
        
        navigateAction = popup.addAction("Navigate")
        navigateAction.setCheckable(True)
        
        modeGroup = QtWidgets.QActionGroup(popup)
        modeGroup.addAction(editAction)
        modeGroup.addAction(navigateAction)
        
        if self._nav_.isUrlEditable():
            editAction.setChecked(True)
        else:
            navigateAction.setChecked(True)
            
        popup.addSeparator()
        
        showFullPathAction = popup.addAction("Show Full Path")
        showFullPathAction.setCheckable(True)
        showFullPathAction.setChecked(self._nav_.showFullPath())
        
        activatedAction = popup.exec(QtGui.QCursor.pos())
        
        if activatedAction  == copyAction:
            mimeData = QtCore.QMimeData()
            mimeData.setText(self._nav_.locationUrl().toDisplayString(QtCore.QUrl.PreferLocalFile))
            clipboard.setMimeData(mimeData)
            
        elif activatedAction == pasteAction:
            self._nav_.setLocationUrl(QtCore.QUrl.fromUserInput(clipboard.text()))
            
        elif activatedAction == editAction:
            self._nav_.setUrlEditable(True)
            
        elif activatedAction == navigateAction:
            self._nav_.setUrlEditable(False)
            self.updateButtonVisibility() # see NOTE: 2025-01-21 16:09:08
            
        elif activatedAction == showFullPathAction:
            self._nav_.setShowFullPath(showFullPathAction.isChecked())
            
        if popup is not None:
            popup.deleteLater()
            
    @Slot(str)
    def slotPathBoxChanged(self, text:str): # WARNING 2025-01-19 09:30:32 possible BUG
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
            # scheme = self._nav_.locationUrl().scheme()
            # if len(self._supportedSchemes_) != 1:
            #     self._schemes_.show()
            #
            # This is outside Scipyen's scope therefore I guess it is safe to
            # resture the current url here (for now).
            #
            # See also NOTE: 2023-05-06 22:30:13
            #
            # FIXME/TODO: 2023-05-07 22:52:54
            # the line editor of the url combo box will eventually contain 
            # editing tool buttons for example, to remove current text from
            # navigation history - in this case we DO NOT want to restore 
            # current url, but the next available one in the history.
            signalBlocker = QtCore.QSignalBlocker(self._pathBox_)
            url = QtCore.QUrl(pathlib.Path.cwd().as_uri())
            self._nav_.setLocationUrl(url)
            return
        # else:
            # self._schemes_.hide() # see NOTE: 2023-05-06 22:30:13
        
    def appendWidget(self, widget:QtWidgets.QWidget, stretch:int=0):
        # NOTE: 2023-05-08 11:04:33
        # CAUTION: does NOT append to self._navButtons_!!!
        # this must be done separately when appending a UrlNavigatorButton, see
        # NOTE: 2023-05-08 11:05:23
        self._layout_.insertWidget(self._layout_.count()-2, widget, stretch)
        
    def retrievePlaceUrl(self): # TODO/FIXME: 2023-05-07 23:09:25 ?!?
        # KUrlNavigatorPrivate
        # NOTE: 2025-01-20 11:31:36
        # create a new QUrl object, otherwise it WILL be modified (if passed by reference)
        # and mess up the actual location url (see NOTE 2025-01-20 11:31:01)
        url = QtCore.QUrl(self._nav_.locationUrl()) # to avoid modifying the underlining location url, 
        url.setPath("") # - why this !?!            # <- when calling this 
        # print(f"{self.__class__.__name__}.retrievePlaceUrl: currentUrl = {currentUrl}")
        return url
    
    @Slot()
    def switchToBreadcrumbMode(self):
        # KUrlNavigatorPrivate
        self._nav_.setUrlEditable(False)
        
    def buttonUrl(self, ndx:int) -> QtCore.QUrl:
        # print(f"{self.__class__.__name__}.buttonUrl: ndx = {ndx}")
        # KUrlNavigatorPrivate
        if ndx < 0:
            ndx = 0
            
        url = QtCore.QUrl(self._nav_.locationUrl()) # see NOTE 2025-01-20 11:31:01
                                                    # and NOTE: 2025-01-20 11:31:36
        # print(f"\tlocation url is {url}")
        # path:str = url.path()
        # path:str = dutils.urlToPath(url).as_posix()
        path:pathlib.Path = dutils.urlToPath(url)
        pathParts = path.parts

        # print(f"\tpathParts = {pathParts}")

        # print(f"\tpath = {path} ({type(path).__name__}), ndx = {ndx}")
        #
        # if sys.platform.startswith("win32"):
        #     if path.startswith("/"):
        #         path = path[1:]
        #         print(f"\tpath win32 = {path} ({type(path).__name__}), ndx = {ndx}")
        
        # if len(path):
        newPathStr = "/"
        
        if dutils.pathStrLen(path):
            if sys.platform.startswith("win32"):
                if ndx == 0:
                    # newPathStr = "file:///" + path.drive
                    return QtCore.QUrl.fromLocalFile(path.drive)
                else:
                    newPath = pathlib.Path.joinpath(*list(map(lambda x: pathlib.Path(x), pathParts[:ndx+1])))
                    if newPath.is_absolute():
                        newUrl = QtCore.QUrl(newPath.as_uri())
                    else:
                        newUrl = QtCore.QUrl.fromLocalFile(newPath.as_posix())

                    return newUrl

                    # newPathStr = "file:///" + newPath.as_posix()
            else:
                if ndx == 0:
                    newPathStr = "/"

                else:
                    # pathParts = path.split("/")
                    newPath = pathlib.Path.joinpath(*list(map(lambda x: pathlib.Path(x), pathParts[:ndx+1])))
                    newPathStr = "/".join(pathParts[:ndx+1])

                    # path = "/".join(pathParts[ndx:])
                # print(f"\tsetting path '{newPathStr}' for url: {url}")
                url.setPath(newPathStr)
                return url

        # url.setPath(path)
        # url.setPath(newPathStr)

        # print(f"\treturns url: {url}")
        return url
    
    def deleteButtons(self):
        # KUrlNavigatorPrivate
        for button in self._navButtons_:
            button.hide()
            button.deleteLater()
            
        self._navButtons_.clear()
    
    def updateContent(self):
        # KUrlNavigatorPrivate  
        # print(f"\n{self.__class__.__name__}.updateContent")
        # print(f"\teditable: {self._editable_}")
        currentUrl = self._nav_.locationUrl()

        # NOTE: 2025-01-24 21:22:27 CMT
        self._closestPlace_ = dutils.closestPlace(currentUrl)
        # print(f"\tself._closestPlace_ {self._closestPlace_}")
        # print(f"{self.__class__.__name__}.updateContent(): currentUrl = {currentUrl}")
        # print(f"\tself._placesSelector_ {self._placesSelector_}")
        # WARNING: 2025-01-20 22:32:18 temporary -- FIXME
        # TODO: Implement places selector
        if self._placesSelector_ is not None:
            self._placesSelector_.updateSelection(currentUrl)

        # print(f"\tself._editable_ {self._editable_}")
        if self._editable_:
            # self._schemes_.hide() # see NOTE: 2023-05-06 22:30:13
            self._dropDownButton_.hide()
            self._badgeWidgetContainer_.hide()

            self.deleteButtons() # clear the breadcrumbs

            self._toggleEditableMode_.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                                    QtWidgets.QSizePolicy.Preferred)

            self._nav_.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                    QtWidgets.QSizePolicy.Fixed)

            self._pathBox_.show()
            self._pathBox_.setUrl(currentUrl)
            # print(f"\tself._pathBox_.urls: {self._pathBox_.urls()}")

        else:
            self._pathBox_.hide()
            # self._dropDownButton_.show()
            self._badgeWidgetContainer_.show()

            # self._schemes_.hide() # see NOTE: 2023-05-06 22:30:13
            self._toggleEditableMode_.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                    QtWidgets.QSizePolicy.Preferred)

            self._nav_.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                    QtWidgets.QSizePolicy.Fixed)

            placeUrl = QtCore.QUrl()

            if sys.platform.startswith("win32"): # ?!?
                placeUrl = currentUrl

            # ### BEGIN NOTE: 2025-01-24 21:18:58 CMT reinstate this once
            # a PlacesModel/PlacesSelector become available
            # if self._placesSelector_ is not None and not self._showFullPath_:
            #     placeUrl = self._placesSelector_.selectedPlaceUrl()
            # else:
            #     placeUrl = currentUrl
            # ### END   NOTE: 2025-01-24 21:18:58 CMT reinstate this once there will be a PlacesModel/PlacesSelector

            if not self._showFullPath_ and isinstance(self._closestPlace_, dutils.DEPlace):
                placeUrl = self._closestPlace_.url
            else:
                placeUrl = currentUrl


            if not placeUrl.isValid():
                placeUrl = self.retrievePlaceUrl()

            # print(f"\tvalid placeUrl =  {placeUrl}")
            # placePath = trailingSlashRemoved(placeUrl.path())
            placePath = dutils.urlToPath(placeUrl)
            placePathStr = trailingSlashRemoved(placePath.as_posix())

            if sys.platform.startswith("win32"):
                drive = placePath.drive
                placePathStr = placePathStr[len(drive):]
            else:
                drive = ""


            startIndex = placePathStr.count('/')
            # print(f"\tshowFullPath: {self._showFullPath_}, closestPlace: {self._closestPlace_}")
            # print(f"\tcurrentUrl = {currentUrl}, placeUrl = {placeUrl}, placePathStr =  {placePathStr}, drive = {drive}, startIndex =  {startIndex}")

            # # if sys.platform.startswith("win32"):
            # #     startIndex = len(placePath.parts)
            # # else:
            # #     startIndex = placePathStr.count('/')
            # # print(f"\tstartIndex =  {startIndex}")

            # NOTE: 2025-02-05 15:06:38
            # RE BUG 2025-02-05 14:50:50 FIXME:
            # the following forces redraw of all buttons when full path must be
            # shown
            if self._showFullPath_ or not isinstance(self._closestPlace_, dutils.DEPlace):
                startIndex = 0
            
            self.updateButtons(startIndex)
            
    def updateButtons(self, startIndex:int): # NOTE: 2023-05-08 11:05:23 FIXME
        # print(f"{self.__class__.__name__}.updateButtons({startIndex}):")
        # KUrlNavigatorPrivate  
        currentUrl = self._nav_.locationUrl() # NOTE 2025-01-20 11:31:01 this must NOT be modified 
                                              # see NOTE: 2025-01-20 11:31:36
        # print(f"\tcurrentUrl: {currentUrl}")
        if not currentUrl.isValid():
            return
        
        # path = currentUrl.path()
        path = dutils.urlToPath(currentUrl)
        # print(f"\tpath = {path} ({type(path).__name__})")

        pathStr = trailingSlashRemoved(path.as_posix())

        if sys.platform.startswith("win32"):
            drive = path.drive
            pathStr = pathStr[len(drive):]
        else:
            drive = ""

        # if sys.platform.startswith("win32"):
        #     if path.startswith("/"):
        #         path = path[1:]
        
        oldButtonCount = len(self._navButtons_)
        # print(f"\toldButtonCount = {oldButtonCount}")
        
        ndx = startIndex
        
        hasNext = True # this flags whether there should be another button
        
        pathParts = path.parts
        # pathParts = pathlib.Path(path).parts
        # print(f"\tpathParts = {pathParts} ({len(pathParts)} elements)")
        
        _k_ = 0
        
        # print(f"\tndx = {ndx}, startIndex = {startIndex}, hasNext = {hasNext}")
        # print(f"\twhile hasNext BEGIN\n\n")
        
        while hasNext:
            # print(f"\t\t_k_ = {_k_}, ndx = {ndx}:")
            if ndx >= len(pathParts): # reached end of pathParts
                # print(f"\t\t{ndx} >= {len(pathParts)} -> while haxNext BREAK")
                break
            
            createButton = ((ndx - startIndex) >= oldButtonCount)
            isFirstButton = (ndx == startIndex)
            # print(f"\t\tcreateButton = {createButton}, isFirstButton = {isFirstButton}")

            # if ndx >= len(pathParts):
            # if ndx >= len(pathParts) - 1:
            #     hasNext = False

            dirName = pathParts[ndx] # directory currently pointed to by the button
            # NOTE: when ndx < len(parParts)-1, ndx+1 should be the active subdirectory
            # and the one pointed to by the next button
            
            # print(f"\t\tdirName = {dirName}")

            hasNext = isFirstButton or len(dirName) > 0
            
            if hasNext:
                button = None
                if createButton:
                    # print(f"\t\t{printStyled('**creating button**', color='red')}")
                    # print(f"\t\tgetting the url for a new button:")
                    urlForButton = self.buttonUrl(ndx)
                    # print(f"\t\tcreating button with url: {urlForButton}")
                    button = UrlNavigatorButton(urlForButton, None, self._nav_)
                    button.installEventFilter(self._nav_)
                    button.setForegroundRole(QtGui.QPalette.WindowText)
                    button.urlsDroppedOnNavButton.connect(self._nav_._slot_dropUrls) # CMT: wraps to dropUrls
                    # button.navigatorButtonActivated.connect(self._slot_navigatorButtonActivated)
                    button.navigatorButtonActivated.connect(self.slotNavigatorButtonClicked)
                    button.finishedTextResolving.connect(self.updateButtonVisibility)

                    # print(f"\t\tappending the new button")
                    self.appendWidget(button)

                else:
                    btn_ndx = ndx-startIndex
                    # print(f"\t\t{printStyled('**reusing button**', color='yellow')} {btn_ndx}")
                    button = self._navButtons_[btn_ndx]
                    # button = self._navButtons_[ndx-startIndex]
                    urlForButton = self.buttonUrl(ndx)
                    # print(f"\t\tsetting the url '{urlForButton}' at ndx {ndx} for existing button at [{btn_ndx}]")
                    button.setUrl(urlForButton)
                    if ndx == len(pathParts)-1:
                        button.setActiveSubDirectory("")
                    
                if isFirstButton:
                    # NOTE: 2025-02-25 17:59:51
                    # responsible for displaying the name of the closest
                    # place in the button, when NOT showing the full path
                    textForFirstButton = self.firstButtonText()
                    # print(f"\t\tsetting the text '{textForFirstButton}' for the first button")
                    button.setText(textForFirstButton)
                    
                
                # print(f"\t\tsetting the button active state")
                button.setActive(self._nav_.isActive())
                
                if createButton:
                    if not isFirstButton:
                        # NOTE: 2025-01-19 09:44:27 
                        # sets order in which idgets are focussed when pressing the Tab key
                        self._nav_.setTabOrder(self._navButtons_[-1], button)
                        
                    self._navButtons_.append(button)
                    
            ndx += 1
            if ndx < len(pathParts):
                # print(f"\t\tset active subdirectory '{pathParts[ndx]}' for button {ndx}")
                button.setActiveSubDirectory(pathParts[ndx])
            
            _k_ += 1
            # ndx += 1
            # print(f"\t\thasNext = {hasNext}")
        
            # print(f"\t\tdirName = {dirName}, hasNext = {hasNext}")
            if not hasNext:
                # print(f"\t\tnot hasNext -> BREAK")
                break
            
            # print("\t\t>>>NEXT STEP<<<\n\n")
            
        # print(f"\twhile hasNext END -> _k_ = {_k_}")
        newButtonCount = ndx - startIndex
        
        if newButtonCount < oldButtonCount:
            for button in self._navButtons_[newButtonCount:]:
                button.hide()
                button.deleteLater()
                
            self._navButtons_ = self._navButtons_[:newButtonCount]
            
        if len(self._navButtons_) > 0:
            self._nav_.setTabOrder(self._dropDownButton_, self._navButtons_[0])
            self._nav_.setTabOrder(self._navButtons_[-1], self._toggleEditableMode_)
        
        ptxt = currentUrl.toDisplayString(QtCore.QUrl.RemoveScheme | QtCore.QUrl.NormalizePathSegments | QtCore.QUrl.RemoveAuthority).replace("///", "/");
        
        self._dropDownButton_.setToolTip(f"Go to any location on the path {ptxt}")
        self.updateButtonVisibility()
            
    def updateButtonVisibility(self):
        if self._editable_:
            return
        
        buttonsCount = len(self._navButtons_)
        if buttonsCount == 0:
            self._dropDownButton_.hide()
            return
        
        availableWidth = self._nav_.width() - self._toggleEditableMode_.minimumWidth()
        
        availableWidth -= self._badgeWidgetContainer_.width()
        
        if self._placesSelector_ is not None and self._placesSelector_.isVisible():
            availableWidth -= self._placesSelector_.width()
            
        if self._schemes_ is not None and self._schemes_.isVisible():
            availableWidth -= self._schemes_.width()
            
        requiredButtonWidth = sum(map(lambda x: int(x.minimumWidth()), self._navButtons_))
        
        if requiredButtonWidth > availableWidth:
            # see KIO class: at least one button must be hidden, therefore we must show the
            # dropdown button (which will use up some available space)
            availableWidth -= self._dropDownButton_.width()
            
        # Hide buttons ...
        isLastButton = True
        hasHiddenButtons = False
        
        buttonsToShow = list()

        # NOTE: 2025-01-21 15:02:59 reverse iteration below:
        # for (auto it = m_navButtons.crbegin(); it != m_navButtons.crend(); ++it) // C++
        for button in reversed(self._navButtons_): 
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
            
            # FIXME 2025-01-20 16:51:28 ajust according to "place"
            visible = (not url.matches(upUrl(url), QtCore.QUrl.StripTrailingSlash)) and url.scheme() not in ("baloosearch", "filenamesearch")
            self._dropDownButton_.setVisible(visible)
            
        self.updateTabOrder()
            
    def updateTabOrder(self):
        visibleChildrenSortexByX = list()
        childWidgets = self._nav_.findChildren(QtWidgets.QWidget)
        for childWidget in childWidgets:
            if childWidget.isVisible():
                visibleChildrenSortexByX.append(childWidget)
                
        if len(visibleChildrenSortexByX) == 0:
            return
        
        visibleChildrenSortexByX = sorted(visibleChildrenSortexByX, key = lambda x: x.x(), reverse = self._nav_.layoutDirection() != QtCore.Qt.LeftToRight)
            
        self._nav_.setFocusProxy(visibleChildrenSortexByX[0])
        for k in range(len(visibleChildrenSortexByX)-1):
            self._nav_.setTabOrder(visibleChildrenSortexByX[k], visibleChildrenSortexByX[k+1])
                    
    def firstButtonText(self):
        # KUrlNavigatorPrivate
        # print(f"{self.__class__.__name__}.firstButtonText")
        text = ""

        # ### BEGIN NOTE: 2025-01-24 21:38:14 CMT reinstate this once placesmodel module is finalized
        # if self._placesSelector_ is not None and not self._showFullPath_:
        #     text = self._placesSelector_.selectedPlaceText()
        # ### END   NOTE: 2025-01-24 21:38:14 CMT reinstate this once placesmodel module is finalized

        if isinstance(self._closestPlace_, dutils.DEPlace) and not self._showFullPath_:
            text = self._closestPlace_.name

        # print(f"\ttext from closest place = {text}")

        currentUrl = self._nav_.locationUrl()
        
        if len(text) == 0:
            if currentUrl.isLocalFile():
                if sys.platform.startswith("win32"):
                    urlPath = dutils.urlToPath(currentUrl)
                    drive = urlPath.drive
                    text = drive if len(drive) else QtCore.QDir.rootPath()
                    # text = currentUrl.path()[:2] if len(currentUrl.path()) > 1 else QtCore.QDir.rootPath()
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


class UrlNavigator(QtWidgets.QWidget):
    """Implementation of KIO KUrlNavigator
    """
        
    # ### BEGIN signals
    #
    activated               = Signal(name = "activated")
    
    # ATTENTION: 2025-01-20 22:20:07
    # connect this signal (urlChanged) to an appropriate slot in ScipyenWindow or
    # the filesystemModel/fileSystemViewer in ScipyenWindow
    urlChanged              = Signal(QtCore.QUrl, name="urlChanged")
    urlAboutToBeChanged     = Signal(QtCore.QUrl, name = "urlAboutToBeChanged")
    editableStateChanged    = Signal(bool, name = "editableStateChanged")
    historyChanged          = Signal(name = "historyChanged")
    urlsDropped             = Signal(QtCore.QUrl, QtGui.QDropEvent, name = "urlsDropped")
    returnPressed           = Signal(name = "returnPressed")
    
    # NOTE: 2023-05-07 22:03:17
    # Scipyen's file system viewer does not support tabs
    tabRequested            = Signal(QtCore.QUrl, name = "tabRequested")
    activeTabRequested      = Signal(QtCore.QUrl, name = "activeTabRequested")
    
    # NOTE: 2023-05-07 22:03:37
    # this should open the url in the system's default application
    newWindowRequested      = Signal(QtCore.QUrl, name = "newWindowRequested")
    urlSelectionRequested   = Signal(QtCore.QUrl, name = "urlSelectionRequested")
    #
    # ### END signals
    
    # ### BEGIN __init__ UrlNavigator c'tor 
    def __init__(self, placesModel:typing.Optional[PlacesModel]=None,
                 url:typing.Optional[QtCore.QUrl]=None, 
                 parent:typing.Optional[QtWidgets.QWidget] = None):
        if isinstance(placesModel, QtCore.QUrl):
            if isinstance(url, QtWidgets.QWidget):
                parent = url
            url = placesModel
            placesModel = None
        
        super().__init__(parent=parent)
        
        self._nav_p_ = _UrlNavigator_(url, self, placesModel)

        # NOTE:2023-05-03 08:14:35 
        self.setMinimumHeight(self._nav_p_._pathBox_.sizeHint().height())
        self.setMinimumWidth(100)
        self._nav_p_.updateContent()
    # ### END   __init__ UrlNavigator c'tor 
        
    def __del__(self):
        self._nav_p_._dropDownButton_.removeEventFilter(self)
        self._nav_p_._pathBox_.removeEventFilter(self)
        self._nav_p_._toggleEditableMode_.removeEventFilter(self)
        
        for button in self._nav_p_._navButtons_:
            button.removeEventFilter(self)
        
    # TODO 2025-01-19 10:28:19 for below,
    # verify CoreUrlNavigator code
    def locationUrl(self, historyIndex:int = -1) -> QtCore.QUrl: 
        return self._nav_p_._coreUrlNavigator_.locationUrl(historyIndex)
    
    # TODO 2025-01-19 10:28:19 for below,
    # verify CoreUrlNavigator code
    @safeWrapper
    def saveLocationState(self, state:QtCore.QByteArray):
        # print(f"{self.__class__.__name__}.saveLocationState({state})")
        currentState = self._nav_p_._coreUrlNavigator_.locationState()
        self._nav_p_._coreUrlNavigator_.saveLocationState(currentState)
        
    # TODO 2025-01-19 10:28:19 for below,
    # verify CoreUrlNavigator code
    @safeWrapper
    def locationState(self, historyIndex:int = -1) -> QtCore.QByteArray:
        return self._nav_p_._coreUrlNavigator_.locationState(historyIndex)
        
    def goBack(self):
        return self._nav_p_._coreUrlNavigator_.goBack()
    
    def goForward(self):
        return self._nav_p_._coreUrlNavigator_.goForward()
    
    def goUp(self):
        return self._nav_p_._coreUrlNavigator_.goUp()
    
    def goHome(self):
        if not isinstance(self._nav_p_._homeUrl_, QtCore.QUrl) or self._nav_p_._homeUrl_.isEmpty() or not self._nav_p_._homeUrl_.isValid():
            url = QtCore.QUrl.fromLocalFile(QtCore.QDir.homePath())
        else:
            url = self._nav_p_._homeUrl_
            
        self.setLocationUrl(url)
        self.urlChanged.emit(url)
            
    def setHomeUrl(self, url:QtCore.QUrl):
        self._nav_p_._homeUrl_ = url
        
    def homeUrl(self) -> QtCore.QUrl:
        return self._nav_p_._homeUrl_
    
    def setUrlEditable(self, editable:bool):
        if self._nav_p_._editable_ != editable:
            # self._nav_p_.switchView2(editable)
            self._nav_p_.switchView()
            
    def isUrlEditable(self) -> bool:
        return self._nav_p_._editable_
    
    def setShowFullPath(self, show:bool):
        if self._nav_p_._showFullPath_ != show:
            self._nav_p_._showFullPath_ = show
            self._nav_p_.updateContent()
            
    def showFullPath(self) -> bool:
        return self._nav_p_._showFullPath_
    
    def setActive(self, active:bool):
        if active != self._nav_p_._active_:
            self._nav_p_._active_ = active
            
            self._nav_p_._dropDownButton_.setActive(active)
            
            for button in self._nav_p_._navButtons_:
                button.setActive(active)
                
            self.update()
            
            if active:
                self.activated.emit()
                
    def isActive(self) -> bool:
        return self._nav_p_._active_
    
    def setPlacesSelectorVisible(self, visible:bool):
        if visible == self._nav_p_._showPlacesSelector_:
            return
        
        if visible and self._nav_p_._placesSelector_ is None:
            # places selector is None when no places model is available
            return
        
        self._nav_p_._showPlacesSelector_ = visible
        self.__d_._placesSelector_.setVisible(visible)
        
    def isPlacesSelectorVisible(self) -> bool:
        return self._nav_p_._showPlacesSelector_
    
    def uncommittedUrl(self) -> QtCore.QUrl:
        pass # TODO/FIXME implement KUriFilter functionality
    
    @Slot(QtCore.QUrl)
    def setLocationUrl(self, url:QtCore.QUrl):
        if url != self.locationUrl():
            # print(f"Slot {self.__class__.__name__}.setLocationUrl({url})")
            self._nav_p_._coreUrlNavigator_.setCurrentLocationUrl(url)
            # WARNING 2025-01-20 22:44:08 temporary FIXME
            # TODO implement places selector
            self._nav_p_.updateContent()
            # self.setShowFullPath(True)  
            # self.requestActivation()
    
    @Slot()
    def requestActivation(self):
        self.setActive(True)
    
    @Slot()
    def setFocus(self):
        if self.isUrlEditable():
            self._nav_p_._pathBox_.setFocus()
        else:
            super().setFocus()
    
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
        evt.accept()
        
    def mouseReleaseEvent(self, evt:QtGui.QMouseEvent):
        if evt.button() == QtCore.Qt.MiddleButton:
            bounds = self._nav_p_._toggleEditableMode_.geometry()
            if bounds.contains(evt.pos()):
                clipboard = QtWidgets.QApplication.clipboard()
                mimeData = clipboard.mimeData()
                if mimeData.hasText():
                    text = mimeData.text()
                    self.setLocationUrl(QtCore.QUrl.fromUserInput(text))
                    
        super().mouseReleaseEvent(evt)
        evt.accept()
        
    def resizeEvent(self, evt:QtGui.QResizeEvent):
        QtCore.QTimer.singleShot(0, self._nav_p_.updateButtonVisibility)
        
        super().resizeEvent(evt)
        
    def wheelEvent(self, evt:QtGui.QWheelEvent):
        self.setActive(True)
        super().wheelEvent(evt)
        
    def eventFilter(self, watched:QtCore.QObject, evt:QtCore.QEvent) -> bool:
        eType = evt.type()
        
        if eType == QtCore.QEvent.FocusIn:
            if watched == self._nav_p_._pathBox_:
                self.requestActivation()
                self.setFocus()
                
            for button in self._nav_p_._navButtons_:
                button.setShowMnemonic(True)
                
        elif eType == QtCore.QEvent.FocusOut:
            for button in self._nav_p_._navButtons_:
                button.setShowMnemonic(False)
                
        elif eType == QtCore.QEvent.ShortcutOverride:
            if (evt.key() == QtCore.Qt.Key_Enter or evt.key() == QtCore.Qt.Key_Return) and (evt.modifiers() & QtCore.Qt.AltModifier or evt.modifiers() & QtCore.Qt.ShiftModifier):
                evt.accept()
                return True
                
        return super().eventFilter(watched, evt)
    
    def historySize(self):
        return self._nav_p_._coreUrlNavigator_.historySize()
    
    def historyIndex(self):
        return self.__d_._coreUrlNavigator_.historyIndex()
    
    def editor(self):
        return self._nav_p_._pathBox_
    
    def setCustomProtocols(self, protocols:typing.List[str]):
        self._nav_p_._customProtocols_[:] = [protocols]
        # self._schemes_.setCustomProtocols(self._customProtocols_) # TODO/FIXME
        
    def customProtocols(self):
        return self._nav_p_._customProtocols_
    
    def dropWidget(self):
        return self._nav_p_._dropWidget_
    
    def setShowHiddenFolders(self, showHiddenFolders:bool):
        self._nav_p_._subfolderOptions_.showHidden = showHiddenFolders
        
    def showHiddenFolders(self) -> bool:
        return self._nav_p_._subfolderOptions_.sortHiddenLast
        
    def setSortHiddenFoldersLast(self, sortHiddenFoldersLast:bool):
        self._nav_p_._subfolderOptions_.sortHiddenLast = showHidden
        
    def sortHiddenFoldersLast(self) -> bool:
        return self._nav_p_._subfolderOptions_.sortHiddenLast
    
    def setSupportedSchemes(self, schemes:list):
        self._nav_p_._supportedSchemes_[:] = schemes
        self._nav_p_.schemes.setSupportedSchemes(self._nav_p_._supportedSchemes_)
        
    def supportedSchemes(self) -> list:
        return self._nav_p_._supportedSchemes_
        
    def setBadgeWidget(self, widget:QtWidgets.QWidget):
        oldWidget = self.badgeWidget()
        if isinstance(oldWidget, QtWidgets.QWidget):
            if oldWidget == widget:
                return
            
            self._nav_p_._badgeWidgetContainer_.layout().replaceWidget(oldWidget, widget)
            oldWidget.deleteLater()
        else:
            self._nav_p_._badgeWidgetContainer_.layout().addWidget(widget)
            
    def badgeWidget(self) -> QtWidgets.QWidget | None:
        item = self._nav_p_._badgeWidgetContainer_.layout().itemAt(0)
        if item is not None:
            return item.widget()
        else:
            return None
        
    
    # ### BEGIN Slots
    @Slot()
    def slot_returnPressed(self):
        # NOTE: 2025-01-17 23:21:55 no support for Tabs
        # therefore either apply url here or open platform's default appliuation
        keyboardModifiers = QtWidgets.QApplication.keyboardModifiers()
        
        if int(keyboardModifiers & QtCore.Qt.ShiftModifier):
            self._nav_p_.applyUncommittedUrl(ApplyUrlMethod.NewWindow) # -> open in application
            
        elif int(keyboardModifiers & QtCore.Qt.ControlModifier):
            self._nav_p_.switchToBreadcrumbMode()
            self._nav_p_.updateButtonVisibility()
            # self._sig_switchToBreadCrumbMode.emit()
            
        else:
            self._nav_p_.applyUncommittedUrl(ApplyUrlMethod.Apply) # navigate here
            self._nav_p_.switchToBreadcrumbMode()
            self._nav_p_.updateButtonVisibility()
            # self._nav_.returnPressed.emit()
            
        # indirection to emitting returnPressed
        # self.applyUncommittedUrl()
        self.returnPressed.emit()
        
        # if QtWidgets.QApplication.KeyboardModifiers() & QtCore.Qt.ControlModifier:
        #     self.switchToBreadcrumbMode()
            
    @Slot(QtCore.QUrl, QtGui.QDropEvent) # CMT
    def _slot_dropUrls(self, url:QtCore.QUrl, evt:QtGui.QDropEvent):
        button = self.sender()
        if isinstance(button, UrlNavigatorButton):
            self.dropUrls(url, evt, button)
            
    @Slot(QtCore.QUrl, QtCore.Qt.KeyboardModifiers)
    def _slot_navigatorButtonActivated(self, url:QtCore.QUrl, modifiers:QtCore.Qt.KeyboardModifiers):
        # button = self.sender()
        btn = QtWidgets.QApplication.mouseButtons()
        
        # FIXME 2025-01-19 09:39:32 
        # use reference to _UrlNavigator_
        self.slotNavigatorButtonClicked(url, btn, modifiers)
        
    # @Slot(str)
    # def slotProtocolChanged(self, protocol:str):
    #     pass # TODO
    
    @Slot()
    def _slot_historyChanged(self):
        self.historyChanged.emit()
    
    @Slot()
    def _slot_newWindowRequested_(self):
        action = self.sender()
        url = QtCore.QUrl(action.data().toString())
        if url.isValid():
            self.newWindowRequested.emit(url)
    
#     @Slot(QtCore.QUrl)
#     def setUrl(self, url:QtCore.QUrl):
#         pass # TODO DEPRECATED
#     
#     @Slot(QtCore.QUrl)
#     def saveRootUrl(self, url:QtCore.QUrl):
#         pass # TODO DEPRECATED
#     
#     @Slot(int, int)
#     def savePosition(self, x:int, y:int):
#         pass # TODO DEPRECATED
    
    @Slot()
    def slot_coreUrlNavigatorUrlChanged(self):
        self._nav_p_.updateContent() # !
        self.urlChanged.emit(self._nav_p_._coreUrlNavigator_.currentLocationUrl())
        
    @Slot(QtCore.QUrl)
    def slot_coreUrlNavigatorUrlAboutToBeChanged(self, url):
        self.urlAboutToBeChanged.emit(url)
        
    @Slot(QtCore.QUrl)
    def slot_coreUrlNavigatorUrlSelectionRequested(self, url:QtCore.QUrl):
        self.urlSelectionRequested.emit(url)
        
    @Slot(QtCore.QUrl)
    def slot_pathSelectorEventFilterTabRequested(self, url:QtCore.QUrl):
        self.tabRequested.emit(url)
    
    @Slot(str)
    def slotSchemeChanged(self, scheme:str): # TODO
        pass
        
    
    # ### END Slots

    # ### BEGIN New methods by CMT
    def lineEdit(self) -> QtWidgets.QLineEdit():
        return self._nav_p_._pathBox_
    
    @singledispatchmethod
    def addLocationHistory(self, obj:typing.Any):
        raise NotImplementedError
    
    @addLocationHistory.register(str)
    @addLocationHistory.register(QtCore.QUrl)
    @addLocationHistory.register(pathlib.Path)
    def _(self, loc:typing.Union[str, QtCore.QUrl, pathlib.Path]):
        location = pathToLocation(loc)
        
        if location not in self._nav_p_._coreUrlNavigator_._oldSessionsHistory_:
            self._nav_p_._coreUrlNavigator_._oldSessionsHistory_.append(pathToLocation(loc))
        
    @addLocationHistory.register(list)
    @addLocationHistory.register(deque)
    def _(self, loc:typing.Union[list, deque]):
        # add mainwindows recentDirectories:
        try:
            locations = list(filter(lambda x: x not in self._nav_p_._coreUrlNavigator_._oldSessionsHistory_, map(lambda x: pathToLocation(x), loc)))
            self._nav_p_._coreUrlNavigator_._oldSessionsHistory_.extend(locations)
        except:
            traceback.print_exc()
        
    # ### END   New methods by CMT
