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
from core.quantities import unitsConvertible
from core.datatypes import (Episode, Schedule, ProcedureType, AdministrationRoute, 
                            Procedure, TypeEnum, BioSourceType, TaxonDescriptor, Taxon,
                            )

@dataclass
class BaseScipyenData:
    # NOTE: 2024-11-16 10:07:21
    # The fields below, from 'name' to 'rec_datetime' are meant to align this
    # data model to the one used in NeuralEnsemble's neo library.
    # In addition, I introduce an "analysis_datetime" field to ease up tracking
    # analysis times, and a "triggers" field (which may not be generally useful,
    # see NOTE below)
    name:str = ""
    description:str = ""
    file_origin:typing.Union[str, pathlib.Path] = dataclasses.field(default="")
    file_datetime:datetime = dataclasses.field(default_factory = datetime.now)
    rec_datetime:datetime = dataclasses.field(default_factory = datetime.now)
    analysis_datetime:datetime = dataclasses.field(default_factory = datetime.now)
    # NOTE: 2024-11-16 10:10:16 Revisit this:
    # 'triggers' does not seem useful for this generic data type; it might be better 
    # introduced with SOME descendant classes, or included in the Procedure model
    # (with the caveat that it would be too deeply nested in the final object)
    triggers:typing.Union[TriggerProtocol, list] = dataclasses.field(default_factory=TriggerProtocol)
    
    source:BioSourceType = dataclasses.field(default=BioSourceType.exvivo)
    
    taxon:TaxonDescriptor = dataclasses.field(default=TaxonDescriptor())
    
    subspecies:str = "Sprague Dawley"
    
    sourceID:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # identifier for the cell source: this may a (meaningful) combination of:
    #   animal ID,
    #   experimental date
    #   cortex region
    #
    #   e.g. TS2_1234567_01_02_22_VisCx_
    #
    # NOTE: the rules for naming the source are up to you, BUT:
    #   1) be consistent
    #   2) should contain ONLY alphanumeric characters and underscore ('_')
    #   3) should NOT begin with a digit or underscore ('_')

    cell:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # identifier for this cell; there may be more than one cell from the same animal
    #
    # NOTE: the rules for constructing a cell ID are up to you, BUT:
    #   1) be consistent
    #   2) should contain ONLY alphanumeric characters and underscore ('_')
    #   3) should NOT begin with a digit or underscore ('_')
    # 
    
    field:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)

    genotype:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # genotype of the source - keep it simple
    #
    # NOTE: avoid strings like (+/-, TSNeo/-, etc) as they don't play well when
    # importing data in, say, R
    # These are entirely conventional, and, within the same line of genetic 
    # animal model they would have a well-defined meaning
    #
    

    sex:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # ID of source sex (where appropriate); one of "f", "m", "na" (case-insensitive)
    #
    
    age:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # animal's age (more generaly the age of the biological source)- almost 
    # free-form string, see NOTE for animal ID - keep it
    #   simple, yet meaningful, and indicate units (e.g. 3_mo, or 20_d, or 1_yr)
    #
    # NOTE: these are simply for a quick information; in the future Scipyen will
    # provide a more standardized way to store this information, hopefully more
    # suitable to some sort of database management
    
    
    
    biometric_weight:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA) 
    biometric_height:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    
    procedure:typing.Optional[Procedure] = None
    # This WILL include treatment, with dosage route, and schedule
    
    # NOTE: 2024-11-16 10:03:19
    # these below are DEPRECATED, as they are now fields of procedure, above
    
    # procedure_type:typing.Union[str, int, ProcedureType, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # procedure_name:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # procedure_dose:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # procedure_route:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # procedure_schedule:neo.Epoch = dataclasses.field(default_factory=neo.Epoch)
    
