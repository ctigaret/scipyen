# -*- coding: utf-8 -*-
# $Id: help_modules.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Helper script to replate pydoc "modules" invocation
"""
import sys, os, typing
import pydoc
# from core.prog import (safewrapper, safeguiwrapper, scipwarn, print_styled)

__module_path__ = os.path.abspath(os.path.dirname(__file__))
_scipyendir_ = os.path.dirname(os.path.dirname(__module_path__))

my_conda_env = os.environ.get("CONDA_DEFAULT_ENV", None)
conda_env_prefix = os.environ.get("CONDA_PREFIX", None)

my_virtualenv = os.environ.get("VIRTUAL_ENV", None)

class ModuleScanner:
    """An interruptible scanner that searches module synopses."""

    def run(self, callback, key=None, completer=None, onerror=None):
        if key: key = key.lower()
        self.quit = False
        seen = {}

        for modname in sys.builtin_module_names:
            if modname != '__main__':
                seen[modname] = 1
                if key is None:
                    callback(None, modname, '')
                else:
                    name = __import__(modname).__doc__ or ''
                    desc = name.split('\n')[0]
                    name = modname + ' - ' + desc
                    if name.lower().find(key) >= 0:
                        callback(None, modname, desc)

        for importer, modname, ispkg in pkgutil.walk_packages(onerror=onerror):
            if self.quit:
                break

            if key is None:
                callback(None, modname, '')
            else:
                try:
                    spec = importer.find_spec(modname)
                except SyntaxError:
                    # raised by tests for bad coding cookies or BOM
                    continue
                loader = spec.loader
                if hasattr(loader, 'get_source'):
                    try:
                        source = loader.get_source(modname)
                    except Exception:
                        if onerror:
                            onerror(modname)
                        continue
                    desc = source_synopsis(io.StringIO(source)) or ''
                    if hasattr(loader, 'get_filename'):
                        path = loader.get_filename(modname)
                    else:
                        path = None
                else:
                    try:
                        module = importlib._bootstrap._load(spec)
                    except ImportError:
                        if onerror:
                            onerror(modname)
                        continue
                    desc = module.__doc__.splitlines()[0] if module.__doc__ else ''
                    path = getattr(module,'__file__',None)
                name = modname + ' - ' + desc
                if name.lower().find(key) >= 0:
                    callback(path, modname, desc)

        if completer:
            completer()

def apropos(key):
    """Print all the one-line module summaries that contain a substring."""
    def callback(path, modname, desc):
        if modname[-9:] == '.__init__':
            modname = modname[:-9] + ' (package)'
        print(modname, desc and '- ' + desc)
    def onerror(modname):
        pass
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore') # ignore problems during import
        ModuleScanner().run(callback, key, onerror=onerror)
