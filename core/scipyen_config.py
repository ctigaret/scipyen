#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" Scipyen configuration module for non-gui (Qt) options 

are configuration settings for various Scipyen functionalities:

ScanData analysis

electrophysiology apps (LTP, AP analysis, IV curves, etc)

The non-gui options are stored in yaml file format using the confuse library.

The gui options are stored directly in Scipyen.conf under groups given by the
name of the QMainWindow or QWidget subclass which represents the user interface
of the (sub)application that uses these options (e.g., LSCaTWindow, ScipyenWindow,
SignalViewer, etc).

While gui-related options (e.g., window size/position, recent files,
recent directories, etc.) are stored using the PyQt5/Qt5 settings framework,
non-gui options contain custom parameter values for various modules, e.g.
options for ScanData objects, trigger detection, etc. 

These "non-gui" options are often represented by hierarchica data structures
(e.g., nested dict) not easily amenable to the linear (and binary) format of the
Qt5 settings framework.

"""
# NOTE: 2021-01-09 10:54:10
# A framework for configuration options:
# A configuration is a possibly nested (i.e., hierarchical) mapping that contains 
# parameter values for various modules and functions in Scipyen, that are unrelated
# to GUI configuration options
# 
# When the mapping is hierarchical, it provides a branched configuration structure 
# (think nested dictionaries): a parameter may be retrieved directly by its "leaf"
# name as long as the leaf name is unique inside the configuration, or by its 
# fully-qualified path name (dot-separated names).
# 
# A parameter value can be any type, and is stored under a str key (the name of 
# the parameter) which must be a valid Python identifier (this excludes Python
# keywords).
# 
# Some leaf names are fixed (e.g. see FunctionConfiguration, below)
# 
# Implementation:
# Configurations are DataBag() objects. A parameter with value type DataBag and
# stored in the configuration will be interpreted as a "subconfiguraton"
#

#import base64
import os
import inspect, typing
import confuse
from types import new_class
from functools import partial

from matplotlib.figure import Figure
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtWidgets import (QWidget, QMainWindow)
from PyQt5.QtCore import (QSettings, QVariant)

import traitlets
from traitlets.utils.bunch import Bunch
import traitlets.config
from .traitcontainers import DataBag
from core import traitutils
from core.prog import safeWrapper


# BEGIN NOTE: 2021-01-10 13:17:58
# LazyConfig inherits form confuse.Configuration, but its read() method must be 
# called explicitly/programmatically (i.e. unlike its ancestor Configuration,
# read is NOT called at initialization).
# 
# this is the passed to the mainWindow constructor as the 'settings' parameter
# where its read() method must be called exactly once!
#
# The second parameter is the name of a shim module (empty) just in order to set
# the path correctly for where the default configuration yaml file is located

# ATTENTION 2021-08-17 14:33:10
# do not confuse this with 'config' from console - for IPyton configuration - or
# with other package-specific configurations, in particular those that rely
# on environment variables (e.g. pyqtgraph)
# END NOTE: 2021-01-10 13:17:58

scipyen_config = confuse.LazyConfig("Scipyen", "scipyen_defaults")
if not scipyen_config._materialized:# make sure this is done only once
    scipyen_config.read() 
    
@safeWrapper
def qSettingsGroupPfx(win:typing.Union[QMainWindow, QWidget, Figure]) -> typing.Tuple[str, str]:
    """Generates a QSettings group name and, optionally, a prefix for a window.
    
    Parameters:
    ===========
    win: QMainWindow, QWidget, or matplotlib Figure
    
    Returns:
    =======
    
    A tuple of str (group_name, prefix), where:
    
        * group_name is the name of the settings group in the QSettings .conf 
            file (on Linux this is $HOME/.config/Scipyen/Scipyen.conf)
    
        * prefix is to be prepended to the QSettings key name (pseudo-subgroups)
         and may be the empty string.
        
    For Scipyen's top-level instances of QMainWindow (see NOTE 1):
        * 'group_name' is the name of the viewer's class
        * 'prefix' is the empty string.
        
    For Scipyen's viewers that are not 'top-level':
        * 'group_name' is the name of the viewer's parent class
        * 'prefix' is composed of the name of the viewer's class and a persistent
            tag string that differentiates the specific win instance from other
            instances of the same class as win.
            
    This ensures that the QSettings are consistent among all the instances 
    of the viewer. For example, if there are several ImageViewer instances,
    the window geometry, colormap and other GUI-related settings are those
    of the last ImageViewer window being closed.
    
    Since there can be any number of ImageViewer windows open during a Scipyen
    session, managing the settings for each individual instance is not only 
    difficult, but does not make sense.
        
    For QMainWindow instances that are managed by a Scipyen top-level window it
    is assumed that there is a maximum number of such instances, and managing 
    their settings individually not only is possible but it may also make more 
    sense.
    
    The typical example is that of LSCaT where the main GUI window is a 
    'top-level' Scipyen viewer and manages a fixed number of ImageViewer windows
    (up to the number of image channels). The settings for these individual
    ImageViewer windows need to be persistent across sessions and managed
    individually (e.g., a given channel should always be viewed in the same 
    colormap, etc).
    
    NOTE 1: A 'top-level' window is any Scipyen viewer that operates directly in 
            Scipyen's workspace and is managed by Scipyen's main window.
            
            These include Scipyen's main window (ScipyenWindow), the console
            classes (ScipyenConsole, ExternalConsole, and ExternalConsoleWindow)
            and all matplotlib figures managed by matplotlib.pyplot
            
    """
    pfx = ""
    
    if isinstance(win, QMainWindow):
        #if isinstance(win, WorkspaceGuiMixin): 
        # cannot have here this as importing gui.workspacegui would trigger 
        # recursive import cycles
        if hasattr(win, "isTopLevel"): # (this is a WorkspaceGuiMixin)
            if win.parent() is None or win.isTopLevel:
                gname = win.__class__.__name__
            else:
                gname = win.parent().__class__.__name__
                pfx = win.__class__.__name__
        else:
            # again cannot import ScipyenWindow directly 'cause it will trigger
            # recursive import cycles
            if win.parent() is None or "ScipyenWindow" in win.parent().__class__.__name__:
                gname = win.__class__.__name__
            else:
                gname = win.parent().__class__.__name__
                pfx = win.__class__.__name__
                
    elif isinstance(win, Figure):
        gname = win.canvas.__class__.__name__
                
    else:
        gname = win.__class__.__name__
        
    return gname, pfx

#@safeWrapper
def saveQSettingsKey(qsettings:QSettings, 
                    gname:str, pfx:str, key:str, val:typing.Any) -> None:
    if len(gname.strip()) == 0:
        gname = "General"
    key_name = "%s%s" % (pfx, key)
    #print("saveQSettingsKey group %s key %s, value %s (%s)" % (gname, key_name, val, type(val)))
    qsettings.beginGroup(gname)
    qsettings.setValue(key_name, val)
    qsettings.endGroup()
    
#@safeWrapper
def loadQSettingsKey(qsettings:QSettings,
                     gname:str, pfx:str, key:str, default:typing.Any) -> typing.Any:
    if len(gname.strip()) == 0:
        gname = "General"
    key_name = "%s%s" % (pfx, key)
    #print("loadQSettingsKey group %s key %s, default %s (%s)" % (gname, key_name, type(default).__name__, default))
    qsettings.beginGroup(gname)
    ret = qsettings.value(key_name, default)
    qsettings.endGroup()
    return ret

def syncScipyenSettings():
    pass
    
def syncQSettings(qsettings:QSettings, 
                    win:typing.Union[QMainWindow, QWidget, Figure], 
                    group_name:typing.Optional[str]=None,
                    prefix:typing.Optional[str]=None,
                    save:bool=True)-> typing.Tuple[str, str]:
    """Synchronize user-specifc settings with the Scipyen's Qt configuration file.
    
    The Scipyen's configuration file is in native format, and on Linux it usually
    is $HOME/.config/Scipyen/Scipyen.conf. For details, please see QSettings 
    class documentation in Qt Assistant, or at:
    https://doc.qt.io/qt-5/qsettings.html
    
    The direction of synchronization is determined by the :bool: value of the 
    'save' parameter: when True, the settings are save to the file; otherwise,
    they are loaded.
    
    The general idea is that the QSettings conf file only supports one level of
    grouping for qsetting key/value entries. Subgroups can be emulated with
    distinct prefixes to the qsettings key.
    
    What exactly is synchronized is specified in the class attributes '_qtcfg'
    and '_ownqtcfg' of win.
    
    All window classes in Scipyen that inherit from gui.workspacegui.WorkspaceGuiMixin
    have at least the '_qtcfg' attribute.
    
    _qtcfg is a mapping of QSettings key names to a tuple of str containing:
    * either a single element - corresponding to an instance property with read/write access
    * or two elements corresponding to the getter and setter method (in this order)
        for the particular setting
        
    By default, '_qtcfg' is:
    
    {'WindowSize':      ('size',        'resize'),
     'WindowPosition':  ('pos',         'move'),
     'WindowGeometry':  ('geometry',    'setGeometry'),
     'WindowState':     ('saveState',   'restoreState')
     }
     
    In subclasses of WorkspaceGuiMixin '_qtcfg' should be augmented by a similar
    mapping in '_ownqtcfg'
    
    E.g., for SignalViewer, the '_ownqtcfg' is 
    
    {'VisibleDocks': ('visibleDocks',)}
    
    where 'visibleDocks' is a dynamic property that retrieves a dict 
    {dock_name1: visible bool, dock_name2: visible bool, <etc...>} and its 
    setter expects the same.
    
    The '_qtcfg'-based mechanism ensures that the following keys are always
    synchronized whenever the win's class provides 'getter' and 'setter' methods
    for access:
    
    QSettings key     Getter method                   Setter method
    ------------------------------------------------------------------------------
    Window size       win.size()      -> QSize        win.resisze(QSize)
    Window position   win.pos()       -> QPoint       win.move(QPoint)
    Window geometry   win.geometry()  -> QRect        win.setGeometry(QRect)
    Window state      win.saveState() -> QByteArray   win.restoreState(QByteArray)
    
    Of these, the first three are available for all objects derived from QWidget
    (including RichJupyterWidget,such as Cipyen's console); the window state is 
    only available for objects derived from QMainWindow.
    
    This mechanism can be bypassed in order to save/load QSettings keys directly
    using the QSettings API, or, for a more consistent group and key nomenclature, 
    via qSettingsGroupPfx(), followed by saveQSettingsKey() or loadQsettingsKey()
    functions in this module.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically, or it can be specified.
    
    Because the conf file only supports one level of group nesting (i.e. no 
    "sub-groups") an optional extra-nesting level is emulated by prepending
    a custom prefix to the setting's name (or key).
    
    Parameters:
    ==========
    
    qsettings: QtCore.QSettings. Typically, Scipyen's global QSettings.
    
    win: QMainWindow or matplotlib Figure. The window for which the settings are
        loaded.
    
    group_name:str, optional, default is None. The qsettings group name under 
        which the settings will be saved.
        
        When specified, this will override the automatically determined group 
        name (see below).
    
        When group_name is None, the group name is determined from win's type 
        as follows:
        
        * When win is a matplotlib Figure instance, group name is set to the 
            class name of the Figure's canvas 
            
        * When win is an instance of a QMainWindow (this includes Scipyen's main
            window, all Scipyen viewer windows, and ExternalConsoleWindow):
            
            * for instances of WorkspaceGuiMixin:
                * if win is top level, or win.parent() is None:
                    group name is the name of the win's class
                    
                * otherwise:
                    group name is set to the class name of win.parent(); 
                    prefix is set to the win's class class name in order to
                    specify the settings entries
            
            * otherwise, the win is considered top level and the group name is
            set to the win's class name
            
        For any other window types, the group name is set to the window's class 
        name (for now, this is only the case for ScipyenConsole which inherits 
        from QWidget, and not from QMainWindow).
        
    prefix: str (optional, default is None)
        When given, it will be prepended to the settings entry name. This is 
        useful to distinguish between several windows of the same type which are
        children of the same parent, yet need distinct settings.
        
    custom: A key(str) : value(typing.Any) mapping for additional entries.
    
        The values in the mapping are default values used when their keys are 
        not found in qsettings.
        
        If found, their values will be mapped to the corresponding key in 'custom'
        
        Since 'custom' is passed by reference, the new settings values can be 
        accessed directly from there, in the caller namespace.
        
    Returns:
    ========
    
    A tuple: (group_name, prefix) 
        group_name is the qsettings group name under which the win's settings 
            were saved
            
        prefix is th prefix prepended to each setting name
        
        These are useful to append settings later
    
    """
    
    gname, pfx = qSettingsGroupPfx(win)
    
    if isinstance(group_name, str) and len(group_name.strip()):
        # NOTE: 2021-08-24 15:04:31 override internally determined group name
        gname = group_name
        
    if isinstance(prefix, str) and len(prefix.strip()):
        # NOTE: 2021-08-24 15:04:31 override internally determined group name
        pfx = prefix
        
    if isinstance(pfx, str) and len(pfx.strip()):
        key_prefix = "%s_" % pfx
    else:
        key_prefix=""
        
    settings = dict()
    
    qtcfg = dict()
    qtcfg.update(getattr(win, "_qtcfg", {}))
    qtcfg.update(getattr(win, "_ownqtcfg", {}))
    
    #qtcfg.update(getattr(type(win), "_qtcfg", {}))
    #qtcfg.update(getattr(type(win), "_ownqtcfg", {}))
    
    
    for key, getset in qtcfg.items():
        # NOTE: 2021-08-28 21:59:43
        # val, below, can be a function, or the value of a property
        # in the former case it SHOULD have a '__call__' attribute;
        # in the latter, it is whatever the property.fget returns (which may still be
        # a function or method, with a '__call__' attribute!)
        
        gettername = getset[0]

        if not isinstance(gettername, str) or len(gettername.strip()) == 0:
            continue
        
        getter = inspect.getattr_static(win, gettername, None)
        
        if isinstance(getter, property):
            val = getattr(win, gettername)
            
        elif getter is not None: # in case gettername does not exist as a win's attribute name
            # getter may by a function/method, or a sip.wrapper (for Qt objects)
            val = getattr(win, gettername)()
        
        else:
            continue
            
        #action = "save" if save else "load"
        #print("syncQSettings, %s: win: %s, key: %s, getset: %s, gname: %s, pfx: %s, val %s (%s)" % (action, win.__class__.__name__, key, str(getset), gname, pfx, type(val).__name__, val))
        
        if save:
            saveQSettingsKey(qsettings, gname, key_prefix, key, val)
            
        else:
            if len(getset) == 2:
                settername = getset[1]
                
            else:
                settername = getset[0]
                
            setter = inspect.getattr_static(win, settername, None)
            
            default = val
            
            newval = loadQSettingsKey(qsettings, gname, key_prefix, key, default)
            
            if isinstance(setter, property):
                #print("win.%s = %s" % (settername, newval))
                setattr(win, settername, newval)
                
            elif setter is not None:
                setter = getattr(win, settername)
                setter(newval)
                
            else:
                continue
            
        
        #if len(getset) == 1:
            #if save:
                ##if inspect.isfunction(val) or inspect.isbuiltin(val) or inspect.ismethod(val):
                #if hasattr(val, "__call__"):
                    #saveQSettingsKey(qsettings, gname, key_prefix, key, val())
                    
                #elif val is not None:
                    #saveQSettingsKey(qsettings, gname, key_prefix, key, val)
                    
            #else:
                #if inspect.isfunction(val):
                    #default = val()
                #else:
                    #default = val
                    
                #newval = loadQSettingsKey(qsettings, gname, key_prefix, key, default)
                ## NOTE: when getset is a 1-tuple will raise if getset[0] is not
                ## a read/write property
                
                #if isinstance(setter, property):
                    #setattr(win, setter, newval)
                    
                #elif setter is not None:
                    #setter
                #else:
                    #continue
                #setattr(win, getset[0], newval)
            
        #elif len(getset) == 2:
            #if save:
                #if inspect.isfunction(val) or inspect.isbuiltin(val):
                    #saveQSettingsKey(qsettings, gname, key_prefix, key, val())
                #elif val is not None:
                    #saveQSettingsKey(qsettings, gname, key_prefix, key, val)
            #else:
                #setter = getattr(win, getset[1], None)
                #if setter is not None:
                    #if inspect.isfunction(val) or inspect.isbuiltin(val):
                        #default = val()
                    #else:
                        #default = val
                        
                    #newval = loadQSettingsKey(qsettings, gname, key_prefix, key, default)
                    
                    #if inspect.isfunction(setter):
                        #setter(newval)
                    #else:
                        #setattr(win, getset[1], newval)
            
        #elif len(getset) == 3:
            #default = getset[2]
            #if save:
                #if inspect.isfunction(val):
                    #saveQSettingsKey(qsettings, gname, key_prefix, key, val())
                    
                #elif val is not None:
                    #saveQSettingsKey(qsettings, gname, key_prefix, key, val)
            #else:
                #setter = getattr(win, getset[1], None)
                #if setter is not None:
                    #newval = loadQSettingsKey(qsettings, gname, key_prefix, key, default)
                    #setter(newval)
            
    return gname, pfx
    
class ScipyenConfigurable(object):
    """Defines the makeConfigurable decorator for settings management
    
    See ScipyenConfigurable.makeConfigurable documentation for details
    
    Unrelated to traitlets.config.Configurable - not not confuse!
    
    """
    @classmethod
    def makeConfigurable(cls, confname:str, conftype:str="Qt"):
        """Decorator to set up a type's property as a configurable.
        
        A configurable is an attribute (typically, a data descriptor) that can 
        be saved as a persistent setting of an object, to be restored in a later
        Scipyen session.
        
        This is achieved by augmenting the type with an attribute that maps an 
        arbitrary setting name (str) to a tuple containing the names of the
        getter and setter methods for the particular data descriptor defined in 
        the object's type.
        
        Depending on the third argument of the initializer, the new type 
        attribute is  called '_qtcfg', or '_cfg' and takes the form:
        
        {
            SettingName1: (getter_method1_name, setter_method1_name),
            SettingName2: (getter_method2_name, setter_method2_name),
            ... etc...
        }
        
        The '_qtcfg' and '_cfg' mappings are used by syncQSettings and 
        syncScipyenSettings, respectively
        
        When the tuple contains only one str, this is assumed to be the name of
        a read/write property. CAUTION: this may raise AttributeError when the
        property is read-only and an attempt is made to set it to a value loaded
        from the config file.
        
        WARNING This behaviour may change in the future, enforcing the read/write
        property to be represented by a tuple of (getter, setter) names even when 
        they are the same.
        
        Of course, the '_qtcfg' and '_cfg' type attributes can be also set 
        manually (i.e. 'hardcoded') in any user-defined type. This is useful 
        when the user-defined type is derived (inherits) from a type defined in 
        a thid party library (and thus cannot be modified), provided that:
        
        1) the designer of the new type already KNOWS what are the getter/setter
        methods for a settings 
        
        2) the setter accepts the same data type as returned by the getter
        
        For example, see WorkspaceGuiMixin._qtcfg which uses 
        PyQt5.QWidgets.QMainWindow method names for window size, position, etc)
        
        Usage scenarios:
        
        1) As a decorator for data descriptors in user-defined classes - this is 
        a shorthand for manually defining '_qtcfg' and/or '_cfg' as above.
        
        Let 'SomeType' a user-defined type, where the designer has defined a
        read-write property called 'someprop':
        
        # this defines the property 'someprop' of 'SomeType' as read-only
        # because this is the first thing that the Python compiler sees when reading
        # the source code, and therefore 'someprop' will only have its 'fget'
        # defined as a function.
        @property           
        def someprop(self):
            return ...
            
        # this adds write capability to the 'someprop' property of 'SomeType'
        # now, the compiler rightly set the property's 'fset' attribute to a 
        # function
        @someprop.setter    
        def someprop(self, val):
            ...
            
        To covert 'someprop' into a Qt setting, decorate _AT_LEAST_ the setter
        so that the property can be used in both ways (read/write)
        
        # this will make it a read-only settings: it can be saved to, or loaded
        # from the config file, but if 'SomeType' does not also define a setter,
        # attempts to set a value loaded from the config file will raise
        # AttributeError
        # NOTE that this happens because when the 'someprop' property is first
        # defined, it is by default read-only (i.e., its 'fset' method is an
        # empty wrapper)
        @makeConfigurable(SomeType, 'SomeProp') # 'Qt' is the default
        @property
        def someprop(self):
            ...
            
        # this will overwrite mechanism the effect of the above by explicitly
        # mapping the settings name 'SomeProp' to ('someprop' , 'someprop')
        # in SomeType._qtcfg attribute
        #
        # Hence, as 'SomeType' is defining a setter for 'someprop', the 
        # decorator needs only to be used here.
        #
        @makeConfigurable(SomeType, 'SomeProp') # 'Qt' is the default
        @someprop.setter
        def someprop(self):
            ...
                
        Parameters:
        ==========
        
        cls: type = the type of the object where the property to be set as a 
            configurable, is defined
            
        confname: str = the name of the configuration (or setting) element
        
        conftype: str = 'Qt', 'default', or anything else (optional, default is 'Qt')
        
            When 'type' is the 'Qt', (the default) then this is a setting to be 
            saved in / loaded from the Scipyen's QSettings conf file 
            (typically, $HOME/.config/Scipyen/Scipyen.conf).
            
            When 'type' is 'default', then this is a setting to be saved in, or
            loaded from, the config_default.yaml file
            (typically, in the root directory of where Scipyen is installed, 
            assuming it has read/write access to the user)
            
            Otherwise, it will be considerd to be a setting to be saved in the 
            user's config.yaml fileLoaders
            (typically, in $HOME/.config/Scipyen/config.yaml)
            
        """
        #print("makeConfigurable: cls", cls, "confname", confname, "conftype", conftype)
        if not isinstance(confname, str) or len(confname.strip()) == 0:
            return f # fails silently
        
        def wrapper(f):
            if isinstance(f, property):
                gs = []
                if inspect.isfunction(f.fget):
                    propname = f.fget.__qualname__.split(".")[-1]
                    gs.append(propname)
                    
                if inspect.isfunction(f.fset):
                    propname = f.fset.__qualname__.split(".")[-1]
                    gs.append(propname)
                    
                if conftype is "Qt":
                    if hasattr(cls, "_qtcfg") and isinstance(cls._qtcfg, dict):
                        cls._qtcfg.update({confname: tuple(gs)})
                        
                    else:
                        cls._qtcfg = Bunch({confname: tuple(gs)})

                elif conftype is "default":
                    # TODO: 2021-08-28 14:55:28
                    # implement saving to defaults
                    pass
            
                else:
                    if hasattr(cls, "_cfg") and isinstance(cls._cfg, dict):
                        cls._cfg.update({confname: tuple(gs)})
                        
                    else:
                        cls._cfg = Bunch({confname: tuple(gs)})
                        
            return f
        
        return wrapper

    @property
    def configurables(self):
        return getattr(self, "_cfg", None) # only present in derived classes
    
    @property
    def qtconfigurables(self):
        """A str -> type mapping of configurable properties for QSettings.
        
        The keys of the mapping (str) are attributes or descriptors with read &
        write access, defined in the viewer class, as follows. 
        
        key:str = QSettings key
        
        value: 
        EITHER: tuple (str, str) = (getter method name, setter method name)
                where:
                    getter method name: name of instance or :class: method that
                                        returns a Python object (CAUTION: when
                                        the method returns SEVERAL obejcts they
                                        will be captured in a tuple!)
                                        
                    setter method name: name of the instance or :class: method that
                                        accepts ONE Python object as parameter
                                        of the same type as the return value of
                                        the getter method
        
        OR:     tuple (str, ) = property
                where: property is the name of a descriptor with read-write access
                CAUTION: If the propert is read-only, trying to set values
                loaded from configuration file will raise AttributeError
                
                WARNING: this behaviour is on its way out, and two method names
                will be required for read-write settings (even if they refer to
                the same method).
        
        The values are returned by the getter method is expected to be built-in 
        Python types that can be easily converted to a QVariant, EXCLUDING:
        - context managers
        - modules
        - classes
        - functions and methods
        - code objects
        - type objects
        - Ellipsis
        - NotImplemented
        - stack frame objects
        - traceback objects
        
        NOTE: No type checking is performed.
        
        """
        # TODO 2021-08-25 16:47:16
        # if using traitlets.config framework then define observer functions to 
        # write atomic qsettings keys to the conf file, as the configurble is changed
        return getattr(self, "_cfg", None) # only present in derived classes

class ScipyenConfiguration(DataBag):
    """Superclass of all non-gui configurations
    """
    leaf_parameters = tuple()
    
    def __init__(self, *args, **kwargs):
        mutable_types = kwargs.pop("mutable_types", False)
        use_casting = kwargs.pop("use_casting", False)
        allow_none = kwargs.pop("allow_none", True)

        if len(self.__class__.leaf_parameters):
            for key in kwargs:
                if key not in self.__class__.leaf_parameters:
                    raise NameError("Parameter %s is non allowed in %s" % (key, self.__class__))
            
        super().__init__(*args, **kwargs, 
                        mutable_types = mutable_types,
                        use_casting = use_casting,
                        allow_none = allow_none)

class FunctionConfiguration(ScipyenConfiguration):
    """ScipyenConfiguration specialized for functional options.
    
    A functional option stores the name of a function, and the names and
    values of its parameters, if present, as one of the many functions available to
    perform a given data processing operation.
    
    The operation itself is described by a function which takes some data and
    possibily other parameters to generate a result.
    
    For example, the process of applying a filter to an image, in order to 
    improve its signal/noise ratio, can use one of several 2D signal processing
    functions defined in, say, scipy.signal, or some custom de-noising function
    of the identify function (i.e. returns the data unprocessed).
    
    A FunctionConfiguration object makes the choice of the filter function used
    in this operation configurable (and, as a result, persistent across Scipyen
    sessions).
    
    
    Describes a function call defined by three parameters:
    
    "name": str = the name of the function; this can be a dotted name.
    
    "args": tuple (default is empty) of unnamed parameters passed to the function
    
    "kwargs": mapping (default is dict()) of keyword parameters passed to the 
            function.
    
    Instances of FunctionConfiguration are designed to store function calls;
    they do not evaluate, or otherwise call, this function.
    
    Usage:
    ------
    
    The function object must first be created, using the stored function name.
    
    Given fcont, a FunctionConfiguration object:
    
    1. "Retrieve" the function object:
    
        Prerequisite: the Python's usual namespace lookup must be able to
        access thre function's symbol.
        
        fn = eval(fconf.name) 
        
    2. Call the function
    
    2.a) with default(*) keyword / named parameter values:
        (*) CAUTION: these default values are the ones stored in fconf, NOT the
        default ones defined in the original function signature
    
        fn(*fconf.args, **fconf.kwargs)
        
        fn(..., **fconf.kwargs) # call with own poritional parameters values
        
    2.b) with its own default(**) parameter values as originally defined in the 
        function signature
        (**) These default values are NOT necessarily those stored in fconf
        
        fn(*fconf.args)
        
        fn(...) # using new positional parameter values
        
    2.c) with completely different new parameter values from those stored in fconf
    
        fn(*args, **kwargs)
        
        
    Construction:
    -------------
    See the documentation for the initializer (FunctionConfiguration())
    
    
    """
    leaf_parameters = ("name", "args", "kwargs")
    
    def __init__(self, *args, **kwargs):
        """Constructs a FunctionConfiguration object.
        Examples:
        1. To create a function configuration for the linear algebra function 
        "norm" (numpy package) either one of the next three calls creates the
        same:
        
        fconf  = FunctionConfiguration(name="np.linalg.norm", kwargs={"axis":0,"ord":2})
        fconf1 = FunctionConfiguration("np.linalg.norm", axis=0, ord=2)
        fconf2 = FunctionConfiguration("np.linalg.norm", **{"axis":0,"ord":2})
        
        Result:
        
        {'args': (), 'kwargs': {'axis': 0, 'ord': 2}, 'name': 'np.linalg.norm'}
        
        NOTE: The third call must explicitly "unwind" the last dictionary, 
        otherwise it will be interpreted as a function's argument of type dict 
        (as if the function specified by 'name' would have expected a dict)

        """
        fname=""
        fargs = tuple()
        fkwargs = dict()
        
        if len(args):
            if isinstance(args[0], str):
                if len(args[0].strip()):
                    fname = args[0].strip()
                    
                else:
                    raise ValueError("Function name cannot be an empty string")
                
            else:
                raise TypeError("First argument must be a str; got %s instead" % type(args[0]).__name__)
            
            if len(args) > 1: # store the rest of the arguments in the fargs
                fargs = args[1:]
                
        fname = kwargs.pop("name", fname)
        fargs = kwargs.pop("args", fargs)
        fkwargs = kwargs.pop("kwargs", fkwargs)
        
        if len(kwargs):
            fkwargs.update(kwargs)
        
        if not isinstance(fname, str):
            raise TypeError("'name' must be a str; got %s instead" % type(fname).__name__)
        
        if len(fname.strip()) == 0:
            raise ValueError("'name' cannot be empty")
        
        super().__init__(name=fname, args=fargs, kwargs=fkwargs)
        
def create_option(option_name:str, 
                  option_value:typing.Any, 
                  parent:ScipyenConfiguration=None) -> ScipyenConfiguration:
    """Creates/adds an option path to an option dictionary
    """
    pass
    
def get_config_file(configuration:confuse.Configuration=scipyen_config,
                    default:bool=False) -> str:
    if not configuration._materialized:
        configuration.read()
        
    if default:
        defsrc = [s for s in configuration.sources if s.default]
        if len(defsrc):
            return defsrc[0].filename
        
    return configuration.user_config_path()
    
def get_config_dir(configuration:confuse.Configuration=scipyen_config) -> str:
    if not configuration._materialized:
        configuration.read()
            
    return configuration.config_dir()
