# -*- coding: utf-8 -*-
""" Scipyen configuration module to manage and store GUI- and non-GUI-related 
configuration data (a.k.a "settings") specific to Scipyen, beyond the lifetime
of a running Scipyen session.

There are three sets of settings in Scipyen:

1) Qt settings.
These relate to Scipyen's graphical user interface (GUI). Examples include the
geometry and state of Scipyen's windows (and, where applicable, their docklets),
and other UI-related information such as the filters for file and/or variable 
names, directory history, etc).

    Because Scipyen's GUI is built using the Qt toolkit (via PyQt5) these
    settings are managed and stored using Qt toolkit QSettings framework in Qt 
    Core module.
    
    The Qt settings are stored across Scipyen sessions in the fioe "Scipyen.conf"
    at a location that depends on the OS.
    
    On Linux distributions with the latest directory hierarchy standard (the 
    XDG Base Directory Specification¹) the "Scipyen.conf" file is in 
    "NativeFormat" and is located in $HOME/.config/Scipyen.
    
    The location of the Qt settings data can be found by calling
    
    `mainWindow.qsettings.fileName()`
    
    or
    
    `scipyenconf.get_QtSettings_file()`
    
    at the Scipyen console
    

2) Non-Qt settings
These relate to various Scipyen components (e.g. cursor colors in SignalViewer, 
settings for Scipyen's apps - mostly numeric and textual data)

    These settings are managed by the python confuse package, which operates with
    two files:
    
    • a read-only "default" configuration (found in Scipyen's installation 
    directory) named "config_default.yaml"
    
    • a user configuration file named "config.yaml" located in the same directory
    where the QSettings are installed.
    
3) Jupyter/IPython settings
These relate to various configurations for the jupyter/IPython framework used 
by Scipyen's console, and also for matplotlib and for most part ARE NOT managed
by Scipyen. For details please see online documentation for jupyter & IPython²,
and matplotlib³.

    NOTE: Some of these configurations are superseded by some Qt and non-Qt
    settings (e.g. location of the vertical scrollbar in the Scipyen's console)

NOTE: There is currently, a limited overlap between the scopes of the first two
categories of settings (e.g. colors of the GUI cursors are specified as non-Qt
even though the cursors are rendered using the Qt toolkit).

The reason for a "setting" to be considered as Qt or non-Qt largely depends on
whether the setting (and its value) is more suitable to be stored in a 
hierarchical (i.e. arbitrarily nested) structure.

The confuse package (used for the so-called non-Qt settings) natively allows a
hierarchical organization of the settings. 

In contrast, both Qt's QSettings and Jupyter/IPython/matplotlib configuration 
frameworks (see below) are best suited for a linear organization of the 
configuration data (i.e. without nesting).

Footnotes:
¹ https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

² https://docs.jupyter.org/en/latest/use/config.html?highlight=configuration

³ https://matplotlib.org/stable/tutorials/introductory/customizing.html

are configuration settings for various Scipyen functionalities:


"""
#import base64
import os, inspect, typing, types, math, numbers, json, traceback, warnings
import yaml
import dataclasses
from copy import (copy, deepcopy,)
import confuse
from types import new_class
from functools import (partial, wraps,)
from pprint import pprint
import collections
import numpy as np
import pandas as pd
import quantities as pq

import matplotlib as mpl # needed to expose the mro of Figure.canvas
from matplotlib.figure import Figure
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg,)
from qtpy.QtWidgets import (QWidget, QMainWindow)
from qtpy.QtCore import QSettings # NOTE: 2024-05-03 09:26:33 QVariant not available in PySide
# from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
# from PyQt5.QtWidgets import (QWidget, QMainWindow)
# from PyQt5.QtCore import (QSettings, QVariant)

from IPython.lib.pretty import pprint

import traitlets
from traitlets.utils.bunch import Bunch
import traitlets.config
from .traitcontainers import DataBag
from core import (traitutils, strutils)
from core.prog import (safeWrapper, printStyled)
from core.workspacefunctions import user_workspace
from core.quantities import(quantity2str, str2quantity)
from iolib.jsonio import (object2JSON, json2python)

def quantity_representer(dumper, data):
    return dumper.represent_scalar("tag:pq.Quantity", quantity2str(data, precision=8))

def quantity_constructor(loader, node):
    value = loader.construct_scalar(node)
    return str2quantity(value)

confuse.yaml_util.Dumper.add_representer(pq.Quantity, quantity_representer)
confuse.yaml_util.Loader.add_constructor("tag:pq.Quantity", quantity_constructor)

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

#
# Usage examples:
# 
#   # create (or modify) a user-specific configurable at the LazyConfig level
#   scipyen_settings["key"].set(value)
#
#   # OR: access the user config source directly:
#
#   # get user-specific configuration
#   user_src = [s for s in scipyen_config.sources if  not s.default]
#
#   manipulate e.g. add/set a key/value:
#
#   user_src["key"] = value
#
#   # in either case 'key' can be retrived directly from config source or from
#   #   the LazyConfig a result
#
#
#   scipyen_config["key"].get() -> value
#
#   when not sure if 'key' exists, call:
#
#   ret = scipyen_config["key"].get(None) -> None if 'key' doesn't exist
#  
#   save using write_config() defined here

# ATTENTION 2021-08-17 14:33:10
# do not confuse this with 'config' from console - for IPyton configuration - or
# with other package-specific configurations, in particular those that rely
# on environment variables (e.g. pyqtgraph)
# END NOTE: 2021-01-10 13:17:58

application_name = "Scipyen"
organization_name = "Scipyen"

global scipyen_config
scipyen_config = confuse.LazyConfig(application_name, "scipyen_defaults")

if not scipyen_config._materialized:# make sure this is done only once
    scipyen_config.read() 
    
#print(f"scipyen_config module: global qsettings {qsettings.fileName()}")
scipyen_user_config_source = [s for s in scipyen_config.sources if not s.default][0]

def configsrc2bunch(src:typing.Union[confuse.ConfigSource, Bunch]):
    """Creates a nested Bunch from this confuse.ConfigSource
    
    Useful for loading configurable values from a source.
    
    WARNING: If data is a confuse.ConfigSource or traitlets.Bunch, its contents 
    are considered to be configurables (including being nested in several levels).
    
    Any other mapping type (including dict) will be stored directly as is, so 
    that a value of dict type is stored as such, and its contents will not be
    considered a collection of configurables.
    
    """
    return Bunch(((k, configsrc2bunch(v)) if isinstance(v, (confuse.ConfigSource, Bunch)) else (k,v) for k,v in src.items()))

def markConfigurable(confname:str, conftype:str="", setter:bool=True, default:typing.Optional[typing.Any]=None, trait_notifier:typing.Optional[typing.Union[bool, DataBag]] = None, value_type=None):
    """Decorator for instance methods & properties.
    
    Decorates instance properties and methods that access instance attributes 
    considered to be persistent configuration options.
    
    These are managed by Scipyen's QSettings and confuse frameworks.
    
    Parameters:
    ===========
    
    confname: str: the name of the settings parameter (arbitrary but indicative 
        of what it represents)
        
        If this is an empty string, the decorator does nothing.
    
    conftype: str, optional, default is '' (the empty str)
        When 'conftype' is 'Qt' (case-insensitive) the decorated method or
        property will be used as getter/setter in the QSettings framework.
        
        Otherwise, the decorated methods or property will be used as getter/setter
        in the confuse framework.
        
    setter: bool, default is True - required for methods only, where it indicates
        whether the decorated method is a setter (when True) or a getter (when 
        False)
        
        NOTE: for properties, this is determined by the decorated property's
        'fget' and 'fset' attributes.
        
        For a read-only property, 'fset' is None.
        
        For a read-write property, both 'fget' and 'fset' are functions.
        
    default: any type (optional, default is None)
        When present it is used to supply a 'factory' default value to the setter,
        in case the configuration file doesn't have one.
        
    trait_notifier: bool or a DataBag with registered observer handles
        Optional default is None.
        
        When 'trait_notifier' is True, the :class: that owns the decorated property
        or method MUST have an instance attribute 'configurable_traits' with type
        DataBag. Owner derived from ScipyenConfigurable inherit this attribute
        directly from ScipyenConfigurable.
        
        When 'trait_notifier' is a DataBag, the DataBag is an object independent
        of the :class: where this decorator is used. In this case, the DataBag
        object:
        * MUST be accessible from the scope of the caller
        * SHOULD be "observed" by an appropriate callback function (handler).
        
        When trait_notifier is None, then changes ot the confuigurables can be
        hardcoded directly in the observed setter method or property (see. e.g,
        SignalViewer and ImageViewer)
        
        The handler used by the trait notifier's 'observe' function can be an
        ubound function, or an instance method. For ScipyenConfigurable-derived
        :classes: this is the '_observe_configurables_' method, which simply 
        synchronizes the configurable value with the  user's config.yaml file
        (see above).
        
        To customize these actions in the owner :class: use any combination of 
        (a) and (b) options, or the option (c), below:
        
        a) override the 'configurable_traits' DataBag attribute in the :class:
        b) reimplement the '_observe_configurables_' method in the :class:
        c) outside the :class:, define a DataBag trait notifier and a handler, 
            register the handler with the notifier (notifier.observe(...)) then
            pass the notifier as parameter to this decorator.
        
        WARNING:
        The default strategy is to assume that the object passed to the setter
        method or property is directly assigned to the owner instance attribute.
        Acordingly, the trait notifier passed as parameter to the decorator will
        use this object directly. 
        
        This has unintended consequences when the setter generates the attribute 
        value dynamically e.g. it uses the passed object to compute a value for
        the instance attribute. 
        
        In this case the trait notifier should be called directly from within 
        the setter's body, instead of via this decorator (and leave the value
        of 'trait_notifier' to its default None). 
        
        Neveretheless, the decorator is still useful for LOADING the attribute
        value from config.yaml (provided this is what the setter expects).
        
        CAUTION: Always make sure the getter returns the same type of data as 
        that expected by the setter!
    
    value_type: optional default None
        When specified, it must be a type, useful to force cast a config value to
        a desired type. This seems to be necessary for qsettings which converts 
        numbers to strings.
        
    Returns:
    =======
    f: the decorated method or property object, augmented as described below.
        
    Usage:
    ======
    
    1) For read/write properties, decorate the setter's definition, e.g.:
    
    @property
    :def: someprop(self):
        return self._my_prop_
        
    # below, the property is a configurable that will be synchronized with the
    # config.yaml file in the user's Scipyen config directory:
    # '$HOME/.config/Scipyen/config.yaml'
    
    @markConfigurable("MyProperty", trait_notifier=True)
    @someprop.setter(self, val)
    :def: someprop(self, val):
        self._my_prop_ = val
        
        
    @property
    :def: someQtProp(self):
        return self._my_qt_thing_
    
    # below, the property is a configurable that will be synchronized with the
    # QSettings Scipyen.conf file in the user's Scipyen config directory:
    # '$HOME/.config/Scipyen/Scipyen.conf'
    @markConfigurable("MyQtThing", "qt")
    @someQtProp.setter
    :def: someQtProp(self, val):
        self._my_qt_thing_ = val
        
    2) For getter and setter methods, BOTH must be decorated, e.g.:
    
    @markConfigurable("MyProperty", setter=False, trait_notifier=True)
    :def: get_my_prop(self):
        return self._my_prop_
        
    @markConfigurable("MyProperty", setter=True, trait_notifier=True)
    :def: set_my_prop(self, val):
        self._my_prop_ = val
        
    3) Call directly:
    
    3.1) pass an instance method (a function):
    
    func  = markConfigurable(cofnname, conftype, setter, 
                             default=default_val,
                             trait_notifier=<some_databag OR bool>)(obj.method)
                             
    Where func is a bound method, the new (decorated) version of obj.method.
    
    See documentation of makeConfigurable for details - FIXME.
    
    What it does:
    ============
    
    1) When f is a property:
    
    * if f.fget is a function, adds to it a 'configurable_getter' attribute:
            
        f.fget.configurable_getter = {'type': conftype, 
                                      'name': confname, 
                                      'getter':f.fget.__name__, 
                                      'default':None,
                                      'trait_notifier':obj}
            
    * if f.fset is a function, adds to it a 'configurable_setter' attribute:
        f.fset.configurable_getter = {'type': conftype, 
                                      'name': confname, 
                                      'setter':f.fget.__name__, 
                                      'default':None,
                                      'trait_notifier':obj}
            
    2) When f is a method function:
    
    * if setter is False, adds to it a 'configurable_getter' attribute as for
        'f.fget' aboe
        
    * if setter is True, adds to it a 'configurable_setter' attribute as for
        'f.fset' above
    
    CAUTION: the 'default' values are references to python objects; make sure
    they still exist; it is better to leave this parameter to its default (None)
        
    The decorated methods and properties will be used by collect_configurables()
    defined in this module to set up a mapping of configuraiton options.
    
    """
    # FIXME? 2021-11-26 16:47:11
    # cannot check 'f' here !?
    if not isinstance(confname, str) or len(confname.strip()) == 0:
        return f # fail silently
    
    if not isinstance(conftype, str):
        return f # fail silently
    
    conftype = conftype.lower()
    
    def wrapper(f, trn):
        # TODO 2021-09-10 09:55:54
        # check if still works with supplied notifier
        # FIXME 2021-09-10 10:05:55
        # not sure the default really works/is necessary
        if isinstance(f, property):
            # NOTE 2021-09-06 10:42:49
            # applies only to read-write properties
            # hence only decorate xxx.setter if defined
            if all((inspect.isfunction(func) for func in (f.fget, f.fset))):
                setattr(f.fget, "configurable_getter", Bunch({"type": conftype, "name": confname, "getter":f.fget.__name__, "default": default, "value_type": value_type}))
                setattr(f.fset, "configurable_setter", Bunch({"type": conftype, "name": confname, "setter":f.fset.__name__, "default": default, "value_type": value_type}))
                
                if conftype != "qt": #and isinstance(trait_notifier, DataBag):
                    # NOTE: 2021-09-08 09:14:16
                    # for non-qt configurable properties ONLY:
                    # if trait_notifier is defined, then replace f.fset with a 
                    # new function that also updates the trait_notifier
                    # 'trait_notifier' is supposed to be a DataBag with a
                    # registered observer handler, OR a bool which when True, 
                    # expects the :class: owner of the property to provide such
                    # a DataBag via the attribute 'configurable_traits'
                    
                    conf_setter = f.fset.configurable_setter
                    
                    def newfset(instance, *args, **kwargs):
                        """Calls the owner's property fset function & updates the trait notifier.
                        This only has effect when trait notifier is a DataBag
                        that is observing.
                        """
                        
                        trn = kwargs.pop("_trait_notifier_", None)
                        
                        f.fset.__call__(instance, *args, **kwargs)
                        
                        if trn is True:
                            trn = getattr(instance, "configurable_traits", None)
                            
                        if isinstance(trn, DataBag):
                            trn[confname] = args[0]
                            
                    if isinstance(trn, DataBag):
                        conf_setter["trait_notifier"] = trn
                        
                    parset = partial(newfset, _trait_notifier_=trn)
                    
                    setattr(parset, "configurable_setter", conf_setter)
                    
                    return property(fget = f.fget, fset = parset, doc = f.__doc__)
                
        elif inspect.isfunction(f):
            if setter is True:
                setattr(f, "configurable_setter", Bunch({"type": conftype, "name": confname, "setter":f.__name__, "default": default, "value_type": value_type}))
                
                if conftype != "qt":# and isinstance(trait_notifier, DataBag):
                    # see NOTE: 2021-09-08 09:14:16
                        
                    conf_setter = f.configurable_setter #["trait_notifier"] = trait_notifier
                        
                    def newf(instance, trn, *args, **kwargs):
                        """Calls the owner's setter method & updates the trait notifier.
                        This only has effect when trait notifier is a DataBag
                        that is observing.
                        """
                        f(instance, *args, **kwargs)
                        
                        if trn is true:
                            trn = getattr(instance, "configurable_traits", None)
                        
                        if isinstance(trn, DataBag):
                            trn[confname] = args[0]
                            
                    if isinstance(trn, DataBag):
                        conf_setter["trait_notifier"] = trn
                        
                    parset = partial(newf, trn = trn)
                    
                    setattr(parset, "configurable_setter", conf_setter)
                    
                    return parset 
        
            else:
                setattr(f, "configurable_getter", Bunch({"type": conftype, "name": confname, "getter":f.__name__, "default": default, "value_type": value_type}))
                
        elif inspect.isbuiltin(f): # FIXME 2021-09-09 14:09:04
            # NOTE: 2021-09-08 10:10:07
            # builtin_function_or_method callable types (C function & method) 
            # cannot be augmented as above (they're read-only); therefore, we
            # we must wrap on the fly
            #print("trait_notifier", trait_notifier)
            if setter is True:
                conf_setter = Bunch({"type": conftype, "name": confname, "setter":f.__name__, "default": default, "value_type": value_type})

                def newf(instance,  trn, *args, **kwargs):
                    """Calls the owner's setter method & updates the trait notifier.
                    This only has effect when trait notifier is a DataBag
                    that is observing.
                    """
                    f(instance, *args, **kwargs)
                    
                    if conftype != "qt":
                        if trn is True:
                            trn = getattr(instance, "configurable_traits", None)
                            
                        if isinstance(trn, DataBag):
                            trn[confname] = args[0]
                            
                if conftype != "qt" and isinstance(trn, DataBag):
                    conf_setter["trait_notifier"] = trn
                    
                parset = partial(newf, trn=trn)
                    
                setattr(parset, "configurable_setter", conf_setter)
                
                return parset
                
            else:
                configurable_getter = Bunch({"type": conftype, "name": confname, "getter":f.__name__, "default": default, "value_type": value_type})
                
                def newf(instance, *args, **kwargs):
                    return f(instance, *args, **kwargs)
                
                setattr(newf, "configurable_getter", configurable_getter)
                
                return newf
        
        return f
    
    return partial(wrapper, trn = trait_notifier)
    
@safeWrapper
def qSettingsGroupPfx(win:typing.Union[QMainWindow, QWidget, Figure]):
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
        if hasattr(win, "isTopLevel") and win.isTopLevel: # (this is a WorkspaceGuiMixin)
            gname = win.__class__.__name__
        else:
            gname = win.parent().__class__.__name__
            tag = getattr(win, "configTag", "")
            if isinstance(tag, str) and len(tag.strip()):
                pfx = f"{win.__class__.__name__}_{tag}"
            else:
                pfx = win.__class__.__name__
                
    elif isinstance(win, Figure):
        gname = win.canvas.__class__.__name__
                
    else:
        gname = win.__class__.__name__
        
    return gname, pfx

@safeWrapper
def saveQSettingsKey(qsettings:QSettings, gname:str, pfx:str, key:str, val:typing.Any):
    if len(gname.strip()) == 0:
        gname = "General"
    # key_name = "%s%s" % (pfx, key)
    key_name = f"{pfx}{key}"
    # print(f"saveQSettingsKey group: {gname}, key: {key}, value: {val} ({type(val).__name__})")
    qsettings.beginGroup(gname)
    qsettings.setValue(key_name, val)
    qsettings.endGroup()
    
@safeWrapper
def loadQSettingsKey(qsettings:QSettings, gname:str, pfx:str, key:str, default:typing.Any):
    if len(gname.strip()) == 0:
        gname = "General"
    key_name = "%s%s" % (pfx, key)
    
    qsettings.beginGroup(gname)
    # print(f"loadQSettingsKey group: {gname}, key: {key})")
    ret = qsettings.value(key_name, default)
    qsettings.endGroup()
    # print(f"loadQSettingsKey group: {gname}, key: {key}, value: {ret} ({type(ret).__name__})")
    return ret

def syncQtSettings(qsettings:QSettings, win:typing.Union[QMainWindow, QWidget, Figure], 
                   group_name:typing.Optional[str]=None,
                   prefix:typing.Optional[str]=None, 
                   save:bool=True):
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
    distinct prefixes to the qsettings key as described below.
    
    What exactly is synchronized is specified in the ::class:: attribute '_qtcfg'
    of 'win'.
    
    All window classes in Scipyen that inherit from gui.workspacegui.WorkspaceGuiMixin
    have at least the '_qtcfg' attribute which is a mapping of the form:
    
    {setting_name: {'getter': getter_name, 'setter': setter_name}}
    
    , where:
    
    seting_name (str) if the name of the QSettings element (or 'key') in 
        Scipyen.conf file
        
    getter_name (str) is the name of the property or method that returns the
        value which is to be assigned as value to the QSettings 'key' in the 
        Scipyen.conf file
        
    setter_name (str) is the name of the read-write property or method that takes
        the value of the QSettings 'key' in Scipyen.conf as sole argument.
        
    As defined in WorkspaceGuiMixin, '_qtcfg' is a nested Bunch:
    
    {"WindowSize":       {"getter":"size",        "setter":"resize"},
     "WindowPosition":   {"getter":"pos",         "setter":"move"},
     "WindowGeometry":   {"getter":"geometry",    "setter":"setGeometry"},
     "WindowState":      {"getter":"saveState",   "setter":"restoreState"}
    }
    
    This mechanism ensures that the following keys are always synchronized with
    the Scipyen.conf file contents for the standard QMainWindow and QWidget
    settings.
    
    QSettings key     Getter method                   Setter method
    ------------------------------------------------------------------------------
    Window size       win.size()      -> QSize        win.resisze(QSize)
    Window position   win.pos()       -> QPoint       win.move(QPoint)
    Window geometry   win.geometry()  -> QRect        win.setGeometry(QRect)
    Window state      win.saveState() -> QByteArray   win.restoreState(QByteArray)
    
    Subclasses derived from WorkspaceGuiMixin can add their own configurables to
    be managed via QSettings framework and Scipyen.conf file using one of the
    folowing strategies:
    
    1) define their own '_qtcfg' which will be augmented with 
    WorkspaceGuiMixin._qtcfg upon initialization
    
    2) be decorated with the makeConfigurable class decorator; this requires
    that selected read-write properties, as well as getter and setter methods,
    to be decorated with markConfigurable function decorator.
    
    3) define an '_ownqtcfg' attribute fo the same form as _qtcfg: this will be
    taken into account by this function (this strategy is historic)
    
    Classes that do NOT inherit from WorkspaceGuiMixin SHOULD use the strategies
    (2) and (3) - see gui.consoles.ExternalConsoleWidget for example.
    
    NOTE For ::classes:: derived from QWidget, only the first three are available
    (this includes RichJupyterWidget-derived types such as Scipyen's console);
    the window state is only available for objects derived from QMainWindow.
    
    E.g., for SignalViewer._qtcfg is 
    
    {"VisibleDocks": {"getter":"visibleDocks","setter":"visibleDocks"}}
    
    where 'visibleDocks' is a dynamic property that retrieves a dict 
    {dock_name1: visible bool, dock_name2: visible bool, <etc...>} and its 
    setter expects the same.
    
    If SignalViewer did not inherit from WorkspaceGuiMixin, the scipyen_config
    framework would not save/restore the standard QMainWindow parameters
    size, geometry, position and state.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically using 'qSettingsGroupPfx', or it can be 
    manually specified.
    
    Because the QSettings Scipyen.conf file only supports one level of grouping 
    (i.e. no "sub-groups") an optional extra-nesting level is emulated by 
    prepending a custom prefix to the setting's name (or key). This can be 
    determined automatically via 'qSettingsGroupPfx' or set manually.
    
    Finaly, this mechanism can be bypassed in order to save/load QSettings keys
    directly using the QSettings API, and hardcoding appropriate methods in the
    ::class:: defintion. For a more consistent group and key nomenclature, use
    the qSettingsGroupPfx(), followed by saveQSettingsKey() or loadQsettingsKey()
    functions in this module.
    
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
            
        prefix is the prefix prepended to each setting name
        
        These are useful to append settings later
    
    """
    
    gname = ""
    pfx = ""
    
    #gname, pfx = qSettingsGroupPfx(win)
    
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
        
    #print("syncQtSettings %s: win = %s, gname = %s, key_prefix = %s" % ("save" if save else "load", win, gname, key_prefix))
    #print("\n***\nsyncQtSettings %s: win = %s" % ("save" if save else "load", win, ))
    #print("\tgname = '%s', key_prefix = '%s'" % (gname, key_prefix))
    
    if hasattr(win, "qtconfigurables"):
        qtcfg = win.qtconfigurables
        # print(f"\tsyncQtSettings {win.__class__.__name__}, {win.windowTitle()}:")
        
    elif issubclass(win, (mpl.backend_bases.FigureCanvasBase, win, QtWidgets.QWidget)):
        # executed when a :class: inherits from matplotlib.Figure AND ScipyenConfigurable
        qtcfg = Bunch({"WindowSize":       Bunch({"getter":"size",        "setter":"resize"}),
                       "WindowPosition":   Bunch({"getter":"pos",         "setter":"move"}),
                       "WindowGeometry":   Bunch({"getter":"geometry",    "setter":"setGeometry"}),
                      })
        
    elif isinstance(win, Figure):
        # "freestanding" case: loadWindowSettings is called manually to save/store
        # window size & pos & geometry 
        canvas = getattr(win, "canvas", None)
        
        if issubclass(canvas, (mpl.backend_bases.FigureCanvasBase, win, QtWidgets.QWidget)):
            qtcfg = Bunch({"WindowSize":       Bunch({"getter":"size",        "setter":"resize"}),
                           "WindowPosition":   Bunch({"getter":"pos",         "setter":"move"}),
                           "WindowGeometry":   Bunch({"getter":"geometry",    "setter":"setGeometry"}),
                        })
            
            win = canvas
        
    else:
        qtcfg = Bunch()
        qtcfg.update(getattr(win, "_qtcfg", Bunch()))
        qtcfg.update(getattr(win, "_ownqtcfg", Bunch()))
    
    # print(f"\tsyncQtSettings {win.__class__.__name__}, {win.windowTitle()}:\n\t{qtcfg}")
    # if save:
    #     print(f"\n\tsyncQtSettings {win.__class__.__name__}, {win.windowTitle()}:")

    for confname, getset in qtcfg.items():
        # NOTE: 2021-08-28 21:59:43
        # val, below, can be a function, or the value of a property
        # in the former case it SHOULD have a '__call__' attribute;
        # in the latter, it is whatever the property.fget returns (which may still be
        # a function or method, with a '__call__' attribute!)
        #print("\tconfname = %s" % confname)
        gettername = getset.get("getter", None)
        # if save: 
        #     print(f"\t\tgettername = {gettername}")

        if not isinstance(gettername, str) or len(gettername.strip()) == 0:
            continue
        
        getter = inspect.getattr_static(win, gettername, None)
        
        if isinstance(getter, property):
            val = getattr(win, gettername)
            #val = getter.fget(win)
            #print("\t\tgetter win.%s -> %s" % (gettername, val))
            
        elif getter is not None: # in case gettername does not exist as a win's attribute name
            # getter may by a function/method, or a sip.wrapper (for Qt objects)
            val = getattr(win, gettername)()
            #print("\t\tgetter win.%s() -> %s" % (gettername, val))
        
        else:
            continue
            
        #action = "save" if save else "load"
        #print("syncQtSettings, %s: win: %s, key: %s, getset: %s, gname: %s, pfx: %s, val %s (%s)" % (action, win.__class__.__name__, key, str(getset), gname, pfx, type(val).__name__, val))
        
        if save:
            saveQSettingsKey(qsettings, gname, key_prefix, confname, val)
            
        else:
            settername = getset.get("setter", None)
            #print("\t\tsettername = %s" % settername)
            
            if not isinstance(settername, str) or len(settername.strip()) == 0:
                continue
                
            setter = inspect.getattr_static(win, settername, None)
            
            default = val
            
            newval = loadQSettingsKey(qsettings, gname, key_prefix, confname, default)
            # print(f"group {gname} key_prefix {key_prefix} confname {confname} newval {newval}")
            
            # NOTE: 2023-09-18 11:38:33
            # Compensate for the situation where the window position or geometry
            # stored in the configuration would place it off screen.
            # 
            # This is the case when Scipyen is sed on a machine which occasionally 
            # is connected to a supplementary monitor ("screen"): after running
            # Scipyen on, say, two monitors, and with windows shown on the 
            # second monitor, these windows would be painted off-screen if 
            # Scipyen would be relaunched after disconnecting the supplementary
            # monitor. This is can happen when the machine is, say a laptop
            # which only occasionally gets connected to a second (external) monitor.
            #
            # The code below finds out if the stored window position coordinates 
            # (either as a WindowPosition QtCore.QPoint, or as the X,Y coordinates
            # in WindowGeometry QtCore.QRect) go beyond the boundaries of the 
            # virtual geometry of the desktop. It then resets the offending 
            # coordinate to the minimum value available.
            if confname in ("WindowPosition", "WindowGeometry"):
                availableVirtGeom = QtGui.QGuiApplication.primaryScreen().availableVirtualGeometry()
                
                if newval.x() > availableVirtGeom.x() + availableVirtGeom.width():
                    newX = availableVirtGeom.x()
                else:
                    newX = newval.x()
                    
                if newval.y() > availableVirtGeom.y() + availableVirtGeom.height():
                    newY = availableVirtGeom.y()
                else:
                    newY = newval.y()
                    
                if confname == "WindowPosition":
                    newval = QtCore.QPoint(newX, newY)
                    
                else:
                    newW = newval.width()
                    newH = newval.height()
                    
                    newval = QtCore.QRect(newX, newY, newW, newH)
            
            if isinstance(setter, property):
                config_setter = getattr(setter.fset, "configurable_setter")
                value_type = config_setter.get("value_type", None)
                if not isinstance(value_type, type):
                    value_type = type(default)
                    
                try:
                    if value_type is bool:
                        if isinstance(newval, str):
                            newval = newval.lower()=="true"
                        elif not isinstance(newval, bool):
                            newval = False
                            
                    elif value_type is not None:
                        newval = value_type(newval)
                    
                except:
                    # warnings.warn(f"Cannot cast {type(newval).__name__} to {value_type.__name__}; reverting to default", category=RuntimeWarning)
                    newval = default
                
                # if settername == "autoRemoveViewers":
                #     print(f"{win.__class__.__name__} syncQtSettings: settername = {settername},  newval = {newval}")
                #print("\t\tsetter win.%s = %s" % (settername, newval))
                setattr(win, settername, newval)
                
            elif setter is not None:
                #print("\t\tsetter win.%s(%s)" % (settername, newval))
                setter = getattr(win, settername)
                setter(newval)
                
            else:
                continue
            
    return gname, pfx

def collect_configurables(cls):
    """Collects all configurables for this instance in a mapping.
    
    The mapping has two fields: 'qt' and 'conf' that describe what settings
    are to be saved to / loaded from the Scipyen.conf ('qt') or config.yaml 
    ('conf') files.
    
    Each field is a mapping of str keys (the name of the configurable as
    it would be stored in the config file) to a dict that identifies the
    getter, setter, configuration type, and a 'factory default' value.
    
    """
    if not inspect.isclass(cls):
        cls = cls.__class__
    
    ret = Bunch({"qt": Bunch(), "conf": Bunch()})
    
    for name, fn in inspect.getmembers(cls):
        getterdict = Bunch()
        setterdict = Bunch()
        confdict = Bunch()
        if isinstance(fn, property):
            if inspect.isfunction(fn.fget) or isinstance(fn.fget, partial):
                confdict.update(getattr(fn.fget, "configurable_getter", Bunch()))

            if inspect.isfunction(fn.fset) or isinstance(fn.fset, partial):
                confdict.update(getattr(fn.fset, "configurable_setter", Bunch()))
                
        elif inspect.isfunction(fn) or isinstance(fn, partial):
            confdict.update(getattr(fn, "configurable_getter", Bunch()))
            confdict.update(getattr(fn, "configurable_setter", Bunch()))
                
        else:
            continue # skip members that are not methods or properties
        
        if len(confdict):
            target = ret.qt if confdict.type.lower() == "qt" else ret.conf

            cfgget = confdict.get("getter", None)
            cfgset = confdict.get("setter", None)
            cfgdfl = confdict.get("default", None)
            cfgtrt = confdict.get("trait_notifier", None)
            
            cfgdict = Bunch()
            
            if cfgget is not None:
                cfgdict.getter = cfgget
            
            if cfgset is not None:
                cfgdict.setter = cfgset
                
            cfgdict.default = cfgdfl
            cfgdict.trait_notifier = cfgtrt
                
            if confdict.name not in target:
                target[confdict.name] = cfgdict
                
            else:
                target[confdict.name].update(cfgdict)
                
    # adapt for "old" API
    ret.qt.update(getattr(cls, "_qtcfg", dict()))
    ret.qt.update(getattr(cls, "_ownqtcfg", dict()))
    ret.conf.update(getattr(cls, "_cfg", dict()))
    ret.conf.update(getattr(cls, "_owncfg", dict()))
    
    return ret

class ScipyenConfigurable(object):
    """Base :class: for Scipyen's configurable types.
    
    Implements functionality to deal with non-Qt settings made persistent across
    Scipyen sessions.
    
    Provides common functionality for Scipyen's QMainWindow-based GUI classes (as
    long as they inherit from ScipyenConfigurable as well, either directly, or
    indirectly via WorkspaceGuiMixin)
    
    Qt-based GUI settings (where appropriate) are dealt with separately, by either
    inheriting from gui.workspacegui.WorkspaceGuiMixin, or directly by using
    the loadWindowSettings and saveWindowSettings in the gui.workspacegui module,
    or using the syncQtSettings function defined in this module.
    
    ScipyenConfigurable is inherited directly by:
        • gui.workspacegui.WorkspaceGuiMixin
        • gui.consoles.ConsoleWidget
        
    and indirectly (via WorkspaceGuiMixin) by:
        • gui.mainwindow.ScipyenWindow
        • gui.consoles.ExternalConsoleWindow
        • gui.consoles.ScipyenConsole,
        • gui.consoles.ScipyenConsoleWidget ← gui.consoles.ConsoleWidget
        • gui.scipyenviewer.ScipyenViewer
        • gui.scipyenviewer.ScipyenFrameViewer ← gui.scipyenviewer.ScipyenViewer
        • all viewer classes in gui subpackage, indirectly via either 
        gui.scipyenviewer.ScipyenViewer or gui.scipyenviewer.ScipyenFrameViewer.
    
    NOTE: For developers:
    1) If the derived class defines a UI component, is better to call`loadSettings`
        called AFTER the initialization of its widgets. 
    
        This is MANDATORY whenever the derived class uses the `loadSettings` 
        method to assign default values (read from the config file) to various 
        widgets.
    
        When exactly `loadSettings` should be called depends on what UI widgets 
        it affects, and when are these defined and initialized.
    
        For example, SignalViewer and ImageViewer have a special function
        `_configureUI_` (inherited from ScipyenViewer) which calls `setupUi`,
        the adds a few more actions & widgets (I agree, this is bad practice).
    
        For this reason, `loadSettings` is called AFTER `_configureUI_`; since
        this approach is used in common by SignalViewer and ImageViewer, it 
        was factored out in ScipyenViewer and therefore it will be used by any
        class that inherits from ScipyenViewer (either directly, or indirectly
        via ScipyenFrameViewer).
    
        The consequence that an UI class inheriting from ScipyenConfigurable may
        need to reimplement the `loadSettings` method.
    
        The `loadSettings` method defined here only reads the values for
        configurables from the config file(s). Therefore, it should be called 
        from within the `loadSettings` of the derived class; for example:
    
        `super().loadSettings()` 
    
        or
    
        `super(WorkspaceGuiMixin, self).loadSettings()`
    
        If the derived class does not store default values for its UI widgets
        in the config file then it does not need to reimplement this method. 
        This is what SignalViewer does, because it stores in the config file only
        data that is associated with objects that are NOT initialized during
        __init__ (such as the colours of various cursor types).
    
    2) must call saveSettings() inside the closeEvent() handler in the derived
        class
    
    """
    # NOTE: 2021-09-23 11:39:57
    # added self._tag and tag property getter/setter
    # to be used for configurables of non-top level windows 
    qsettings = QtCore.QSettings(organization_name, application_name)

    _scipyen_settings_  = scipyen_config
    _user_settings_src_ = scipyen_user_config_source
    _user_settings_file_ = _user_settings_src_.filename
    
    def __init__(self, configTag:typing.Optional[str]=None):
        self.configurable_traits = DataBag()
        self.configurable_traits.observe(self._observe_configurables_)
        self._tag = configTag
        
    def _get_parent_(self):
        parent = None
        parent_f = inspect.getattr_static(self, "parent", None)
        if inspect.isfunction(parent_f) or inspect.ismethoddescriptor(parent_f):
            parent = self.parent()
            
        elif isinstance(parent_f, property):
            parent = parent_f.fget(self)
            
        return parent

    def _observe_configurables_(self, change):
        isTop = hasattr(self, "isTopLevel") and self.isTopLevel
        parent = self._get_parent_()
        tag = self.configTag
        
        cfg = self._make_confuse_config_data_(change, isTop, parent, tag)
        #### BEGIN debug - comment out when done
#         if self.__class__.__name__ == "TwoPathwaysOnlineLTP":
#             print(f"ScipyenConfigurable<{self.__class__.__name__}>._observe_configurables_():")
#             stack = inspect.stack()
#             for s in stack:
#                 print(f"\t\tcaller {s.function}")
#             # currentexecframe = inspect.currentframe()
#             # outerframes = inspect.getouterframes(currentexecframe, 2)
#             # print(f"\tcaller {callframe[1][3]}")
#             print(f"\tchange.name = {change.name}")
#             print(f"\tchange.type = {change.type}")
#             print(f"\tchange.old = {change.old} ({type(change.old).__name__})")
#             print(f"\tchange.new = {change.new} ({type(change.new).__name__})")
#             print(f"\tconfig = {cfg}")
#         
#             print("\ttraits observer state:") 
#             for k, v in self.configurable_traits.__observer__.__getstate__().items():
#                 if isinstance(v, dict):
#                     print(f"\t\t{k}:")
#                     for kk, vv in v.items():
#                         print(f"\t\t\t{kk} = {vv}")
#                 else:
#                     print(f"\t\t{k} = {v}")
#             print("\tobserver class traits:")
#             for k, v in self.configurable_traits.__observer__.class_traits().items():
#                 print(f"\t\t{k} = {v}")
#             print("\tobserver class own traits")
#             for k, v in self.configurable_traits.__observer__.class_own_traits().items():
#                 print(f"\t\t{k} = {v}")
        #### END debug - comment out when done
                
        
        if isinstance(cfg, Bunch):
            for k,v in cfg.items():
                scipyen_config[k].set(v)
                
        else:
            for k,v in cfg.items():
                for kk,vv in v.items():
                    scipyen_config[k][kk].set(vv)
                    
        #### BEGIN debug - comment out when done
#         if self.__class__.__name__ == "EventAnalysis":
#             print(f"\twriting configuration file")
        #### END debug - comment out when done
            
        write_config(scipyen_config)
        
        #### BEGIN debug - comment out when done
        # if self.__class__.__name__ == "EventAnalysis":
        #     print(f"DONE ScipyenConfigurable<{self.__class__.__name__}>._observe_configurables_()\n\n")
        #### END debug - comment out when done
            
        
    def _make_confuse_config_data_(self, change, isTop=True, parent=None, tag=None):
        """Wraps change.new data to a structure storable with confuse library
        `change` is a dict sent via the traits notification mechanism
    
        Prepares data for the `write` side of the confuse framework
    
        WARNING: Curently the confuse library (via pyyaml) only supports plain
        Python (basic) data types: numeric scalars, strings and basic collections
        (tuple, list, dict)
    
        TODO/FIXME: 2022-11-01 13:33:44
        Fancy data types (like numpy array, quantities, etc) are NOT supported,
        although is MIGHT be possible to implement support for these using 
        Scipyen's iolib.jsonio
    
        
        """
        if isinstance(change.new, (collections.deque, tuple)):
            v = [v_ for v_ in change.new] if len(change.new) else []
            
        elif isinstance(change.new, type):
            v = []
        else:
            v = change.new
        
        if isTop:
            return Bunch({self.__class__.__name__:Bunch({change.name:v})})
        
        if parent is not None:
            if isinstance(tag, str) and len(tag.strip()):
                return dict({parent.__class__.__name__:Bunch({self.__class__.__name__:Bunch({tag:Bunch({change.name:v})})})})
                
            return dict({parent.__class__.__name__:Bunch({self.__class__.__name__:Bunch({change.name:v})})})
        
        return Bunch({self.__class__.__name__:Bunch({change.name:v})})
        
    def _get_config_view_(self, isTop=True, parent=None, tag=None):
        """
        If isTop, returns the confuse config section for the class of this instance:
                scipyen_config → this class name
        Else:
            If parent is not None:
                If tag is not None (or an empty str)
                    return the sub-subsection: scipyen_config → parent class name → this class name → tag
                Else
                    return the sub-subsection: scipyen_config → parent class name → this class name
        
            Else:
                return the same thing as if isTop were True ('cause there's no parent, let alone a tag)
                    
        """
        # if self.__class__.__name__ == "EventAnalysis":
        #     print(f"scipyen_config {id(scipyen_config)} {scipyen_config}")
            
        if isTop: 
            return scipyen_config[self.__class__.__name__]#.get()
            # return scipyen_config[self.__class__.__name__].get(None)
            
        if parent is not None:
            if isinstance(tag, str) and len(tag.strip()):
                return scipyen_config[parent.__class__.__name__][self.__class__.__name__][tag]#.get(None)
            
            return scipyen_config[parent.__class__.__name__][self.__class__.__name__]#.get(None)
        
        return scipyen_config[self.__class__.__name__]#.get(None) 
            
    @property
    def configTag(self) -> str:
        return self._tag
    
    @configTag.setter
    def configTag(self, val:str) -> None:
        if isinstance(val, (str, type(None))):
            self._tag = val
        else:
            warnings.warn(f"The attempt to set configTag to {val} failed")
        
    @property
    def configurables(self):
        """All configurables
        
        Collects all configurables for this ::class:: in a mapping.
        
        The mapping has two fields: 'qt' and 'conf' that describe what settings
        are to be saved to / loaded from the Scipyen.conf ('qt') or config.yaml 
        ('conf') files.
        
        Each field is a mapping of str keys (the name of the configurable as
        it would be stored in the config file) to a dict that identifies the
        getter, setter, configuration type, and a 'factory default' value.
        
        """
        return collect_configurables(self.__class__)
    
    @property
    def qtconfigurables(self):
        """QSettings configurables
        """
        return  self.configurables.get("qt", Bunch())
    
    @property
    def clsconfigurables(self):
        """Class configurables
        """
        return self.configurables.get("conf", Bunch())
    
    def loadWindowSettings(self):
        """Reads window and Qt GUI settings from the QSettings file
        """
        # print(f"ScipyenConfigurable<{self.__class__.__name__}>.loadWindowSettings")
        if isinstance(self, Figure): # this presupposes self is an instance that also inherits from matplotlib Figure
            if issubclass(self.canvas, (mpl.backend_bases.FigureCanvasBase, QtWidgets.QWidget)):
                loadWindowSettings(ScipyenConfigurable.qsettings, self.canvas, group_name = self.canvas.__class__.__name__, prefix="")
            return
        
        group_name, prefix = qSettingsGroupPfx(self)
        #print(f"self.loadWindowSettings {self.__class__.__name__}, group: {group_name}, prefix: {prefix} from {self.qsettings.fileName()}")
        loadWindowSettings(self.qsettings, self, group_name = group_name, prefix=prefix)
    
    def saveWindowSettings(self):
        """Writes windows and Qt GUI settins to the QSettings file
        """
        # print(f"ScipyenConfigurable<{self.__class__.__name__}>.saveWindowSettings")
        if isinstance(self, Figure):# this presupposes self is an instance that also inherits from matplotlib Figure
            if issubclass(self.canvas, (mpl.backend_bases.FigureCanvasBase, win, QtWidgets.QWidget)):
                saveWindowSettings(ScipyenConfigurable.qsettings, self.canvas, group_name = self.canvas.__class__.__name__, prefix="")
            return
        
        group_name, prefix = qSettingsGroupPfx(self)
        saveWindowSettings(self.qsettings, self, group_name=group_name, prefix=prefix)
    
    def _assign_trait_from_config_(self, settername, val):
        #### BEGIN debug - comment out when done
        # if self.__class__.__name__ == "EventAnalysis":
        #     print(f"ScipyenConfigurable<{self.__class__.__name__}>._assign_trait_from_config_ settername {settername}, val {val}")
        #### END debug - comment out when done
        setter = inspect.getattr_static(self, settername, None)
        
        if isinstance(val, str):
            # NOTE: 2022-11-27 12:46:17 POSSIBLE NEW BUG
            # The json library will help identify string representation of 
            # sequences but fail in any other case. 
            # HOWEVER:
            # What if we WANT to store a str representation of a sequence, 
            # and retrieve it as such, instead of retrieving the original
            # sequence represented here?
            #
            # The answer to that is to enclose the whole string in double or
            # single quotes at writing time; then, here, let the caller deal
            # with the result...
            try:
                val = json.loads(val)
            except:
                val = strutils.str2sequence(val)
        
        # FIXME BUG 2022-11-27 12:33:35
        # this messes up string that may contain parantheses inside (such as a
        # file filter specification !!!!)
        # if isinstance(val, str) and any(c in val for c in ("()")):
        #     # this is a string rep of a basic Pyton sequence such as a tuple or list
        #     val = tuple(v_.strip() for v_ in val.strip("()").split(","))
        
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            with self.configurable_traits.observer.hold_trait_notifications():
                #print("\t holds notifications")
                if isinstance(setter, property):
                    setattr(self, settername, val)
                    
                elif setter is not None:
                    setter = getattr(self, settername)
                    setter(val)
                    
        else:
            if isinstance(setter, property):
                setattr(self, settername, val)
                
            elif setter is not None:
                setter = getattr(self, settername)
                setter(val)
    
    def loadSettings(self):
        cfg = self.clsconfigurables
            
        # NOTE 2021-09-06 17:37:14
        # keep Qt settings segregated
        if len(cfg):
            isTop = hasattr(self, "isTopLevel") and self.isTopLevel
            parent = self._get_parent_()
            tag = self.configTag if isinstance(self.configTag, str) and len(self.configTag.strip()) else None
            user_conf = self._get_config_view_(isTop, parent, tag)
            
            # #### BEGIN debug - comment out when done
            # if self.__class__.__name__ == "TwoPathwaysOnlineLTP":
            #     print(f"ScipyenConfigurable<{self.__class__.__name__}>.loadSettings() to load user_conf:")
            #     pprint(user_conf)
            #### END debug - comment out when done

            if isinstance(user_conf, confuse.Subview):
                for k, v in user_conf.items():
                    if k in cfg:
                        try:
                            self.set_configurable_attribute(k, v.get(), cfg)
                        except Exception as e:
                            traceback.print_exc()
                            continue
                    
        if issubclass(self.__class__, QtWidgets.QWidget):
            self.loadWindowSettings() 
            
    def saveSettings(self):
        """ Must be called with super() if reimplemented in subclasses
        
        NOTE: 2022-11-01 22:13:57 Does not support mapping collections as
        configuration settings. In other words, an individual setting cannot be
        an object of type that inherits from dict.
        
        On the other hand, individual settings can be organized hierarchically
        by collecting them in a dict (or dict-like) object.
        """
        # print(f"ScipyenConfigurable<{self.__class__.__name__}.saveSettings()")
        # NOTE: 2021-05-04 21:53:04
        # This saveSettings has access to all the subclass attributes (with the
        # subclass being  fully initialized by the time this is called).
        #print("ScipyenConfigurable <%s>.saveSettings" % self.__class__.__name__)
        cfg = self.clsconfigurables
        
        # NOTE: 2021-09-13 23:19:30
        # usr_conf is set up automatically by the trait_notifier!
        # here we only do the final save when the configurables goes out of scope
        # or (for windows) when they are closed (i.e. called from their closeEvent)
        
        if len(cfg):
            isTop = hasattr(self, "isTopLevel") and self.isTopLevel
                
            parent = self._get_parent_()
            tag = self.configTag if hasattr(self, "configTag") and isinstance(self.configTag, str) and len(self.configTag.strip()) else None
            user_conf = self._get_config_view_(isTop, parent, tag)
            
            #### BEGIN debug - comment out when done
            # if self.__class__.__name__ == "EventAnalysis":
            #     print(f"ScipyenConfigurable<{self.__class__.__name__}>.saveSettings() to save user_conf:")
            #     pprint(user_conf)
            # if self.__class__.__name__ == "TwoPathwaysOnlineLTP":
            #     print(f"ScipyenConfigurable<{self.__class__.__name__}>.saveSettings() to save user_conf:")
            #     pprint(user_conf)
            #### END debug - comment out when done
            
            changed = False
            
            if isinstance(user_conf, dict):
                for k, v in user_conf.items():
                    try:
                        val = self.get_configurable_attribute(k, cfg)
                    except Exception as e:
                        traceback.print_exc()
                        continue

                    #### BEGIN debug - comment out when done
                    # if self.__class__.__name__ == "Events_Analysis":
                        # print(f"ScipyenConfigurable<{self.__class__.__name__}>.saveSettings(), getter={gettername} → {k}={val} ({type(val).__name__}), v {v} ({type(v).__name__})")
                    #### END debug - comment out when done
                    
                    if val != v:
                        # NOTE: 2022-11-01 21:54:34
                        # must convert value to something digestible by 
                        # confuse.yaml framework
                        
                        # val_ = data2confuse(x)
                        
                        if hasattr(user_conf[k], "set"):
                            user_conf[k].set(val)
                        else:
                            user_conf[k] = val

                        changed = True
                        
            if changed:
                #### BEGIN debug - comment out when done
                # if self.__class__.__name__ == "EventAnalysis":
                #     print(f"\twriting configuration file")
                #### END debug - comment out when done
                write_config(scipyen_config)
                #### BEGIN debug - comment out when done
                # if self.__class__.__name__ == "EventAnalysis":
                #     print(f"DONE ScipyenConfigurable<{self.__class__.__name__}>.saveSettings()\n\n")
                #### END debug - comment out when done
                
        if issubclass(self.__class__, (QtWidgets.QWidget, Figure)):
            self.saveWindowSettings()
            
    def get_configurable_attribute(self, name, config_dict):
        """Helper to get the actual attribute value correspondong to a config entry.
        Called in order to WRITE a the value of a configurable attribute to the 
        config file.
        """
        getset = config_dict.get(name, {})
        gettername = getset.get("getter", None)
        if not isinstance(gettername, str) or len(gettername.strip()) == 0:
            raise RuntimeError(f"{name} is not a configurable")
        
        getter = inspect.getattr_static(self, gettername, None)
        
        if isinstance(getter, property):
            return getattr(self, gettername)
            
        elif getter is not None:
            getter = getattr(self, gettername)
            return getter()
            
        else:
            raise RuntimeError(f"{gettername} is not a `get` property")
        
    def set_configurable_attribute(self, name, val, config_dict):
        """Helper function to assign the value of an attribute to a configurable attribute
        Called in order to READ a config value from the config file and assign it to
        the coprrespondng attribute via its 'setter' method
        """
        getset = config_dict.get(name, {})
        settername = getset.get("setter", None)
        if not isinstance(settername, str) or len(settername.strip()) == 0:
            raise RuntimeError(f"{name} is not a configurable")
        
        self._assign_trait_from_config_(settername, val)
        
        
        
        
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
        
def get_config_file(configuration:confuse.Configuration=scipyen_config, default:bool=False):
    """Returns the fully qualified path to the file holding non-Qt configuration.
        
    Named Parameters
    ================
    • configuration - optional;
        By default, this is `scipyen_config`, the default confuse.LazyConfig object 
        currently active during a Scipyen session.        
        
        However, a different instance of confuse.Configuration obejct can be 
        specified here (this can also be a LazyConfig object)
        
    • default: optional default if False
        When True, the function returns the path to file holding the default
        configuration data (typically, in the directory where Scipyen is installed).
        
        When False, the function returns the path to the file holding the user
        configuration, the contents of which may vary from session to session
        (and reflect the state of the last running Scipyen session)
        
        
    """
    if not configuration._materialized:
        configuration.read()
        
    if default:
        defsrc = [s for s in configuration.sources if s.default]
        if len(defsrc):
            return defsrc[0].filename
        
    return configuration.user_config_path()
    
def get_config_dir(configuration:confuse.Configuration=scipyen_config):
    if not configuration._materialized:
        configuration.read()
            
    return configuration.config_dir()

def get_QtSettings_file():
    return ScipyenConfigurable.qsettings.fileName()

@safeWrapper
def write_config(config:typing.Optional[confuse.Configuration]=scipyen_config, filename:typing.Optional[str]=None, full:bool=True, redact:bool=False, as_default:bool=False, default_only:bool=False):
    """Saves Scipyen non-gui configuration options to an yaml file.
    Settings are saved implicitly to the config.yaml file located in the 
    application configuration directory and stored in the 'filename' attribute
    of the first configuration source.
    
    What can be dumped (below, 'default' refers to the 'package default' settings
    stored in config_default.yaml located in scipyen directory):
    
    1) all settings even if they are no different from the defaults - useful to
    genereate/update the default settings when 'as_default' is True
    
    2) only settings that are different from the defaults 
    WARNING specifying 'as_default' True will overwrite the default settings.
    
    3) of either (1) or (2) the redacted settings may be left out
    
    Named parameters:
    ================
    config: a confuse.ConfigView object, or None (default)
        
        When None, this defaults to the 'scipyen_settings' in the user workspace.
        
        Otherwise, this can be a confuse.Configuration (or confuse.LazyConfig) 
        object, or a confuse.SubView (the latter is useful to dump a subset of 
        configuration settings to a local file).
    
    filename: str or None (default).
        Specifies the file where the configuration will be dumped. An '.yaml'
        extension will be added to the file if not present.
        
        When None (the default) the configuration settings are saved to 
        the user's 'config.yaml' file, or to the config_default.yaml file located
        in scipyen directory if 'as_default' is True
        
    full: bool
        When True (default) dump as in case (1) above
    
    redact: bool
        When False (default) the redacted settings are left out 
        (i.e., not dumped)
        
    as_default:bool. 
        When False (default) the settings will be dumped to the file specified 
        by 'filename', or to the 'config_default.yaml' file in the application
        configuration directory
        
    default_only:bool, default is False
        When True, only the package default values will be saved to the 
        config_default.yaml. The 'full' and 'as_default' parameters are ignored.
    
    """
    if config is None:
        user_ns = user_workspace()
        config = user_ns["scipyen_settings"]
        
    if not isinstance(config, confuse.ConfigView):
        return False
    
    defsrc = [s for s in config.sources if s.default] # default source
    src = [s for s in config.sources if not s.default] # non-default sources
    out = ""
    
    if default_only:
        as_default = True # force saving to the package default
    
    if filename is None or (isinstance(filename, str) and len(filename.strip()) == 0):
        if as_default:
            filename = defsrc[-1].filename
        else:
            filename = src[-1].filename
    else:
        (fn, ext) = os.path.splitext(filename)
        if ext != ".yaml":
            filename = ".".join([fn, "yaml"])
            
    #print(f"scipyen_config.write_config: filename {filename}")
            
    if isinstance(config, confuse.Configuration): # Configuration and LazyConfig
        out = config.dump(full=full, redact=redact)
        
    else:
        if full:
            out = config.flatten(redact=redact)
        else: # exclude defaults
            temp_root = confuse.RootView(src)
            temp_root.redactions = config.redactions
            out = temp_root.flatten(redact=redact)

    #NOTE: 2021-01-13 17:23:36
    # allow the use of empty output - effectively this wipes out the yaml file
    # NOTE: 2021-01-13 17:25:25
    # because of this, we allow here a GUI dialog (QMessageBox) warning the user
    # to the possiblity of wiping out the config_default.yaml file!
    if len(out) == 0:
        txt = "The configuration file %s is about to be cleared. Do you wish to continue?" % filename
        ret = QtWidgets.QMessageBox.warning(None,"Scipyen configuration",txt)
        
        if ret != QtWidgets.QMessageBox.OK:
            return False
        
    with open(filename, "wt") as yamlfile:
        yamlfile.write(out)
        
    return True
    
def saveWindowSettings(qsettings:QtCore.QSettings, win:typing.Union[QtWidgets.QMainWindow, Figure], group_name:typing.Optional[str]=None, prefix:typing.Optional[str]=None):
    """Saves window settings to the Scipyen's Qt configuration file.
    
    On recent Linux distributions this is $HOME/.config/Scipyen/Scipyen.conf 
    
    The following mandatory settings will be saved:
    
    * For all QWidget-derived objects:
        * WindowSize
        * WindowPosition
        * WindowGeometry
        
    * Only for QMainWindow-derived objects, or objects that have a 'saveState()'
        method returning a QByteArray:
        * WindowState 
        
    Additional (custom) entries and values can be saved when passed as a mapping.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically, or it can be specified.
    
    Because the conf file only supports one level of group nesting (i.e. no 
    "sub-groups") an extra-nesting level is emulated by prepending a custom
    prefix to the setting's name.
    
    Parameters:
    ==========
    
    qsettings: QtCore.QSettings. Typically, Scipyen's global QSettings.
    
    win: QMainWindow or matplotlib Figure. The window for which the settings are
        saved.
    
    group_name:str, optional, default is None. The qsettings group name under 
        which the settings will be saved.
        
        When specified, this will reimplement the automatically determined group 
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
        
    **kwargs: A mapping of key(str) : value(typing.Any) for additional entries
        beyond the mandatory ones.
    
    Returns:
    ========
    
    A tuple: (group_name, prefix) 
        group_name is the qsettings group name under which the win's settings 
            were saved
            
        prefix is th prefix prepended to each setting name
        
        These are useful to append settings later
        
        
    NOTE: Delegates to core.scipyen_config.syncQtSettings
    
    """
    # print("saveWindowSettings %s" % win.__class__.__name__)
    return syncQtSettings(qsettings, win, group_name, prefix, True)
    
def loadWindowSettings(qsettings:QtCore.QSettings,
                       win:typing.Union[QtWidgets.QMainWindow, Figure],
                       group_name:typing.Optional[str]=None,
                       prefix:typing.Optional[str]=None):
    """Loads window settings from the Scipyen's Qt configuration file.
    
    On recent Linux distributions this is $HOME/.config/Scipyen/Scipyen.conf 
    
    The following mandatory settings will be loaded:
    
    * For all QWidget-derived objects:
        * WindowSize
        * WindowPosition
        * WindowGeometry
        
    * Only for QMainWindow-derived objects, or objects that have a 'saveState()'
        method returning a QByteArray:
        * WindowState 
        
    Additional (custom) entries and values can be loaded when passed as a mapping.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically, or it can be specified.
    
    Because the conf file only supports one level of group nesting (i.e. no 
    "sub-groups") an extra-nesting level, when needed, is emulated by prepending
    a custom prefix to the setting's name.
    
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
    
    NOTE: Delegates to core.scipyen_config.syncQtSettings
    
    """
    return syncQtSettings(qsettings, win, group_name, prefix, False)


def data2confuse(x):
    """Filter to convert some special data to str for yaml representation.
    Uses iolib.jonsio to enable storage of more specialized /complex data types
    with the confuse framework.
    A bit expensive, though... Therefore not sure I will use it...
    """
    return object2JSON(x)

# Some yaml representers and constructors for special object types

