# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Shapely-based planar graphics 2024-08-27 10:21:39
Work in progress
"""
import sys, os, re, numbers, itertools, warnings, traceback
import dataclasses
from dataclasses import dataclass
import typing
import math
from collections import (ChainMap, namedtuple, defaultdict, OrderedDict,)
from functools import (partial, partialmethod,)
from enum import (Enum, IntEnum,)
from abc import (ABC, abstractmethod,)# ABCMeta)
from copy import copy
import numpy as np
import scipy
from traitlets import Bunch
from qtpy import QtCore, QtGui, QtWidgets, QtXml
from qtpy.QtCore import Signal, Slot, Property
from core.datatypes import (TypeEnum, )
from core.utilities import (reverse_mapping_lookup, reverse_dict, )
from core.traitcontainers import DataBag
from core.prog import (safeWrapper, deprecated,
                       timefunc, processtimefunc,filter_type)
#from core.utilities import (unique, index_of,)
from core.workspacefunctions import debug_scipyen
#### END core modules

#### BEGIN other gui stuff
from .painting_shared import (standardQtGradientTypes, standardQtGradientPresets,
                              g2l, g2c, g2r, gradientCoordinates, 
                              qPathElementCoordinates)

import gui.scipyen_colormaps as colormaps
from .scipyen_colormaps import ColorPalette

import shapely
# from shapely import lib as shapely_lib
# from shapely_lib.base import BaseGeometry
from shapely import (Geometry,     
                     Point,
                     LineString,
                     Polygon,
                     MultiPoint,
                     MultiLineString,
                     MultiPolygon,
                     GeometryCollection,
                     LinearRing,
                    )

@dataclass
class PlanarShape(object):
    shape:Geometry
    state:Bunch = dataclasses.field(init=False)
    z_frame:typing.Optional[int] = None
    frames:typing.Optional[typing.Union[tuple[int], range, slice, list[int]]] = dataclasses.field(default_factory = list)
    
    def __post_init__(self, shape:Geometry):
        if not isinstance(shape, Geometry):
            raise TypeError(f"Expecting a shapely.Geometry; instead, got {type(shape).__module__}.{type(shape).__name__}")
        if z_frame is None:
            shape = shapely.fore_2d(shape)
        elif isinstance(z_frame, int):
            if z_frame >= 0:
                shape = shapely.force_3d(shape, z_frame)
            
        self.state = Bunch({"shape": shape, "z_frame": z_frame})
        if frames is None:
            shapely.force_2d(shape)
            
        elif isinstance(frames, )
    
    
    
