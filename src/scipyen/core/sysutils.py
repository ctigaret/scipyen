# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""System and platform utilities
NOTE: This does NOT relate to the standard library's ``sys`` module.
"""
import os, sys, subprocess, shutil, platform, pathlib, typing, types
from shutil import which
import importlib
from core.prog import print_styled

def adapt_ui_path(module_path, uifile):
    return os.path.join(module_path, uifile)

def getUnbuiltVersion(path:pathlib.Path) -> str:
    proc = subprocess.run([sys.executable, "-m", "setuptools_scm"], capture_output=True, cwd=path.as_posix())
    if proc.returncode == 0:
        return proc.stdout.decode().replace("\n", "")

def checkGitRepo(path:pathlib.Path, label:str = "Scipyen", verb:typing.Optional[str]=None) -> bool:
    if not isinstance(verb,str) or len(verb.strip()) == 0:
        verb = "Running"
        
    gitTest = subprocess.run(["git", "-C", path.as_posix(), "status", "--short", "--branch"], capture_output=True)

    if gitTest.returncode == 0:
        result = gitTest.stdout.decode().split("\n")
        brComp = result[0]
        head, branches = brComp.split("## ")
        local, remote = branches.split("...")
        local = print_styled(local, color="green")
        remote = print_styled(remote, color="red")
        msg = f"{print_styled('WARNING:', color='yellow')} {verb} {local} branch of the local {label} git repository in {print_styled(path.as_posix(), color='blue')}, with status:"
        result[0] = "## "+local+"..."+remote
        if len(result) > 1:
            for k in range(1,len(result)):
                s = result[k]
                head = print_styled(s[:2], color="red")
                fileName = s[2:]
                result[k] = head+fileName

        result.insert(0, msg)
        print("\n".join(result))
        return True
    
    return False
    
class _SuperLazyModule(types.ModuleType):
    
    def __getattribute__(self, attr):
        """Trigger the load of the module and return the attribute."""
        __spec__ = object.__getattribute__(self, '__spec__')
        loader_state = __spec__.loader_state
        with loader_state['lock']:
            # Only the first thread to get the lock should trigger the load
            # and reset the module's class. The rest can now getattr().
            if object.__getattribute__(self, '__class__') is _SuperLazyModule:
                __class__ = loader_state['__class__']

                # Reentrant calls from the same thread must be allowed to proceed without
                # triggering the load again.
                # exec_module() and self-referential imports are the primary ways this can
                # happen, but in any case we must return something to avoid deadlock.
                if loader_state['is_loading']:
                    return __class__.__getattribute__(self, attr)
                loader_state['is_loading'] = True

                __dict__ = __class__.__getattribute__(self, '__dict__')

                # All module metadata must be gathered from __spec__ in order to avoid
                # using mutated values.
                # Get the original name to make sure no object substitution occurred
                # in sys.modules.
                original_name = __spec__.name
                # Figure out exactly what attributes were mutated between the creation
                # of the module and now.
                attrs_then = loader_state['__dict__']
                attrs_now = __dict__
                attrs_updated = {}
                for key, value in attrs_now.items():
                    # Code that set an attribute may have kept a reference to the
                    # assigned object, making identity more important than equality.
                    if key not in attrs_then:
                        attrs_updated[key] = value
                    elif id(attrs_now[key]) != id(attrs_then[key]):
                        attrs_updated[key] = value
                        
                print(f"{self.__class__.__name__}.__getattribute__(attr={attr}): __spec__.loader: {__spec__.loader}  ")
                __spec__.loader.exec_module(self)
                # If exec_module() was used directly there is no guarantee the module
                # object was put into sys.modules.
                # # # # if original_name in sys.modules:
                # # # #     if id(self) != id(sys.modules[original_name]):
                # # # #         raise ValueError(f"module object for {original_name!r} "
                # # # #                           "substituted in sys.modules during a lazy "
                # # # #                           "load")
                # Update after loading since that's what would happen in an eager
                # loading situation.
                __dict__.update(attrs_updated)
                # Finally, stop triggering this method, if the module did not
                # already update its own __class__.
                if isinstance(self, _SuperLazyModule):
                    object.__setattr__(self, '__class__', __class__)

        return getattr(self, attr)

    def __delattr__(self, attr):
        """Trigger the load and then perform the deletion."""
        # To trigger the load and raise an exception if the attribute
        # doesn't exist.
        self.__getattribute__(attr)
        delattr(self, attr)

class SuperLazyLoader(importlib.util.Loader):
    @staticmethod
    def __check_eager_loader(loader):
        if not hasattr(loader, 'exec_module'):
            raise TypeError('loader must define exec_module()')

    @classmethod
    def factory(cls, loader):
        """Construct a callable which returns the eager loader made lazy."""
        cls.__check_eager_loader(loader)
        return lambda *args, **kwargs: cls(loader(*args, **kwargs))

    def __init__(self, loader):
        self.__check_eager_loader(loader)
        self.loader = loader

    def create_module(self, spec):
        return self.loader.create_module(spec)

    def exec_module(self, module):
        """Make the module load lazily."""
        # Threading is only needed for lazy loading, and importlib.util can
        # be pulled in at interpreter startup, so defer until needed.
        import threading
        module.__spec__.loader = self.loader
        module.__loader__ = self.loader
        # Don't need to worry about deep-copying as trying to set an attribute
        # on an object would have triggered the load,
        # e.g. ``module.__spec__.loader = None`` would trigger a load from
        # trying to access module.__spec__.
        loader_state = {}
        loader_state['__dict__'] = module.__dict__.copy()
        loader_state['__class__'] = module.__class__
        loader_state['lock'] = threading.RLock()
        loader_state['is_loading'] = False
        module.__spec__.loader_state = loader_state
        module.__class__ = _SuperLazyModule
    
