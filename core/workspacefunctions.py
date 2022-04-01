""" Various utilities for Scipyen workspace functions
All functions defined here are to be imported in the top namespace
(e.g., 'from workspacefunctions import *')

DOES NOT WORK (yet)

"""
from __future__ import print_function
#from sys import getsizeof, stderr

import re as _re # re is also imported directly from pict

import inspect, keyword, warnings, typing

from operator import attrgetter, itemgetter, methodcaller

from collections import OrderedDict, deque


try:
    from reprlib import repr
except ImportError:
    pass

def debug_scipyen(arg:typing.Optional[typing.Union[str, bool]] = None) -> bool:
    """Sets or gets the state of scipyen debugging.
    
    The state is a boolean variable SCIPYEN_DEBUG in the user namespace.
    
    When True, then specific "print" messages in the scipyen modules get executed
    
    Parameters:
    -----------
    arg: str, bool, optional (default is None)
        When str, "on" (case-insensitive) turns debugging ON ; anything else
            turns debugging OFF
            
        When bool, True turns debugging ON, False turns it OFF
        
        When None, the function returns the current state of SCIPYEN_DEBUG.
        
        NOTE this is deliberately different from the behaviour of the
        'scipyen_debug' line magic which, whehn called without argument, toggles
        the debugging state ON or OFF
    
    """
    ns = user_workspace()
    if not isinstance(ns, dict):
        return False
    
    if arg is None:
        if "SCIPYEN_DEBUG" not in ns:
            ns["SCIPYEN_DEBUG"] = False
            
        return ns["SCIPYEN_DEBUG"]
    
    if isinstance(arg, str):
        val = arg.strip().lower() == "on"
        ns["SCIPYEN_DEBUG"] = val
        return ns["SCIPYEN_DEBUG"]
    
    elif isinstance(arg, bool):
        ns["SCIPYEN_DEBUG"] = arg
        return ns["SCIPYEN_DEBUG"]
        
    elif not isinstance(arg, bool):
        raise TypeError("Expecting a str ('on' or 'off'), a bool, or None; got %s instead" % arg)
        
def lsvars(*args, glob:bool=True, ws:typing.Union[dict, type(None)]=None, 
            var_type:typing.Union[type, type(None), typing.Tuple[type], typing.List[type]]=None,
            sort:bool=False, sortkey:object=None, reverse:bool=False):
    """List names of variables in a namespace, according to a selection criterion.
    
    Returns a (possibly sorted) list of variable names if found, or an empty list.
    
    See also: docstring for getvars() for details
    
    Var-positional parameters:
    -------------------------
    args: comma-separated list of strings, types, or sequence of types
    
        When args contains strings, these define patterns to match against the 
        variable names in the search namespace.
        
        When args only contain an empty string, or not given, the function
        returns a list with all the varioable names in the search namespace.
        
        When args contains types, these identify what type of variables to be listed
        in the search namespace.
    
    Named parameters:
    -----------------
    
    glob: bool (default is True)
        When True, the strings in args are treated as UNIX shell-style globs; 
            otherwise, they are treated as regular expression strings.
        
    ws: dict (default None) = the search namespace
    
        When a dict, its keys must all be strings.
        
        The search namespace. This can be:
        a) a global namespace as returned by globals(),
        b) a local namespace as returned by locals(), or vars()
        c) an object's namespace as returned by vars([object]) -- technically, 
            the object.__dict__
        
        When None, the function tries ot find the user namespace (the "workspace")
        as set up by the Scipyen Main Window in Scipyen application.
    
    var_type: a type, a sequence of types, or None (default)
        When a type, only select the variables of the indicated type
        
    """
    from fnmatch import translate
    
    if ws is None:
        ws = user_workspace()
    if ws is None:
        raise ValueError("No valid workspace has been specified or found")
        
    if len(args) == 0: # no selector arguments: get all variables names in ws
        return ws.keys()

    elif len(args) == 1: # one selector argument
        sel = args[0]
        
        if sel is None:
            return ws.keys() # no selector: get all variables names in ws
            
        elif isinstance(sel, str): # select by variable name
            
            if len(sel.strip()) == 0:# empty selector string: get all variables names in ws
                return ws.keys()
            
            p = _re.compile(translate(sel)) if glob else _re.compile(sel)
            
            var_names_filter = filter(p.match, ws.keys())
            vlist =  [k for k in var_names_filter] # return a list of variable names
            
            if isinstance(var_type, type) or (isinstance(var_type, (tuple, list)) and all([isinstance(v, type) for v in var_type])):
                ret = [s for s in vlist if isinstance(ws[s], var_type)]
                
            else:
                ret =  vlist # return a list of variable names
        
        elif isinstance(sel, type) or (isinstance(sel, (list, tuple)) and all([isinstance(k, type) for k in sel])):
            # select by variable type (or types)
            # ignore var_type parameter
            ret = [k for (k,v) in ws.items() if sel is not type(None) and isinstance(v, sel)] # return a list of variable names
            
        else:
            raise TypeError("Unexpected type for the selector argument: got %s" % type(sel).__name__)
            
    else: # comma-separated list of selector arguments
        ret = list()
        for (sk, sel) in enumerate(args):
            if isinstance(sel, str): # string selector
                if len(sel.strip()):
                    
                    p = _re.compile(translate(sel)) if glob else _re.compile(sel)
                    
                    var_names_filter = filter(p.match, ws.keys())
                    
                    vlist = [k for k in var_names_filter] 
                    
                    if isinstance(var_type, type) or (isinstance(var_type, (tuple, list)) and all([isinstance(v, type) for v in var_type])):
                        ret.expand([s for s in vlist if isinstance(ws[s], var_type)])
                        
                    else:
                        ret.expand(vlist) # return a list of variable names
                    
                #if len(ret) == 0:
                    #return ws.keys()
            
            elif isinstance(sel, type) or (isinstance(sel, (list, tuple)) and all([isinstance(k, type) for k in sel])):
                # ignore var_type
                ret += [k for (k,v) in ws.items() if isinstance(v, sel)] # return a list of variable names
                
            else:
                raise TypeError("Unexpected type for the selector argument number %d: got %s" % (sk, type(sel).__name__))
                
    
    if sort:
        return sorted(ret, key=sortkey, reverse=reverse)
    
    return ret
    
    
def getvarsbytype(vartype, ws=None):
    """Get variables by type, from a namespace or a dict
    """
    if not isinstance(vartype, (type, tuple, list)):
        raise TypeError("Expecting  type or a sequence of types as first argument; got %s instead" % (type(vartype).__name__))
    
    if isinstance(vartype, (tuple, list)):
        if len(vartype) == 0:
            return dict()
        
        if not all([isinstance(v, type) for v in vartype]):
            raise TypeError("Sequence in the first argument must contain only types")
        
        if isinstance(vartype, list):
            vatrtype = tuple(vartype)
        
    if ws is None:
        ws = user_workspace()
    if ws is None:
        raise ValueError("No valid workspace has been specified or found")
        
    return dict((name, val) for (name, val) in ws.items() if isinstance(val, vartype) and not name.startswith("_"))
    #lst=[(name, val) for (name, val) in ws.items() if (any([isinstance(val, v_type) for v_type in vartype]) and not name.startswith("_"))]
    
    #return dict(lst)
        
def getvars(*args, glob:bool=True, ws:typing.Union[dict, type(None)]=None, 
            var_type:typing.Union[type, type(None), typing.Tuple[type], typing.List[type]]=None,
            as_dict:bool=False, sort:bool= False, sortkey:object=None, reverse:bool = False) -> object:
    """Collects a subset of variabes from a workspace or a dictionary.

    Returns a (possibly sorted) list of the variables if found, or an empty list.
    
    Var-positional parameters:
    ==========================
    *args: selection criterion. This may be: 
        1) a string or a sequence of strings, each containing either a shell-type
            "glob" expression, or a regular expression (a "regexp", see python's 
            re module for help about regexps).
            
            For example, to select variables with names beginning with "data",
            the selection string may be either
            
            "data*" (a shell-type glob) or "^data*" (a regexp string)
            
            Whether the sele tion string is interpreted as a glob or a regexp
            depends on the value of the "glob" parameter (see below).
        
        2) a type, or an iterable (list, tuple) of types
        
            This allows to select all ws variables of the type(s) specified in 'sel'
            
    Named parameters:
    =================
    glob: bool, default is True
    
        When True, the selection strings in args are treated these as UNIX 
            shell-type globs.
            
        Otherwise, they are treated as regular expression strings.
    
    ws : a dictionary or None (default).
    
        When a dict, its keys must all be strings, and represents the namespace
        where the variables are searched.
        
            This can be:
            a) a global namespace as returned by globals(),
            b) a local namespace as returned by locals(), or vars()
            c) an object's namespace as returned by vars([object]);
                this is technically the __dict__ attribute of the object
            
        When None, the function searches inside the user namespace. This is a
        reference to the console kernel's namespace and is the same as the 
        "workspace" attribute of Scipyen's main window. In turn, Scipyen
        main window is referenced as the "mainWindow" variable in the console 
        namespace.
        
    var_type: a type, a sequence of types, or None (default)
        When a type, only select the variables of the indicated type
        
    as_dict: bool, default False.
    
        When True, returns an ordered dict with objects stored by their names in
        the search namespace, sorted alphabetically;
        
        Whe False (the default) the function return a list of objects.
        
    sort:bool, default is False
        Sort the variables according to their name (by default) or by sortkey
        
    sortkey:None or an objetc that is valid as a sort key for list sorting
        (see list.sorted() or sort() python functions)
        
    reverse:bool, default is False.
        When sort is True, the data is sorted in reverse order. Otherwise, this 
        is ignored.
    
            
    Returns:
    ========
    a list or a dict.
        The list is sorted by the variable name.

    Examples:
    =========
    
    ret = getvars(some_type, ws=globals())
    
        Returns a list of all variables in the user namespace that are instances of some_type
        
    ret = getvars(list_or_tuple_of_type_objects, ws=globals())
    
        Returns a list of variables in the user namespace that are instances of any of the 
            types contained in list_or_tuple_of_type_objects
            
    ret = getvars(regexp, glob=False, ws=globals())
    
    ret = getvars(glob_pattern, glob=True, ws=globals())
        Return a list of variables in the user name space, with names that return a match 
        for the string in regexp
        
        
    ret = getvars(neo.Block, ws = locals())
    
    # useful idioms:
    
    # lst=[(name, val) for (name, val) in locals().items() if isinstance(val,neo.Block)]
    #
    #sort by variable name:
    #
    # slst = sorted(lst, key = lambda v: v[0])
    #
    #
    # check this: compare lst[0][0] with slst[0][0]
    
    NOTE: The function calls lsvars(...) to select the variables.
    
    See also: lsvars(), sorted()
            
    NOTE: The function was designed to complement the %who, %who_ls and %whos 
            IPython linemagics, which conspicuously lack the facility to filter
            their output according to variable names or types. It is NOT thread
            safe -- if the contents of the "ws" workspace are concurrently 
            modified by another thread, it may raise an exception.
            
    """
    if ws is None:
        ws = user_workspace()
        
    if ws is None:
        raise ValueError("No valid workspace has been specified or found")
        
    var_names = lsvars(*args, glob=glob, var_type=var_type, ws=ws)
    
    
    if as_dict:
        lst = [(n, ws[n]) for n in var_names]
        
        # NOTE: 2020-10-12 14:18:14
        # var_type already used in lsvars
        #if isinstance(var_type, type) or (isinstance(var_type, (tuple, list)) and all([isinstance(v, type) for v in var_type])):
            #lst = [(n, ws[n]) for n in var_names if isinstance(ws[n], var_type)]
            
        #else:
            #lst = [(n, ws[n]) for n in var_names]
        
        if sort and sortkey is not None:
            lst.sort(key=sortkey)
        
        ret = OrderedDict(lst)
        
    else:
        ret = [ws[n] for n in var_names]
        
        # NOTE: 2020-10-12 14:18:14
        # var_type already used in lsvars
        #if isinstance(var_type, type) or (isinstance(var_type, (tuple, list)) and all([isinstance(v, type) for v in var_type])):
            #ret = [ws[n] for n in var_names if isinstance(ws[n], var_type)]
            
        #else:
            #ret = [ws[n] for n in var_names]
        
        if sort and sortkey is not None:
            ret.sort(key=sortkey)
        
    return ret

    
def assignin(variable, varname, ws=None):
    """Assign variable as varname in workspace ws"""
    
    if ws is None:
        ws = user_workspace()
        
    if ws is None:
        raise ValueError("No valid workspace has been specified or found")
        
        #frame_records = inspect.getouterframes(inspect.currentframe())
        ##print(frame_records)
        #for (n,f) in enumerate(frame_records):
            #if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within Scipyen's IPython console
                #ws = f[0].f_globals["mainWindow"].workspace
                ##ws = f[0].f_globals
                #break
        
    ws[varname] = variable
    
assign = assignin # syntactic sugar

def get_symbol_in_namespace(x:typing.Any, ws:typing.Optional[dict] = None) -> list:
    """Returns a list of symbols to which 'x' is bound in the namespace 'ws'
    
    The  list is empty when the variable 'x' does not exist in ws (e.g when it is
    dynamically created by an expression).
    
    WARNING The same variable may be bound to more than one symbol.
    
    Parameters:
    ----------
    x : a Python object of any type
    ws: dict (optional default is None)
        When None, the functions looks up the variable in the user's "lobal" namespace
    """
    if ws is None:
        ws = user_workspace()
        
    elif not isinstance(ws, dict):
        raise TypeError("'ws' expected ot be a dict; got %s instead" % type(ws).__name__)
        
    return [k for k in ws if ws[k] is x and not k.startswith("_")]

def user_workspace() -> dict:
    """Returns a reference to the user workspace (a.k.a user namespace)
    """
    frame_records = inspect.getouterframes(inspect.currentframe())
    for (n,f) in enumerate(frame_records):
        if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within Scipyen's IPython console
            return f[0].f_globals["mainWindow"].workspace
        
def scipyentopdir() -> str:
    user_ns = user_workspace()
    return user_ns["mainWindow"]._scipyendir_

def delvars(*args, glob=True, ws=None):
    """Delete variable named in *args from workspace ws
    CAUTION 
    """
    if ws is None:
        ws = user_workspace()
        
    if ws is None:
        raise ValueError("No valid workspace has been specified or found")
        
        #frame_records = inspect.getouterframes(inspect.currentframe())
        #for (n,f) in enumerate(frame_records):
            #if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within the IPython console
                #ws = f[0].f_globals["mainWindow"].workspace
                #break
    
    #print(args)
    
    if len(args) == 0:
        raise ValueError("empty argument list")
    
    if len(args) == 1:
        item = args[0]
        
        if item is None:
            raise TypeError("can't delete None object")
        
        if isinstance(item, str):
            if len(item.strip()) == 0:
                # NOTE: 2019-09-06 22:44:08
                # item may itself be a str variable which is empty
                targets = [(k, v) for k,v in ws.items() if v is item]
                
                if len(targets) == 0: 
                    raise NameError("can't delete an empty identifier")
                
                for t in targets:
                    ws.pop(t[0], None)
                    
                #raise ValueError("can't delete an empty identifier")
            else:
                varlist = lsvars(item, glob=glob, ws=ws)
            
                if len(varlist) == 0:
                    # see NOTE: 2019-09-06 22:44:08
                    targets = [(k, v) for k,v in ws.items() if v is item]
                    
                    if len(targets) == 0: 
                        raise NameError("there are no variables with names defined by this pattern: %s" % item)
                        #raise NameError("can't delete an empty identifier")
                    
                    for t in targets:
                        ws.pop(t[0], None)
                    
                else:
                    for v in varlist:
                        ws.pop(v, None)
                
        elif isinstance(item, type) or (isinstance(item, (list, tuple)) and all([isinstance(k, type) for k in item])):
            varlist = lsvars(item, ws=ws)
            if len(varlist) == 0:
                raise TypeError("there are no variables with type(s) %s" % item)
            
            for v in varlist:
                ws.pop(v, None)
                
        elif args[0] is not None:
            targets = [(k, v) for k,v in ws.items() if v is args[0]]
            # NOTE: 2019-09-06 22:32:34
            # this won't happen because passing unbound name to this function
            # will raise NameError anyway
            #if len(targets) == 0: 
                #raise NameError("specified variables are not defined")
            
            for t in targets:
                ws.pop(t[0], None)
                
    else:
        for item in args:
            if isinstance(item, (str, type)):
                varlist = lsvars(item, glob=glob, ws=ws)

                if len(varlist) == 0:
                    # see NOTE: 2019-09-06 22:44:08
                    targets = [(k, v) for k,v in ws.items() if v is item]
                    
                    if len(targets) == 0: 
                        raise NameError("there are no variables with names defined by this pattern: %s" % item)
                        #raise NameError("can't delete an empty identifier")
                    
                    for t in targets:
                        ws.pop(t[0], None)
                    
                    #raise NameError("there are no variables with name pattern %s" % item)
                else:
                    for v in varlist:
                        ws.pop(v, None)
                    
                
            elif (isinstance(item, (list, tuple)) and all([isinstance(k, type) for k in item])):
                varlist = lsvars(item, glob=glob, ws=ws)

                if len(varlist) == 0:
                    # see NOTE: 2019-09-06 22:44:08
                    targets = [(k, v) for k,v in ws.items() if v is item]
                    
                    if len(targets) == 0: 
                        raise NameError("there are no variables with names defined by this pattern: %s" % item)
                        #raise NameError("can't delete an empty identifier")
                    
                    for t in targets:
                        ws.pop(t[0], None)
                    
                    #raise TypeError("there are no variables with type %s" % item)
                else:
                    for v in varlist:
                        ws.pop(v, None)
                    
            elif item is not None:
                targets = [(k, v) for k,v in ws.items() if v is item]
                # see NOTE: 2019-09-06 22:32:34
                #if len(targets) == 0:
                    #raise ValueError("specified variables are not defined")
                
                for t in targets:
                    ws.pop(t[0], None)
                        
                    
def validate_varname(arg, ws=None):
    """Converts a putative variable name "arg" into a valid one.
    
    arg: a string
    ws: a namespace (dict), default None => will search for the topmost workspace
    
    1)  Non-valid characters are replaced with underscores.
    
    2)  If "arg" begins with a digit or is a standard python language keyword, 
        it will be prefixed with "variable_".
    3)  If "arg" already exists in the "ws" dictionary (e.g. a workspace/namespace)
        then it will be suffixed with "_counter" where counter starts at 1 and 
        carries on; 
        
        3.a) if there is already a variable with this suffix, it will be incremented
            as necessary
    
    Returns:
    
    a modified variable name
    
    """
    from core.utilities import counter_suffix
    
    if ws is None:
        frame_records = inspect.getouterframes(inspect.currentframe())
        for (n,f) in enumerate(frame_records):
            if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within the IPython console
                ws = f[0].f_globals["mainWindow"].workspace
                break
    if not isinstance(arg, str) or len(arg.strip()) == 0:
        arg = "data"
    # check if arg is a valid python variable identifier; replace non-valid characters with 
    # "_" (underscore) and prepend "data_" if it starts with a digit
    if not arg.isidentifier():
        arg = _re.sub("^(?=\d)","data_", _re.sub("\W", "_", arg))
        
    # avoid arg being a valid python language keyword
    if keyword.iskeyword(arg):
        arg = "data_" + arg
        
    arg = counter_suffix(arg, ws.keys())
        
    #if arg in ws.keys():
        #while arg in ws.keys():
            #m = _re.search("_(\d+)$", arg)
            #if m:
                #count = int(m.group(0).split("_")[1]) + 1
                #arg = _re.sub("_(\d+)$", "_%d" % count, arg)
                
            #else:
                #arg += "_01"
        
            ##print("validate_varname: new name: %s", arg)
                
            
    return arg
    
