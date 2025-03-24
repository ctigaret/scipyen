# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Base ancestor of Scipyen's data objects: AnalysisUnit, ScanData
"""
import functools, typing, dataclasses, pathlib
import collections
from collections import deque
from datetime import datetime, date, time, timedelta
from dataclasses import (dataclass, field, MISSING, KW_ONLY, InitVar)
import numpy as np
import quantities as pq
import neo
import h5py
from core.vigra_patches import vigra
import pandas as pd
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.quantities import unitsConvertible

# from core.datatypes import * # clashes with datetime class imported from datetime module !!!
from core.typeenum import TypeEnum
from core.scipyendataclasses import (Episode, Schedule, ProcedureType, AdministrationRoute, 
                            Procedure, BioSourceType, TaxonDescriptor, Taxon,
                            BiologicalSource, CellCompartment, CellCompartmentType,
                            Organism, Biometrics, ScipyenDataclass, 
                            )

@dataclass
class BaseScipyenData(ScipyenDataclass):
    # NOTE: 2024-11-16 10:07:21
    # The fields below, from 'name' to 'rec_datetime' are meant to align this
    # data model to the one used in NeuralEnsemble's neo library.
    # In addition, I introduce an "analysis_datetime" field to ease up tracking
    # analysis times, and a "triggers" field (which may not be generally useful,
    # see NOTE below)
    # name:str = ""
    # description:str = ""
    file_origin:typing.Union[str, pathlib.Path] = dataclasses.field(default="")
    # which file it originates from
    file_datetime:datetime = dataclasses.field(default_factory = datetime.now)
    # when was the file created
    rec_datetime:datetime = dataclasses.field(default_factory = datetime.now)
    # when was data recorded
    analysis_datetime:datetime = dataclasses.field(default_factory = datetime.now)
    # when was data analysed
    
    # NOTE: 2024-11-16 10:10:16 Revisit this:
    # 'triggers' does not seem useful for this generic data type; it might be better 
    # introduced with SOME descendant classes, or included in the Procedure model
    # (with the caveat that it would be too deeply nested in the final object)
    # triggers:typing.Union[TriggerProtocol, list] = dataclasses.field(default_factory=TriggerProtocol)
    
    # biological source including organism, organ, tissue, cell, ID, 
    source:BiologicalSource = dataclasses.field(default_factory=BiologicalSource)
    # includes treatment, with dosage route, and schedule; does NOT include triggers
    # as these are specific to ephys/imaging protocols.
    procedure:Procedure = dataclasses.field(default_factory=Procedure)
    
    # __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("file_origin",
    #                                                               "file_datetime",
    #                                                               "rec_datetime",
    #                                                               "analysis_datetime")))
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
