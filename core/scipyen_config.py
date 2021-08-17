#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" Scipyen configuration module for non-gui options and Qt gui settings other 
than window geometry and state.

Non-gui options are configuration settings for various Scipyen functionalities:

ScanData analysis

electrophysiology apps (LTP, AP analysis, IV curves, etc)

The non-gui options are stored in yaml file format using the confuse library.

The gui options are stored directly in Scipyen.conf under groups given by the
name of the QMainWindow or QWidget subclass which represents the user interface
of the (sub)application that uses these options (e.g., LSCaTWindow, ScipyenWindow,
SignalViewer, etc).

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

from .traitcontainers import DataBag

scipyen_lazy_config = confuse.LazyConfig("Scipyen")

# NOTE: 2021-07-18 22:45:53
# on GNU/Linux, this is '$HOME/.config/Scipyen'
scipyen_config_dir = os.path.dirname(scipyen_lazy_config.user_config_path())

#from goodconf import GoodConf, Value
#from dynaconf import Dynaconf

#settings = Dynaconf(
    #envvar_prefix="SCIPYEN",
    #settings_files=['settings.toml', '.secrets.toml'],
#)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load this files in the order.

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
    
    Instances of FunctionConfiguration are designed to store function calls
        The only requirement is that the function name is a symbol present in the 
        caller namespace.
        
    
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
        otherwise it will be interpreted as one of the function's arguments (as 
        if the function specified by 'name' would have expected a dict)

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
        
        #kwargs["name"] = fname
        #kwargs["args"] = fargs
        #kwargs["kwargs"] = fkwargs
                    
        super().__init__(name=fname, args=fargs, kwargs=fkwargs)
        

def create_option(option_name:str, option_value:typing.Any, parent:DataBag=None) -> DataBag:
    """Creates/adds an option path to an option dictionary
    """
    pass
    
def get_scipyen_config_file(configuration:confuse.Configuration, 
                            default:bool = False) -> typing.Optional[str]:
    if isinstance(configuration, confuse.Configuration):
        if not configuration._materialized:
            configuration.read()
            
        if default:
            defsrc = [s for s in configuration.sources if s.default]
            if len(defsrc):
                return defsrc[0].filename
            
        return configuration.user_config_path()
    
