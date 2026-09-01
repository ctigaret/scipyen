# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# BEGIN import modules
# BEGIN core python modules
import sys
import os
import types
# import atexit
import re
import inspect
# import gc
import io
import warnings
import numbers
import decimal # noqa
import fractions # noqa
# import faulthandler
import importlib
# NOTE: 2024-09-26 12:16:28
# I wrap reload with scipyen_plugin_loader.reload, further below
# from importlib import reload  # I use this all too often !
import subprocess
import platform
import traceback
import keyword # noqa
import inspect # noqa
import weakref # noqa
import itertools
import more_itertools # NOTE: 2024-09-26 12:44:08 this is not a core python but might as well be! # noqa
import typing
import functools # noqa
import operator # noqa
import json # noqa
import pathlib
from pprint import pprint # noqa
from copy import copy # noqa
from copy import deepcopy
import collections
# from collections import deque
# from collections import ChainMap
import cmath # noqa
from tribool import Tribool # noqa
import datetime
import math

# END core python modules

# BEGIN 3rd party modules

# BEGIN PyQtxxx
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ =False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut

__has_qtdbus__ = False
try:
    from qtpy import QtDBus
    __has_qtdbus__ = True
except: # noqa
    __has_qtdbus__ = False

# BEGIN About QStyle plugins
# WARNING: 2024-09-26 15:44:57
#
# A PtQtxxx stack pulled from PyPi or conda-forge, it is likely to have a limited
# set of Qt styles available. In this case, there is nothing much that can be done.
# Simply "copying" the style libraries available on the your platform won't do,
# as this may crash Scipyen because they belong to a different build.
#
# The alternative is to build an environment locally (see install.sh) which
# WILL involve building a local PyQt wheel. Incidentally, this will also build
# the vigra libraries locally, from sources. However, this option has its limitations
# due to embedded dependencies on the host platform.
#
#
#
# END About QStyle plugins

# END PyQtxxx

# BEGIN jupyter, ipython, qtconsole et al
# from jupyter_client.session import Message
# from IPython.display import set_matplotlib_formats
from IPython.core.history import HistoryAccessor
from jupyter_core.paths import jupyter_runtime_dir
from qtconsole.svg import save_svg, svg_to_clipboard, svg_to_image # noqa
# from IPython.lib.deepreload import reload as dreload

# from IPython.core.autocall import ZMQExitAutocall

# BEGIN Configurable objects with traitlets.config
# NOTE: 2021-08-23 11:02:10
# ATTENTION do not import config directly, as it will override IPython's own
# 'config' object
import traitlets # noqa
from traitlets.utils.bunch import Bunch

# END Configurable objects with traitlets.config

# END jupyter, ipython, qtconsole et al

# BEGIN numerics & data visualization
# BEGIN data types & numerics
# NOTE: 2024-09-26 12:36:36
# vigra is imported via my own vigra_patches module
import numpy as np
import numpy.ma as ma # noqa
import pywt  # wavelets # noqa
import scipy # noqa
from scipy import io as sio # noqa
from scipy import stats # noqa
import sympy # noqa
import shapely # noqa
import neo
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList

else:
    NeoObjectList = list # alias for backward compatibility :(

import h5py # noqa
import xarray as xa # noqa
import quantities as pq
# END data types & numerics

# BEGIN statistics, plotting and visualization (other than pyqtgraph)
# NOTE: 2024-09-26 12:40:27
# ptqtgraph is imported via gui.pyqtgraph_patch

import statsmodels.api as sm # noqa
import statsmodels.formula.api as smf # noqa
import statsmodels.stats as sms # noqa
import statsmodels.regression as smr # noqa
import patsy as pt # noqa

# for DataFrame and Series
import pandas as pd

# nicer stats
import pingouin as pn  # noqa

import mpmath as mpm # noqa

#import researchpy as rp  # for use with DataFrames & stats -- not here ?!?
import joblib as jl  # to use functions as pipelines: lightweight pipelining in Python # noqa
# import sklearn as sk  # machine learning, also nice plot_* functionality
import seaborn as sb  # statistical data visualization # noqa
# print("mainwindow.py __name__ =", __name__)

# BEGIN matplotlib modules
import matplotlib as mpl
if __has_PyQt6__ or __has_PySide6__: # still doesn't seem to work properly? see NOTE: 2025-06-22 22:38:23 in ScipyenWindow.newViewer(…)
    mpl.use("qtagg")
else:
    mpl.use("qt5agg")

from matplotlib._pylab_helpers import Gcf as Gcf # noqa
import matplotlib.mlab as mlb # noqa
import matplotlib.pyplot as plt

# BEGIN configure matplotlib
# NOTE: 2024-05-02 10:47:43
# the  next line is obsolete as os.environ["QT_API"] should take care of it ?
# mpl.use("Qtagg")
# mpl.use("Qt5Agg") #
# NOTE: 2021-08-17 12:17:08
# this is NOT recommended anymore
# import matplotlib.pylab as plb

mpl.rcParams["savefig.format"] = "svg"
mpl.rcParams["xtick.direction"] = "in"
mpl.rcParams["ytick.direction"] = "in"
mpl.rcParams["svg.fonttype"]="none"

# NOTE: 2017-08-24 22:48:45
# required to enable interaction with matplotlib plots
plt.ion()

# END configure matplotlib

# END matplotlib modules

# END statistics, plotting and visualization (other than pyqtgraph)

# for console output styles
import colorama  # noqa
# END numerics & data visualization

# END 3rd party modules

# BEGIN scipyen modules
from core import qtutils # noqa
from core.qtutils import (qVariant, QVariantType) #, fromQVariant)
from core import datazone # noqa
from core import datatypes # noqa
from core import basescipyen # noqa
from core import neoutils # noqa
from core import prog # noqa
from core import pyabfbridge as pab # noqa
from core import scipyen_plugin_loader # noqa
from core import scipyen_config as scipyenconf # noqa
from core import scipyendataclasses as sdc # noqa
from core import utilities # noqa
from core import svgutils # noqa
from core import models # noqa
from core import (bgbridge, taxonbridge) # noqa
from core import deferredmeasures as dms # noqa
from core.deferredmeasures import * # noqa

from core.basescipyen import BaseScipyenData # noqa

from core.datazone import (DataZone, Interval, # noqa
                           intervals2cursors, intervals2epoch, # noqa
                           epoch2cursors, epoch2intervals) # noqa

from core.datasignal import (DataSignal, IrregularlySampledDataSignal,) # noqa
# from core.datatypes import *
import core.datatypes as datatypes # noqa

from core.prog import (safewrapper, deprecation, iter_attribute, # noqa
                       filter_type, filterfalse_type, # noqa
                       filter_attribute, filterfalse_attribute, # noqa
                       timefunc, timemethod, timeblock, processtimefunc, # noqa
                       processtimeblock, Timer, scipywarn, warn_with_traceback, # noqa
                       get_properties, print_styled) # noqa

# NOTE: 2024-01-30 22:00:13
# use our own warning - OK for scipyen console
warnings.showwarning = prog.showwarning

from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType, ) # noqa
from core.triggerprotocols import TriggerProtocol # noqa
from core.traitcontainers import DataBag # noqa

from core.utilities import (summarize_object_properties, # noqa
                            augment_obj_prop_dict, # noqa
                            standard_obj_summary_headers, # noqa
                            safe_identity_test, unique, index_of, # noqa
                            gethash, NestedFinder, normalized_index, # noqa
                            reverse_mapping_lookup) # noqa

import core.curvefitting as crvf # noqa
import core.data_analysis as anl # noqa
import core.desktoputils as desktoputils # noqa
import core.scipyen_quantities as cq # noqa
import core.strutils as strutils # noqa
from core.strutils import counter_suffix # noqa
import core.signalprocessing as sigp # noqa
import core.sysutils as sysutils # noqa
import core.tiwt as tiwt # noqa
import core.utilities as utilities # noqa
import core.xmlutils as xmlutils # noqa

from core.scipyen_config import (markConfigurable, confuse, # noqa
                                 saveWindowSettings, loadWindowSettings, ) # noqa
from core.scipyen_config import scipyen_config as scipyen_settings # noqa
from core.scipyenmagics import ScipyenMagics # noqa
from core.strutils import InflectEngine # noqa
from core.scipyen_plugin_loader import reload # noqa
from core.vigra_patches import vigra # noqa
from core.workspacefunctions import * # noqa
from core.deferredmeasures import DeferredSignalMeasure # noqa

from plots import plots as plots # noqa


from imaging.axisutils import (axisTypeFromString, # noqa
                               axisTypeName, # noqa
                               axisTypeStrings, # noqa
                               axisTypeSymbol, # noqa
                               axisTypeUnits, # noqa
                               dimEnum, # noqa
                               dimIter, # noqa
                               evalAxisTypeExpression, # noqa
                               getAxisTypeFlagsInt, # noqa
                               getNonChannelDimensions, # noqa
                               hasChannelAxis, # noqa
                               ) # noqa

from imaging import axisutils, vigrautils # noqa
from imaging import (imageprocessing as imgp, imgsim,) # noqa
from imaging.scandata import (AnalysisUnit, ScanData,) # noqa
from imaging.axiscalibration import (AxesCalibration, # noqa
                                     AxisCalibrationData, # noqa
                                     ChannelCalibrationData, # noqa
                                     CalibrationData) # noqa
from ephys import (ephys, membrane, ephys_pathways) # noqa
from systems import * # noqa

from gui.guiutils import (get_font_style, get_font_weight, treeWidgetItems) # noqa

from . import delegates # noqa
from . import interact # noqa
from . import scipyen_colormaps as colormaps # noqa
from . import consoles # noqa
from . import guiutils # noqa
from . import scipyenviewer # noqa
from . import quickdialog as qd # noqa
# from .resources import resources_rc #as resources_rc
# from .resources import icons_rc
if __has_PySide6__:
    from .resources.pyside6 import breeze_icons_rc # noqa
    from .resources.pyside6 import breeze_dark_icons_rc # noqa
    from .resources.pyside6 import extra_icons_rc # noqa
    from .resources.pyside6 import images_rc # noqa
else:
    from .resources.pyqt6 import breeze_icons_rc # noqa
    from .resources.pyqt6 import breeze_dark_icons_rc # noqa
    from .resources.pyqt6 import extra_icons_rc # noqa
    from .resources.pyqt6 import images_rc # noqa

from . import pictgui as pgui # noqa
from . import xmlviewer as xv # noqa
from . import textviewer as tv # noqa
from . import tableeditor as te # noqa
from . import signalviewer as sv # noqa
from . import matrixviewer as matview # noqa
from . import imageviewer as iv # noqa
from . import datatreeviewer as dv # noqa
# from gui.pythonhelpwidget import PythonHelpWidget

from .consoles import styles, pstyles # noqa
from .cursors import (SignalCursor, SignalCursorTypes,DataCursor, # noqa
                    cursors2epoch, cursors2intervals) # noqa
from .interact import (getInput, getInputs, packInputs, selectWSData) # noqa
from .itemslistdialog import ItemsListDialog # noqa
from .menuproxy import MenuProxy # noqa
from .triggerdetectgui import guiDetectTriggers # noqa
from .widgets import gradientwidgets # noqa
from .widgets import stylewidgets # noqa
from .widgets import colorwidgets # noqa
from .workspacegui import (WorkspaceGuiMixin, DirectoryObserver) # noqa

from gui.itemmodels.workspacemodel import WorkspaceModel
from gui.itemmodels.filesystemmodel import FileSystemModel

# NOTE: 2026-08-07 22:33:36
# using ui modules precompiled with pyside6-uic
from gui.aboutdialog import AboutDialog
from gui.scriptmanager import ScriptManager
# from gui.workspaceviewer import WorkspaceViewer


from iolib import h5io, jsonio, network, navigation # noqa
from iolib.navigation import filesystems # noqa
from iolib import pictio as pio # noqa
from iolib.navigation import navigator # noqa


from core.pyqtgraph_patch import pyqtgraph as pg # noqa

# from gui.cursors import (DataCursor, SignalCursor, SignalCursorTypes)
# END scipyen modules


# END import modules

class FileColumnView(QtWidgets.QColumnView):
    def __init__(self, parent: QtWidgets.QWidget | None = None, **kwargs):
        super().__init__(parent)

    def mouseReleaseEvent(self, evt):
        super().mouseReleaseEvent(evt)
        evt.accept()
