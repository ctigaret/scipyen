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
                               isFileIndexingEnabled)

HAS_PYXDG = False
# HAS_XDGSPEC = False
try:
    import xdg # CAUTION this is from pyxdg
    HAS_PYXDG = True
    
except:
    pass

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class AdditionalRoles: pass # NOTE: 2025-01-02 23:36:06 this for the sole purpose of showing up in Kate Symbol browser
AdditionalRoles = IntEnum("AdditionalRoles", 
                            {"UrlRole" : 0x069CD12B,
                            "HiddenRole" : 0x0741CAAC,
                            "SetupNeededRole" : 0x059A935D,
                            "CapacityBarRecommendedRole" : 0x1548C5C4,
                            "GroupRole" : 0x0a5b64ee,
                            "IconNameRole" : 0x00a45c00,
                            "GroupHiddenRole" : 0x21a4b936,
                            "TeardownAllowedRole" : 0x02533364,
                            "EjectAllowedRole" : 0x0A16AC5B,
                            "TeardownOverlayRecommendedRole" : 0x032EDCCE,
                            "DeviceAccessibilityRole" : 0x023FFD93},
                            module = __name__)

class GroupType: pass # see NOTE: 2025-01-02 23:36:06
GroupType = IntEnum ("GroupType", 
                     ["PlacesType", "RemoteType", "RecentlySavedType",
                      "SearchForType", "DevicesType", "RemovableDevicesType",
                      "UnknownType", "TagsType"],
                     module = __name__)

class DeviceAccessibility: pass # see NOTE: 2025-01-02 23:36:06
DeviceAccessibility = IntEnum("DeviceAccessibility",
                              ["SetupNeeded", "SetupInProgress", "Accessible", 
                               "TeardownInProgress"],#
                              module = __name__)
                              
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


class PlacesItem(QtCore.QAbstractItemModel):
    """Thin port of KFilePlacesItem.
    Has no, or partial, functionality related to the Trash (Wastebin) protocol, 
    the KDE Solid framework, and special KIO protocols (e.g. kdeconnect:/, 
    remote:/, etc.)
    
    """
    
    # itemChanged = Signal(str, name="itemChanged")
    
    def __init__(self, address:str, parent):
        super().__init__(parent)
        self._isAccessible_ = False
        self._groupName_ = ""
        self._bookmark_ = findByAddress(address) # may be None!
        
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
        
            
class PlacesModel: # fwd declaration for PlacesModelPrivate
    pass 

class PlacesModelPrivate: # not really needed !
    def __init__(self, qq:PlacesModel):
        self.qq = qq
        # self.tags = list() # of str - not sure I need this
        self.supportedSchemes = list()
        
    
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
        super().__init__(parent)
        self.supportedSchemes = list()
        
        self.alternativeApplicationName = "" # not needed?
        
    def reloadAndSignal(self):
        pass 
    
    def loadBookmarkList(self):
        pass
    
    def url(self, index:QtCore.QModelIndex):
        pass
    
    def setupNeeded(self, index:QtCore.QModelIndex):
        pass
    
    def isTearDownAllowed(self, index:QtCore.QModelIndex):
        pass
    
    def isEjectAllowed(self, index:QtCore.QModelIndex):
        pass
        
    def isTearDownOverlayRecommended(self, index:QtCore.QModelIndex):
        pass
    
    def deviceAccessibility(self, index:QtCore.QModelIndex):
        pass
    
    def icon(self, index:QtCore.QModelIndex):
        pass
    
    def text(self, index:QtCore.QModelIndex):
        pass
    
    def ishidden(self, index:QtCore.QModelIndex):
        pass
    
    @singledispatchmethod
    def isGroupHidden(self, val):
        pass
    
    @isGroupHidden.register
    def _(self, val:GroupType):
        pass
    
    @isGroupHidden.register
    def _(self, val:QtCore.QModelIndex):
        pass
    
    def bookmarkForIndex(self, index:QtCore.QModelIndex):
        pass
    
    def bookmarkForUrl(self, searchUrl:QtCore.QUrl):
        pass
    
    def groupType(self, index:QtCore.QModelIndex):
        pass
    
    def groupIndexes(self, groupType:GroupType):
        pass
    
    # NOTE: 2023-05-01 13:43:24
    # ### BEGIN methods that need KDE Solid framework -- NOT IMPLEMENTED
    #
    def deviceForIndex(self, index:QtCore.QModelIndex):
        pass
    
    def teardownActionForIndex(self, index:QtCore.QModelIndex):
        pass
    
#     def isDevice(self, index:QtCore.QModelIndex):
#         pass
#     
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
    
    def addPlace(self, test:str, url:QtCore.QUrl, iconName:str, appName:str="", after:typing.Optional[QtCore.QModelIndex] = None):
        pass
    
    def editPlace(self, index:QtCore.QModelIndex, test:str, url:url, iconName:str = "", appName:str = ""):
        pass
    
    def removePlace(self, index:QtCore.QModelIndex):
        pass
    
    def setPlaceHidden(self, index:QtCore.QModelIndex, hidden:bool):
        pass
    
    def setGroupHidden(self, groupType:GroupType,hidden:bool):
        pass
    
    def movePlace(itemRow:int, row:int):
        pass
    
    def hiddenCount(self):
        pass
    
    def data(self, index:QtCore.QModelIndex, role:int):
        pass
    
    def index(self, row:int, column:int, parent:QtCore.QModelIndex = QtCore.QModelIndex()):
        pass
    
    def parent(self, child:QtCore.QModelIndex):
        pass
    
    def roleNames(self):
        pass
    
    def rowCount(self, parent:QtCore.QModelIndex = QtCore.QModelIndex()):
        pass
    
    def columnCount(self, parent:QtCore.QModelIndex = QtCore.QModelIndex()):
        pass
    
    def closestItem(self, url:QtCore.QUrl):
        pass
    
    def supportedDropActions(self):
        pass
    
    def flags(self, index:QtCore.QModelIndex):
        pass
    
    def mimeTypes(self):
        pass
    
    def mimeData(self, indexes:list):
        pass
    
    def dropMimeData(self, data:QtCore.QMimeData, action:QtCore.Qt.DropAction, row:int, column:int, parent:QtCore.QModelIndex):
        pass
    
    def refresh(self):
        pass
    
    def convertedUrl(self, url:QtCore.QUrl):
        pass
    
    def setSupportedSchemes(self, schemes:list):
        pass
    
    def supportedSchemes(self):
        pass
    

