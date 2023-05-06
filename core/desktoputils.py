# -*- coding: utf-8 -*-
"""Utilities for Linux desktop integration
"""
# NOTE: 2020-10-24 12:11:26
# Useful functions from os.path module ("path" is a str or a pathlib.Path object)
# ------------------------------------------------------
# os.path.exists: check existence of a physical path (even if it is a symbolic link)
# os.path.ismount: if the path is a mount point
# os.path.isabs: False when path is relative to getcwd()
# os.path.abspath: return the normalized (absolute) path for a relative path
# os.path.normpath: as above (but more platform-restricted?)
# os.path.commonpath: the common path leading to the path items in a list
# os.path.basename, dirname, join, split, splitdrive, splitext, normcase, realpath
#
# Useful function from the pathlib module ("pth" is a str, "path" is a pathlib.Path)
# --------------------------------------------------------------------------------------
#   class methods
# Path.cwd() #`> current directory
# Path.home()
#
#   constructors
# path = Path(*path_components)
# p1 = Path("/","home" ,"cezar") # or p1 = Path("/home", "cezar")
# p2 = Path("Documents")
# 
#   operators
# path = p1 / p2 # => "home/cezar/Documents"
#
#   access to parts
# path.parts # --> a tuple
#
#   properties and methods
# path.drive # --> only works well in windows, not posix
#            # --> on Windows UNC shares are also "drives"
#
# path.root  # --> local or global root if any
#
# path.anchor # --> drive and root concatenated
#
# Useful urllib functions
# ------------------------
# urllib.parse.urlparse

import sys, os, pathlib, urllib, typing, warnings, subprocess, traceback
import core.xmlutils as xmlutils
import iolib.pictio as pio
import xml.etree.ElementTree as ET
from enum import Enum, IntEnum
from functools import (singledispatch, singledispatchmethod)

from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)

# desktop integration - according to freedesktop.org (XDG)
# ATTENTION: DO NOT install xdg as it will mess up pyxdg
# install pyxdg instead !!!
# Currently (2023-04-30 13:45:34) I have no experience with xdgspec
HAS_PYXDG = False
# HAS_XDGSPEC = False
try:
    import xdg # CAUTION this is from pyxdg
    HAS_PYXDG = True
    
except:
    pass
    # try:
    #     import xdgspec
    #     HAS_XDGSPEC = True
    # except:
    #     pass
    
def get_local_filesystem_places():
    """
    Get special directories (KDE Plasma5 specific)
    """
    ret = get_desktop_places()
    
    if len(ret):
        result = dict((k,v) for k,v in ret.items() if not k.startswith("file:///"))
        
        return result
    
    return ret

def get_my_desktop_session():
    env = dict((k,v) for k,v in os.environ.items() if any(s in k.lower() for s in ("desktop", "session", "xdg")))
    if len(env) == 0:
        return
    
    xdg_session_desktop = env.get("XDG_SESSION_DESKTOP", "")
    return xdg_session_desktop

def get_trash_icon_name():
    if get_my_desktop_session() == "KDE":
        try:
            trashproc = subprocess.run(["kioclient", "stat", "trash:/"],
                                       capture_output=True)
            
            trashstat = dict(v for v in (s.split() for s in trashproc.stdout.decode().split("\n")) if len(v) == 2)

            return trashstat.get("ICON_NAME", "user-trash")
        except:
            # traceback.print_exc()
            return "user-trash"
        
    return "user-trash"
        

def get_desktop_places():
    """Collect user places as defined in the freedesktop.org XDG framework.
    Useful for Linux desktops that comply with XDG (e.g. KDE, GNOME, XFCE, LXDE, etc).
    
    
    Returns:
    ========

    A mapping of url (str) ↦ {"name"    ↦ descriptive name (str), 
                              "icon"    ↦ icon theme name (str),
                              "system"  ↦ is this a system place? (bool, default False),
                              "hidden"  ↦ is this a hidden place? (bool, default False),
                              "app"     ↦ None (for now)}

    If the `pyxdg` module is installed, the function will parse the file
    `user-places.xbel` located in the xdg.BaseDirectory.xdg_data_home directory.
    
    Otherwise, the function relies on the QtCore.QStandardPaths to build a 
    generic list of "places".
    
    NOTE: Not all these places will be useful in Scipyen. 

    In particular, the places relating to specific IO protocols and KDE Solid 
    devices should be filterd out of the results (e.g., see get_local_filesystem_places).
    
    
    """
    
    ret = dict()
    
    # NOTE: 2023-05-01 13:38:10 TODO
    # below we are using the file `user-places.xbel` located in 
    # `xdg.BaseDirectory.xdg_data_home`
    #
    # For recently visited stuff (available e.g. in KDE and possibly in all other
    # advanced Linux dekstop environments) the file `recently-used.xbel` in the 
    # same location should be used (TODO).      
    
    if sys.platform == "linux" and HAS_PYXDG:
        places = pio.loadXMLFile(os.path.join(xdg.BaseDirectory.xdg_data_home, "user-places.xbel"))
            
        if "xbel" not in places.documentElement.tagName.lower():
            return ret
        
        bookmarks = places.getElementsByTagName("bookmark")
        
        for b in places.getElementsByTagName("bookmark"):
            place_name = b.getElementsByTagName("title")[0].childNodes[0].data
            place_url = b.getAttribute("href")
            
            if len(place_name) == 0 or len(place_url) == 0:
                continue
            
            info_node = b.getElementsByTagName("info")[0]
            info_metadata_nodes = info_node.getElementsByTagName("metadata")
            
            place_icon_name = info_metadata_nodes[0].getElementsByTagName("bookmark:icon")[0].getAttribute("name")
            
            systemitem_nodes = info_metadata_nodes[1].getElementsByTagName("isSystemItem")
            hidden_nodes = info_metadata_nodes[1].getElementsByTagName("isHidden")
            app_nodes = info_metadata_nodes[1].getElementsByTagName("OnlyInApp")
            
            if len(systemitem_nodes):
                is_system_place = systemitem_nodes[0].childNodes[0].data == "true"
            else:
                is_system_place=False
                
            if len(hidden_nodes):
                is_hidden = hidden_nodes[0].childNodes[0].data == "true"
            else:
                is_hidden = False
                
            if len(app_nodes):
                app_info = app_nodes[0].childNodes
                if len(app_info):
                    app = app_info[0].data
                else:
                    app = None
            else:
                app = None
            
            ret[place_url] = {"name": place_name, 
                              "url": place_url,
                              "icon": place_icon_name, # can be a system icon name or a path/file name
                              "system":is_system_place == "true",
                              "hidden":is_hidden == "true",
                              "app":app}
    else:
        skippedLocs = ["FontsLocation","TempLocation", "RuntimeLocation", 
                       "CacheLocation", "ConfigLocation", "GenericDataLocation", 
                       "GenericCacheLocation", "GenericConfigLocation", 
                       "AppDataLocation", "AppConfigLocation","AppLocalDataLocation",
                       "DataLocation","ApplicationsLocation"]
        
        locs = dict(sorted([(x, n) for x, n in vars(QtCore.QStandardPaths).items() if isinstance(n, QtCore.QStandardPaths.StandardLocation) and not any(v in x for v in skippedLocs)], key=lambda i:i[1]))
        
        for k,v in locs.items():
            stdlocs = QtCore.QStandardPaths.standardLocations(v)
            place_url = f"file://{stdlocs[0]}"
            place_name = QtCore.QStandardPaths.displayName(v)
            loc_icon = "user-home" if place_name == "Home" else f"folder-{place_name.lower()}"
            ret[place_url] = {"name": place_name, "url": place_url, "icon": loc_icon,"system":False, "hidden": False, "app":None}
        
    return ret

def iconNameForUrl(url:QtCore.QUrl):
    if len(url.scheme()) == 0:
        return "unknown"
    
    iconName = ""
    
    mimeDB = QtCore.QMimeDatabase()
    
    mimeType = mimeDB.mimeTypeForUrl(url)
    
    if url.isLocalFile():
        if mimeType.inherits("inode/directory"):
            iconName = iconForStandardPath(url.toLocalFile())
            
        if len(iconName) == 0:
            iconName = "unknown" # FIXME/TODO
            
    else:
        if url.scheme().startswith("http"):
            iconName = favIconForUrl(url)
            
        elif url.scheme() == "trash":
            if len(url.path()) <= 1:
                iconName = get_trash_icon_name()
            else:
                iconName = mimeType.iconName()
                
        if len(iconName) == 0 and (mimeType.isDefault() or len(url.path()) <= 1):
            if get_my_desktop_session() == "KDE":
                try:
                    kioproc = subprocess.run(["kioclient", "stat", url.scheme()],
                                            capture_output=True)
                    
                    kiostat = dict(v for v in (s.split() for s in kioproc.stdout.decode().split("\n")) if len(v) == 2)

                    iconName = kiostat.get("ICON_NAME", "")
                    
                except:
                    pass
                
    if len(iconName) == 0:
        iconName = mimeType.iconName()
        
    return iconName

def findByAddress(address:str):
    places = get_desktop_places()
    return places.get(address, None)

def get_recent_places():
    """
    Get recently viewed places in the underlying desktop environment.
    
    NOTE: These are NOT necessarily the recently opened files and directories in 
    Scipyen!
    
    Meaningful only when Scipyen is run inside on a Linux platform with a 
    desktop environment that complied with the freedesktop.org XDG specification.
    
    In all other circumstances, returns an empty dict.
    
    WARNING: This should be filtered to remove entries pointing to hidden files,
    special IO protocols (e.g. "desktop:/", etc) or entries not relevant to 
    Scipyen.
    
    In addition, Scipyen manages its own recently used files, directories and
    scripts indepenedently, so there should be no much use for this function
    in the day-to-day use.
    
    """
    
    ret = dict()
    
    if sys.platform == "linux" and HAS_PYXDG:
        places = pio.loadXMLFile(os.path.join(xdg.BaseDirectory.xdg_data_home, "recently-used.xbel"))
            
        if "xbel" not in places.documentElement.tagName.lower():
            return ret
        
        bookmarks = places.getElementsByTagName("bookmark")
        
        for b in places.getElementsByTagName("bookmark"):
            place_url   = b.getAttribute("href")
            modified    = b.getAttribute("modified")
            visited     = b.getAttribute("visited")
            added       = b.getAttribute("added")
            
            info_node = b.getElementsByTagName("info")[0]
            info_metadata_nodes = info_node.getElementsByTagName("metadata")
            
            if len(info_metadata_nodes) == 0:
                continue
            
            info_metadata_node = info_metadata_nodes[0]
            
            place_mime_type = info_metadata_node.getElementsByTagName("mime:mime-type")[0].getAttribute("type")
            applications_node = info_metadata_node.getElementsByTagName("bookmark:applications")[0]
            
            application_nodes = applications_node.getElementsByTagName("bookmark:application")
            
            application_data = list()
            
            for application_node in application_nodes:
                application_data.append({
                                         "count": application_node.getAttribute("count"),
                                         "modified": application_node.getAttribute("modified"),
                                         "name": application_node.getAttribute("name"),
                                         "exec": application_node.getAttribute("exec"),
                                         })

            ret[place_url] = {"mimetype": place_mime_type,
                              "applications": application_data,
                              "added": added, 
                              "modified": modified,
                              "visited": visited,
                              }
    return ret

def local_recent_places():
    ret = get_recent_places()
    
    return dict([(k,v) for k,v in ret.items() if k.startswith("file:/")])
    

# NOTE: 2023-05-01 10:44:19
# below - not sure we need all of this ...

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
                            
GroupType = IntEnum ("GroupType", 
                     ["PlacesType", "RemoteType", "RecentlySavedType",
                      "SearchForType", "DevicesType", "RemovableDevicesType",
                      "UnknownType", "TagsType"],
                     module = __name__)
                        
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
    
def isFileIndexingEnabled():
    return False

def timelineDateString(year:int, month:int, day:int=0):
    date = f"{year}-{month}"
    if day > 0:
        date = f"{date}-{day}"
        
    return date

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

def removeReducedCJKAccMark(label:str, pos:int):
    # NOTE: 2023-05-06 18:06:09
    # from ki18n frameworks i18n common_helpers.cpp
    # https://invent.kde.org/frameworks/ki18n/-/blob/master/src/i18n/common_helpers.cpp
    if pos > 0 and pos + 1 < len(label) and label[pos-1] == '(' and label[pos+1] == ')' and label[pos].isalnum():
        length = len(label)
        p1 = pos-2
        
        while p1 >= 0 and not label[p1].isalnum():
            p1 -= 1
            
        p1 += 1
        
        p2 = pos + 2
        
        while p2 < length and not label[p2].isalnum():
            p2 += 1
            
        p2 -= 1
        
        if p1 == 0:
            return label[0:(pos-1)] + label[(p2+1):]
        elif p2 + 1 == length:
            return label[0:p1] + label[(pos+2):]
        
    return label
        

def removeAcceleratorMarker(label:str):
    # NOTE: 2023-05-06 10:48:50
    # from ki18n frameworks i18n common_helpers.cpp
    # https://invent.kde.org/frameworks/ki18n/-/blob/master/src/i18n/common_helpers.cpp
    
    p = 0
    accmarkRemoved = False
    while True:
        if '&' not in label:
            break
        print(f"label = {label}")
        
        try:
            p = label.index('&', p)
        except:
            traceback.print_exc()
            break
        
        if p + 1 == len(label):
            break
        
        marker = label[p+1]
        
        if marker.isalnum():
            label = label[:p] + label[(p+1):]
            
            label = removeReducedCJKAccMark(label, p)
            accmarkRemoved = True
        
        elif marker == '&':
            label = label[:p] + label[(p+1):]
            
        p += 1
    
    if not accmarkRemoved:
        hasCJK = False
        for c in label:
            if c >= chr(ord('\u2e00')):
                hasCJK = True
                break
            
        if hasCJK:
            p = 0
            while True:
                if '(' not in label:
                    break
                
                p = label.index('(', p)
                
                label = removeReducedCJKAccMark(label, p+1)
                p == 1
                
    return label
    
        
        

class PlacesItem(QtCore.QObject):
    """Thin port of KFilePlacesItem.
    Has no functionality related to the Trash (Wastebin) protocol, the KDE
    Solid framework, and special KIO protocols (e.g. kdeconnect:/, remote:/, etc.)
    
    """
    
    # itemChanged = pyqtSignal(str, name="itemChanged")
    
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
                using python's xml
    
    Moreover, this implementation is READ-ONLY: one cannot use it to add/remove/
    create new "places". For this, one MUST use the tools provided by the
    specific desktop environment (e.g. KDE, GNOME, XFCE, LXDE, etc). 
    
    See also `get_desktop_places()` function in this module.
    
    This is partly by design (Scipyen is not meant to provide all the functionality
    of modern navigators of the file system or the web) and partially by necessity
    (there are no comprehensive python bindings for KDE at this time: 2023-05-01).
    
    Hopefully, in a not too distant future, there will be a coherent implementation
    of Python bindings for KDE framework libraries, but I'm not holding my breadth...
    
    """
    errorMessage = pyqtSignal(str, name = "errorMessage", arguments=["message"])
    
    setupDone = pyqtSignal(QtCore.QModelIndex, bool, name="setupDone", arguments=["index", "success"])
    
    teardownDone = pyqtSignal(QtCore.QModelIndex, object, object, name="teardownDone", arguments=["index", "error", "errorData"])
    
    reloaded = pyqtSignal(name="reloaded")
    
    supportedSchemesChanged = pyqtSignal(name = "supportedSchemesChanged")
    
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
    # ### BEGIN methods that need KDE Solid framework
    #
#     def deviceForIndex(self, index:QtCore.QModelIndex):
#         pass
#     
#     def isDevice(self, index:QtCore.QModelIndex):
#         pass
#     
#     def teardownActionForIndex(self, index:QtCore.QModelIndex):
#         pass
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
    
    def mineData(self, indexes:list):
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
    
     
    
    
