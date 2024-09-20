# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Module with utilities for an external IPython kernel.
To be used on the client side (i.e. Scipyen app side, NOT in the REMOTE kernel).
Contains functions and types used to communicate with the remote kernel via its
messaging API.
"""
# on the client side, in a received execute_reply message the keys of
# msg["content"]["user_expressions"] are identical to those in the
# sent execute_request message["content"]["user_expressions"] NOTE that such
# execute_request message is sent when client.execute(...) is called, and the 
# user_expressions field of the message gets the valueof the user_expressions
# parameter to that call.

# NOTE 2020-07-11 10:26:38
# Strategies for getting information about the properties of an object located
# in the remote kernel namespace
# 
# A. Break it down in steps:
#
# 1. define a custom function in the remote kernel namespace by sending this
# string as a code string (1st execute() call)
#
# 2. run the newly created function in the remote kernel, this time as part
# of an "user_expressions" dict (2nd execute() call)
#
# 3. (optionally) delete the custom function from the remote kernel namespace
# to avoid clutter (3rd execute() call).
#
# B. Copy the data to the local namespace, get its properties there, then
# delete the data.
#
# C. For selected operations only we could simply import the relevant modules
# and/or functions at launching the remote kernel, especially if they are also
# useful for operations inside the remote kernel namespace.
# 
# An example would be core.utilities.summarize_object_properties() function
# that retrieves informative properties of an object as type, size, etc).

# Advantages of strategy A:
# 1. does not require data serialization, 
# 2. avoids cluttering the remote kernel namespace with modules that are 
# only for accomplishing the particular operation
# 3. can be scaled to several steps, if necessary
# 
# Prerequisites for strategy A:
# a. the operation to be accomplished by the client can be broken down in steps
# b. data relevant to the client is received via the "user_expressions" dict 
#    of "execute_reply" messages (e.g. step 2 above)
# c. the "execute_reply" messages containing relevant "user_expressions" need 
#    to be easily distinguished from other "execute_reply" messages (e.g. using
#    naming conventions for the keys in "user_expressions" dict) 
# d. moreover, the "user expressions" code generating data in the relevant
#    "execute_reply" messages should not rely on data from previous "execute_reply"
#    "user_expressions" content (these messages are received and processed 
#    on the client side asynchronously, via Qt signal/slot mechanism, and
#    therefore such dependencies would require a clever mechanism 
#    (coroutines etc. TODO: investigate this)
#
# Strategy B is less cumbersome that Strategy A, but can create heavy traffic
# between the remote kernel and the client, because is relies on data
# serialization & transfer (so even if this happens on the same physical 
# machine, we still may end up transferring megabytes of data and incur 
# serialization/deserialization overheads.)
#
# Strategy C is probably the easiest (and most economical) but could be
# easily abused by importing into the remote namespace functions and modules 
# that end up only being used by the client, in the local namespace.

import os, sys, pickle, inspect, traceback, types, typing
from functools import wraps
from core.traitcontainers import DataBag
from core.prog import safeWrapper
import qtpy

qtPackages = ", ".join([p for p in qtpy.__dict__.keys() if p.startswith("Qt") and isinstance(qtpy.__dict__[p], types.ModuleType)])

#from contextlib import contextmanager
#print(sys.path)

__module_path__ = os.path.abspath(os.path.dirname(__file__)) # this should be ending in "/core"

__scipyen_path__ =  os.path.dirname(__module_path__)

__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

# initialization script for ALL available external IPython consoles
# private: call indirectly via init_commands!
_ext_ipython_initialization_file = os.path.join(__module_path__, "extipy_init.py")
_ext_ipython_initialization_cmd = " ".join(["get_ipython().run_cell(", "'run -i -n", _ext_ipython_initialization_file, "')"])

# initialization script for NEURON in external ipython process
# only called when launching a NEURON external console
# expected to be passed as 'code' parameter to tab with frontend factories in 
# ExternalIPython / ExternalConsolewindow!
nrn_ipython_initialization_file = os.path.join(os.path.dirname(__module_path__),"neuron_python", "nrn_ipython.py")
nrn_ipython_initialization_cmd = " ".join(["run -i -n", nrn_ipython_initialization_file, " 'gui'"])

# NOTE: 2021-01-14 12:12:11
# the last two lines in the init_commands make these two modules available for 
# importing in the "remote" kernel
# TODO: 2021-01-14 12:18:45
# figure out how to use Qt5 Agg in the external ipython (mpl.use("Qt5Agg") crashes
# the kernel when a mpl figure is shown)
# for now stick with inline figures
# TODO: 2022-02-06 22:28:41
# consider consolidating these and the extipyutils_host if possible
init_commands = [
    "import sys, os, io, warnings, numbers, types, typing, re, importlib",
    "import traceback, keyword, inspect, itertools, functools, collections",
    ]

# NOTE: 2022-02-06 22:30:26
# some of the commands below expose Scipyen API to external kernels; this may
# be done via such init commands as below; 
# These MIGHT also be imported from within extipyutils_host BUT they won't be 
# directly available in the REMOTE kernel workspace - but only indirectly as
# members of the 'hostutils' module available in the REMOTE kernel workspace.
# Hence, hostutils (a.k.a extipyutils_host) shoud only contain API deemed as
# housekeeping for the REMOTE python kernel, including for communication
# between the Scipyen kernel and the REMOTE kernel, and not requiring regular
# access by the user.
init_commands.extend(
    [
    "".join(["sys.path.insert(2, '", __scipyen_path__, "')"]),
    "import signal, pickle, json, csv",
    "import numpy as np",
    "import scipy",
    "import pandas as pd",
    "import seaborn as sb",
    "from importlib import reload",
    "from pprint import pprint",
    f"from qtpy import ({qtPackages})",
    "import matplotlib as mpl",
    "mpl.rcParams['savefig.format'] = 'svg'",
    "mpl.rcParams['xtick.direction'] = 'in'",
    "mpl.rcParams['ytick.direction'] = 'in'",
    "from matplotlib import pyplot as plt",
    "from matplotlib import cm",
    "import matplotlib.mlab as mlb",
    "import core.extipyutils_host as hostutils",
    # "from hostutils import ContextExecutor",
    "from core.workspacefunctions import *",
    "from plots import plots as plots",
    "from core import datatypes as dt",
    "from core import neoutils",
    "from core.datatypes import * ",
    "import core.signalprocessing as sigp",
    "import core.curvefitting as crvf",
    "import core.strutils as strutils",
    "import core.data_analysis as anl",
    "from core.utilities import (summarize_object_properties,standard_obj_summary_headers,safe_identity_test, unique, index_of, gethash,NestedFinder, normalized_index)",
    "from core.prog import (safeWrapper, deprecation, iter_attribute,filter_type, filterfalse_type, filter_attribute, filterfalse_attribute)",
    "from core import prog",
    "from core.traitcontainers import DataBag",
    "from core.triggerprotocols import TriggerProtocol",
    "from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType, )",
    "from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)",
    "from core.datazone import DataZone",
    "from systems import *",
    "from imaging import (imageprocessing as imgp, imgsim,)",
    "from imaging import axisutils, vigrautils",
    "from imaging.axisutils import (axisTypeFromString, axisTypeName,axisTypeStrings,axisTypeSymbol, axisTypeUnits,dimEnum,dimIter,evalAxisTypeExpression,getAxisTypeFlagsInt,getNonChannelDimensions,hasChannelAxis,)",
    "from imaging.axiscalibration import (AxesCalibration,AxisCalibrationData, ChannelCalibrationData, CalibrationData)",
    "from iolib import pictio as pio",
    "from iolib import h5io, jsonio",
    "print('To use matplotlib run %matplotlib magic')",
    
    ])

if os.path.isfile(_ext_ipython_initialization_file):
    init_commands.append(_ext_ipython_initialization_cmd)
    
init_commands.extend([
    "u_ns = get_ipython().user_ns",
    "get_ipython().user_ns_hidden.update(u_ns)",
    "del u_ns"
    ])

class ForeignCall(DataBag):
    """Usage:
    call = ForeignCall(user_expressions={"test":"etc"})
    
    kernel_client.execute(*call())
    
    kernel_client.execute(**call.dict())
    
    NOTE: 2021-01-14 16:55:36
    The user_expression dict is a str:str mapping used to serialize data 
    generated in the remote kernel so that it is captured in the Scipyen workspace.
    
    The serialization occurs via JSON (as ascii data), optionally pickled.
    
    CAUTION: Not all Python objects can be pickled - in particular some Qt objects
    (e.g., widgets, or from the QGraphics framework) cannot be pickled.
    
    Also, pickling/unpickling of user-defined data types depends on the modules
    defining the data type being imported in both the remote and local (Scipyen's)
    IPython kernels.
    
    The keys in user_expressions are name of the variables as they are to appear
    in Scipyen's user workspace. 
    
    The values are str which are going to be evaluated in the calling namespace, 
    or treated as a byte stream of pickled data, when the key is prefixed with 
    "pickled_"; in the latter case, the data will be "unpickled" at the receiving
    end (see unpack_shell_channel_data() in this module).
    
    TODO: not used: The user_expressions may contain the special keyword __REDIRECT__ which must
    be mapped to either "True" or "False"
    
    When present and mapped to "True", then the variables returned by the 
    user_expressions mechanism will be returned to the caller's namespace instead
    of being exported to Scipyen's user workspace.
    
    """
    def __init__(self, code="", silent=True, store_history=False, user_expressions=None,
                 allow_stdin=None, stop_on_error=True):
        
        super().__init__(code=code, silent=silent, store_history=store_history,
                         user_expressions=user_expressions,
                         allow_stdin=allow_stdin, stop_on_error=stop_on_error)
            
    def __call__(self):
        yield from (self.code,
                self.silent,
                self.store_history,
                self.user_expressions,
                self.allow_stdin,
                self.stop_on_error,
                )
    
    def dict(self):
        return {"code":self.code,
                "silent":self.silent,
                "store_history":self.store_history,
                "user_expressions":self.user_expressions,
                "allow_stdin": self.allow_stdin,
                "stop_on_error":self.stop_on_error,
                }
    
    def copy(self):
        return ForeignCall(self.code, self.silent, self.store_history,
                           self.user_expressions, self.allow_stdin,
                           self.stop_on_error)

#### BEGIN expression generators    

def make_user_expression(**kwargs):
    """TODO Generates a single user_expressions string for execution in a remote kernel.

    The user_expressions parameter to the kernel local client's execute() is a 
    dict mapping some name (local to the calling namespace) to a command string
    that is to be evaluated in the remote kernel namespace. 
    
    user_expressions = {"output": expression_cmd}
    
    Upon execute() call, the remote kernel executes the 'expression_cmd' and
    the returned object is mapped to the "output" key in user_expressions, 
    embedded in the 'execute_reply' message received from the remote kernel 
    via the kernel client's shell channel.
    
    The message received from the remote kernel contains:
    (NOTE that only the relevant key/value pairs are listed below)
    
    message["content"]["user_expressions"]: a dict with the following key/value
    pairs:
    
    local_name ->  user_sub_expression dict(): a nested dict with the key/value  pairs:
    
        "status" -> str = OK when the message passing from the kernel was successful
        
        "data" -> dict() -  with the mapping:
        
            "status" -> str = "ok" when 'expression_cmd' execution was successful
            
            "text/plain" -> str  = string representation of the result of 
                                    'expression_cmd' execution in the remote 
                                    kernel namespace. 
                                    
                                    This may be a byte array, when is the result 
                                    of serialization in the remote kernel
                                    namespace (see below).
                                    
    A successful execute(...) call is indicated when the next conditions are
    simultaneously satisfied:
    
        message["content"]["status"] == "ok"
        
        message["content"]["user_expressions"][local_name]["status"] == "ok"
        
    As stated above, the string representation of the result is in
    
    message["content"]["user_expressions"][local_name]["data"]["text/plain"]
    
    In the example above, local_name is "output".
                                    
    Sometimes it is useful to get the objects returned by evaluating 'expression_cmd',
    not just their string representation. This is possible only for objects that
    can be serialized (using the pickle module).
    
    In this case, 'expression_cmd' must instruct the remote kernel to "pack" 
    the remote execution result itself into a serializable object, such as a 
    dictionary, then pickle it (as bytes) to a string. 
    
    Such a "pickled" command has the (strict) syntax:
    
    "pickle.dumps({...})" 
    
        where {...} is the python text code for generating the dictionary in the
        remote kernel namespace
    
    For example, given the expression "dir()", the following:
    
        pickled_sub_expression_cmd = "pickle.dumps({'namespace': dir()})"
        
        binds the result of dir() (a list of str - the contents of the remote
        kernel namespace) to the symbol "namespace".
        
    In turn, the containing user_expressions on the call side would be:
        {'namespace':pickled_sub_expression_cmd}
        
    and the string representation of the serialized dict 
        {"namespace":<result of dir()>} will be assigned to
    
        message["contents"]["user_expressions"]["namespace"]["data"]["text/plain"]
        
        in the execute_reply message (provided execution was successful).
        
    Using a dictionary on the remote kernel "side" is not mandatory. A dict will
    bind the result to a symbol or a name, the key of the remote dictionary), 
    with the price that the result of the actual pickled expression of introducing
    a deeper level of nesting in the execute_reply message.
    
    
    This string (containing serialized bytes) is then mapped to the "text/plain"
    key in the "data" sub-dictionary of the particular user expression mapped
    to the appropriate local key name (in the example given here, "output")
    
    The serialized bytes will be placed as a string, in
    
        message["content"]["user_expressions"]["output"]["data"]["text/plain"]
    
    These can be deserialized in the calling namespace by executing pickle.loads(eval(x))
    
    where "x" is message["content"]["user_expressions"]["output"]["data"]["text/plain"]`
    
    
    Parameters:
    ----------
    **kwargs:
    
    
    
    Returns:
    --------
    
    A str with the contents of the expression_cmd
    
    
    Where:
        key is a quoted str (i.e. must evaluate to a string in the remote kernel)
        
        expression is a str that must evaliuate to a valid expression in the remote kernel
    
    """
    
    pass

def pickle_wrap_expr(expr):
    if not isinstance(expr, str):
        raise TypeError("expecting a str, got %s" % type(expr).__name__)
    
    return "".join(["pickle.dumps(",expr,")"])
    
def define_foreign_data_props_getter_fun_str(dataname:str, namespace:str="Internal") -> str:
    """Defines a function to retieve object properties in the foreign namespace.
    
    The function is wrapped by a context manager so that any module imports are
    are not reflected in the foreign namespace. - is this true !?
    
    The function should be removed from the foreign ns after use.
    """
    # NOTE: 2024-09-20 22:07:10
    # remove "Icon" from summary, otherwise we have issues eval-ing it
    return "\n".join(["@hostutils.ContextExecutor()", # core.extipyutils_host is imported remotely as hostutils
    "def f(objname, obj):",                           # use regular function wrapped in a context manager
    "    from core.utilities import summarize_object_properties",
    f"    ret = summarize_object_properties(objname, obj, namespace='{namespace}')",
    "    ret.pop('Icon', None)",
    "    return ret"
    "", # ensure NEWLINE
    ])
    # return "\n".join(["@hostutils.ContextExecutor()", # core.extipyutils_host is imported remotely as hostutils
    # "def f(objname, obj):",                           # use regular function wrapped in a context manager
    # "    from core.utilities import summarize_object_properties",
    # "    return summarize_object_properties(objname, obj, namespace='%s')" % namespace,
    # "", # ensure NEWLINE
    # ])

def define_foreign_data_props_getter_gen_str(dataname:str, namespace:str="Internal") -> str:
    """Defines a generator to retrieve object properties in the foreign namespace.
    
    The function is decorated with @contextmanager hence behaves like such, and
    any module imports are not reflected in the foreign namespace.
    
    The downside of this strategy is that it creates temporary data in the foreign
    namespace, which will have to be removed alongside with the generator, after 
    use.
    """
    return "\n".join(["@hostutils.contextmanager", # core.extipyutils_host is imported remotely as hostutils
    "def f_gen(objname, obj):",             # use a generator func
    "    from core.utilities import summarize_object_properties",
    f"    ret = summarize_object_properties(objname, obj, namespace='{namespace}')",
    "    ret = ret.pop('Icon', None)",
    "    yield ret"
    "",                                                     # ensure NEWLINE
     ])
    
#### END expression generators

#### BEGIN call generators

def cmds_get_foreign_data_props(dataname:str, namespace:str="Internal") -> list:
    """Creates a list of execute calls retrieving data properties in foregn ns
    
    """
    # see NOTE 2020-07-11 10:26:3`8
    #
    # NOTE: user_expressions code should be one-liners; it does not accept
    # compound statements such as function definitions, with context manager 
    # statements even when written on one line (there is a mandatory colon, ":")
    # etc.
    exec_calls = list()
    
    special = "properties_of"
    
    # Using strategy A (see NOTE 2020-07-11 10:26:38):
    
    #### BEGIN variant 1 - works
    # execution expression to define the function that retrieves the data properties
    cmd = define_foreign_data_props_getter_fun_str(dataname,namespace)
    
    # executes the definition of the function
    exec_calls.append(ForeignCall(code=cmd))
    
    # calls the function defined above then captures the result in user_expressions
    exec_calls.append(ForeignCall(user_expressions={"%s_%s" % (special, dataname): "".join(["f('", dataname, "', ", dataname, ")"])}))
    
    # cleans up after use.
    exec_calls.append(ForeignCall(code="del f"))
    
    #### END variant 1
    
    ##### BEGIN variant 3 - no joy - remote kernel reports attribute error __enter__
    # when using a generator instead of a function -- why ??!
    #cmd1 = "\n".join(["@hostutils.ContextExecutor()", # core.extipyutils_host is imported remotely as hostutils
    #"def f_gen(objname, obj):",             # use a generator func
    #"    from core.utilities import summarize_object_properties",
    #"    yield summarize_object_properties(objname, obj)",
    #"",                                                     # ensure NEWLINE
     #])
    #exec_calls.append({"code": cmd1, "user_expressions":None})
    #exec_calls.append({"code": "".join(["with f_gen('", dataname, "', ", dataname, ") as ", "obj_props_%s:" % dataname, " pass"]),
                       #"user_expressions": None})
    #exec_calls.append({"code": "",
                       #"user_expressions": {"obj_props_%s:" % dataname: "obj_props_%s" % dataname}})
    
    ##exec_calls.append({"code":"del f_gen"})
    
    ##### END variant 3
    return exec_calls
    
def cmds_get_foreign_data_props2(dataname:str, namespace:str="Internal") -> list:
    """Creates a list of execute calls retrieving data properties in foregn ns
    
    """
    exec_calls = list()
    #### BEGIN variant 2 - works but the 'with' statement must be executed (hence
    # passed as code , not as part of user_expressions)
    # a bit more convoluted, as it creates sub_special_%(dataname) in the foreign namespace
    special = "properties_of"
    sub_special = "obj_props"
    
     # defines a generator fcn decorated with contextmanager
    cmd1 = define_foreign_data_props_getter_gen_str(dataname, namespace)
    
    # creates the with ... as ... statement; upon execution it creates the 
    # sub_special_%(dataname) in the foreign namespace
    cmd2 = "".join(["with f_gen('", dataname, "', ", dataname, ") as ", "%s_%s:" % (sub_special,dataname), " pass"])
    
    # executes the definition of the generator fcn (cmd1)
    exec_calls.append(ForeignCall(code = cmd1))
    #exec_calls.append({"code": cmd1, "silent": True, "store_history":False, 
                       #"user_expressions": None})
    
    # executes the with context manager statement (cmd2)
    exec_calls.append(ForeignCall(code=cmd2))
    #exec_calls.append({"code": cmd2, "silent": True, "store_history":False, 
                       #"user_expressions": None})
    
    # assigns the result of the previous exec, to user_expressions
    exec_calls.append(ForeignCall(user_expressions ={"%s_%s" % (special, dataname): "%s_%s" % (sub_special,dataname)}))
    
    # clean up after use
    exec_calls.append(ForeignCall(code = "del(f_gen, %s_%s)" % (sub_special,dataname)))
    
    #exec_calls.append({"code": "del(f_gen, %s_%s)" % (sub_special,dataname), "silent": True, "store_history":False, 
                       #"user_expressions": None})
    
    
    #### END variant 3
    
    return exec_calls
    
def cmd_copy_from_foreign(varname:str, as_call=True) -> typing.Union[ForeignCall, dict]:
    """Create user expression to fetch varname from a foreign kernel's namespace.
    
    The foreign kernel is the with which the kernel client executing this command
    is communicating.
    
    Parameters:
    -----------
    varname : str - the name (identifier) to which a variable we wish to fetch
            from the remote kernel namespace, is bound.
            
    as_call: bool, default True
    
        When True, returns a ForeignCall which can be passed to execute, e.g.
        ExternalIPython.execute(*call())
        
        Otherwise, return a dict usable as a user_expressions key/value mapping
    
    Returns:
    --------
    
    If as_call is False:
        A dict with a single key, "varname", mapped to a command string that, when
        executed in the remote kernel, will be substituted with the serialized
        (pickled) variable named "varname" (as a byte string) upon evaluation
        by the remote kernel.
        
        The seralized data is then captured in the "execute_reply" message received
        from the remote kernel via its client's shell channel.
        
        
    To be evaluated in the remote kernel and the result captured in Scipyen, the 
    dict must be included inside the "user_expressions" parameter to execute()
    method of the client for the remote kernel.
    
    Once captured in the "execute_reply" message, the variable can be deserialized
    in Scipyen's workspace, by passing the received "execute_reply" message to the 
    using unpack_shell_channel_data() function.
    
    If as_call is True:
        A ForeignCall object with user_expression set to the dict as explained above.
    
    
    NOTE: This mechanism creates in the caller's namespace copies of the data 
    existing in the remote kernel (byte-to-byte identical to their originals).
    
    To fetch several variables use cmd_copies_from_foreign().
    
    See also unpack_shell_channel_data.
    
    For details about messaging in Jupyter see:
    
    https://jupyter-client.readthedocs.io/en/latest/messaging.html
    
    """
    special = "pickled_"
    remote_expr = "".join(["{'",varname,"':",varname,"}"])
    expr = {"%s_%s" % (special,varname):pickle_wrap_expr(remote_expr)}
    
    if as_call:
        return ForeignCall(user_expressions = expr)
    
    else:
        return expr

def cmd_copies_from_foreign(*args, as_call=True) -> typing.Union[ForeignCall, dict]:
    """Create user expressions to fetch several variables from a foreign kernel.
    
    The foreign kernel is the with which the kernel client executing this command
    is communicating.
    
    Parameter:
    ---------
    args - variable sequence of strings - the names of the variables we want to
            fetch from the remote kernel
            
            This function calls cmd_copy_from_foreign() for each element 
            in args then merges the results in a dict.
            
            
    as_call: bool, optional (default True)
        Whe True, returns a ForeignCall; otherwise, returns a user-expresions dict
            
    Returns:
    ---------
    
    If as_call is False:
        A dict with several key:value pairs, where each key is a (unique) varname
        in *args, and values are command strings to be evaluated by the remote 
        kernel in its own namespace.
        
        When evaluated, the commands trigger the serialization (pickling) of the
        named variables in the remote kernel.
            
    Similar to cmd_copy_from_foreign() function, the dict returned 
    here needs to be included in the "user_expressions" parameter of the kernel's 
    client execute() method.
    
    The fetched variables are shuttled back into client code in serialized form 
    (pickled str bytes) via the "execute_reply" shell channel message. From there
    variables are recovered by passing the "execute_reply" message to the 
    unpack_shell_channel_data() function.
    
    When as_call is true (default):
        A ForeignCall with the user_expressions set to the dict with structure
        as explained above.
    
    
    See also unpack_shell_channel_data.
    
    For details about messaging in Jupyter see:
    
    https://jupyter-client.readthedocs.io/en/latest/messaging.html
    
    """
    import itertools

    vardicts = (cmd_copy_from_foreign(arg, as_call=False) for arg in args)
    
    expr = dict((x for x in itertools.chain(*(a.items() for a in vardicts))))
    
    if as_call:
        return ForeignCall(user_expressions = expr)

    return expr

def cmd_copy_to_foreign(dataname, data:typing.Any) -> str:
    """Creates a user expression to place a copy of data to a remote kernel space.
    
    The data will be bound, in the remote namespace, to the identifier specified
    by "dataname".
    
    Parameters:
    -----------
    dataname: str
    data: typing.Any - Must be serializable.
    
    Unlike the result from cmd_copy_from_foreign(s), the command string 
    returned by this function can be passed to the remote kernel for evaluation
    as the "code" parameter of the client's execute() method.
    
    ATTENTION Existing data in the remote kernel that is bound to an identical 
    identifier WILL be overwritten ATTENTION.
    
    """
    exec_calls = list()
    #print("cmd_copy_to_foreign: dataname=%s , data=%s" % (dataname, data))
    pickle_str = str(pickle.dumps({dataname:data}))
    #print("cmd_copy_to_foreign: pickle_str = %s" % pickle_str)
    
    prepper_cmd="\n".join(["@hostutils.ContextExecutor()",
    "def f(picklebytes):",
    "   data = pickle.loads(eval(str(picklebytes)))",
    "   get_ipython().user_ns.update(data)"])
    
    exec_calls.append(ForeignCall(code=prepper_cmd))
    
    unpickler_cmd = "".join(["f(", pickle_str, ")"])
    exec_calls.append(ForeignCall(code=unpickler_cmd))
    
    cleanup_cmd = "del(f)"
    exec_calls.append(ForeignCall(code = "del f"))
    
    return exec_calls
    
def cmd_foreign_namespace_listing(namespace:str="Internal", as_call=True) -> dict:
    """Creates a user_expression containing the variable names in a foreign namespace.
    """
    
    expr = {"ns_listing_of_%s" % namespace : "dir()"}
    #expr = {"ns_listing_of_%s" % namespace.replace(" ", "_") : "dir()"}
    
    if as_call:
        return ForeignCall(user_expressions = expr)
    
    return expr
    
def cmd_foreign_shell_ns_listing(namespace:str="Internal", as_call=True) -> dict:
    """Creates a user_expression containing the variable names in a foreign namespace.
    
    This one returns get_ipython().user_ns and get_ipython().user_ns_hidden
    """
    
    # NOTE 2020-07-29 22:51:02: WRONG: the value of "ns_listing_of_%s" % namespace
    # must be a str
    #ue1 = "{'user_ns':set([k for k in get_ipython().user_ns.keys() if k not in get_ipython().user_ns_hidden.keys() and not inspect.ismodule(get_ipython().user_ns[k]) and not k.startswith('_') ])}"
    
    # NOTE: allow listing of imported modules!
    ue1 = "{'user_ns':set([k for k in get_ipython().user_ns.keys() if k not in get_ipython().user_ns_hidden.keys() and not k.startswith('_') ])}"
    
    expr = {"ns_listing_of_%s" % namespace : ue1}
    #expr = {"ns_listing_of_%s" % namespace.replace(" ", "_") : ue1}
    
    if as_call:
        return ForeignCall(user_expressions = expr)
    
    return expr
    
def cmd_foreign_shell_ns_hidden_listing(namespace:str="Internal", as_call=True) -> dict:
    """Creates a user_expression containing the variable names in a foreign namespace.
    
    This one returns get_ipython().user_ns and get_ipython().user_ns_hidden
    """
    
    # NOTE 2020-07-29 22:51:02: WRONG: the value of "ns_listing_of_%s" % namespace
    # must be a str
    #ue1 = "{'user_ns':set([k for k in get_ipython().user_ns.keys() if k not in get_ipython().user_ns_hidden.keys() and not inspect.ismodule(get_ipython().user_ns[k]) and not k.startswith('_') ])}"
    
    ue1 = "{'user_ns':set([k for k in get_ipython().user_ns_hidden.keys() or k.startswith('_') ])}"
    
    expr = {f"hidden_ns_listing_of_{namespace}" : ue1}
    #expr = {"ns_listing_of_%s" % namespace.replace(" ", "_") : ue1}
    
    if as_call:
        return ForeignCall(user_expressions = expr)
    
    return expr
    
#### END call generators

@safeWrapper
def unpack_shell_channel_data(msg:dict) -> dict:
    """Extracts data shuttled from the remote kernel via " execute_reply" message.
    
    The data are present as text/plain mime type data in the received execute_reply
    message, inside its "content"/"user_expressions" nested dictionary.
    
    Messages received in response to requests for variable transfer (copy) will
    contain in the "user_expressions" keys named as "pickled_%s" where "%s" stands 
    for the variable identifier in the remote kernel namespace. 
    
    This is so that this function can decide whether the data received is a 
    string representation of the seriazied variable (as a byte string) or just 
    plain text information. 
    
    In the former case, the fucntion de-serialized the bytes into a copy of the 
    variable and binds it to %s (i..e, the same identifier to which the variable 
    is bound in the remote namespace).

    In the latter case, the string associated to the "text/plain" data is assigned
    to the %s identifier in the caller namespace
    
    ATTENTION 
    If ths identifier is already bound to another variable in the caller namespace,
    this may result in this (local) variable being overwritten by the copy of the 
    remote variable. 
    
    It is up to the caller to decide what to do in this situation.
    ATTENTION
    
    For details about messaging in Jupyter see:
    
    https://jupyter-client.readthedocs.io/en/latest/messaging.html

    """
    # NOTE: "specials" are (%s being substituted with the value of the identifier
    #       shown in parenthesis):
    #
    # "pickled_%s"          (varname)
    #
    # "properties_of_%s"    (varname)
    #
    # "ns_listing_of_%s"    (workspace_name)
    #
    # ATTENTION The specials are set by the functions than generate the commands
    # generating the user_expressions dictionaries.
    
    ret = dict()
    # peel-off layers one by one so we can always be clear of what this does
    msg_status = msg["content"]["status"]
    usr_expr = msg["content"].get("user_expressions", {})
    # print(f"unpack_shell_channel_data: usr_expr = {usr_expr}")
    if msg_status == "ok":
        for key, value in usr_expr.items():
            value_status = value["status"]
            if value_status == "ok":
                data_str = value["data"]["text/plain"] # this nested dict exists only if value_status is OK
                if key.startswith("pickled_"): # by OUR OWN convention, see cmd_copy_from_foreign
                    data_dict = pickle.loads(eval(data_str))
                    
                else:
                    try:
                        data_dict = {key:eval(data_str)}
                    except:
                        print(f"unpack_shell_channel_data: data_str = {data_str}\n")
                        traceback.print_exc()
                    
                ret.update(data_dict)

    return ret

def execute(client, *args, **kwargs):
    """Execute code in the kernel, sent via the specified kernel client.
        
    Parameters
    ----------
    client: a kernel client
    
    *args, **kwargs - passed directly to client.execute(...), are as follows:
    
        code : str
        
            A string of code in the kernel's language.
        
        silent : bool, optional (default False)
            If set, the kernel will execute the code as quietly possible, and
            will force store_history to be False.
        
        store_history : bool, optional (default True)
            If set, the kernel will store command history.  This is forced
            to be False if silent is True.
        
        user_expressions : dict, optional
            A dict mapping names to expressions to be evaluated in the user's
            dict. The expression values are returned as strings formatted using
            :func:`repr`.
        
        allow_stdin : bool, optional (default self.allow_stdin)
            Flag for whether the kernel can send stdin requests to frontends.
        
            Some frontends (e.g. the Notebook) do not support stdin requests.
            If raw_input is called from code executed from such a frontend, a
            StdinNotImplementedError will be raised.
        
        stop_on_error: bool, optional (default True)
            Flag whether to abort the execution queue, if an exception is encountered.
    
    Returns
    -------
    The msg_id of the message sent.


    """
    
    return client.execute(*args, **kwargs)




