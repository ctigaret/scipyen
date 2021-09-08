#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" Scipyen configuration module

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
import inspect, typing, types
from copy import (copy, deepcopy,)
import confuse
from types import new_class
from functools import (partial, wraps,)
from pprint import pprint

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
#from iolib.pictio import save_settings as write_config


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

scipyen_config = confuse.LazyConfig("Scipyen", "scipyen_defaults")

if not scipyen_config._materialized:# make sure this is done only once
    scipyen_config.read() 
    
scipyen_user_config_source = [s for s in scipyen_config.sources if not s.default][0]

def _cfg_exec_body_(ns, supplement={}):
    print("_cfg_exec_body_ supplement")
    ns.update(supplement)
    
    if not isinstance(ns.get("_scipyen_settings_", None), confuse.Configuration):
        ns["_scipyen_settings_"] = scipyen_config
        
    if not isinstance(ns.get("_user_settings_src_", None), confuse.ConfigSource):
        ns["_user_settings_src_"] = scipyen_user_config_source
        
    if not isinstance(ns.get("qsettings", None), QtCore.QSettings):
        ns["qsettings"] = QtCore.QSettings("Scipyen", "Scipyen") # user scope, application-level
        
    if not isinstance(ns.get("configurables", None), property):
        ns["configurables"] = property(fget = _configurables, doc = "All configurables")
        
    if not isinstance(ns.get("qtconfigurables", None), property):
        ns["qtconfigurables"] = property(fget = _qtconfigurables, doc = "QSettings configurables")
        
    if not isinstance(ns.get("clsconfigurables", None), property):
        ns["clsconfigurables"] = property(fget = _clsconfigurables, doc = "Class configurables")
        
    if not inspect.isfunction(ns.get("_observe_configurables_", None)):
        ns["_observe_configurables_"] = _observe_configurables_
        
    if not isinstance (ns.get("configurable_traits", None), DataBag):
        ns["configurable_traits"] = DataBag()
        
    ns["configurable_traits"].observe(ns["_observe_configurables_"])
    
    if not inspect.isfunction(ns.get("loadSettings", None)):
        ns["loadSettings"] = _loadSettings_
                
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


    
def makeConfigurable(configurables:typing.Optional[Bunch]=None,
                     extras:typing.Optional[Bunch]=None):
    """:Class: decorator for configurables management.
    
    Auguments the decorated ::class:: with functionality for loading/saving
    configurable parameters (options) to/from configuration files.
    
    Parameters:
    ===========
    configurables: traitlets.Bunch. Optional (default is None)

        When given, it is expected ot have the following structure:
        
        {Name: Bunch({'type':           'qt' or any str - case insensitive,
                      'getter':         getter method or property,
                      'setter':         setter method_or property,
                      'default':        default value or None,
                      'trait_notifier': DataBag instance, bool, or None,
                     },
                    )}
                          
        where Name is the name of the configuration 'key'.
    
        In the inner Bunch, only the first two fields (or 'keys') are mandatory 
        and represent the method or property, respectively, for retrieving and
        assigning the value of the instance attribute associated with 
        SettingsName (see NOTE, below)
        
    extras: traitlets.Bunch Optional (default is None)
        A mapping that overrides instance attributes, methods and properties in
        the generated new type.
        
    Returns:
    =======
    A function which takes the decorated :class: as sole parameter and generates
    a new ('decorated') :class: with enhanced functionality.
        
    By default (when 'configurables' is None or an empty mapping) the function
    uses the :class: attributes (methods, properties) decorated with 
    'markConfigurable' to determine what is configurable in the decorated 
    :class:.
    
    Briefly, 'markConfigurable' decorates selected methods that work as a 
    getter/setter pair, or properties defined in the ::class::, to be used in
    saving/loading settings to/from configuration files.
    
    
    NOTE: 
        The 'getter' is a method or property that retrieves the value of an 
        attribute in order for it to be stored (saved) in a configuration
        file, under the name given by the 'SettingsName' key.
            
        The 'setter' if a method or property that assigns the value loaded from
        a configuration file to an attribute of an instance of the :class:
    
        Scipyen manages two kinds of persistent configurations:
        
        1) Qt GUI related settings.
            These are stored in a Scipyen.conf file in Scipyen's configuration 
            directory, using QtCore.QSettings framework and are appropriate for 
            :classes: that inherit from Qt :clases: such as QtWidgets.QWidget 
            and QtWidgets.QMainWindow.
            
            This allows for persistent storage of Qt objects that can be
            serialized (such as QSize, QPoint, QRect, QColor, QByteArray, etc.), 
            transparently via QSettings.
            
            
        2) Settings not related to GUI.
            These are persistent configuration options for various non-GUI
            components of Scipyen (e.g., ScanData options, TriggerProtocol
            options, etc) such as the relative/absolute numeric tolerances used
            in numerical algorithms and so on.
        
            The configuration is stored in YAML format in a 'config.yaml' file
            in Scipyen's configuration directory, which supports deeply nested
            dict-like structures.
        
    
            The values (objects) returned by the getter method and expected by
            the setter SHOULD be built-in Python types EXCLUDING:
            - types inheriting from Qt types
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
        
        CAUTION: No type checking is performed.
        
    Usage:
    ======
    1. As a :class: decorator
    -------------------------
    
    Do NOT confuse this notion with that of a 'decorator :class:' - they are
    entirely different species!
    
    * a :class: decorator is used to decorate a :class:
    
    * a decorator :class: is a :class: that can be used as a decorator (usually
        of a function or method)
    
    To use as :class: decorator, decorate the ::class:: definition with 
    @makeConfigurable like so:
    
    @makeConfigurable()
    class MyClass():
        pass
    
    DO NOTE the call syntax in the above: DO NOT FORGET THE PARENTHESES (see the
    Technical note below for an explanation).
    
    Inside the :class: definition body, decorate the relevant instance methods 
    and properties with the 'markConfigurable' decorator defined in this module.
    
    For read-write properties, it is only relevant to decorate the *.setter 
    (where * is the property name), e.g.:
    
    @property
    def some_property(self): # defines the 'getter'
        pass
        
    # decorates the read/write property named 'some_property'
    @markConfigurable("SomeProperty") 
    @some_property.setter
    def some_property(self, val): # defines  the 'setter'
        pass
    
    For callable attributes (i.e., methods) make sure you:
    
    * decorate BOTH the getter and setter methods (they typically are named 
        differently, e.g. 'size' / 'resize', 'pos' / 'move') 
        
    * when decorating, assign values to the 'confname', 'conftype' and 'setter'
        parameters of 'markConfigurable' such that:
            'confname' and 'conftype' are the same for both the getter and setter
            'setter' is True for the setter method and False for the getter
                    method
    
    
    See documentation for 'markConfigurable' for details.
    
    2. As a dynamic type creator
    ----------------------------
    Useful with :classes: imported from 3rd party libraries, where using the 
    'markConfigurable' decorator would require defining a derived :class: to 
    override the relevant methods and properties simply in order to decorate 
    them with 'markConfigurable'.
    
    This is notably useful for PyQt5 :classes:.
    
    Here, the 'configurables' and 'extras' parameters SHOULD be specified, as 
    shown in the following examples:
    
    a. - likely not useful, unless 'makeConfigurable' finds methods or 
        properties with configurable_getter and configurable_setter attributes
        inside the source :class: (which in this example is guaranteed to fail, 
        because the source :class: is QMainWindow)
        
    MyClass = makeConfigurable()(QtWidgets.QMainWindow)
    
    b. - unlikely to be useful because, even if configurables are set in the 
        new type 'MyClass', the instances of MyClass doesn't know what to do
        with them
        
    configs = Bunch({"WindowSize": Bunch({"type":"qt","getter":"size", "setter":"resize"}),
                                         "WindowPosition": Bunch({"type":"qt", "getter":"pos","setter":"move"}),
                                         "WindowGeometry": Bunch({"type":"qt", "getter":"geometry", "setter":"setGeometry"}),
                                         "WindowState": Bunch({"type":"qt","getter":"saveState", "setter":"restoreState"}),
                                         })
                                         
    MyClass = makeConfigurable(configurables = configs)(QtWidgets.QMainWindow)
    
    Now, MyClass has all the functionality of QMainWindow and MyClass instance
    correctly reports qtconfigurables:
    
    window = MyClass()
    
    pprint(window.qtconfigurables)
    
    {'WindowGeometry': {'default': None,
                        'getter': 'geometry',
                        'setter': 'setGeometry',
                        'trait_notifier': None},
    'WindowPosition': {'default': None,
                        'getter': 'pos',
                        'setter': 'move',
                        'trait_notifier': None},
    'WindowSize': {'default': None,
                    'getter': 'size',
                    'setter': 'resize',
                    'trait_notifier': None},
    'WindowState': {'default': None,
                    'getter': 'saveState',
                    'setter': 'restoreState',
                    'trait_notifier': None}}
                    
    However, these configurables are not loaded, nor saved, unless makeConfigurable
    is used on a derived class that introduces this functionality
    
    c. useful: makeConfigurable now also adds functionality to load/save the
    configurables - TODO/FIXME
    
    NOTE: configs are defined in example (b) above
    
    def _load_settings_(instance):
        ... code to load settings...
        
    def _save_settings_(instance):
        ... code to save settings...
        
    def _new_init_(instance, *args, **kwargs):
        instance.__cls__.__init__(instance, *args, **kwargs)
        instance._load_settings_()
        
        
    def _new_close_event_(instance, evt):
        instance._save_settings_()
        instance.closeEvent(evt)
        
    extras = Bunch({"__ini__":_new_init_, "closeEvent": _new_close_event_})
    
    
    MyClass = makeConfigurable(configurables = configs, extras=extras)(QtWidgets.QMainWindow)
    
    
    Technical notes:
    ===============
    
    The call syntax (see Usage 1 above) is necessary because this decorator
    actually returns a function and not a class (as a 'regular' :class: decorator
    is expected to do).
    
    In turn, the returned function takes the to-be-decorated :class: as a sole 
    parameter and returns a NEW generated type which is the equivalent of the
    'decorated' version of :class:.
    
    This strategy allows passing parameters to makeConfigurable, such as the
    'configurables' dictionary shown above.
    
    """
    # in the ::class:: definition, a property setter is always defined after a
    # property getter (otherwise the source code won't compile)
    # however, getter and setter methods MAY be defined in ANY order so as we
    # loop through them a setting may first appear as getter-only, or as 
    # setter-only
    
    #print("makeConfigurable cls %s" % cls.__name__)
    
    def _klass_wrapper_(cls):
        #print("makeConfigurable._klass_wrapper_(%s)" % cls.__name__)
        #print("\tconfigurables", configurables)
        def _observe_configurables_(instance, change):
            cfg = Bunch({instance.__class__.__name__: Bunch({change.name:change.new})})
            pprint(cfg)
            
        def _configurables(instance):
            return collect_configurables(instance.__class__)
                        
        def _qtconfigurables(instance):
            return collect_configurables(instance.__class__).get("qt", Bunch())
        
        def _clsconfigurables(instance):
            return collect_configurables(instance.__class__).get("conf", Bunch())
            
        def _loadSettings_(instance):
            cfg = collect_configurables(instance.__class__)
            # NOTE: These updates are necessary; see e.g., WorkspaceGuiMixin
            cfcfg = cfg.get("conf", Bunch())
            qtcfg = cfg.get("qt", Bunch())
            
            if len(cfcfg):
                user_conf = scipyen_settings[instance.__class__.__name__].get(None)
                
                if isinstance(user_conf, dict):
                    for k, v in user_conf.items():
                        getset = cfcfg.get(k, {})
                        settername = getset.get("setter", None)
                        
                        if not isinstance(settername, str) or len(settername.strip())==0:
                            continue
                        
                        trait_notifier = getset.get("trait_notifier", None)
                        
                        if not isinstance(trait_notifier, (bool, DataBag)):
                            continue
                        
                        if trait_notifier is True and isinstance(getattr(instance, "configurable_traits", None), DataBag):
                            trait_notifier = instance.configurable_traits
                            
                        else:
                            continue
                            
                        with trait_notifier.hold_trait_notifications():
                            default = getset.get("default", None)
                            
                            setter = inspect.getattr_static(instance, settername, None)

                            if isinstance(setter, property):
                                setattr(instance, settername, v)
                                
                            elif setter is not None:
                                setter = getattr(instance, settername)
                                setter(val)
            if len(qtcfg):
                syncQtSettings(cls.qsettings, instance, False)
            
        def _exec_body_(ns, supplement={}):
            #print("_exec_body_ supplement", supplement )
            ns.update(supplement)
            
            if not isinstance(ns.get("_scipyen_settings_", None), confuse.Configuration):
                ns["_scipyen_settings_"] = scipyen_config
                
            if not isinstance(ns.get("_user_settings_src_", None), confuse.ConfigSource):
                ns["_user_settings_src_"] = scipyen_user_config_source
                
            if not isinstance(ns.get("qsettings", None), QtCore.QSettings):
                ns["qsettings"] = QtCore.QSettings("Scipyen", "Scipyen") # user scope, application-level
                
            if not isinstance(ns.get("configurables", None), property):
                ns["configurables"] = property(fget = _configurables, doc = "All configurables")
                
            if not isinstance(ns.get("qtconfigurables", None), property):
                ns["qtconfigurables"] = property(fget = _qtconfigurables, doc = "QSettings configurables")
                
            if not isinstance(ns.get("clsconfigurables", None), property):
                ns["clsconfigurables"] = property(fget = _clsconfigurables, doc = "Class configurables")
                
            if not inspect.isfunction(ns.get("_observe_configurables_", None)):
                ns["_observe_configurables_"] = _observe_configurables_
                
            if not isinstance (ns.get("configurable_traits", None), DataBag):
                ns["configurable_traits"] = DataBag()
                
            ns["configurable_traits"].observe(ns["_observe_configurables_"])
            
            if not inspect.isfunction(ns.get("loadSettings", None)):
                ns["loadSettings"] = _loadSettings_
                
            #print("_exec_body_ ns", ns)
                
        new_configurables = dict()
        
        if isinstance(extras, dict):
            new_configurables.update(extras)
        
        if isinstance(configurables, dict) and len(configurables):
            for confname, confdict in configurables.items():
                if all((s in confdict for s in ("type", "getter", "setter"))):
                    getname = confdict["getter"]
                    setname = confdict["setter"]
                    conftype = confdict["type"]
                    
                    default = confdict.get("default", None)
                    trait_notifier = confdict.get("trait_notifier", None)
                    
                    #print("\t\tgetname: %s, setname: %s, conftype: %s, default: %s, trait_notifier: %s" % (getname, setname, conftype, default, trait_notifier))
                    
                    if getname == setname:
                        # this SHOULD be a property with getter and setter
                        prop = getattr(cls, getname, None)
                        
                        if isinstance(prop, property):
                            new_configurables[getname] = markConfigurable(confname,
                                                                        conftype,
                                                                        True,
                                                                        default=default,
                                                                        trait_notifier=trait_notifier)(prop)
                            
                    else:
                        # NOTE: 2021-09-08 13:13:13
                        # when this decorator is applied to a mixin like ScipyenConfigurable2
                        # getname and setname may not be available inside the mixin,
                        # although they may be available inside the other bases
                        getterfunc = getattr(cls, getname, None)
                        setterfunc = getattr(cls, setname, None)
                        #print("\t\tin %s" % cls.__name__)
                        #print("\t\tgetterfunc: %s (%s):" % (getterfunc, getattr(getterfunc, "__qualname__", None)))
                        #print("\t\tsetterfunc: %s (%s):" % (setterfunc, getattr(setterfunc, "__qualname__", None)))
                        #print()
                        if all((inspect.isfunction(f) or inspect.isbuiltin(f) for f in (getterfunc, setterfunc))):
                            
                            new_configurables[getname] = markConfigurable(confname,
                                                                        conftype,
                                                                        False,
                                                                        default=default,
                                                                        trait_notifier=trait_notifier)(getterfunc)
                            
                            new_configurables[setname] = markConfigurable(confname,
                                                                        conftype,
                                                                        True,
                                                                        default=default,
                                                                        trait_notifier=trait_notifier)(setterfunc)
                            
        #print("\tnew_configurables", new_configurables)
        # NOTE: 2021-09-08 13:34:23 WRONG APPROACH; for Qt :classes: the 
        # sip.methodwrapper types like 'show()', 'setVisible()', 'closeEvent', 
        # etc don't get called
        # THEREFORE, THE CORRECT WAY is to create a new type by expanding
        # the original :class: _dict__ (see NOTE: 2021-09-08 13:37:22 below )
        # exec body populates the namespace of the instance
        #exec_body = partial(_exec_body_, supplement = new_configurables)
        #new_cls = new_class(cls.__name__, bases = cls.__bases__, exec_body = exec_body)
        
        # NOTE: 2021-09-08 13:37:22 THIS WORKS!
        original = dict(((k,v) for k,v in cls.__dict__.items()))
        
        _exec_body_(original, supplement = new_configurables)
        
        new_cls = type(cls.__name__, cls.__bases__, original)
        
        return new_cls
    
    return _klass_wrapper_
    
def markConfigurable(confname:str, conftype:str="", 
                     setter:bool=True, 
                     default:typing.Optional[typing.Any]=None,
                     trait_notifier:typing.Optional[typing.Union[bool, DataBag]] = None):
    """Decorator for instance methods & properties.
    
    Properties and methods decorates with this will be collected by the ::class::
    decorator makeConfigurable to enable saving/loading used settings for that 
    ::class::
    
    Can also be called directly:
    
    1) pass an instance method (a function):
    
    func  = markConfigurable(cofnname, conftype, setter, 
                             default=default_val,
                             trait_notifier=<some_databag OR bool>)(obj.method)
                             
    Where func is a bound method, the new (decorated) version of obj.method.
    
    See documentation of makeConfigurable for details.
    
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
        
        
    Returns:
    =======
    f: the decorated method or property object, augmented as described below.
        
    What it does:
    ============
    
    1) When f is a property:
    
    * if f.fget is a function, adds to it a 'configurable_getter' attribute:
            
    f.fget.configurable_getter = {'type': conftype, 'name': confname, 'getter':f.fget.__name__}
            
    * if f.fset is a function, adds to it a 'configurable_setter' attribute:
        
    f.fset.configurable_setter = {'type':conftype, 'name': confname, 'setter': f.fset.__name__, 'default':None}
    
    2) When f is a method function:
    
    * if setter is False, adds to it a 'configurable_getter' attribute:
        
    f.configurable_getter = {'type': conftype, 'name': confname, 'getter':f.__name__}
    
    * if setter is True, adds to it a 'configurable_setter' attribute:
    
    f.configurable_setter = {'type': conftype, 'name': confname, 'setter':f.__name__, 'default'None}
    
    In the above the 'default' field is mapped to the value of the 'default'
    parameter of this decorator function.
    
    CAUTION: the 'default' values are references to python objects; make sure
    they still exist; it is better to leave this parameter to its default (None)
    
    
    These attributes will be parsed by the ::class:: decorator makeConfigurable
    to construct the ::class:: attributes '_qtcfg' and '_cfg' according to the
    value of 'conftype'
    
    """
    if not isinstance(confname, str) or len(confname.strip()) == 0:
        return f # fail silently
    
    if not isinstance(conftype, str):
        return f # fail silently
    
    conftype = conftype.lower()
    
    def wrapper(f):
        # NOTE 2021-09-06 10:42:49
        # applies only to read-write properties
        # hence only decorate xxx.setter if defined
        if isinstance(f, property):
            if all((inspect.isfunction(func) for func in (f.fget, f.fset))):
                setattr(f.fget, "configurable_getter", Bunch({"type": conftype, "name": confname, "getter":f.fget.__name__, "default": default}))
                setattr(f.fset, "configurable_setter", Bunch({"type": conftype, "name": confname, "setter":f.fset.__name__, "default": default}))
                
                if conftype != "qt" and isinstance(trait_notifier, (bool, DataBag)):
                    # NOTE: 2021-09-08 09:14:16
                    # for non-qt configurable properties ONLY:
                    # if trait_notifier is defined, then replace f.fset with a 
                    # new function that also updates the trait_notifier
                    # 'trait_notifier' is supposed to be a DataBag with a
                    # registered observer handler, OR a bool which when True, 
                    # expects the :class: owner of the property to provide such
                    # a DataBag via the attribute 'configurable_traits'
                    
                    if isinstance(trait_notifier, bool) and trait_notifier is True:
                        trait_notifier = getattr(instance, "configurable_traits", None)
                        
                    if isinstance(trait_notifier, DataBag):
                        f.fset.configurable_setter["trait_notifier"] = trait_notifier
                        
                        def newfset(instance, *args, **kwargs):
                            """Calls the owner's property fset function & updates the trait notifier.
                            This only has effect when trait notifier is a DataBag
                            that is observing.
                            """
                            f.fset.__call__(instance, *args, **kwargs)
                            trait_notifier[confname] = args[0]
                            #if isinstance(trait_notifier, DataBag):
                                
                            #elif trait_notifier is True and isinstance(getattr(instance, "configurable_traits", None), DataBag):
                                #instance.configurable_traits[confname] = args[0]
                                
                        setattr(newfset, "configurable_setter", f.fset.configurable_setter)
                        
                        return property(fget = f.fget, fset = newfset, doc = f.__doc__)
                
        elif inspect.isfunction(f):
            if setter is True:
                setattr(f, "configurable_setter", Bunch({"type": conftype, "name": confname, "setter":f.__name__, "default": default}))
                
                if conftype != "qt" and isinstance(trait_notifier, (bool, DataBag)):
                    # see NOTE: 2021-09-08 09:14:16
                    if isinstance(trait_notifier, bool) and trait_notifier is True:
                        trait_notifier = getattr(instance, "configurable_traits", None)
                        
                    if isinstance(trait_notifier, DataBag):
                        f.configurable_setter["trait_notifier"] = trait_notifier
                        
                    #f.configurable_setter["trait_notifier"] = trait_notifier
                    def newf(instance, *args, **kwargs):
                        """Calls the owner's setter method & updates the trait notifier.
                        This only has effect when trait notifier is a DataBag
                        that is observing.
                        """
                        f(instance, *args, **kwargs)
                        trait_notifier[confname] = args[0]
                        #if isinstance(trait_notifier, DataBag):
                            #trait_notifier[confname] = args[0]
                            
                        #elif trait_notifier is True and isinstance(getattr(instance, "configurable_traits", None), DataBag):
                            #instance.configurable_traits[confname] = args[0]
                            
                    setattr(newf, "configurable_setter", f.configurable_setter)
                    
                    return newf
        
            else:
                setattr(f, "configurable_getter", Bunch({"type": conftype, "name": confname, "getter":f.__name__, "default": default}))
                
        elif inspect.isbuiltin(f): 
            # NOTE: 2021-09-08 10:10:07
            # builtin_function_or_method callable types (C function & method) 
            # cannot be augmented as above (they're read-only); therefore, we
            # we must wrap on the fly
            if setter is True:
                configurable_setter = Bunch({"type": conftype, "name": confname, "setter":f.__name__, "default": default})

                if conftype != "qt" and isinstance(trait_notifier, (bool, DataBag)):
                    # see NOTE: 2021-09-08 09:14:16
                    if isinstance(trait_notifier, bool) and trait_notifier is True:
                        trait_notifier = getattr(instance, "configurable_traits", None)
                        
                    if isinstance(trait_notifier, DataBag):
                        configurable_setter["trait_notifier"] = trait_notifier
                        
                def newf(instance, *args, **kwargs):
                    """Calls the owner's setter method & updates the trait notifier.
                    This only has effect when trait notifier is a DataBag
                    that is observing.
                    """
                    f(instance, *args, **kwargs)
                    if isinstance(trait_notifier, DataBag):
                        trait_notifier[confname] = args[0]
                        
                setattr(newf, "configurable_setter", configurable_setter)
                
                return newf
                
            else:
                configurable_getter = Bunch({"type": conftype, "name": confname, "getter":f.__name__, "default": default})
                
                def newf(instance, *args, **kwargs):
                    return f(instance, *args, **kwargs)
                
                setattr(newf, "configurable_getter", configurable_getter)
                
                return newf
        
        return f
    
    return wrapper
    
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

def syncQtSettings(qsettings:QSettings, 
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
        
    As defined in QorkspaceGuiMixin, '_qtcfg' is a nested Bunch:
    
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
        
    #print("syncQtSettings %s: win = %s, gname = %s, key_prefix = %s" % ("save" if save else "load", win, gname, key_prefix))
    #print("\n***\nsyncQtSettings %s: win = %s" % ("save" if save else "load", win, ))
    #print("\tgname = '%s', key_prefix = '%s'" % (gname, key_prefix))
    
    if hasattr(win, "qtconfigurables"):
        qtcfg = win.qtconfigurables
    else:
        qtcfg = Bunch()
        qtcfg.update(getattr(win, "_qtcfg", Bunch()))
        qtcfg.update(getattr(win, "_ownqtcfg", Bunch()))
    
    #print("\tqtcfg for %s: %s" % (win.__class__.__name__, qtcfg))

    for confname, getset in qtcfg.items():
        # NOTE: 2021-08-28 21:59:43
        # val, below, can be a function, or the value of a property
        # in the former case it SHOULD have a '__call__' attribute;
        # in the latter, it is whatever the property.fget returns (which may still be
        # a function or method, with a '__call__' attribute!)
        #print("\tconfname = %s" % confname)
        gettername = getset.get("getter", None)
        #print("\t\tgettername = %s" % gettername)

        if not isinstance(gettername, str) or len(gettername.strip()) == 0:
            continue
        
        getter = inspect.getattr_static(win, gettername, None)
        
        if isinstance(getter, property):
            val = getattr(win, gettername)
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
            
            if isinstance(setter, property):
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
    #cls = instance.__class__ # this is normally the derived type
    
    ret = Bunch({"qt": Bunch(), "conf": Bunch()})
    
    for name, fn in inspect.getmembers(cls):
        getterdict = Bunch()
        setterdict = Bunch()
        confdict = Bunch()
        if isinstance(fn, property):
            if inspect.isfunction(fn.fget) and hasattr(fn.fget, "configurable_getter"):
                getterdict = fn.fget.configurable_getter
                
            if inspect.isfunction(fn.fset) and hasattr(fn.fset, "configurable_setter"):
                setterdict = fn.fset.configurable_setter
                    
        elif inspect.isfunction(fn):
            if hasattr(fn, "configurable_getter"):
                getterdict = fn.configurable_getter
                
            if hasattr(fn, "configurable_setter"):
                setterdict = fn.configurable_setter
                
        else:
            continue # skip members that are not methods or properties
        
        if len(getterdict): 
            confdict.update(getterdict)
            
            if len(setterdict): 
                # this is executed in case of properties, as they are the only
                # ones providing BOTH a getterdict and setterdict, when decorated
                # so we check here that
                if setterdict.type != getterdict.type or setterdict.name != getterdict.name:
                    continue
                
                confdict.update(setterdict)
                
        elif len(setterdict):
            confdict.update(setterdict)
            
            
        if len(confdict):
            #print("%s confdict" % cls.__name__, confdict)
            if confdict.type.lower() == "qt":
                target = ret.qt
                if hasattr(cls, "_qtcfg"):
                    d1 = cls._qtcfg
                else:
                    d1 = dict()
                    
                if hasattr(cls, "_ownqtcfg"):
                    d2 = cls._ownqtcfg
                    
                else:
                    d2 = dict()
                    
            else:
                target = ret.conf
                if hasattr(cls, "_cfg"):
                    d1 = cls._cfg
                else:
                    d1 = dict()
                    
                if hasattr(cls, "_owncfg"):
                    d2 = cls._owncfg
                else:
                    d2 = dict()
                    
            #kcfg = Bunch()
            
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
                
            #kcfg[confdict.name] = cfgdict
            
            #if len(cfgdict):
                #kcfg[confdict.name] = cfgdict
                
            if confdict.name not in target:
                target[confdict.name] = cfgdict
                
            else:
                target[confdict.name].update(cfgdict)
                
            target.update(d1)
            target.update(d2)
            
    return ret

class ScipyenConfigurable(object):
    """Superclass for Scipyen's configurable types.
    
    Implements functionality to deal with non-Qt settings made persistent across
    Scipyen sessions.
    
    Qt-based GUI settings (where appropriate) are dealt with separately, by either
    inheriting from gui.workspacegui.WorkspaceGuiMixin, or by directly using
    the loadWindowSettings and saveWindowSettings in the gui.workspacegui module,
    or the syncQtSettings defined in this module.
    
    """
    qsettings = QtCore.QSettings(QtCore.QCoreApplication.organizationName(),
                                 QtCore.QCoreApplication.applicationName())
    #qsettings = QtCore.QSettings("Scipyen", "Scipyen")
    _scipyen_settings_  = scipyen_config
    _user_settings_src_ = scipyen_user_config_source
    
    def __init__(self):
        super().__init__()
        #self.qsettings = QtCore.QSettings("Scipyen", "Scipyen")
        #self._scipyen_settings_  = scipyen_config
        #self._user_settings_src_ = scipyen_user_config_source
        self.configurable_traits = DataBag()
        self.configurable_traits.observe(self._observe_configurables_)
        
    def _observe_configurables_(self, change):
        cfg = Bunch({self.__class__.__name__: Bunch({change.name:change.new})})
        pprint(cfg)
        
        
    @property
    def configurables(self) -> Bunch:
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
        return  self.configurables["qt"]
    
    @property
    def clsconfigurables(self):
        """Class configurables
        """
        return self.configurables["conf"]
    
    def loadSettings(self):
        #print("ScipyenConfigurable <%s>.loadSettings" % self.__class__.__name__)
        cfg = self.configurables
        # NOTE 2021-09-06 17:37:14
        # keep Qt settings segregated
        cfcfg = self.configurables.get("conf",Bunch())
        #qtcfg = self.configurables.get("qt",Bunch())
        
        if len(cfcfg):
            user_conf = scipyen_settings[self.__class__.__name__].get(None)
            
            if isinstance(user_conf, dict):
                for k, v in user_conf.items():
                    getset = cfcfg.get(k, {})
                    settername = getset.get("setter", None)
                    
                    if not isinstance(settername, str) or len(settername.strip())==0:
                        continue
                    
                    trait_notifier = getset.get("trait_notifier", None)
                    
                    if not isinstance(trait_notifier, (bool, DataBag)):
                        continue
                    
                    if trait_notifier is True and isinstance(getattr(self, "configurable_traits", None), DataBag):
                        trait_notifier = self.configurable_traits
                        
                    else:
                        continue
                        
                    with trait_notifier.hold_trait_notifications():
                        default = getset.get("default", None)
                        
                        setter = inspect.getattr_static(self, settername, None)

                        if isinstance(setter, property):
                            setattr(self, settername, v)
                            
                        elif setter is not None:
                            setter = getattr(self, settername)
                            setter(val)
                
        #else:
            #print("\tNo non-qt configurables found")
        #if len(qtcfg):
            #syncQtSettings(self.qsettings, self, False)
            #loadwindowSettings(self.qsettings, self)
    #def saveSettings(self):
        #pass
        
# NOTE: 2021-09-08 13:01:30 This WON'T WORK!!!
# because neither function named in configurables is an attribute of the 
# decorated :class: ScipyenConfigurable2
#
# For this reason, ScipyenConfigurable2 it NOT a good vehicle for
# the makeConfigurable decorator - see workspacegui.TestGuiWindow for 
# example.
#
# On the other hand, makeConfigurable will be able to find these getter &
# setter when applied to a :class: with base :classes: that contain them
# - see the example of workspacegui.TestGuiWindow2
#@makeConfigurable(configurables = Bunch({"WindowSize": Bunch({"type":"qt","getter":"size", "setter":"resize"}),
                                         #"WindowPosition": Bunch({"type":"qt", "getter":"pos","setter":"move"}),
                                         #"WindowGeometry": Bunch({"type":"qt", "getter":"geometry", "setter":"setGeometry"}),
                                         #"WindowState": Bunch({"type":"qt","getter":"saveState", "setter":"restoreState"}),
                                         #}))
@makeConfigurable()
class ScipyenConfigurable2(object):
    """NOTE: remove before release
    """
    qsettings = QtCore.QSettings(QtCore.QCoreApplication.organizationName(),
                                 QtCore.QCoreApplication.applicationName())
    #qsettings = QtCore.QSettings("Scipyen", "Scipyen")
    _scipyen_settings_  = scipyen_config
    _user_settings_src_ = scipyen_user_config_source
    
    def _observe_configurables_(self, change):
        cfg = Bunch({self.__class__.__name__: Bunch({change.name:change.new})})
        pprint(cfg)
        
        
    def loadSettings(self):
        cfg = self.configurables
        # NOTE 2021-09-06 17:37:14
        # keep Qt settings segregated
        cfcfg = self.configurables.get("conf", {})
        
        if len(cfcfg) == 0:
            return
        
        user_conf = scipyen_settings[self.__class__.__name__].get(None)
        
        if isinstance(user_conf, dict):
            for k, v in user_conf.items():
                getset = cfcfg.get(k, {})
                settername = getset.get("setter", None)
                
                if not isinstance(settername, str) or len(settername.strip())==0:
                    continue
                
                trait_notifier = getset.get("trait_notifier", None)
                
                if not isinstance(trait_notifier, (bool, DataBag)):
                    continue
                
                if trait_notifier is True and isinstance(getattr(self, "configurable_traits", None), DataBag):
                    trait_notifier = self.configurable_traits
                    
                else:
                    continue
                    
                with trait_notifier.hold_trait_notifications():
                    default = getset.get("default", None)
                    
                    setter = inspect.getattr_static(self, settername, None)

                    if isinstance(setter, property):
                        setattr(self, settername, v)
                        
                    elif setter is not None:
                        setter = getattr(self, settername)
                        setter(val)
               
            
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

@safeWrapper
def write_config(config:typing.Optional[confuse.Configuration]=None, 
                filename:typing.Optional[str]=None, 
                full:bool=True, redact:bool=False, as_default:bool=False,
                default_only:bool=False) -> bool:
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
    
