# -*- coding: utf-8 -*-
# $Id: scipyendataclasses.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
from abc import ABC, ABCMeta, abstractmethod
import collections
from collections import deque, namedtuple
from functools import (singledispatch, singledispatchmethod)
import itertools
import datetime
from enum import (Enum, IntEnum, EnumMeta, Flag, auto) #noqa
import inspect
import numbers
import math
import dataclasses
from dataclasses import (dataclass, KW_ONLY, MISSING, field)
import sys, os
import time, datetime
import traceback
import typing
import types
import warnings
import weakref
import h5py
import treelib
import pathlib
from copy import (deepcopy, copy,)
import numpy as np
from numpy import ndarray
import numpy.matlib as mlib
import pandas as pd
import quantities as pq
from core.vigra_patches import vigra
import neo
from neo.core import (baseneo, basesignal, container,)
from neo.core.dataobject import (DataObject, ArrayDict,)


#### END 3rd party modules

#### BEGIN pict.core.modules
from core import scipyen_quantities as scq
from core import xmlutils
from core import strutils
from core.prog import (safewrapper, is_hashable, is_type_or_subclass,
                       ImmutableDescriptor, scipywarn, NoData, print_styled)
# from core.datazone import DataZone
from core.datasignal import (_new_DataSignal, _new_IrregularlySampledDataSignal, DataSignal, IrregularlySampledDataSignal)
# from core import bgbridge
# from core.bgbridge import (BGStructureDescriptor, BrainGlobeAtlas)
from core import taxonbridge
from core.taxonbridge import(Taxon, TaxonDescriptor)
from core.typeenum import TypeEnum
from core.constants import (RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE,
                            EQUAL_NAN, GENOTYPES)

#### END pict.core.modules

@dataclass
class TestData:
    a: str|int|typing.Sequence[int] = dataclasses.field(default_factory = str)
    # a: typing.Union[str, int, typing.Sequence[int]] = dataclasses.field(default_factory = str)
    b: typing.Optional[typing.Union[pq.Quantity, typing.Sequence[pq.Quantity]]] = None
    c: typing.Optional[dict[int,str] | str] = None
    name: str = ""

