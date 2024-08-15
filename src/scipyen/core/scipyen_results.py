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
from core import quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.quantities import units_convertible

class ScipyenResults(BaseScipyenData):
    """TODO: 2022-11-18 14:46:04"""
    _data_attributes_ = ("result", dict)
    
    _analysis_attributes_ = ("options", dict,
                             "sourceApp", "")
    
    _attributes_ = _data_attributes_ + _analysis_attributes_ + BaseScipyenData._attributes_
    
    def __init__(self, result:typing.Any, **kwargs):
        super().__init__(**kwargs)
