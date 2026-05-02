# -*- coding: utf-8 -*-
# $Id: historymodel.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

mport gc
import contextlib
import itertools
import seaborn as sb
import numpy as np
import matplotlib as mpl
import matplotlib.mlab as mlb
import matplotlib.pyplot as plt
from matplotlib._pylab_helpers import Gcf as Gcf
import traceback
import typing
import inspect
import os
import asyncio
import warnings
from copy import deepcopy
from functools import partial
from collections import deque
import json

from traitlets import Bunch

from gui.guiutils import (get_text_width, get_elided_text)
from gui import pictgui as pgui
from core.traitcontainers import DataBag
from core.utilities import (summarize_object_properties,
                            standard_obj_summary_headers,
                            safe_identity_test,
                            reverse_mapping_lookup,
                            )
from core.strutils import (is_cached_output_varname, is_cached_input_varname)

from core.prog import (safewrapper, timefunc, processtimefunc, timeblock, print_styled)
from core.typeenum import TypeEnum
# from jupyter_core.paths import jupyter_runtime_dir

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

class HistoryModel(QtGui.QStandardItemModel):
    # TODO: 2026-05-02 15:48:07 finalize me
    def __init__(self, parent=None):
        super().__init__(0,2,parent)
        self._history_ = dict[str, str]()
