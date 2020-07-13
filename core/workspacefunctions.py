""" Various utilities for Scipyen workspace functions
All functions defined here are to be imported in the top namespace
(e.g., 'from workspacefunctions import *')

DOES NOT WORK (yet)

"""
#import pict

from __future__ import print_function
from sys import getsizeof, stderr
from itertools import chain

import re as _re # re is also imported directly from pict

import inspect, keyword, warnings

from operator import attrgetter, itemgetter, methodcaller

from collections import OrderedDict, deque

from .utilities import safeWrapper

try:
    from reprlib import repr
except ImportError:
    pass

def total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    Author:
    Raymond Hettinger
    
    Reference:
    Compute memory footprint of an object and its contents (python recipe)
    
    Raymond Hettinger python recipe 577504-1
    https://code.activestate.com/recipes/577504/
    
    """
    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)

#"def" lsvars(ws = None, sel = None, sort=False, sortkey=None, reverse=None):
#"def" lsvars(*args, ws = None, sort=False, sortkey=None, reverse=None):
def lsvars(*args, glob:bool=True, ws:[dict, type(None)]=None, 
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
        When True, the strings in args are treated as UNIC shell-style globs; 
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
    
    
    """
    from fnmatch import translate
    
    if ws is None:
        frames_list = inspect.getouterframes(inspect.currentframe())
        for (n,f) in enumerate(frames_list):
            if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within the IPython console
                ws = f[0].f_globals["mainWindow"].workspace
                #ws = f[0].f_globals
                break
    
    #if sortkey is not None:
        #sort=True
        
    #if reverse is None:
        #reverse = False
        
    #if sel is None:
        #ret = ws.keys()
        
    if len(args) == 0: # no selector arguments: get all variables names in ws
        return ws.keys()

    elif len(args) == 1: # one selector argument
        sel = args[0]
        
        if sel is None:
            return ws.keys()
            
        elif isinstance(sel, str): #select by variable name
            
            if len(sel.strip()) == 0:
                return ws.keys()
            
            p = _re.compile(translate(sel)) if glob else _re.compile(sel)
            
            var_names_filter = filter(p.match, ws.keys())
            
            return [k for k in var_names_filter] # return a list of variable names
        
        elif isinstance(sel, type) or (isinstance(sel, (list, tuple)) and all([isinstance(k, type) for k in sel])):
            # select by variable type (or types)
            return [k for (k,v) in ws.items() if sel is not type(None) and isinstance(v, sel)] # return a list of variable names
            
        else:
            raise TypeError("Unexpected type for the selector argument: got %s" % type(sel).__name__)
            
    else: # comma-separated list of selector arguments
        for (sk, sel) in enumerate(args):
            ret = list()
            
            if isinstance(sel, str):
                if len(sel.strip()):
                    
                    p = _re.compile(translate(sel)) if glob else _re.compile(sel)
                    
                    var_names_filter = filter(p.match, ws.keys())
                    
                    ret += [k for k in var_names_filter] # return a list of variable names
                    
                if len(ret) == 0:
                    return ws.keys()
            
            elif isinstance(sel, type) or (isinstance(sel, (list, tuple)) and all([isinstance(k, type) for k in sel])):
                ret += [k for (k,v) in ws.items() if isinstance(v, sel)] # return a list of variable names
                
            else:
                raise TypeError("Unexpected type for the selector argument number %d: got %s" % (sk, type(sel).__name__))
                
        return ret
    
    
    if sort:
        return sorted(ret, key=sortkey, reverse=reverse)
    
    
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
        
    else:
        vartype = [vartype]
    
    if ws is None:
        frames_list = inspect.getouterframes(inspect.currentframe())
        
        for (n,f) in enumerate(frames_list):
            if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within the IPython console
                ws = f[0].f_globals["mainWindow"].workspace
                #ws = f[0].f_globals
                break
        
    lst=[(name, val) for (name, val) in ws.items() if (any([isinstance(val, v_type) for v_type in vartype]) and not name.startswith("_"))]
    
    return dict(lst)
        
def getvars(*args, glob:bool=True, ws:[dict, type(None)]=None, as_dict:bool=False,
            sort:bool= False, sortkey:object=None, reverse:bool = False) -> object:
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
        frames_list = inspect.getouterframes(inspect.currentframe())
        for (n,f) in enumerate(frames_list):
            if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within the IPython console
                ws = f[0].f_globals["mainWindow"].workspace
                #ws = f[0].f_globals
                break
        
    var_names = lsvars(*args, glob=glob, ws=ws)
    
    
    if as_dict:
        lst = [(n, ws[n]) for n in var_names]
        
        if sort and sortkey is not None:
            lst.sort(key=sortkey)
        
        ret = OrderedDict(lst)
        
    else:
        ret = [ws[n] for n in var_names]
        
        if sort and sortkey is not None:
            ret.sort(key=sortkey)
        
    return ret

    
def assignin(variable, varname, ws=None):
    """Assign variable as varname in workspace ws"""
    
    if ws is None:
        frames_list = inspect.getouterframes(inspect.currentframe())
        #print(frames_list)
        for (n,f) in enumerate(frames_list):
            if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within Scipyen's IPython console
                ws = f[0].f_globals["mainWindow"].workspace
                #ws = f[0].f_globals
                break
        
    ws[varname] = variable
    
assign = assignin # syntactic sugar

def userWorkspace():
    """Returns a reference to the user workspace
    """
    frames_list = inspect.getouterframes(inspect.currentframe())
    for (n,f) in enumerate(frames_list):
        if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within Scipyen's IPython console
            return f[0].f_globals["mainWindow"].workspace
            #return ws
    

#@safeWrapper
def delvars(*args, glob=True, ws=None):
    """Delete variable named in *args from workspace ws
    CAUTION 
    """
    if ws is None:
        frames_list = inspect.getouterframes(inspect.currentframe())
        for (n,f) in enumerate(frames_list):
            if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within the IPython console
                ws = f[0].f_globals["mainWindow"].workspace
                break
    
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
                        
                    
def validateVarName(arg, ws=None):
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
    
    if ws is None:
        frames_list = inspect.getouterframes(inspect.currentframe())
        for (n,f) in enumerate(frames_list):
            if "mainWindow" in f[0].f_globals.keys(): # hack to find out the "global" namespace accessed from within the IPython console
                ws = f[0].f_globals["mainWindow"].workspace
                break
    
    # check if arg is a valid python variable identifier; replace non-valid characters with 
    # "_" (underscore) and prepend "variable_" if it starts with a digit
    if not arg.isidentifier():
        arg = _re.sub("^(?=\d)","variable_", _re.sub("\W", "_", arg))
        
    # avoid arg being a valid python language keyword
    if keyword.iskeyword(arg):
        arg = "variable_" + arg
        
    if arg in ws.keys():
        while arg in ws.keys():
            m = _re.search("_(\d+)$", arg)
            if m:
                count = int(m.group(0).split("_")[1]) + 1
                arg = _re.sub("_(\d+)$", "_%d" % count, arg)
                
            else:
                arg += "_01"
        
            #print("validateVarName: new name: %s", arg)
                
            
    return arg
    
