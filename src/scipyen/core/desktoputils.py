# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Utilities for Linux desktop integration
"""
# ### BEGIN internal comments
# NOTE: 2025-01-03 17:37:47
# Command line tools for desktpp integration (since KDE Frameworks 6 has become
# "mainstream", excutables provided by KDE below come under two flavours: 
#   <exec_name> — for KDE Frameworks 6 & KDE Plasma 6
#   <exec_name>5 — for KDE Frameworks 5 and KDE Plasma 5 (some applications may
#   still deend on KDE Frameworks 5, but I think as of the time of writing,
#   KDE Plasma 5 is on its way out in most distributions)
#
# • KDE:
#   ∘ kmimetypefinder / kmimetypeinder5 

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

# ### END internal comments

import sys, os, pathlib, urllib, typing, warnings, subprocess, traceback
import platform
import core.xmlutils as xmlutils
import iolib.pictio as pio
import xml.etree.ElementTree as ET
from enum import Enum, IntEnum
from functools import (singledispatch, singledispatchmethod)
from traitlets.utils.bunch import Bunch

from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg,)
from qtpy.QtCore import (Signal, Slot, Property,)

from qtpy import (QtCore, QtWidgets, QtGui)
has_qtdbus = False
try:
    from qtpy import QtDBus
    has_qtdbus = False
except:
    pass

SCHEMAS = ("file", "recentlyused", "remote", "search", "tags", "timeline", "trash")

class DesktopPlace(Bunch):
    """Stand-in for PlacesItem - use in the absence of PlacesModel
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
class PlacesMap(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
    
def get_wm():
    """Retrieves the name of the window manager, on Linux platforms.
    On any other platforms returns None.
    Somewhat redundant to get_desktop()
    """
    # NOTE: 2023-01-07 16:08:36
    # From
    # https://stackoverflow.com/questions/3333243/how-can-i-check-with-python-which-window-manager-is-running
    if not sys.platform.startswith("linux"):
        return
    
    # wmctrl = which("wmctrl")
    wmctrl = shutil.which("wmctrl")
    
    if len(wmctrl):
        wmctrl = os.path.basename(wmctrl)
        
        out = subprocess.run([wmctrl, "-m"], text=True,
                             stdout=subprocess.PIPE,
                             stderr =subprocess.PIPE)
        
        if len(out.stdout) == 0:
            print(out.stderr)
            return
        
        wmname = [s for s in out.stdout.split("\n") if s.startswith("Name: ")]
        
        if len(wmname):
            return wmname[0].strip("Name: ")
        
    else:
        inxi = shutil.which("inxi")
        if len(inxi):
            inxi = os.path.basename(inxi)
            out = subprocess.run([inxi, "-Sxx", "-y", "1", "--indents", "0"],
                                 text=True,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE)
            
            if len(out.stdout) == 0:
                print(out.stderr)
                return
            
            inxiout = dict(filter(lambda x: len(x) == 2, (tuple(s.split(": ")) for s in out.stdout.split("\n"))))
            
            if len(inxiout) == 0:
                return
            
            desktop = inxiout.get("Desktop", None)
            tk = inxiout.get("tk", None)
            wm = inxiout.get("wm", None)
            
            return wm

def get_desktop(what:str="desktop"):
    """Somewhat redundant to get_wm()
    """
    if sys.platform.startswith("linux"):
        if what == "wm":
            return os.environ.get("WINDOWMANAGER", None)
        
        elif what == "session":
            return os.environ.get("XDG_SESSION_TYPE", None)
        
        else:
            return os.environ.get("XDG_CURRENT_DESKTOP", os.environ.get("XDG_SESSION_DESKTOP", None))
                
    else:
        return sys.platform

def get_dbus_service_names(what:str="session"):
    """
    what: one of "session", "system"
    """
    if not has_qtdbus:
        scipywarn("No QtDBus on this platform")
        return
    
    if platform.system() != "Linux":
        return
    
    if not isinstance(what, str):
        raise TypeError(f"Expecting a str; instead, got {type(what).__name__}")
    
    if what == "system":
        busConnection = QtDBus.QDBusConnection.systemBus()
    else:
        busConnection = QtDBus.QDBusConnection.sessionBus()
        
    return busConnection.interface().registeredServiceNames().value()
    
def is_kde_x11():
    if platform.system() != "Linux":
        return False
    
    return get_desktop("session").lower() == "x11" and get_desktop() == "KDE"

def is_kde_wayland():
    if platform.system() != "Linux":
        return False
    
    return get_desktop("session").lower() == "wayland" and get_desktop() == "KDE"

def is_kde():
    if platform.system() != "Linux":
        return False
    
    return get_desktop("session").lower() in ("x11", "wayland") and get_desktop() == "KDE"

def get_local_filesystem_places(placesDict:typing.Optional[dict]=None) -> dict:
    """
    Get special directories (KDE Plasma5 specific)
    """
    if not isinstance(placesDict, dict):
        placesDict = get_desktop_places()
    
    filterFunc = lambda x: not x.startswith("file") if isinstance(x, str) else not x.scheme().startswith("file") if isinstance(x, QtCore.QUrl) else False
    
    if len(placesDict):
        # result = dict((k,v) for k,v in ret.items() if not k.startswith("file:///"))
        result = dict((k,v) for k,v in placesDict.items() if not filterFunc(k))
        
        return result
    
    return placesDict

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
        
def get_system_terminal_executable():
    # TODO: 2023-09-28 12:41:32 FIXME
    # store shell in global configuration
    # cascade through available options e.g. by calling
    #   on windows:
    #       out = subprocess.run(["where", shell], shell=True, capture_output=True)
    #   on linux:
    #       out = subprocess.run(["which", shell], shell=True, capture_output=True)
    #   and test that out.returncode == 0 (i.e. success)
    #
    #   while iterating through a list of available shells
    #
    #   on windows: powershell, wt, cmd
    #   on linux:   xterm, konsole, gnome-terminal, qterminal, lxterminal, rxvt, rxvt-unicode. 
    if sys.platform.startswith("win32"):
        return "cmd"
    elif sys.platform.startswith("linux"):
        if os.getenv("XDG_SESSION_DESKTOP").startswith("KDE"):
            return "konsole" # MY OWN default, for now
        else:
            return "xterm"
    elif sys.platform.startswith("darwin"):
        return "/System/Applications/Utilities/Terminal.app"
    else:
        warnings.warn(f"{sys.platform} platform is not yet supported")
        
        
def get_desktop_places(schema:typing.Optional[str]=None, as_qUrls:bool=False) -> PlacesMap:
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
    if isinstance(schema, str) and schema not in SCHEMAS:
        schema = None
        
    elif isinstance(schema, bool):
        as_qUrls = schema = True
        schema = None
        
    ret = dict()
    
    # NOTE: 2023-05-01 13:38:10 TODO
    # below we are using the file `user-places.xbel` located in 
    # `xdg.BaseDirectory.xdg_data_home`
    #
    # For recently visited stuff (available e.g. in KDE and possibly in all other
    # advanced Linux dekstop environments) the file `recently-used.xbel` in the 
    # same location should be used (TODO).      
    
    if sys.platform.startswith("linux") and HAS_PYXDG:
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
            
            # NOTE: 2025-01-22 11:41:26 apply schema filter if any
            if isinstance(schema, str) and len(schema):
                if not place_url.startswith(schema):
                    continue
                
            if as_qUrls:
                place_url = QtCore.QUrl(place_url)
                
            ret[place_url] = DesktopPlace({"name": place_name, 
                              "url": place_url,
                              "icon": place_icon_name, # can be a system icon name or a path/file name
                              "system":is_system_place == "true",
                              "hidden":is_hidden == "true",
                              "app":app})
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
            ret[place_url] = DesktopPlace({"name": place_name, "url": place_url, "icon": loc_icon,"system":False, "hidden": False, "app":None})
        
    return PlacesMap(ret)

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
    
    if sys.platform.startswith("linux") and HAS_PYXDG:
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

    
def isFileIndexingEnabled():
    # place holder; Baloo or localsearch are not used by Scipyen hence this will
    # be False
    # TODO - on opensource unix platforms check the functionality provided by
    # the desktop environment under which the current Scipyen session is running.
    return False

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
    
def desktopPlaceUrl(p:DesktopPlace) -> QtCore.QUrl:
    if not isinstance(p, DesktopPlace):
        raise TypeError(f"Expecting a DesktopPlace; instead, got {type(p).__name__}")
    url = p.url
    return url if isinstance(url, QtCore.QUrl) else QtCore.QUrl(url)
        
def closestUrl(url:QtCore.QUrl, places:typing.Optional[PlacesMap]=None) -> QtCore.QUrl:
    schema = url.scheme()
    if not isinstance(places, PlacesMap):
        places = get_desktop_places(schema) #, True)
        
    if len(places) == 0:
        return url
    
    uPath = pathlib.Path(url.path()).resolve()
    
    urlToPath = lambda x: pathlib.Path(x.strip(schema+":")) if isinstance(x, str) else pathlib.Path(x.path())
    pathLen = lambda x: len(x.path()) if isinstance(x, QtCore.QUrl) else len(x.strip(schema+":"))
    
    foundPlaces = list(reversed(sorted(list(filter(lambda x: uPath.is_relative_to(urlToPath(x["url"]).resolve()), places.values())), key = lambda x: pathLen(x["url"]))))
    
    toUrl = lambda x: x if isinstance(x, QtCore.QUrl) else QtCore.QUrl(x)
    
    return toUrl(foundPlaces[0]["url"]) if len(foundPlaces) else url
        
    
def closestPlace(url:QtCore.QUrl, places:typing.Optional[PlacesMap]=None) -> DesktopPlace:
    schema = url.scheme()
    if not isinstance(places, PlacesMap):
        places = get_desktop_places(schema) #, True)
        
    fallback = DesktopPlace(name=None, url = url, icon = iconNameForUrl(url), system=False, hidden=False, app=None)
        
    if len(places) == 0:
        return fallback
    
    uPath = pathlib.Path(url.path()).resolve()
    
    urlToPath = lambda x: pathlib.Path(x.strip(schema+":")) if isinstance(x, str) else pathlib.Path(x.path())
    pathLen = lambda x: len(x.path()) if isinstance(x, QtCore.QUrl) else len(x.strip(schema+":"))
    
    foundPlaces = list(reversed(sorted(list(filter(lambda x: uPath.is_relative_to(urlToPath(x["url"]).resolve()), places.values())), key = lambda x: pathLen(x["url"]))))
    
    # toUrl = lambda x: x if isinstance(x, QtCore.QUrl) else QtCore.QUrl(x)
    
    return foundPlaces[0] if len(foundPlaces) else fallback
        
    
    

     
    
    
