# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: Cezar M. Tigaret 2025 <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, pathlib, urllib, typing, warnings, subprocess, traceback
import core.xmlutils as xmlutils
import iolib.pictio as pio
import xml.etree.ElementTree as ET
from enum import Enum, IntEnum
from functools import (singledispatch, singledispatchmethod)

from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

from core.utilities import timelineDateString
from core.desktoputils import (get_desktop_places, get_recent_places, 
                               local_recent_places, iconNameForUrl,
                               get_system_terminal_executable,
                               get_trash_icon_name,
                               get_my_desktop_session,
                               get_local_filesystem_places,
                               removeAcceleratorMarker,
                               removeReducedCJKAccMark,
                               isFileIndexingEnabled, DEPlace, PlacesMap)

from systems.devices.device import Device

HAS_PYXDG = False
# HAS_XDGSPEC = False
try:
    import xdg # CAUTION this is from pyxdg
    HAS_PYXDG = True
    
except:
    pass

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class AdditionalRoles(IntEnum):
    UrlRole = 0x069CD12B
    HiddenRole = 0x0741CAAC
    SetupNeededRole = 0x059A935D
    CapacityBarRecommendedRole = 0x1548C5C4
    GroupRole = 0x0a5b64ee
    IconNameRole = 0x00a45c00
    GroupHiddenRole = 0x21a4b936
    TeardownAllowedRole = 0x02533364
    EjectAllowedRole = 0x0A16AC5B
    TeardownOverlayRecommendedRole = 0x032EDCCE
    DeviceAccessibilityRole = 0x023FFD93

class GroupType:pass
GroupType = IntEnum("GroupType",
                    ["PlacesType",
                    "RemoteType",
                    "RecentlySavedType",
                    "SearchForType",
                    "DevicesType",
                    "RemovableDevicesType",
                    "UnknownType",
                    "TagsType"]
                    )

class DeviceAccessibility:pass
DeviceAccessibility = IntEnum("DeviceAccessibility",
                                ["SetupNeeded",
                                "SetupInProgress",
                                "Accessible", 
                                "TeardownInProgress"]
                                )

def stateNameForGroupType(groupType:GroupType):
    if groupType == GroupType.PlacesModel:
        return "GroupState-Places-IsHidden"
    elif groupType == GroupType.RemoteType:
        return "GroupState-Remote-IsHidden"
    elif groupType == GroupType.RecentlySavedType:
        return "GroupState-RecentlySaved-IsHidden"
    elif groupType == GroupType.SearchForType:
        return "GroupState-SearchFor-IsHidden"
    elif groupType == GroupType.RemovableDevicesType:
        return "GroupState-RemovableDevices-IsHidden"
    elif groupType == GroupType.TagsType:
        return "GroupState-Tags-IsHidden"
    else:
        return ""

def createTimelineUrl(url:QtCore.QUrl):
    timelinePrefix = "timeline:/"
    path = url.toDisplayString(QtCore.QUrl.PreferLocalFile)
    
    if path.endswith("/yesterday"):
        date = QtCore.QDate.currentDate().addDays(-1)
        year = date.year()
        month = date.month()
        day = date.day()
        
        timelineUrl = QtCore.QUrl(timelinePrefix + timelineDateString(year, month) + '/' + timelineDateString(yea, month, day))
        
    elif path.endswith("/thismonth"):
        date = QtCore.QDate.currentDate()
        timelineUrl = QtCore.QUrl(timelinePrefix + timelineDateString(date.year(), date.month()))
        
    elif path.endswith("/lastmonth"):
        date = QtCore.QDate.currentDate().addMonths(-1)
        timelineUrl = QtCore.QUrl(timelinePrefix + timelineDateString(date.year(), date.month()))
    else:
        assert path.endswith("/today")
        timelineUrl = url
        
    return timelineUrl
        
def createSearchUrl(url:QtCore.QUrl):
    path = url.toDisplayString(QtCore.QUrl.PreferLocalFile)
    validSearchPaths = ["/documents", "/images", "/audio", "/videos"]
    searchUrl = QtCore.QUrl()
    for validPath in validSearchPaths:
        if path.endswith(validPath):
            searchUrl.setScheme("baloosearch")
            return searchUrl
        
    warnings.warn(f"Invalid search url: {url.toString()}")
    
    return searchUrl

def findByAddress(address:str):
    places = get_desktop_places()
    return places.get(address, None)

class PlacesModel:pass

class PlacesItem(QtCore.QAbstractItemModel):
    """Thin port of KFilePlacesItem.
    Has no, or partial, functionality related to the Trash (Wastebin) protocol, 
    the KDE Solid framework, and special KIO protocols (e.g. kdeconnect:/, 
    remote:/, etc.)
    
    """
    
    itemChanged = Signal(str, list, name="itemChanged") # str, list[int]
    
    def __init__(self, address:str, udi:str, parent:PlacesModel):
        super().__init__(parent)
        self._bookmark_ = findByAddress(address) # may be None!
        self._manager_ = None # TODO
        self._folderIsEmpty_:bool = True
        self._isCdrom_:bool = False
        self._isAccessible_:bool = False
        self._isTearDownAllowed_:bool = False
        self._isTearDownOverlayRecommended_:bool = False
        self._isTearDownInProgress_:bool = False
        self._isSetupInProgress_:bool = False
        self._isEjectionInProgress_:bool = False
        self._isReadOnly_:bool = False
        self._text_:str = str()
        
        # NOTE: 2025-02-05 22:42:58 TODO
        # ### BEGIN all these below are Solid framework
        self._device_ = None # TODO 
        self._access_ = None # TODO
        self._volume_ = None  # TODO
        self._drive_ = None  # TODO
        self._block_ = None # TODO
        self._opticalDrive_ = None  # TODO
        self._disc_ = None # TODO
        self._player_ = None  # TODO
        self._networkShare_ = None # TODO
        # ### END   all these below are Solid framework
        
        self._deviceIconName_:str = str()
        self._emblems_:list[str] = list()
        self._backingFile_:str = str()
        self._groupType_:GroupType = GroupType.UnknownType
        self._groupName_:str = str()
        self._deviceDisplayName_:str = str()
        
        self.updateDeviceInfo(udi)
        
    def id(self):
        pass
    
    def isDevice(self) -> bool: # TODO
        pass
    
    def deviceAccessibility(self) -> DeviceAccessibility: # TODO
        pass
        
    def isTearDownAllowed(self) -> bool: # TODO
        pass
    
    def isTearDownOverlayRecommended(self) -> bool: # TODO
        pass
    
    def bookmark(self): # TODO
        pass
    
    def setBookmark(self, bookmark): # TODO
        pass
    
    def device(self): # TODO
        pass
    
    def groupType(self) -> GroupType: # TODO
        pass
    
    def data(self, role:int):
        if role == AdditionalRoles.GroupRole:
            return self._groupName_
        
        elif role == QtCore.Qt.DisplayRole:
            return self._text_
        
        elif role == QtCore.Qt.DecorationRole:
            return self.iconNameForBookmark(self.bookmark())
        
        else:
            return self._text_
       
    def bookmark(self):
        return self._bookmark_
    
    def setBookmark(self, bookmark:dict):
        """A bookmark, IN THIS CONTEXT, is a dict as returned by get_desktop_places()
        The two important data are:
        • the bookmark URL
        • the bookrmark name
    
        For now it is recommended to use the subset of places that point to
        physical paths in the file system (e.g., not remote:/ trash:/, or any other
        KIO protocol, and neither a device as defined in the Solid framework, and
        defined by a unique device identifier - or UDI - and a UUID)
    
        """
        self._bookmark_ = bookmark
        
    def isHidden(self) -> bool: # TODO
        pass
    
    def setHidden(self) -> bool: # TODO
        pass
    
    def hasSupportedScheme(self, schemes:list[str]) -> bool: # TODO
        pass
    
    @Slot()
    def onAccesibilityChanged(self, val:bool): # TODO
        pass
    
    # NOTE: 2025-02-05 21:59:23 TODO:
    # the following three static methods:
    # check if Scipyen is running in an XDG-compliant
    # if it does, then use XDG utlities (see core.desktoputils module )
    #   • for this I need to understand wkat KBookmarkManager does
    #       and implement this via pyxdg
    # otherwise, do nothing
    
    @staticmethod
    def createSystemBookmark(*args, **kwargs): # TODO
        pass
    
    @staticmethod
    def createDeviceBookmark(*args, **kwargs): # TODO
        pass
    
    @staticmethod
    def createTagBookmark(*args, **kwargs): # TODO
        pass
    
    def bookmarkData(self): # TODO
        pass
    
    def deviceData(self): # TODO
        pass
    
    def iconNameForBookmark(self, bookmark): # TODO
        pass
    
    @staticmethod
    def generateNewId() -> str: # TODO
        pass
    
    # NOTE: 2025-02-06 00:00:59 TODO
    # create Device class as a shim implementing (partially) some
    # functionality from Solid framework
    # In the end, all storage devices resolve to a path of some sort...
    def updateDeviceInfo(self, udi:str) -> bool: # TODO
        if self._device_.udi() == udi:
            return False
        
        return True  # TODO
    
    
        
            
class PlacesModel: # fwd declaration for PlacesModelPrivate
    pass 

# class PlacesModelPrivate(QtCore.QObject): # not really needed !
#     def __init__(self, qq:PlacesModel, parent=None):
#         super().__init__(parent)
#         self.model = qq
#         # self.tags = list() # of str - not sure I need this
#         self.supportedSchemes = list()
        
    
class PlacesModel(QtCore.QAbstractItemModel): # TODO/FIXME
    """
    Extremely thin port of the KDE Plasma 5 KIO framework places model.
    
    In particular, the following functionalities (and their necessary KDE plasma
    frameworks) are NOT ported:
    
    Solid → no special handling of devices
    KBookmarks → we try to handle KDE bookmark files (*.xbel, *.xml) directly 
                using python's xml — TODO
    
    Moreover, this implementation is READ-ONLY: one cannot use it to add/remove/
    create new "places". For this, one MUST use the tools provided by the
    specific desktop environment (e.g. KDE, GNOME, XFCE, LXDE, etc). 
    
    See also `get_desktop_places()` function in this module.
    
    This is partly by design (Scipyen is not meant to provide all the functionality
    of modern file system or internet navigators) and partially by necessity, as
    there are no comprehensive python bindings for KDE at this time (2023-05-01)
    and even if they were (making slow progress in 2025) they would tie Scipyen
    to one particular desktop environment, against the overall philosophy.
    
    """
    errorMessage = Signal(str, name = "errorMessage", arguments=["message"])
    
    setupDone = Signal(QtCore.QModelIndex, bool, name="setupDone", arguments=["index", "success"])
    
    teardownDone = Signal(QtCore.QModelIndex, object, object, name="teardownDone", arguments=["index", "error", "errorData"])
    
    reloaded = Signal(name="reloaded")
    
    supportedSchemesChanged = Signal(name = "supportedSchemesChanged")
    
    def __init__(self, parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        
        self.alternativeApplicationName = "" # not needed?
        
        # ### BEGIN KFilePlacesModelPrivate members
        self.items:list[PlacesItem] = list()
        # NOTE: 2025-01-03 14:51:53
        # consider leaving out
        self.availableDevices:list[Device] = list()
        # consider leaving out:
        self.setupInProgress:dict[QtCore.QObject, QtCore.QPersistentModelIndex] = dict()
        # consider leaving out:
        self.teardownInProgress:dict[QtCore.QObject, QtCore.QPersistentModelIndex] = dict()
        #
        self.supportedSchemes:list[str] = list()
        
        # the following, to leave out
        self.predicate = None # Solid::Predicate - here, a functor
        self.bookmarkManager = None # KBookmarkManager
        
        # NOTE: 2025-01-03 15:20:45
        # consider leaving out — this is related to KDE file searching framework
        # (Baloo), specifically on whether it is configured to use file content
        # indexing or not. Currently, Scipyen has got nothing to do with it, 
        # therefore this is always False.
        # (see desktoutils.isFileIndexingEnabled)
        # 
        # In the future, I MAY consider introducing this funcitonality - but be
        # aware that Baloo is KDE-specific! GNOME desktop use a different
        # framework: TinySPARQL / formerly known as "tracker", currently known
        # as "localsearch". 
        #
        # The design philosophy in Scipyen is to be desktop-agnostic, and 
        # there are quite a few file search & indexing packages there see
        # https://www.linuxlinks.com/desktopsearchengines/
        
         
        self.fileIndexingEnabled:bool = False 
        
        self.tags:list[str] = list()
        self.tagsUrlBase = "tags:/"
        self.tagsLister = None # KCoreDirLister
        # ### END KFilePlacesModelPrivate members
        
    # ### BEGIN KFilePlacesModelPrivate methods
    @classmethod
    def ignoreMimeType(cls) -> str:
        return "application/x-kfileplacesmodel-ignore"
        # return "application/octet-stream"
    
    @classmethod
    def internalMimeType(cls, model) -> str:
        return f"application/x-kfileplacesmodel-{id(model)}"
        
    def reloadAndSignal(self): # TODO
        pass 
    
    def loadBookmarkList(self) -> list: # TODO 
        pass
    
    def findNearestPosition(self, source:int, target:int) -> int: # TODO
        pass
    
    def initDeviceList(self): # TODO
        pass
    
    def deviceAdded(self, udi:str): # TODO
        pass
    
    def deviceRemoved(self, udi:str): # TODO
        pass
    
    def itemChanged(self, udi:str, roles:list[int]): # TODO
        pass
    
    def reloadBookmarks(self): # TODO
        pass
    
    def storageSetupDone(self, error, errorData, sender): # TODO
        # void storageSetupDone(Solid::ErrorType error, const QVariant &errorData, Solid::StorageAccess *sender);
        pass
    
    def storageTeardownDone(filePath:typing.Union[pathlib.Path, str], error, errorData, sender): # TODO
        # void storageTeardownDone(const QString &filePath, Solid::ErrorType error, const QVariant &errorData, QObject *sender);
        pass
    
    def isBalooUrl(self, url:QtCore.QUrl) -> bool: # TODO
        pass
    
    # ### END KFilePlacesModelPrivate methods
    
    def url(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def setupNeeded(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def isTearDownAllowed(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def isEjectAllowed(self, index:QtCore.QModelIndex): # TODO
        pass
        
    def isTearDownOverlayRecommended(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def deviceAccessibility(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def icon(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def text(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def ishidden(self, index:QtCore.QModelIndex): # TODO
        pass
    
    @singledispatchmethod
    def isGroupHidden(self, val): # TODO
        pass
    
    @isGroupHidden.register
    def _(self, val:GroupType): # TODO
        pass
    
    @isGroupHidden.register
    def _(self, val:QtCore.QModelIndex): # TODO
        pass
    
    def bookmarkForIndex(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def bookmarkForUrl(self, searchUrl:QtCore.QUrl): # TODO
        pass
    
    def groupType(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def groupIndexes(self, groupType:GroupType): # TODO
        pass
    
    # NOTE: 2023-05-01 13:43:24
    # ### BEGIN methods that need KDE Solid framework -- NOT IMPLEMENTED
    #
    def deviceForIndex(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def teardownActionForIndex(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def isDevice(self, index:QtCore.QModelIndex): # TODO
        pass
    
#     
#     def ejectActionForIndex(self, index:QtCore.QModelIndex):
#         pass
#     
#     def requestTearDown(self, index:QtCore.QModelIndex):
#         pass
#     
#     def requestEject(self, index:QtCore.QModelIndex):
#         pass
#     
#     def requestSetup(self, index:QtCore.QModelIndex):
#         pass
#    
    #
    # ### END methods that need KDE Solid framework
    
    def addPlace(self, test:str, url:QtCore.QUrl, iconName:str, appName:str="", after:typing.Optional[QtCore.QModelIndex] = None): # TODO
        pass
    
    def editPlace(self, index:QtCore.QModelIndex, test:str, url:url, iconName:str = "", appName:str = ""): # TODO
        pass
    
    def removePlace(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def setPlaceHidden(self, index:QtCore.QModelIndex, hidden:bool): # TODO
        pass
    
    def setGroupHidden(self, groupType:GroupType,hidden:bool): # TODO
        pass
    
    def movePlace(itemRow:int, row:int): # TODO
        pass
    
    def hiddenCount(self): # TODO
        pass
    
    def data(self, index:QtCore.QModelIndex, role:int): 
        if not index.isValid():
            return QtCore.QVariant(None)
        
        item = index.internalPointer()
        if role == AdditionalRoles.GroupHiddenRole:
            return self.isGroupHidden(item.groupType())
        pass
    
    def index(self, row:int, column:int, parent:QtCore.QModelIndex = QtCore.QModelIndex()):
        if row < 0 or column != 0 or row >= len(items):
            # return an invalid index when row or column are out of range
            return QtCore.QModelIndex() 
        
        if parent.isValid():
            return QtCore.QModelIndex()
        
        # methid inherited from QAbstractItemModel
        return self.createIndex(row, column, self.items[row])
    
    def parent(self, child:QtCore.QModelIndex):
        return QtCore.QModelIndex()
    
    def roleNames(self): # TODO
        pass
    
    def rowCount(self, parent:QtCore.QModelIndex = QtCore.QModelIndex()): # TODO
        pass
    
    def columnCount(self, parent:QtCore.QModelIndex = QtCore.QModelIndex()): # TODO
        pass
    
    def closestItem(self, url:QtCore.QUrl): # TODO
        pass
    
    def supportedDropActions(self): # TODO
        pass
    
    def flags(self, index:QtCore.QModelIndex): # TODO
        pass
    
    def mimeTypes(self): # TODO
        pass
    
    def mimeData(self, indexes:list): # TODO
        pass
    
    def dropMimeData(self, data:QtCore.QMimeData, action:QtCore.Qt.DropAction, row:int, column:int, parent:QtCore.QModelIndex): # TODO
        pass
    
    def refresh(self): # TODO
        pass
    
    def convertedUrl(self, url:QtCore.QUrl): # TODO
        pass
    
    def setSupportedSchemes(self, schemes:list): # TODO
        pass
    
    def supportedSchemes(self): # TODO
        pass
    

