# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

from core.basescipyen import BaseScipyenData

import functools, typing
import collections
from datetime import datetime, date, time, timedelta
import numpy as np
import quantities as pq
import neo
from core.vigra_patches import vigra
from traitlets.utils.importstring import import_item
from core import scipyen_quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.scipyen_quantities import unitsConvertible

class ScipyenResults(BaseScipyenData):
    r"""TODO: 2022-11-18 14:46:04
    NOTE: 2025-05-29 12:40:11 currently, many analysis functions generate instances 
    of types.SimpleNamespace
    
    I am still to decide if subclassing BaseScipyenData (a dataclass) is something
    needed and what are the benefits in doing so...
    
"""
    _data_attributes_ = ("result", dict)
    
    _analysis_attributes_ = ("options", dict,
                             "sourceApp", "")
    
    _attributes_ = _data_attributes_ + _analysis_attributes_ + BaseScipyenData._attributes_
    
    def __init__(self, result:typing.Any, **kwargs):
        super().__init__(**kwargs)
