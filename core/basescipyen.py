"""Base ancestor of Scipyen's data objects: AnalysisUnit, ScanData
"""
import functools, typing
import collections
from datetime import datetime, date, time, timedelta
import numpy as np
import quantities as pq
import neo
import vigra
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core.triggerprotocols import TriggerProtocol
from core.quantities import units_convertible
from core.prog import (ArgumentError, OneOf, DescriptorTypeValidator, DescriptorGenericValidator,
                       AttributeAdapter, get_descriptors, get_properties,
                       parse_descriptor_specification, WithDescriptors,
                       setup_descriptor)

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
        
    gender: str: one of "F", "M", "NA"; optional, default is None
    
    biometric: dict; optional, default is None
        When a dict it may contain:
            'weight' -> python Quantity of mass units; optional, default is None
            
            'height' -> python Quantity of length units; optional, default is None
            
            ... any other useful biometric with value that can be stored as a 
                short litral description, or a python Quantity, if numeric
            
    procedure: dict; optional, default is None
        When a dict it may contain:
            'type' -> str e.g., "treatment", "surgery", "rotarod", etc informative
                enough to allow data classification later
                
            'name' -> str e.g., the name of the drug, or of the procedure
            
            'dose' -> scalar python Quantity with units of substance (or mass, 
                e.g., g or moles),  density or concentration (i.e. mass/volume)
                or mass/mass (numerically dimensionless after simplification) -
                when it makes sense, e.g. for drug treatments, or None
            
            'route'-> str: how the procedure was administrered (when it makes 
                sense, such as drug treatment, e.g. i.v., i.p., p.o, i.c., 
                perfusion, etc) - should be informative enough to allow data
                classification later
                
            'schedule' -> neo.Epoch: the schedule of treatment, e.g.
                times & duration of drug admninstation or procedure application
                
    protocols: list of TriggerProtocol (for electrophysiology/imaging data)
    
    descriptors: dict with any other descriptors
                
    NOTE: For many of these attributes the values do not yet follow a standard.
    """
    
    # NOTE: 2021-11-30 16:17:53
    # DESCRIPTOR SPECIFICATIONS:
    # will be inherited by derived subclasses, which can also add their own
    # (see ScanData) provided they follow the template below:
    #
    # attr name, type, or default (in whch case type is inferred from default)
    # when 2nd is a type, the default value is set to None
    #
    # see documentation for prog.parse_descriptor_specification for details on how
    # each sequence in the _descriptor_attributes_ tuple is interpreted.
    #
    
    _data_children_     = ()
    _data_attributes_ = (
                            ("sourceID",            "NA"),
                            ("cell",                "NA"),
                            ("genotype",            "NA"),
                            ("gender",              "NA"),
                            ("age",                 (0*pq.s, "NA")),
                            ("biometric_weight",    (0*pq.g, "NA")), 
                            ("biometric_height",    (0*pq.m, "NA")),
                            ("procedure_type",      "NA"),
                            ("procedure_name",      "NA"),
                            ("procedure_dose",      (0*pq.g, "NA")),
                            ("procedure_route",     "NA"),
                            ("procedure_schedule",  neo.Epoch()),
                            ("triggers",            list(),     TriggerProtocol),
                            ("file_datetime",       datetime),
                            ("rec_datetime",        datetime),
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
        for a in self._descriptor_attributes_:
            result.append(f"{a[0]}: {getattr(self, a[0], None)}")
            
        return "\n".join(result)
    
    @property
    def needed_descriptors(self):
        return dict((a[0], getattr(self, a[0], None)) for a in self._descriptor_attributes_)
    

    @property
    def descriptors(self):
        return get_descriptors(self)
