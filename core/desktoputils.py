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
# Path.cwd() # => current directory
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

import sys, os, pathlib, urllib, typing
import core.xmlutils as xmlutils
import iolib.pictio as pio
import xml.etree.ElementTree as ET

# desktop integration - according to freedesktop.org (XDG)
# ATTENTION: DO NOT install xdg as it will mess up pyxdg
HAS_PYXDG = False
HAS_XDGSPEC = False
try:
    import xdg # CAUTION this is from pyxdg
    HAS_PYXDG = True
    
except:
    try:
        import xdgspec
        HAS_XDGSPEC = True
    except:
        pass
    
def special_directories():
    if sys.platform == "linux" and HAS_PYXDG:
        if os.environ.get("XDG_SESSION_DESKTOP", "") == "KDE" and "plasma5" in os.environ.get("DESKTOP_SESSION"):
            pass
            

def get_user_places():
    if sys.platform == "linux" and HAS_PYXDG:
        user_places = pio.loadXMLFile(os.path.join(xdg.BaseDirectory.xdg_data_home, "user-places.xbel"))
            
        if "xbel" not in user_places.documentElement.tagName.lower():
            return
        
        bookmarks = user_places.getElementsByTagName("bookmark")
        
        
def get_user_place(path:typing.Union[pathlib.Path, str]) -> str:
    if isinstance(path, pathlib.Path):
        path = path.as_uri()
        
    else: # normalize path string as uri string
        parsed_path = urllib.parse.urlparse(path)
        
        if len(parsed_path.scheme) == 0:
            if not os.path.isabs(path):
                path = os.path.abspath(path)
                
            path = pathlib.Path(path).as_uri()
        
            
    if sys.platform == "linux" and HAS_PYXDG:
        user_places = pio.loadTextFile(os.path.join(xdg.BaseDirectory.xdg_data_home, "user-places.xbel"), forceText=True)
        root = ET.fromstring(user_places)
        
        if root.tag != "xbel":
            return path
        
        place = root.findtext(".//*[@href='%s']/title" % path)
        
        if place is None:
            return path
        
        return place

        
    else:
        return path
