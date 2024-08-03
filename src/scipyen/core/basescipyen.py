# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Base ancestor of Scipyen's data objects: AnalysisUnit, ScanData
"""
import functools, typing
import collections
from collections import deque
from datetime import datetime, date, time, timedelta
from dataclasses import MISSING
import numpy as np
import quantities as pq
import neo
import vigra
import pandas as pd
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.quantities import units_convertible
from core.prog import (ArgumentError, OneOf, 
                       DescriptorTypeValidator, DescriptorGenericValidator,
                       AttributeAdapter, get_descriptors, get_properties,
                       parse_descriptor_specification, WithDescriptors,
                       setup_descriptor)

from core.datatypes import (Episode, Schedule, ProcedureType, AdministrationRoute, 
                            Procedure, TypeEnum,
                            )

class BaseScipyenData(neo.core.baseneo.BaseNeo, WithDescriptors):
    """Simple repository for the minimally-required, common attributes.
    
    These attributes are : 
    ----------------------------------------------------------------------------
    sourceID: str the ID of the entity source of the data (and ID of a culture
        dish, etc...), 
        
    cell: str, the ID of the cell, or "NA" (not available); optional, default is 
        None (resulting in a "NA value")
        ""
    genotype: str, one of "WT, "HET" or "KO", "+/+", "-/-", "+/-" or a more complex
        and informative genotype notation  
        default is None 
        
    age: scalar python Quantity (with units of time, or convertible to SI time units)
        optional, default is None)
            e.g., 15 pq.div or 20 * pq.pnd (postnatal day), or 16 * pq.emd (embryonic day)
        
    sex: str: one of "F", "M", "NA"; optional, default is None
    
    biometric: dict; optional, default is None; the contents are free-form, but 
        should have some sort of systematic organization.

        When a dict it may contain:
            'weight' -> python Quantity of mass units; optional, default is None
            
            'height' -> python Quantity of length units; optional, default is None
            
            ... any other useful biometric with value that can be stored as a 
                short litral description, or a python Quantity, if numeric
            
    procedure: dict; optional, default is None
        When a dict it may contain:
            'type' -> datatypes.ProcedureType or str e.g., "treatment", "surgery", "rotarod", etc informative
                enough to allow data classification later
                
            'name' -> str e.g., the name of the drug, or of the procedure
            
            'dose' -> scalar python Quantity with units of substance (or mass, 
                e.g., g or moles),  density or concentration (i.e. mass/volume)
                or mass/mass (e/g/, mg/kg, numerically dimensionless after 
                simplification) - when it makes sense, e.g. for drug treatments, 
                or None
            
            'route'-> str: how the procedure was administrered (when it makes 
                sense, such as drug treatment, e.g. i.v., i.p., p.o, i.c., 
                perfusion, etc) - should be informative enough to allow data
                classification later
                
            'schedule' -> neo.Epoch: the schedule of treatment, e.g.
                times & duration of drug adminstration or procedure application
                
    triggers: list of TriggerProtocol (for electrophysiology/imaging data)
    
    descriptors: dict with any other descriptors
                
    """
    
    # NOTE: 2021-11-30 16:17:53
    # DESCRIPTOR SPECIFICATIONS:
    #
    # will be inherited by derived subclasses, which can also add their own
    # (see ScanData) provided they follow the template below:
    #
    # attr name, type, or default (in whch case type is inferred from default)
    # when 2nd is a type, the default value is set to None
    #
    # see documentation for prog.parse_descriptor_specification for details on how
    # each sequence in the _descriptor_attributes_ tuple is interpreted.
    #
    # NOTE: 2024-08-02 13:38:58
    # we follow the neo data model here, rather than Python's dataclass
    # TODO: contemplate switching to dataclass ?
    #
    
    _data_children_     = ()
    _data_attributes_ = (
                            ("sourceID",            (str, type(pd.NA), type(MISSING)),          tuple(),    "NA"),
                            ("cell",                (str, type(pd.NA), type(MISSING)),          tuple(),    "NA"),
                            ("field",               (str, type(pd.NA), type(MISSING)),          tuple(),    "NA"),
                            ("genotype",            (str, type(pd.NA), type(MISSING)),          tuple(),    "NA"),
                            ("sex",                 (str, type(pd.NA), type(MISSING)),          tuple(),    "NA"),
                            ("age",                 (pq.Quantity, type(pd.NA), type(MISSING)),  0*pq.s),
                            ("biometric_weight",    (pq.Quantity, type(pd.NA), type(MISSING)),  0*pq.g), 
                            ("biometric_height",    (pq.Quantity, type(pd.NA), type(MISSING)),  0*pq.m),
                            ("procedure",           Procedure),
                            ("procedure_type",      (str, int, ProcedureType, type(pd.NA), type(MISSING)),  0),
                            ("procedure_name",      (str, type(pd.NA), type(MISSING)),                      "NA"),
                            ("procedure_dose",      (pq.Quantity, type(pd.NA), type(MISSING)),              0*pq.g),
                            ("procedure_route",     (str, type(pd.NA), type(MISSING)),                      "NA"),
                            ("procedure_schedule",  neo.Epoch),
                            ("triggers",            (TriggerProtocol, list, type(MISSING)),            TriggerProtocol()),
                            ("file_datetime",       datetime),
                            ("rec_datetime",        datetime),
                            ("analysis_datetime",   datetime),
                            ("descriptors",         dict)
                        )
    
    _descriptor_attributes_ = _data_children_ + _data_attributes_ + neo.core.baseneo.BaseNeo._recommended_attrs
    
    def __init__(self, name=None, description=None, file_origin=None, **kwargs):
        WithDescriptors.__init__(self, name=None, description=None, file_origin=None, **kwargs)
        
        # so that we don't confuse baseneo._check_annotations in the __init__ 
        # further below
        for d in self._descriptor_attributes_:
            kwargs.pop(d[0], None)
        
        super().__init__(name=name, description=description, file_origin=file_origin, **kwargs)
        
    def __attr_str__(self):
        result = list()
        for a in self._descriptor_attributes_:
            attr = getattr(self, a[0], None)
            attr_str = type(attr).__name__
            
            if isinstance(attr, neo.Block):
                attr_str += f" with {len(attr.segments)} segments"
                
            elif isinstance(attr, np.ndarray):
                attr_str += f" with shape {attr.shape}"
                
            else:
                attr_str = f"{attr}"
                
            result.append(f"{a[0]}: {attr_str}")
            
        return result
        # return "\n".join(result)
    
    def _repr_pretty_(self, p, cycle):
        name = self.name if isinstance(self.name, str) else ""
        
        if cycle:
            p.text(f"{self.__class__.__name__} {name}")
        else:
            p.text(f"{self.__class__.__name__} {name}")
            p.breakable()
            attr_repr = self.__attr_str__()
            with p.group(4 ,"(",")"):
                for t in attr_repr:
                    p.text(t)
                    p.breakable()
                p.text("\n")
                
            p.breakable()
            
    @property
    def mandatory_descriptors(self):
        return dict((a[0], getattr(self, a[0], None)) for a in self._descriptor_attributes_)
    
    @property
    def descriptors(self):
        return get_descriptors(self)
