# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Base ancestor of Scipyen's data objects: AnalysisUnit, ScanData
"""
import functools, typing, dataclasses, pathlib
import collections
from collections import deque
from datetime import datetime, date, time, timedelta
from dataclasses import (dataclass, field, MISSING, KW_ONLY, InitVar)
import numpy as np
import quantities as pq
import neo
from core.vigra_patches import vigra
import pandas as pd
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.quantities import units_convertible
from core.datatypes import (Episode, Schedule, ProcedureType, AdministrationRoute, 
                            Procedure, TypeEnum,
                            )

@dataclass
class BaseScipyenData:
    name:str = ""
    description:str = ""
    file_origin:typing.Union[str, pathlib.Path] = dataclasses.field(default="")
    sourceID:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    cell:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    field:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    genotype:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    sex:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    age:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    biometric_weight:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA) 
    biometric_height:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    procedure:typing.Optional[Procedure] = None,
    procedure_type:typing.Union[str, int, ProcedureType, type(pd.NA)] = dataclasses.field(default=pd.NA)
    procedure_name:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    procedure_dose:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    procedure_route:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    procedure_schedule:neo.Epoch = dataclasses.field(default_factory=neo.Epoch)
    triggers:typing.Union[TriggerProtocol, list] = dataclasses.field(default_factory=TriggerProtocol)
    file_datetime:datetime = dataclasses.field(default_factory = datetime.now)
    rec_datetime:datetime = dataclasses.field(default_factory = datetime.now)
    analysis_datetime:datetime = dataclasses.field(default_factory = datetime.now)
