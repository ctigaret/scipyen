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
#   ∘ kmimetypefinder / kmimetypefinder5 

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

import sys, os, pathlib, urllib, typing, warnings, subprocess, traceback, json
import inspect
import platform
import dataclasses
from dataclasses import dataclass
import core.xmlutils as xmlutils
import iolib.pictio as pio
from enum import Enum, IntEnum
from functools import (singledispatch, singledispatchmethod)
from traitlets.utils.bunch import Bunch
# import xml.etree.ElementTree as ET
from xml.dom import minidom


from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg,)
from qtpy.QtCore import (Signal, Slot, Property,)

from qtpy import (QtCore, QtWidgets, QtGui)

# import pyudev
import quantities as pq
import numpy as np

from iolib.navigation import filesystems
from iolib.navigation.filesystems import (pathStrLen, pathLen,
                                          pathToQUrl, urlToPath)

has_qtdbus = False
try:
    from qtpy import QtDBus
    has_qtdbus = True
except:
    pass

SCHEMAS = ("file", "recentlyused", "remote", "search", "tags", "timeline", "trash")

hiddenLocations = ["TempLocation", "RuntimeLocation", 
                "CacheLocation", "ConfigLocation", "GenericDataLocation", 
                "GenericCacheLocation", "GenericConfigLocation", 
                "AppDataLocation", "AppConfigLocation","AppLocalDataLocation",
                "DataLocation","ApplicationsLocation", "RuntimeLocation"]
        
systemLocations = ["FontsLocation","RuntimeLocation", "TempLocation"]

def standardIconName(locationName:str, all_folder_icons:bool=False) -> str:
    ln = locationName.lower()
    if "desktop" in ln:
        return "folder-desktop" if all_folder_icons else "user-desktop"
    elif "documents" in ln:
        return "folder-documents"
    elif "applications" in ln:
        return "folder-appimage"
    elif "music" in ln:
        return "folder-music"
    elif "movies" in ln:
        return "folder-videos"
    elif "pictures" in ln:
        return "folder-pictures"
    elif "temp" in ln:
        return "folder-temp"
    elif "cache" in ln:
        return "folder-temp"
    elif "runtime" in ln:
        return "folder-temp"
    elif "home" in ln:
        return "user-home"
    elif "data" in ln:
        return "folder-database"
    elif "config" in ln:
        return "folder-log"
    elif "download" in ln:
        return "folder-download"
    elif "pulic" in ln:
        return "folder-public"
    else:
        return "folder"

def isUnixHiddenLocation(p:typing.Union[pathlib.Path, QtCore.QUrl, str]) -> bool:
    if isinstance(p, str):
        if "//" in p: # remove the url sheme
            if "file://" in p:
                p = p[7:]
            else:
                raise ValueError("Expecting a local path")
        p = pathlib.Path(p).resolve()
        
    elif isinstance(p, QtCore.QUrl):
        if p.scheme() != "file":
            raise ValueError("Expecting a local path url")
        
        p = pathlib.Path(p.path()).resolve
        
    elif not isinstance(p, pathlib.Path):
        raise TypeError(f"Expecting a path string, Url or ")
    
    return any(v.startswith(".") for v in p.parts)

def isUnixSystemLocation(p:typing.Union[pathlib.Path, QtCore.QUrl, str]) -> bool:
    if isinstance(p, str):
        if "//" in p: # remove the url sheme
            if "file://" in p:
                p = p[7:]
            else:
                raise ValueError("Expecting a local path")
        p = pathlib.Path(p).resolve()
        
    elif isinstance(p, QtCore.QUrl):
        if p.scheme() != "file":
            raise ValueError("Expecting a local path url")
        
        p = pathlib.Path(p.path()).resolve
        
    elif not isinstance(p, pathlib.Path):
        raise TypeError(f"Expecting a path string, Url or ")

    if sys.platform == "win32":
        return any((p.is_block_device(), p.is_char_device(), p.is_fifo(),
                p.is_reserved(), p.is_socket()))
    else:
        return any((p.is_block_device(), p.is_char_device(), p.is_fifo(), p.is_mount(),
                p.is_reserved(), p.is_socket()))

@dataclass
class DEPlace():
    """Stand-in for PlacesItem - use in UrlNavigator in the absence of PlacesModel
        Or as backend to PlacesItem
    """
    name:str
    url:QtCore.QUrl
    name_aliases:list[str] = dataclasses.field(default_factory=list)
    additional_urls:list[QtCore.QUrl] = dataclasses.field(default_factory=list)
    icon:str = dataclasses.field(default_factory=str)
    system:bool = dataclasses.field(default=False)
    hidden:bool = dataclasses.field(default=False)
    app:typing.Optional[str] = dataclasses.field(default_factory=str)
    
    def urlPath(self) -> pathlib.Path:
        return urlToPath(self.url)
    
    @classmethod
    def separator(cls, name:typing.Optional[str]=None):
        if not isinstance(name, str) or len(name.strip()) == 0:
            name == "separator"
        return cls(name, QtCore.QUrl())
    
    def isSeparator(self):
        return "separator" in self.name.lower() and self.url == QtCore.QUrl()
        
class DEBookmark(Bunch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
class PlacesMap(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    
class BookmarksMap(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class StandardLocationInfo:
    def __init__(self, location: QtCore.QStandardPaths.StandardLocation, all_folder_icons:bool=False):
        self._location_ = location
        self._paths_ = QtCore.QStandardPaths.standardLocations(location)
        self._name_ = QtCore.QStandardPaths.displayName(location)
        self._iconName_ = standardIconName(self._name_, all_folder_icons)
        self._system_ = location in systemLocations or any(isUnixSystemLocation(v) for v in self._paths_)
        self._hidden_ = location in hiddenLocations or any(isUnixHiddenLocation(v) for v in self._paths_)
        
    def __repr__(self) -> str:
        ret = f"{self.__class__.__name__}: name: {self._name_}, icon: {self._iconName_}"
        ret += f" system: {self._system_}, hidden: {self._hidden_},\n\twith paths:"
        
        ret = [ret]
        
        for p in self._paths_:
            ret.append(f"\t{p}")

        return "\n".join(ret)
    
    @property
    def paths(self) -> list:
        return self._paths_
        
    @property
    def location(self)->QtCore.QStandardPaths.StandardLocation:
        return self._location_
    
    @property
    def iconName(self) -> str:
        return self._iconName_
    
    @property
    def name(self) -> str:
        return self._name_
    
    @property
    def system(self) -> bool:
        return self._system_
    
    @property
    def hidden(self) -> bool:
        return self._hidden_
    
StandardDesktopLocationsQt = tuple(sorted(inspect.getmembers(QtCore.QStandardPaths, 
                                                           predicate = lambda x: isinstance(x, QtCore.QStandardPaths.StandardLocation)),
                                        key = lambda x: x[1]))



StandardDesktopLocationQtInfos = tuple(map(lambda x: StandardLocationInfo(getattr(QtCore.QStandardPaths, x[0])), StandardDesktopLocationsQt))

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

def get_cloud_storage_path(service_name):
    """Retrieves the local path for a specified cloud storage service.
    WARNING: Work in progress, DO NOT USE
    Original code at https://tech-champion.com/programming/python-programming/finding-your-onedrive-path-in-python-a-practical-guide/"""
    config_paths = {
        "onedrive": ["%APPDATA%\\OneDrive\\config.json", "%LOCALAPPDATA%\\OneDrive\\config.json"],
        "dropbox": ["%APPDATA%\\Dropbox\\config.json", "~/.dropbox/config.json"]  #Example for Dropbox, adjust as needed
    }

    if service_name not in config_paths:
        scipywarn("Service not supported")
        return

    for path in config_paths[service_name]:
        expanded_path = os.path.expandvars(path)
        if os.path.exists(expanded_path):
            try:
                with open(expanded_path, "r") as f:
                    config_data = json.load(f)
                    ret = config_data.get("local_path", "Path not found in config")
                    if ret == "Path not found in config":
                        scipywarn(ret)
                        return
                    return ret
            except json.JSONDecodeError:
                scipywarn("Invalid JSON in config file")
                return
            except Exception as e:
                scipywarn(f"Error reading config file: {e}")
                return
    scipywarn("Configuration file not found")
    return

# print(get_cloud_storage_path("onedrive"))
# print(get_cloud_storage_path("dropbox"))

def get_dbus_service_names(what:str="session"):
    """
    what: one of "session", "system"
    """
    if platform.system() != "Linux":
        return
    
    if not has_qtdbus:
        scipywarn("No QtDBus on this platform")
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
    Get special directories (KDE Plasma5/6 specific)
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
        
# def get_standard_desktop_places(asQUrl:bool=False, all_folder_icons:bool=False,
#                                 intKeys:bool=False) -> PlacesMap:
# def get_standard_desktop_places(asQUrl:bool=False, all_folder_icons:bool=False) -> PlacesMap:
def get_standard_desktop_places(all_folder_icons:bool=False) -> PlacesMap:
    """Platform-independent Desktop places.
    These are defined in the Qt toolkit
    """
    locations = tuple(map(lambda x: StandardLocationInfo(getattr(QtCore.QStandardPaths, x[0]), standardIconName(x[0], all_folder_icons)), StandardDesktopLocationsQt))
    ret = PlacesMap()
    for k, loc in enumerate(locations):
        if len(loc.paths) == 0:
            continue

        place_uris = list(map(lambda x: pathlib.Path(x).resolve().as_uri(), loc.paths))
        place_uri = place_uris[0]

        additional_urls = list(map(lambda x: QtCore.QUrl(x), place_uris[1:])) if len(place_uris) > 1 else list()

        # if asQUrl:
        #     key = QtCore.QUrl(place_uri)
        # else:
        #     key = place_uri
        key = place_uri

        if key in ret:
            ret[key].name_aliases.append(loc.name)
            ret[key].additional_urls.extend(additional_urls)
        else:
            ret[key] = DEPlace(loc.name, QtCore.QUrl(place_uri), additional_urls = additional_urls,
                                icon = loc.iconName, system = loc.system, hidden = loc.hidden)

    return ret
    
def get_desktop_places(schema:typing.Optional[str]=None, 
                       all_folder_icons:bool=False,
                       include_hidden:bool=False, 
                       include_system:bool=True,
                       intKeys:bool=False) -> PlacesMap:
    """Collect user places as defined in the freedesktop.org XDG framework.
    Useful for xdg-compliant Linux desktops.
    
    Returns:
    ========

    A mapping of url (str) ↦ DEPlace

    If the `pyxdg` module is installed, the function will parse the file
    `user-places.xbel` located in the xdg.BaseDirectory.xdg_data_home directory.
    
    Otherwise, the function relies on the QtCore.QStandardPaths to build a 
    generic list of "places".
    
    NOTE: Not all these places will be useful in Scipyen. 

    In particular, the places relating to specific IO protocols and KDE Solid 
    devices should be filterd out of the results (e.g., see get_local_filesystem_places).
    
    
    """
    # NOTE: 2025-02-08 10:07:51 TODO:
    # This is static: whenever a place, or the places repository, is altered
    # this won't be captured until a new Scipyen session is launched.
    
    nSeparators = 0
    
    if isinstance(schema, str) and schema not in SCHEMAS:
        schema = None
        
    # elif isinstance(schema, bool):
    #     asQUrl = schema = True
    #     schema = None
        
    ret = PlacesMap()
    stdPlaces = get_standard_desktop_places(all_folder_icons)
    # stdPlaces = get_standard_desktop_places(asQUrl, all_folder_icons)
    
    # NOTE: 2023-05-01 13:38:10 TODO
    # below we are using the file `user-places.xbel` or `recently-used.xbel` located in 
    # `xdg.BaseDirectory.xdg_data_home`
    #
    
    # structure -- user-places.xbel:
    # <xbel xmlns:bookmark="http://www.freedesktop.org/standards/desktop-bookmarks" xmlns:kdepriv="http://www.kde.org/kdepriv" xmlns:mime="http://www.freedesktop.org/standards/shared-mime-info">
    # <bookmark href="file:///home/cezar">
    # <title>Home</title>
    # <info>
    # <metadata owner="http://freedesktop.org">
    #     <bookmark:icon name="user-home"/>
    # </metadata>
    # <metadata owner="http://www.kde.org">
    #     <ID>1569705899/0</ID>
    #     <isSystemItem>true</isSystemItem>
    #     <IsHidden>false</IsHidden>
    # </metadata>
    # </info>
    # </bookmark>
    # </xbel>

    getIcon = lambda x: "folder-remote-symbolic" if "remote" in x.opts else "drive-harddisk-symbolic"
    
    partitions = filesystems.get_disk_partitions()

    if sys.platform.startswith("linux"):
        import pyudev
        if HAS_PYXDG:
            xbel = "user-places.xbel"
            xbel_file = os.path.join(xdg.BaseDirectory.xdg_data_home, xbel)
            # if not os.path.exists(xbel_file):
            #     return ret
            if os.path.exists(xbel_file):
                xbel_places = pio.loadXMLFile(xbel_file)

                if "xbel" in xbel_places.documentElement.tagName.lower():
                    bookmark_nodes = xbel_places.getElementsByTagName("bookmark")
                    
                    if isinstance(schema, str) and len(schema):
                        bookmark_nodes = list(filter(lambda x: x.getAttribute("href").startswith(schema), bookmark_nodes))
                    
                    
                    for k,b in enumerate(bookmark_nodes):
                        place_uri = b.getAttribute("href")
                        # NOTE: 2025-01-22 11:41:26 apply schema filter if any
                        # print(f"place_uri: {place_uri}")
                        # if isinstance(schema, str) and len(schema) and not place_uri.startswith(schema):
                        #     continue
                            
                        place_name = b.getElementsByTagName("title")[0].childNodes[0].data
                        
                        if len(place_name) == 0 or len(place_uri) == 0:
                            continue
                        
                        info_node = b.getElementsByTagName("info")[0]
                        info_metadata_nodes = info_node.getElementsByTagName("metadata")
                        
                        place_icon_name = info_metadata_nodes[0].getElementsByTagName("bookmark:icon")[0].getAttribute("name")
                        
                        systemitem_nodes = info_metadata_nodes[1].getElementsByTagName("isSystemItem")
                        hidden_nodes = info_metadata_nodes[1].getElementsByTagName("isHidden")
                        app_nodes = info_metadata_nodes[1].getElementsByTagName("OnlyInApp")
                        
                        if len(systemitem_nodes):
                            is_system_place = systemitem_nodes[0].childNodes[0].data.lower() == "true"
                        else:
                            is_system_place=False
                            
                        if not include_system and is_system_place:
                            continue
                            
                        if len(hidden_nodes):
                            is_hidden = hidden_nodes[0].childNodes[0].data.lower() == "true"
                        else:
                            is_hidden = False
                            
                        if not include_hidden and is_hidden:
                            continue

                        if len(app_nodes):
                            app_info = app_nodes[0].childNodes
                            if len(app_info):
                                app = app_info[0].data
                            else:
                                app = str()
                        else:
                            app = str()
                            
                        place_url = QtCore.QUrl(place_uri)
                        
                        key = place_uri

                        if key in ret and isinstance(ret[key], DEPlace):
                            ret[key].name_aliases.append(place_name)
                        else:
                            ret[key] = DEPlace(place_name, place_url, # always as QUrl regardless of asQUrl
                                                icon = place_icon_name, # can be a system icon name or a path/file name
                                                system = is_system_place,
                                                hidden = is_hidden,
                                                app = app)

        # create desktop places for non-standard partitions or removable media
        # NOTE: 2025-03-03 21:14:26 FIXME/TODO
        # this is quite contrived because it seeks to avoid adding places ot btrfs snapshots and other 
        # paritions such as /boot/EFI
        # -> must streamline this !
        context = pyudev.Context()
        devices = list(context.list_devices(subsystem="block", DEVTYPE="partition"))
        disks = list(context.list_devices().match_property("DEVTYPE", "disk"))
        
        drivePlaces = sorted(list(map(lambda x: DEPlace(x.device.replace("/dev/", ""), 
                                                        QtCore.QUrl(pathlib.Path(x.mountpoint).as_uri()), 
                                                        icon=getIcon(x)),
                               list(filter(lambda x: "/run/media/" in x.mountpoint, partitions)))), key = lambda x: x.name)
        ret_paths = list(map(lambda x: urlToPath(x.url), ret.values()))
        
        # check for custom (fixed) partitions mounts outside /run/media, and add them
        #
        # I need partitions because the pyudev does NOT offer information about
        # where is the device mounted in the file system, while psutil does.
        # This is needed to capture mounted removable media (I'm sure Solid
        # framework does a much better job than this)
        #
        # The down side is that it also includes partitions that are NOT needed, such as
        # /boot/EFI
        # various btrfs snapshots
        #
        # filter: select a "partition" where the value of the 'device' attribute 
        # exists in the list of device names in 'devices' (not in 'disks' because we end up with all the 'loop' devices) 
        # but is absent from the list of drivePlaces names
        #
        # we will search for the parition among the mountpoint in 'disks' to capture
        # any inserted oprical disc
        
        partitionPredicate = lambda x:  x.device in list(map(lambda d: d.get("DEVNAME"), devices)) and \
                                        x.device.replace("/dev/", "") not in list(map(lambda p: p.name, drivePlaces)) and \
                                        "subvol" not in x.opts and "boot" not in x.mountpoint
        
        # non-standard partitions - typically user-defined
        # NOTE: 2025-03-03 22:25:12
        # these might not be necessary, as they can always be accessed from the root filesystem
        # through their mount point 😃
        #
        extraPartitions = list(filter(partitionPredicate, partitions))
        if len(extraPartitions):
            internalDrives = sorted(list(map(lambda x: DEPlace(x.device.replace("/dev/", ""),
                                                            QtCore.QUrl(pathlib.Path(x.mountpoint).as_uri()),
                                                            icon = getIcon(x)), extraPartitions)), key = lambda x: x.name)
            drivePlaces = internalDrives + drivePlaces
            
        if len(drivePlaces):
            for place in drivePlaces:
                # print(f"\nplace: {place}")
                deviceLabel = place.name
                
                # find the device for this place, in 'devices'
                devicesForPlace = list(filter(lambda x: x.sys_name == place.name, devices))
                if len(devicesForPlace) == 0:
                    # a device for the place was not found -> also check in disks - contains mounted optical media
                    devicesForPlace = list(filter(lambda x: x.sys_name == place.name, disks))
                    
                
                if len(devicesForPlace):
                    # a udev device for this place was found
                    placeDevice = devicesForPlace[0]
                    deviceName = placeDevice.get("DEVNAME")
                    # print(f"\tfound device: {placeDevice} (name: {deviceName}) for place: {place}")
                    
                    # get the partition for this device, in the list of extra partitions, if found
                    partitionsForDevice = list(filter(lambda x: x.device == deviceName, extraPartitions))
                    
                    if len(partitionsForDevice):
                        partitionForDevice = partitionsForDevice[0]
                        # partitionMountPointUrl = QtCore.QUrl("file://" + partitionForDevice.mountpoint)
                        partitionMountPointUrl = QtCore.QUrl(pathlib.Path(partitionForDevice.mountpoint).as_uri())
                        # print(f"\t\tpartition: {partitionForDevice} with mount point url: {partitionMountPointUrl}")
                        if partitionMountPointUrl in list(map(lambda x: x.url, drivePlaces)):
                            deviceName = f"{deviceName.replace('/dev/', '')} ({partitionForDevice.mountpoint})"
                        
                    # check for device type, change place icon if necessary
                    mediaType = "Internal Drive"
                    if placeDevice.get("ID_CDROM") is not None:
                        place.icon = "drive-optical-symbolic"
                        mediaType = "Removable Media"
                        
                    elif placeDevice.get("ID_USB_TYPE") is not None:
                        place.icon = "drive-removable-media-usb-symbolic"
                        mediaType = "Removable Media"
                        
                    partitionSize = int(devicesForPlace[0].get("ID_FS_SIZE")) * pq.byte
                    pwr = np.log10(partitionSize.magnitude)
                    if pwr < 3:
                        partitionSize = partitionSize.magnitude.round(1)
                        symbol = "bytes"
                    elif pwr < 6:
                        partitionSize = partitionSize.rescale(pq.KiB).magnitude.round(1)
                        symbol = "KiB"
                    elif pwr < 9:
                        partitionSize = partitionSize.rescale(pq.MiB).magnitude.round(1)
                        symbol = "MiB"
                    elif pwr < 12:
                        partitionSize = partitionSize.rescale(pq.GiB).magnitude.round(1)
                        symbol = "GiB"
                    elif pwr < 15:
                        partitionSize = partitionSize.rescale(pq.TiB).magnitude.round(1)
                        symbol = "TiB"
                    elif pwr < 19:
                        partitionSize = partitionSize.rescale(pq.PiB).magnitude.round(1)
                        symbol = "PiB"
                    elif pwr < 22:
                        partitionSize = partitionSize.rescale(pq.EiB).magnitude.round(1)
                        symbol = "EiB"
                    elif pwr < 25:
                        partitionSize = partitionSize.rescale(pq.ZiB).magnitude.round(1)
                        symbol = "ZiB"
                    else:
                        partitionSize = partitionSize.rescale(pq.YiB).magnitude.round(1)
                        symbol = "YiB"
                        
                    # check for device label, change place name if necessary
                    deviceLabel = placeDevice.get("ID_FS_LABEL", "unlabeled partition")
                    # print(f"\t\tdeviceLabel: {deviceLabel}")
                    if deviceLabel == "unlabeled partition":
                        if mediaType == "Internal Drive":
                            deviceLabel = f"{deviceName} {partitionSize} {symbol} {mediaType}"
                        else:
                            deviceLabel = f"{partitionSize} {symbol} {mediaType}"
                            
                    else:
                        if mediaType == "Internal Drive":
                            deviceLabel += f": {deviceName} {partitionSize} {symbol} {mediaType}"
                        else:
                            deviceLabel += f": {partitionSize} {symbol} {mediaType}"

                place.name = deviceLabel
                
    elif sys.platform.startswith("win32"):
        drivePlaces = sorted(list(map(lambda x: DEPlace(x.mountpoint.replace("\\", ""), 
                                                        QtCore.QUrl(pathlib.Path(x.mountpoint).as_uri()), 
                                                        icon=getIcon(x)),
                               partitions)), key = lambda x: x.name)
            
    # add standard places, but:
    # avoid the duplicates - including those with a different name but with urls
    # pointing to the same resolved physical path
    ret_paths = list(map(lambda x: urlToPath(x.url), ret.values()))

    for key, place in stdPlaces.items():
        if key in ret:
            if place.name not in ret[key].name_aliases:
                ret[key].name_aliases.append(place.name)

        else:
            stdPlace = stdPlaces[key]
            if urlToPath(stdPlace.url) not in ret_paths:
                ret[key] = stdPlaces[key]

    dd = dict()
    if len(drivePlaces):
        for place in drivePlaces:
            key = "file://"+place.url.path()
            # place.name = deviceLabel
            if key not in ret:
                dd[key] = place
                
    if len(dd):
        if nSeparators == 0:
            ret["separator"] = DEPlace.separator("Devices")
        else:
            ret[f"separator_{nSeparators}"] = DEPlace.separator("Devices")
        nSeparators +=1
        
        for key, val in dd.items():
            ret[key] = val
    return ret

# def get_recent_places(asQUrl:bool=False,
#                        intKeys:bool=True) -> BookmarksMap:
def get_recent_places(intKeys:bool=True) -> BookmarksMap:
    """Collect recent places as defined in the freedesktop.org XDG framework.
    Useful for Linux desktops that comply with XDG (e.g. KDE, GNOME, XFCE, LXDE, etc).
    
    Returns:
    ========

    A mapping of url (str | int) ↦ {"name"    ↦ descriptive name (str), 
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
    # NOTE: 2025-02-08 10:07:51 TODO:
    # This is static: whenever a bookmark, or the bookmarks repository, is altered
    # this won't be captured until a new Scipyen session is launched.
    
    
    import datetime
        
    ret = BookmarksMap()
    
    # NOTE: 2023-05-01 13:38:10 TODO
    # below we are using the file `user-places.xbel` or `recently-used.xbel` located in 
    # `xdg.BaseDirectory.xdg_data_home`
    #
    
    # structure -- recently-used.xbel:
    # <xbel version="1.0" xmlns:bookmark="http://www.freedesktop.org/standards/desktop-bookmarks" xmlns:mime="http://www.freedesktop.org/standards/shared-mime-info"
    # <bookmark href="file:///home/cezar/Documents/Reprints/Neuropsychiatric%20illness/16p11.2%20CNV/Arbogast%20Herault%202016%20Reciprocal%20effects%20on%20neurocognitive%20and%20metabolic%20phenotypes%20in%20mouse%20models%20of%2016p11.2%20del%20dup%20syndromes/Arbogast%20Herault%202016%20SI.odt" added="2025-01-16T08:48:16.246000Z" modified="2025-01-17T09:08:28.782000Z" visited="2025-01-17T09:08:28.782000Z">
    #     <info>
    #     <metadata owner="http://freedesktop.org">
    #         <mime:mime-type type="application/vnd.oasis.opendocument.text"/>
    #         <bookmark:applications>
    #         <bookmark:application name="libreoffice-writer" exec="libreoffice --writer %u" modified="2025-01-17T09:08:28.782000Z" count="3"/>
    #         </bookmark:applications>
    #     </metadata>
    #     </info>
    # </bookmark>
    # </xbel>
    
    
    if sys.platform.startswith("linux") and HAS_PYXDG:
        xbel = "recently-used.xbel"
        xbel_file = os.path.join(xdg.BaseDirectory.xdg_data_home, xbel)
        if not os.path.exists(xbel_file):
            return ret
        places = pio.loadXMLFile(xbel_file)
            
        if "xbel" in places.documentElement.tagName.lower():
            bookmark_nodes = places.getElementsByTagName("bookmark")
            if len(bookmark_nodes) == 0:
                return ret
            
            for k,b in enumerate(bookmark_nodes):
                bookmark = DEBookmark()
                url = b.getAttribute("href")
                    
                if len(url) == 0:
                    continue
                
                # if asQUrl:
                #     url = QtCore.QUrl(url)
                    
                bookmark["url"] = QtCore.QUrl(url) # always convert this to QUrl
                bookmark["added"] = datetime.datetime.fromisoformat(b.getAttribute("added"))
                bookmark["modified"] = datetime.datetime.fromisoformat(b.getAttribute("modified"))
                bookmark["visited"] = datetime.datetime.fromisoformat(b.getAttribute("visited"))
                
                
                info_nodes = b.getElementsByTagName("info")
                
                if len(info_nodes) == 0:
                    continue
                
                info_node = info_nodes[0]
                
                info_metadata_nodes = info_node.getElementsByTagName("metadata")
                
                if len(info_metadata_nodes) == 0:
                    continue
                
                info_metadata_node = info_metadata_nodes[0]
                
                mime_nodes = info_metadata_node.getElementsByTagName("mime:mime-type")
                
                if len(mime_nodes) == 0:
                    continue
                
                bookmark["mime-type"] = mime_nodes[0].getAttribute("type").replace("&apos", "")
                bookmark_application_node = info_metadata_nodes[0].getElementsByTagName("bookmark:applications")
                bookmark_applications = bookmark_application_node[0].getElementsByTagName("bookmark:application")
                
                bookmark["applications"] = list()
                for ba in bookmark_applications:
                    app = Bunch()
                    app["name"] = ba.getAttribute("name").replace("&apos", "")
                    app["exec_str"] = ba.getAttribute("exec").replace("&apos", "")
                    # app["exec_str"] = ba.getAttribute("exec").replace("&apos", "'")
                    app["modified"] = datetime.datetime.fromisoformat(ba.getAttribute("modified"))
                    app["count"] = ba.getAttribute("count")
                    bookmark["applications"].append(app)
                
                key = k if intKeys else QtCore.QUrl(url) if asQUrl else url
                ret[key] = bookmark
                
    return ret

def iconForStandardPath(localdirectory:str) -> str:
    icons = list(map(lambda x: x.iconName, filter(lambda x: localdirectory in x.paths, StandardDesktopLocationQtInfos)))
    
    if len(icons):
        return icons[0]
    
    return "folder"

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

#     """
#     Get recently viewed places in the underlying desktop environment.
#     
#     NOTE: These are NOT necessarily the recently opened files and directories in 
#     Scipyen!
#     
#     Meaningful only when Scipyen is run inside on a Linux platform with a 
#     desktop environment that complied with the freedesktop.org XDG specification.
#     
#     In all other circumstances, returns an empty dict.
#     
#     WARNING: This should be filtered to remove entries pointing to hidden files,
#     special IO protocols (e.g. "desktop:/", etc) or entries not relevant to 
#     Scipyen.
#     
#     In addition, Scipyen manages its own recently used files, directories and
#     scripts indepenedently, so there should be no much use for this function
#     in the day-to-day use.
#     
#     """
#     
#     # ret = dict()
#     ret = PlacesMap()
#     
#     if sys.platform.startswith("linux") and HAS_PYXDG:
#         places = pio.loadXMLFile(os.path.join(xdg.BaseDirectory.xdg_data_home, "recently-used.xbel"))
#             
#         if "xbel" not in places.documentElement.tagName.lower():
#             return ret
#         
#         bookmarks = places.getElementsByTagName("bookmark")
#         
#         for b in places.getElementsByTagName("bookmark"):
#             place_url   = b.getAttribute("href")
#             modified    = b.getAttribute("modified")
#             visited     = b.getAttribute("visited")
#             added       = b.getAttribute("added")
#             
#             info_node = b.getElementsByTagName("info")[0]
#             info_metadata_nodes = info_node.getElementsByTagName("metadata")
#             
#             if len(info_metadata_nodes) == 0:
#                 continue
#             
#             info_metadata_node = info_metadata_nodes[0]
#             
#             place_mime_type = info_metadata_node.getElementsByTagName("mime:mime-type")[0].getAttribute("type")
#             applications_node = info_metadata_node.getElementsByTagName("bookmark:applications")[0]
#             
#             application_nodes = applications_node.getElementsByTagName("bookmark:application")
#             
#             application_data = list()
#             
#             for application_node in application_nodes:
#                 application_data.append({
#                                          "count": application_node.getAttribute("count"),
#                                          "modified": application_node.getAttribute("modified"),
#                                          "name": application_node.getAttribute("name"),
#                                          "exec": application_node.getAttribute("exec"),
#                                          })
# 
#             ret[place_url] = {"mimetype": place_mime_type,
#                               "applications": application_data,
#                               "added": added, 
#                               "modified": modified,
#                               "visited": visited,
#                               }
#     return ret

def local_recent_places():
    ret = get_recent_places()
    
    return dict([(k,v) for k,v in ret.items() if k.startswith("file:/")])
    

# NOTE: 2023-05-01 10:44:19
# below - not sure we need all of this ...

    
def isFileIndexingEnabled():
    # place holder; Baloo or localsearch are not used by Scipyen hence this will
    # be False
    # NOTE 2025-02-07 08:59:18 TODO
    # Check the functionality provided by the desktop environment under which
    # Scipyen session is running. Then use the file search & indexing utilities/tools
    # available on that platform
    #
    # for now, return False
    if is_kde():
        # this relies on KConfig framework to read the configuration file
        # "baloofilerc" and extract the value of "Indexing-Enabled" from the 
        # "Basic Settings" group in that cofiguration
        # do I really want to implement this ?!?
        
        # perhaps I should create a subpackage for desktop integration
        # with "adapters" for various Linux desktops - a very long shot...
        #
        # but in the short term I might include there a module with KDE cli
        # utilities (called via subprocess):
        # kde-open, kioclient, kfmclient, kmimetypefinder, kbookmarkmerger
        # krunner (the Alt-F2 thing), kdesu, ktrash6, kfind, balooctl,
        # keditbookmarks, keditfiletype
        # (plasmashell --version)
        # qdbus (to inspect the session bus) - but that relies on qdbus being 
        # installed
        
        # also, to consider cli utilities kreadconfig6, kwriteconfig6:
        # kreadconfig6 --file baloofilerc --group "Basic Settings" --key "Indexing-Enabled" --default "True"
        pass
    
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
    
def desktopPlaceUrl(p:DEPlace) -> QtCore.QUrl:
    if not isinstance(p, DEPlace):
        raise TypeError(f"Expecting a DEPlace; instead, got {type(p).__name__}")
    url = p.url
    return url if isinstance(url, QtCore.QUrl) else QtCore.QUrl(url)
        
def closestPlace(url:QtCore.QUrl, places:typing.Optional[PlacesMap]=None) -> DEPlace | None:
    # TODO 2025-02-21 13:48:06
    # ensure only local paths are dealt with, here
    # print(f"{__name__}.closestPlace({url}, {places})")
    schema = url.scheme()
    if not isinstance(places, PlacesMap):
        places = get_desktop_places(schema) #, True)

    # fallback = DEPlace(str(), url, icon = iconNameForUrl(url))#, app=None)

    if len(places) == 0:
        return fallback

    pathForUrl = urlToPath(url)

    # predicate1 = lambda x: pathForUrl == x.urlPath()
    predicate = lambda x: pathForUrl == x.urlPath() or pathForUrl.is_relative_to(x.urlPath())
    # if sys.platform.startswith("win32"):
    #     predicate = lambda x: pathForUrl == x.urlPath() or pathForUrl.is_relative_to(x.urlPath()) or len(pathForUrl.parts) == len*()


    foundPlaces = list(reversed(sorted(filter(predicate, places.values()), key = lambda x: pathStrLen(x.url))))
    
    # print(f"\tfoundPlaces = {foundPlaces}")

    # toUrl = lambda x: x if isinstance(x, QtCore.QUrl) else QtCore.QUrl(x)
    
    return foundPlaces[0] if len(foundPlaces) else None
        
class PlacesMonitor(QtCore.QObject):
    __instance__ = None # NOTE: Singleton design pattern
    sig_placesChanged = Signal(name="sig_placesChanged")
    sig_bookmarksChanged = Signal(name="sig_bookmarksChanged")
    
    def __new__(cls:typing.Self, *args, **kwargs) -> typing.Self:
        # NOTE: Singleton design pattern
        if not hasattr(cls, "__instance__") or not isinstance(cls.__instance__, cls):
            cls.__instance__ = super(PlacesMonitor, cls).__new__(cls, *args, **kwargs)
            
        return cls.__instance__
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.placesWatcher = QtCore.QFileSystemMonitor(parent=self)
        self.bookmarksWatcher = QtCore.QFileSystemMonitor(parent=self)
        
        self.setupWatcher()
        self.__instance__ = self
        
    @classmethod
    def _walk_mro(cls) -> typing.Generator[typing.Self, None, None]: # NOTE: Singleton design pattern
        for subclass in cls.mro():
            if (
                issubclass(cls, subclass)
                and issubclass(subclass, typing.Self)
                and subclass != typing.Self
            ):
                yield subclass
                
    @classmethod
    def initialized(cls:typing.Self) -> bool: # NOTE: Singleton design pattern
        return hasattr(cls, "__instance__" and isinstance(cls.__instance__, cls))
    
    @classmethod
    def instance(cls:typing.Self, *args, **kwargs) -> typing.Self: # NOTE: Singleton design pattern
        if cls.__instance__ is None:
            inst = cls(*args, **kwargs)
            for subclass in cls._walk_mro():
                subclass.__instance__ = inst
        if hasattr(cls, "__instance__") and isinstance(cls.__instance__, cls):
            return cls.__instance__
        else:
            raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls.__instance__).__name__}")

    # @staticmethod
    # def getSelf() -> typing.Self: # originally self()... in kprotocolinfofactory.cpp
    #     return ProtocolInfoFactory.__instance__
    
    def setupWatcher(self):
        if sys.platform.startswith("linux") and HAS_PYXDG:
            user_xbel = os.path.join(xdg.BaseDirectory.xdg_data_home, "user-places.xbel")
            recents_xbel = os.path.join(xdg.BaseDirectory.xdg_data_home, "recently-used.xbel")
        
            if os.path.exists(user_xbel):
                self.placesWatcher.addPath(user_xbel)
                self.placesWatcher.fileChanged.connect(self.slot_placesChanged)
                
            if os.path.exists(recents_xbel):
                self.bookmarksWatcher.addPath(recents_xbel)
                self.bookmarksWatcher.fileChanged.connect(self.slot_bookmarksChanged)
        
    @Slot()
    def slot_placesChanged(self):
        self.sig_placesChanged.emit()
        
    @Slot()
    def slot_bookmarksChanged(self):
        self.sig_bookmarksChanged.emit()
