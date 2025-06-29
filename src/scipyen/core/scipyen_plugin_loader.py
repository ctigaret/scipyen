# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r''' Mon Apr 04 2016 23:41:53 GMT+0100 (BST)

    Searches for python module source files declared as plugins and loads them. 
    
    The search is executed inside scipyen's directory.
    
    Scipyen plugins provide code (module-level functions) that can also to be 
    via the graphical user interface e.g. menu actions in Scipyen main window.
    
    This approach is useful for extending Scipyen's GUI functionality dyamically,
    without actually editing the GUI code of the ScipyenWindow class (defined in 
    the gui.mainwindow module)


    While the plugin module may define an arbitrary number of functions, a subset
    of these may be useful as "callbacks" to be run interactively from menu items
    in the main windos of Scipyen.
    
    For the purpose of flexibility, the rules to define a module as a "plugin"
    are quite simple.
    
    A Scipyen plugin is any python module that satisfies at least one of the 
    conditions below:
    
    𝟏) contains an attribute `__scipyen_plugin__` (with ANY value)

    𝟐) defines a function named `init_scipyen_plugin` that takes no arguments 
    and returns either:
    
        • a mapping (dict-like) of menu path string ↦ module-level function or
            sequence of module-level functions (all defined in the plugin module)
        
            Menu paths are given as strings of the form:
            
            "Top menu|submenu|sub-submenu|item_or_submenu"
            See ScipyenWindow.installPluginMenu() docstring for details.
        
        • a module-level function or a sequence of module-level functions, all 
            defined in the plugin module.
        
    𝟑) 
    
    
        
    
    The following table illustrates this with some examples:
        
Key:                                Mapped to:          Result:
--------------------------------------------------------------------------------------------
"Menuitem"                          One function        A menu item that calls the plugin 
                                                        function will be created directly
                                                        in the Menu bar of the GUI.

                                    Several functions   "Menuitem" is a top-level menu with 
                                                        each function called by its own 
                                                        menu item named after it.

"Menu|Menuitem"                     One function        A menu item that calls the plugin 
                                                        function is created in a top-level 
                                                        menu.

                                    Several functions   "Menuitem" is a submenu of a top-level
                                                        "Menu" menu with each function
                                                        called by its own menu item named after
                                                        it.

"Menu|Submenu|Menuitem"             One function        A menu item that calls the plugin 
                                                        function is created in a submenu of 
                                                        a top-level menu.

                                    Several functions   "Menuitem" is a submenu of "Submenu"
                                                        and each function is called by its
                                                        own menu item named after it.

"Menu|Submenu|Subsubmenu|Menuitem"  One function        A menu item that calls the plugin 
                                                        function is created in a 2nd level
                                                        submenu.
                                                        
                                    Several functions   As in the previous example.

""                                  One function        A menu item named after the plugin
                                                        function placed in a submenu named
                                                        after the plugin module, inside 
                                                        a "Plugins" top-level menu.
                                    
                                    Several functions   A submenu named after the plugin module,
                                                        inside a "Plugins" top-level menu;
                                                        each function called by a menu item named
                                                        after it.
    
---------------------------------------------------------------------------------------------

        NOTE: The menu items can be nested at any depth level in the menu tree.
        In other words, there can be any number of Submenus defined in the menu 
        path string.

    This approach allows the dynamic generation of GUI dialogs prompting for 
    argument values and for the names of the return variables that will be 
    created in the pict workspace.
    
    -------------------------------------------------------------------------
        
    A plugin module can also be imported directly in other modules. However this
    will NOT result is the plugin installing GUI menu items in Scipyen's main 
    window.
    
    Furthermore, a plugin module can import any other Scipyen modules PROVIDED
    that the import statements are given in absolute import mode (i.e., no
    relative import statements are supported).
    
    -------------------------------------------------------------------------
        
'''
# ### BEGIN
# TODO, FIXME (some already fixed?):
# 
#     Make it easy to introspect the plugin function code so that the number of 
#     return variables, and possibly, the argument types for positional parameters
#     could be deduced directly from the function object.
# 
#     This would simplify init_scipyen_plugin() function -- no need for nested 
#     dictionary but just a simple dictionary mapping a menu path to a function 
#     object.
# 
#     Porting to Python 3 should make it easier to introspect the function code
#     these things easier as there is already a ystem in place for function 
#     annotations and inspection of return variables in the function signature.
# 
# NOTE: 2016-04-17 16:53:00
# 
#     Implemented by using function annotations.
#     
#     See PEP 3107 -- Function Annotations and http://python-future.org/func_annotations.html
#     
#     for details.
#         
#     Although function annotations are optional in python they are useful for 
#     porting code later to Python 3.
#     
#     In python 2.7 use the funcsigs module (https://pypi.python.org/pypi/funcsigs).
#         
# 
#     Here are a few examples, see also example_plugin.py in this directory.
#     
#     Example 1. function signature with 0 arguments and no return (i.e. returns
#     None)
#     
#     def f1():
#         ... some code ...
#         
#     The mapping for f1 should be {f1:(None, None)}  or  {f1:(0, None)}
#     
#     Example 2. function takes 0 arguments and returns one variable
# 
#     def f2():
#         a = ... some computation ...
#         return a
#         
#     The mapping describing f2 signature should be {f2:[1, None]}
# 
# 
#     Example 3. function takes 0 arguments and returns 2 variables -- note 
#         that the return variables are packd as a tuple in python.
#     
#     def f3():
#         a = ... some computation ...
#         b = ... some more computation ..
#         return a,b 
#         
#     The mapping should be {f3:(2, None)}
# 
#     Example 4. function takes 1 string argument and returns 2 variables.
#     
#     def f4(arg):
#         file = open(arg)
#         data = ... read some data from the file name given in arg ...
#         metadata = ... do something with data or some more / different data from the file ...
#         file.close()
#         return data, metadata
#         
#     The mapping should be {f3:(2, str)}
# 
#     Example 5. function takes 2 positional arguments, one with a default value,
#     and returns 3 variables.
#     
#     def f5(arg0, arg1 = 1.0):
#         file = open(arg)
#         data = ... read some data from the file name given in arg ...
#         file.close()
#         
#         a = data * arg1
#         b = ... perform some computation ...
#         c = ... perform some more computation ...
#         return data, metadata
#         
#     The mapping should be {f5:(3, (str, float))}
#     
#     def f7(arg1, arg2='default value for arg2', arg3=44, *args, **kwargs):
#         return arg1, arg2
# 
#     # set function attributes here, as a dict:
#     # NOTE: this is vulnerable to injecting bad values there, but appripriate exceptions
#     # will be raise by the plugin loading code in pict
#     
#     f7.__setattr__('__annotations__',{'return':'a+b', 'arg1':int, 'arg2':str, 'arg3':int})
#     
#     The mapping returned by init_scipyen_plugin() should be:
#     
#     'Example Plugin|Plugin|Annotated function', f7
#     
#     Caveats: 
#     1) the plugin info should be resolved in unique menu paths but this is 
#     not enforced (it is up to the plugin installer code to deal with name clashes)
#     
# 
# ### END

from __future__ import print_function

# FIXME 2016-04-03 00:35:17
# if the plugin advertises itself on an already used menu item and with a similar callback function
# the previosuly loaded plugin will be overwritten !!!

import os, inspect, importlib, sys, traceback
import types, typing, pathlib
import collections, functools, itertools 
from pprint import pprint
# import os, inspect, imp, sys, collections
from core import prog, sysutils

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

loaded_plugins = collections.OrderedDict()

pluginsSpecFinder = prog.SpecFinder({})
# sys.meta_path.append(pluginsSpecFinder)

plugin_source_files = list()
user_plugin_source_files = list()

# __avoid_modules__ = ("scipyen_start", "scipyen_plugin_loader")

def check_plugin_module(file_name) -> bool:
    with open(file_name, "rt", encoding="utf-8") as module_file:
        for line in module_file:
            if line.startswith('__scipyen_plugin__') or line.startswith("def init_scipyen_plugin"):
                return True
            
    return False

# def find_frozen():
#     r"""Locates plugin modules packaged with pyinstaller (i.e., 'frozen')
#     """
#     # this should be run AFTER all relevant modules have been loaded
#     # and BEFORE find_plugins(…) is called
#     plugin_modules = [sys.modules[n] for n in sys.modules if (hasattr(sys.modules[n], "__scipyen_plugin__") or hasattr(sys.modules[n], "init_scipyen_plugin"))]
#     for module in plugin_modules:
#         if isinstance(module, types.ModuleType): # this is guaranteed, no?
#             reloaded_module = importlib.reload(module)
#             loaded_plugins[module.__name__] = module

def find_bytecode_plugins(path:typing.Union[str, pathlib.Path], scipyendir:typing.Union[str,pathlib.Path]):
    r"""Intended to collect bytecode plugins by pyinstaller
    """
    import dis, marshal
    if isinstance(path, pathlib.Path) and path.is_dir() and path.exists():
        path = str(path.absolute())
        
    elif not isinstance(path, str) or len(path.strip()) == 0 or not os.path.isdir(path) or not os.path.exists(path):
        prog.scipywarn(f"Expecting a string or a pathlib.Path for an absolute pathway to an existing directory; instead got {path} ")
        return
    
    if isinstance(scipyendir, pathlib.Path) and scipyendir.is_dir() and scipyendir.exists():
        scipyendir = scipyendir.absolue()
        
    elif isinstance(scipyendir, str) and len(scipyendir.strip()) and os.path.isdir(scipyendir) and os.path.exists(scipyendir):
        scipyendir = pathlib.Path(scipyendir)
        
    else:
        prog.scipywarn(f"Invalid scipyendir parameter: {scipyendir} ")
        return
    
    topdir = pathlib.Path(path)
    
    plugin_bytecode_files = list(map(lambda x: pathlib.Path(x), list(filter(lambda x: os.path.splitext(x)[-1] in importlib.machinery.BYTECODE_SUFFIXES and check_plugin_module(x), list(itertools.chain.from_iterable( (os.path.join(e[0], i) for i in e[2]) for e in os.walk(path)))))))

    # these are modules, by definition?
    
    for file_name in plugin_bytecode_files:
        verb=False
        # see https://mathspp.com/blog/til/read-bytecode-from-a-pyc-file
        with open(file_name, "rb") as pycfile:
            _ = pycfile.read(16) # Header is 16 bytes in 3.6+, 8 bytes on < 3.6
            loaded = marshal.load(pycfile)
            
        code_info = list(filter(lambda x: any(v in x for v in ("__scipyen_plugin__",  "init_scipyen_plugin")), dis.code_info(loaded).split("\n")))
        if len(code_info) == 0:
            continue
        
        module_name = file_name.split('.')[0] # heuristic - is that OK? # FIXME 2024-05-31 16:14:34
        pluginsSpecFinder.path_map[module_name] = file_name
        file_directory = file_name.parent.relative_to(topdir)
        if len(file_directory.parts):
            package_name = '.'.join(file_directory.parts)
            
            submodules_paths = list()
            p = file_name.relative_to(topdir)
            while len(p.parts):
                p = p.parent
                if len(p.parts):
                    submodules_paths.append(topdir.joinpath(p))
            if file_name.name == "__init__.py":
                module_name = package_name
            else:
                module_name = f"{package_name_path}.{module_name}" # NOTE: 2024-05-30 13:09:48 this is CRUCIAL
            
            module_spec = importlib.util.spec_from_file_location(module_name, file_name, 
                                                                    submodule_search_locations = submodules_paths)
        else:               
            module_spec = importlib.util.spec_from_file_location(module_name, file_name)
            
    check_load_module(module_spec, verb)

def find_plugins(path:typing.Union[str, pathlib.Path], 
                 scipyendir:typing.Union[str,pathlib.Path], 
                 checkgit:bool=False):
    r"""Loads and located plugins in a directory tree rooted at `path`
    """
    # ### BEGIN check call parameters
    if isinstance(path, pathlib.Path) and path.is_dir() and path.exists():
        path = path.absolute()
        
    elif not isinstance(path, str) or len(path.strip()) == 0 or not os.path.isdir(path) or not os.path.exists(path):
        prog.scipywarn(f"Expecting a string or a pathlib.Path for an absolute pathway to an existing directory; instead got {path} ")
        return
    
    if isinstance(scipyendir, pathlib.Path) and scipyendir.is_dir() and scipyendir.exists():
        scipyendir = scipyendir.absolute()
        
    elif isinstance(scipyendir, str) and len(scipyendir.strip()) and os.path.isdir(scipyendir) and os.path.exists(scipyendir):
        scipyendir = pathlib.Path(scipyendir).absolute()
        
    else:
        prog.scipywarn(f"Invalid scipyendir parameter: {scipyendir} ")
        return
    # ### END   check call parameters
    
    # NOTE: 2024-05-30 11:33:28
    # a better? version of the code after NOTE: 2023-06-28 21:13:30
    
    topdir = pathlib.Path(path).absolute()
    
    if topdir.as_posix() not in sys.path:
        sys.path.append(topdir.as_posix())
    
    if checkgit:
        sysutils.checkGitRepo(topdir, "Scipyen plugins", "Using plugins in the")
    # print(f"scipyen_plugin_loader.find_plugins: topdir = {topdir}")
    
    plugin_source_files[:] = list(map(lambda x: pathlib.Path(x).absolute(), list(filter(lambda x: os.path.splitext(x)[-1] in importlib.machinery.SOURCE_SUFFIXES and check_plugin_module(x), list(itertools.chain.from_iterable( (os.path.join(e[0], i) for i in e[2]) for e in os.walk(topdir)))))))
    
    # print(f"find_plugins: plugin_source_files = {plugin_source_files}\n")
    
    user_plugin_source_files[:] = list(filter(lambda x: not x.is_relative_to(scipyendir), plugin_source_files))
    # print(f"find_plugins: user_plugin_source_files = {user_plugin_source_files}\n")
    
    modules = list()
    
    for file_name in plugin_source_files:
        if file_name in user_plugin_source_files:
            assert file_name.is_relative_to(topdir), f"The plugin source file {file_name} is not present in {topdir} or any of its subdirectories"
            ndx = file_name.parents.index(topdir)
            package_dotted_path = '.'.join(tuple(map(lambda p: p.stem, reversed(file_name.parents[:ndx]))))
            module = import_module(file_name, package_dotted_path)
        else:
            module = import_module(file_name)
            
        modules.append(module)
        
        for m in modules:
            load_module(m)

def import_module(file_name: pathlib.Path, package:typing.Optional[str] = None):
    module_name = file_name.stem
    parent_path_str = file_name.parent.as_posix()
    if parent_path_str not in sys.path:
        sys.path.append(parent_path_str)
    module = importlib.import_module(module_name, package)
    return check_load_module(module.__spec__)
    
def load_module(module:[types.ModuleType, prog.ModSpec], alias:typing.Optional[str] = None):
    loadedmodule = prog.get_loaded_module(module)
    if inspect.ismodule(loadedmodule): # alternative: if isinstance(loadedmodule, types.ModuleType):
        if inspect.ismodule(module):
            assert loadedmodule == module, f"Mismatch between {loadedmodule} and {module}"
            
        try:
            reloaded_module = importlib.reload(loadedmodule) # CAUTION ``module`` may in fact be a spec
        except:
            traceback.print_exc()
            
        loaded_plugins[module.__name__] = module
            
    else:
        try:
            if isinstance(module, prog.ModSpec): # ``module`` is in fact a module spec
                spec = module
                module = importlib.util.module_from_spec(spec)
                if not hasattr(module, "__spec__"):
                    setattr(module, "__spec__", spec)
                # NOTE: 2025-03-18 23:00:46 see NOTE: 2025-03-18 22:59:47
                setattr(module, "__pluginspec__", spec)
                    
            elif inspect.ismodule(module):
                spec = module.__spec__
                
            else:
                raise TypeError(f"Expecting a module or a module spec; instead, got a {type(module).__name__}")
            
            spec.loader.exec_module(module)
            sys.modules[spec.name] = module
            loaded_plugins[spec.name] = module
            if isinstance(alias, str) and len(alias.strip()) and alias.isidentifier():
                sys.modules[alias] = module
                loaded_plugins[alias] = module
                
        except:
            traceback.print_exc()
        

def get_module(file_name:pathlib.Path, topdir: typing.Optional[pathlib.Path]=None,
               is_user_plugin:bool=True, alias:typing.Optional[str] = None) -> types.ModuleType:
    r"""DEPRECATED """
    if is_user_plugin:
        print(f"scipyen_plugin_loader.get_module for user plugin(\n\tfile_name = {file_name},\n\ttopdir = {topdir},\n\talias = {alias})")
    module_name = inspect.getmodulename(file_name)
    if module_name is not None: # this will never be None, would it?
        if is_user_plugin:
            print(f"\tmodule_name: {module_name}\n")
        verb = False
        pluginsSpecFinder.path_map[module_name] = file_name.as_posix()
        # if file_name in user_plugin_source_files:
        if is_user_plugin:
            assert(file_name.is_relative_to(topdir)), f"Plugin file {file_name} is not located in {topdir}"
            package_module_path = module_name.split('.')
            module_name = package_module_path[-1]
            if len(package_module_path) > 1:
                # topdir_parts = topdir.parts
                parents = package_module_path[:-1]
                file_directory = pathlib.Path(*parents)#.relative_to(topdir)
            else:
                file_directory = file_name.parent
            print(f"\tfile_directory: {file_directory}\n")
            submodules_paths = list()
            if isinstance(file_directory, pathlib.Path) and file_directory.exists() and file_directory.is_dir() and len(file_directory.parts):
                parent_package_names = list()
                if file_directory != topdir:
                    ndx = file_name.parents.index(topdir)
                    parent_dirs_below_topdir = file_name.parents[:,ndx]
                    for p in parent_dirs_below_topdir:
                        parent_package_names.append(p.name)
                        
                    
                # package_name_path = ".".join(file_directory.parts)
                p = file_name.relative_to(topdir)
                while len(p.parts):
                    p = p.parent
                    if len(p.parts):
                        submodules_paths.append(topdir.joinpath(p))
                if file_name.name == "__init__.py":
                    module_name = package_name
                else:
                    module_name = f"{package_name_path}.{module_name}" # NOTE: 2024-05-30 13:09:48 this is CRUCIAL
                
            #     module_spec = importlib.util.spec_from_file_location(module_name, file_name, 
            #                                                             submodule_search_locations = submodules_paths)
            # else:
            #     module_spec = importlib.util.spec_from_file_location(module_name, file_name)
            # print(f"\tsubmodules_paths: {submodules_paths}\n")
            module_spec = importlib.util.spec_from_file_location(module_name, file_name, 
                                                                    submodule_search_locations = submodules_paths)
        else:
            module_spec = importlib.util.spec_from_file_location(module_name, file_name)
            
        return check_load_module(module_spec, verb, alias, True)
    

def check_load_module(spec, verb:bool=False, 
                      alias:typing.Optional[str] = None, 
                      register:bool=True) -> types.ModuleType:
    if verb:
        print(f"check_load_module: spec = {spec}")
        
    module = prog.get_loaded_module(spec)
    
    # print(f"check_load_module get_loaded_module module {module}")
    if isinstance(module, types.ModuleType): # module found, no beef here
        try:
            reloaded_module = importlib.reload(module) # reload plugin to reflect changes
        except:
            traceback.print_exc()
        if register:
            loaded_plugins[module.__name__] = module
            
        return module
        
    else: # module not found ⇒ create and load module
        try:
            module = importlib.util.module_from_spec(spec)
            name = spec.name
            parent_name = name.rpartition('.')[0]
            sys.modules[spec.name] = module
            if isinstance(alias, str) and len(alias.strip()) and alias.isidentifier():
                sys.modules[alias] = module
            # else:
            #     sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            if register:
                if isinstance(alias, str) and len(alias.strip() and alias.isidentifier()):
                    loaded_plugins[alias] = module
                else:
                    loaded_plugins[spec.name] = module
            setattr(module, "__spec__", spec)
            # NOTE: 2025-03-18 23:00:46 see NOTE: 2025-03-18 22:59:47
            setattr(module, "__pluginspec__", spec)
            
            return module
        except:
            traceback.print_exc()
            

def reload_plugin(obj:types.ModuleType) -> types.ModuleType:
    r""" DEPRECATED """
    # BUG: 2025-05-02 23:40:19 FIXME
    # upon reloading, class definitions get re-executed and places at memory
    # address distinct from their original (ie they get new ID) which makes 
    # statements line isinstance(x, Y) fail after reloading even though successful
    # after the first import of the module and Y.__name__ is the same!
    try:
        spec = importlib.util.find_spec(obj.__name__)
        print(f"reload_plugin: spec found by importlib = {spec}")
    except:
        # NOTE: 2025-03-18 22:59:47
        # I dont't quite understand why __spec__ is re-set to None; compensating
        # by using the cached __pluginspec__ attribute
        spec = getattr(obj, "__spec__", None)
        if spec is None:
            spec = getattr(obj, "__pluginspec__", None)
            if spec is None:
                raise
            else:
                setattr(obj, "__spec__", spec)
                
    print(f"reload_plugin: spec = {spec}")
    spec.loader.exec_module(obj) # I think this is the culprit, but there has to be a way to spot differences between old & new versions and replace only what has changed
    sys.modules[spec.name] = obj
    loaded_plugins[spec.name] = obj
    return obj


def reload(obj:types.ModuleType) -> types.ModuleType:
    r""" DEPRECATED """
    try:
        return importlib.reload(obj)
    except:
        return reload_plugin(obj)
    
    
