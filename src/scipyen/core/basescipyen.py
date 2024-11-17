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
import h5py
from core.vigra_patches import vigra
import pandas as pd
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.quantities import unitsConvertible

# from core.datatypes import * # clashes with datetime class imported from datetime module !!!

from core.datatypes import (Episode, Schedule, ProcedureType, AdministrationRoute, 
                            Procedure, TypeEnum, BioSourceType, TaxonDescriptor, Taxon,
                            BiologicalSource, CellCompartment, CellCompartmentType,
                            Organism, Biometrics, 
                            )

# class BaseScipyenData(ScipyenDataclassABC):
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
    # triggers:typing.Union[TriggerProtocol, list] = dataclasses.field(default_factory=TriggerProtocol)
    
    source:BiologicalSource = dataclasses.field(default_factory=BiologicalSource)
    
    procedure:Procedure = dataclasses.field(default_factory=Procedure)
    # This WILL include treatment, with dosage route, and schedule
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        ret = self.name == other.name
        
        if ret:
            ret &= all(getattr(self, f.name) == getattr(other, f.name) for f in dataclasses.fields(self.__class__))

    def __repr__(self):
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def toHDF5(self, group:h5py.Group, name:str, oname:str, 
                       compression:str, chunks:bool, track_order:bool,
                       entity_cache:dict) -> h5py.Group:
        
        from iolib import h5io
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
        
        # full_attrs = dict((x, getattr(self, x)) for x in self.__match_args__)
        full_attrs = asdict(self)
        
        attrs_to_entities = dict((k,v) for k,v in full_attrs.items() if (isinstance(v, np.ndarray) and v.size > 1))
        
        attrs = dict((k,v) for k,v in full_attrs.items() if k not in attrs_to_entities)
        
        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)
        
        if isinstance(name, str) and len(name.strip()):
            target_name = name
        
        entity = group.create_group(target_name, track_order=track_order)
        entity.attrs.update(obj_attrs)
        
        if len(attrs_to_entities):
            for k,v in attrs_to_entities.items():
                h5io.toHDF5(v, entity, name=k, oname=k,
                            compression=compression,chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)
                
        h5io.storeEntityInCache(entity_cache, self, entity)
        
        return entity

    @classmethod
    def fromHDF5(cls, entity:h5py.Group, 
                             attrs:typing.Optional[dict]=None, cache:dict = {}):
        
        from iolib import h5io
        if entity in cache:
            return cache[entity]
        
        attrs = h5io.attrs2dict(entity.attrs)
        
        attrs_as_entities = [a for a in cls.__match_args__ if a not in attrs]
        
        kwargs = dict()
        
        for a in cls.__match_args__:
            if a in attrs:
                kwargs[a] = attrs[a]
            else:
                if a in entity.keys():
                    kwargs[a] = h5io.fromHDF5(entity[a], cache=cache)
                    
        return cls(**kwargs)
    
