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
from enum import (Enum, IntEnum, EnumMeta)
import inspect
import numbers
import math
import dataclasses
from dataclasses import (dataclass, KW_ONLY, MISSING, field)
import sys
import time, datetime
import traceback
import typing
import types
import warnings
import weakref
import h5py
import treelib
from copy import (deepcopy, copy,)

#### END core python modules

#### BEGIN 3rd party modules
from qtpy import (QtGui, QtCore, QtWidgets,)
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
from core import quantities as scq
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

class DoseDescriptor:
    def __set_name__(self, obj:object, name:str):
        if len(name.strip()) == 0:
            raise ValueError("Cannot accept an empty name")
        self._name = "_"+name
        
    def __get__(self, obj:object, objtype:type) -> object:
        if obj is None:
            return #self._default
        return getattr(obj, self._name, None)
    
    def __set__(self, obj:object, value:typing.Optional[pq.Quantity] = None):
        if isinstance(value, pq.Quantity):
            if not scq.checkDosageUnits(value):
                raise ValueError(f"Expecting dosage units; instead got {value.units}")
            
        elif value is not None:
            raise TypeError(f"Expecting a scalar dosage Quantity, or None; instead got {type(value).__name__}")

        setattr(obj, self._name, value)
        
@dataclass
class ScipyenDataclass:
    r"""Ancestor of Scipyen data classes.
    """
    name:str = dataclasses.field(default_factory=str)
    description: str = dataclasses.field(default_factory=str)
    
    def diff(self, other, showValues:bool=False) -> dict | tuple:
        from core.utilities import safe_identity_test
            
        if other.__class__ != self.__class__:
            raise TypeError(f"Expecting an object of type {self.__class__.__name__}; instead, got {type(other).__name__}")
        
        
        fields = tuple(map(lambda f: (f.name, getattr(self, f.name), getattr(other, f.name)), dataclasses.fields(self.__class__)))
        
        diff_fields = tuple(filter(lambda f: type(f[1]) != type(f[2]) or not safe_identity_test(f[1], f[2]), fields))

        if showValues:
            return dict(map(lambda f: (f[0], (f[1], f[2])), diff_fields))
        
        return tuple(map(lambda f: f[0], diff_fields))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        
        return len(self.diff(other)) == 0
    
    def __contains__(self, val:str) -> bool:
        r"""Test the existence of a field name in this instance
    Parameters:
    ===========
    `val` : a string, the symbol (or name) of the field which is potentially 
            defined in this instance's class
    
    Returns:
    =======
    True if a field with name suplied by `val` exists in this instance.
    """
        return val in map(lambda f: f.name, dataclasses.fields(self))
    
    def merge(self, *others) -> typing.Self:
        if len(others) == 0:
            return self
        
        if not all(isDataclass(o) for o in others):
            raise TypeError("Expecting instances of ScipyenDataclass")
        
        of = tuple(itertools.chain.from_iterable(tuple(map(lambda o: tuple(map(lambda f: (o, f.name), dataclasses.fields(o))), 
                                                        (parameters, *extra_params)))))
        
        invalid_field_names = tuple(filter(lambda x: x[1] not in self))
        
        if len(invalid_field_names):
            raise TypeError(f"Arguments contain the following fields which are invalid for this {type(self).__name__} instance: {invalid_field_names}")
        
        for (o, fname) in of:
            setattr(self, fname, getattr(o, fname))
            
        return self
        
    def toHDF5(self, group:h5py.Group, name:str, oname:str, 
                       compression:str, chunks:bool, track_order:bool,
                       entity_cache:dict) -> h5py.Group:
        # BUG: 2024-12-12 00:43:33  FIXME
        # cannot store all fields as entity attributes, because subclasses of 
        # ScipyenDataclass MAY have composite types which cannot be encoded in json.
        #
        # Therefore: TODO: convert to dict using asdict then store it as if is was a dict!
        # TODO: adapt fromHDF5 to reflect this!
        
        # see examples in h5io.objectToEntity
        
        from iolib import h5io
        
        # print(f"\n\n### BEGIN {self.__class__.__name__}.toHDF5")
        
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            # print(f"{self.__class__.__name__}.toHDF5 found entity {cached_entity}")
            # print(f"### END {self.__class__.__name__}.toHDF5 \n\n")
            return cached_entity
        
        if isinstance(name, str) and len(name.strip()):
            target_name = name
            
        # calling asDict recursively converts all nested dataclass instances to
        # a dict -- effectively "peeling out" the dataclass
        data = dataclasses.asdict(self)
        
        # therefore, I need to inspect which of the fields ARE in fact, instances
        # of dataclass
        dataclass_fields = list(filter(lambda f: dataclasses.is_dataclass(getattr(self, f.name)), dataclasses.fields(self)))
        
        # then assign these back into the dictionary from above:
        data.update(dict(map(lambda f: (f.name, getattr(self, f.name)), dataclass_fields)))

        # NOTE: 2024-12-12 15:41:25
        # instead of creating a nested hf5 group, just populate this one with
        # the items from the updated data dict above
        entity = group.create_group(target_name, track_order = track_order)
        entity.attrs.update(obj_attrs)
        
        for name, value in data.items():
            cached_entity = h5io.getCachedEntity(entity_cache, value)
            if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
                entity[name] = cached_entity
            else:
                element_entity = h5io.toHDF5(value, entity, name=name,
                                             compression=compression,
                                             chunks=chunks,
                                             track_order=track_order,
                                             entity_cache=entity_cache)
                # ### BEGIN for debugging
#                 if name in ("dose", "route"):
#                     msg = f"{self.__class__.__name__}.toHDF5 created entity {element_entity} for field '{name}' ({type(value).__name__})"
#                     if isinstance(value, np.ndarray):
#                         msg += f" with size: {value.size} and shape: {value.shape}\n"
#                     else:
#                         msg += "\n"
#                         
#                     print(msg)
                # ### END   for debugging
                
        # print(f"### END {self.__class__.__name__}.toHDF5 \n\n")
        return entity
        
    @classmethod
    def fromHDF5(cls, entity:h5py.Group, 
                attrs:typing.Optional[dict] = None, cache:dict = {}):
        from iolib import h5io
        
        # print(f"\n\n### BEGIN {cls.__name__}.fromHDF5 ")
        
        if entity in cache:
            val = cache[entity]
            # print(f"{cls.__name__}.fromHDF5 got cached entity {type(val).__name__}")
            return val
        
        attrs = h5io.attrs2dict(entity.attrs)
        
        # print(f"{cls.__name__}.fromHDF5: attrs = {attrs}")
        
        # assert attrs["python_class"] == str(cls).strip("<").strip(">").strip("class").strip()[1:-1], \
        assert attrs["python_class"] == cls, f"Object has unexpected class: {attrs['python_class']}"
        
        attrs_as_entities = [a for a in cls.__match_args__ if a not in attrs]
        
        kwargs = dict()
        
        for a in attrs_as_entities:
            if a in entity.keys():
                kwargs[a] = h5io.fromHDF5(entity[a], cache=cache)
                # print(f"{cls.__name__}.fromHDF5: got field '{a}' with type: {type(kwargs[a]).__name__}\n")
                    
        # print(f"### END {cls.__name__}.fromHDF5 \n\n")
        return cls(**kwargs)
    
    @classmethod
    def contains(cls, val:str):
        r"""Test the existence of a field name in this class
    Parameters:
    ===========
    `val` : a string, the symbol (or name) of the field which is potentially defined in the class
    
    Returns:
    =======
    True if a field with name suplied by `val` exists in this class.
    """
        return val in map(lambda f: f.name, dataclasses.fields(cls))

class CellCompartmentType(TypeEnum):
    r"""Follows SWC/CNIC specification augmented with 'spine', 'nucleus', 'nucleolus'. 
    See http://www.neuronland.org/NLMorphologyConverter/MorphologyFormats/SWC/Spec.html
    """
    undefined = 0
    cell = undefined
    soma = 1
    axon = 2
    dendrite = 3 # basal dendrite
    apical_dendrite = 4
    fork_point = 5
    end_point = 6
    spine = 7
    basal_dendrite_spine = dendrite | spine # = 10
    apical_dendrite_spine = apical_dendrite | spine # = 11
    nucleus = 12
    nucleolus = 13
    
class BioSourceType(TypeEnum):
    exvivo      = 1
    invitro     = 2
    insilico    = 4
    monolayer   = 8     # e.g. "primary" culture = invitro | monolayer = 10
    tissue      = 16    # e.g. acute brain slice = exvivo | tissue = 17 
                        # e.g. "organotypic" slice culture = invitro | tissue  = 18
    assembloid  = 32    # e.g. "organoid" = invitro | assembloid = 34
    
    invivo      = 64
    
    organism    = 128   
    
class ProcedureType(TypeEnum):
    null = 0
    mating = 1
    treatment = 2
    behaviour = 4 # includes navigation in real or virtual environment, rotarod, inclined plane, licking etc # TODO to refine
    surgery = 8
    biopsy = 16
    postop = 32
    tagging = 64
    weaning = 128
    cull = 256
    other = 512
    
class OrganismStage(TypeEnum):
    undefined   = 0
    zygote      = 1
    morula      = 2
    blastula    = 4
    gastrula    = 8
    embryo      = zygote | morula | blastula | gastrula # = 15
    foetal      = 16
    prenatal = embryo | foetal # = 31
    larva       = 32
    pup         = larva
    prepubertal = larva
    preweaning  = prepubertal
    adolescent  = 33
    adult       = 34
    juvenile    = larva | adolescent # = 65
    postnatal   = larva | adolescent | adult # = 99
    
class AdministrationRoute(TypeEnum):
    null = 0
    bath = 1 # relates to ex vivo tissue slices
    puff = 2 # relates to ex vivo tissue slices — e.g. picospritzer, pressurized micropipette, etc
    intraperitoneal = 4
    intramuscular = 8
    intravenous = 16
    intraarterial = 32
    intracerebral = 64
    intraventricular = 128 # can be in the heart!
    intracerebroventricular = intracerebral | intraventricular # 192
    intracardiac = 256
    intracardioventricular = intracardiac | intraventricular # 384
    subcutaneous = 512
    transcutaneous = 1024
    peros = 2048 # e.g. gavage
    inhalation = 4096
    intranasal = 8192
    intraorbital = 16384
    food_water = 32768
    other = 65536
    
    # aliases
    ip = intraperitoneal
    iv = intravenous
    ia = intraarterial
    im = intramuscular
    ic = intracerebral
    icv = intracerebroventricular
    icd = intracardiac
    icdv = intracardioventricular
    ins = intranasal # 'in' is a reserved Python keyword
    inh = inhalation
    io = intraorbital
    sc = subcutaneous
    tc = transcutaneous
    gavage = peros
    oral = peros
    custom = other
    bulk = bath
    
@dataclass
class CellCompartment(ScipyenDataclass):
    # name:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    type:CellCompartmentType = CellCompartmentType.undefined
    id:int = 0
    
    # __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("type", "id")))

    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Biometrics(ScipyenDataclass):
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
    
    postnatal:bool=True
    
    weight:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA) 
    height:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Organism(ScipyenDataclass):
    taxon:TaxonDescriptor = TaxonDescriptor()
    subspecies:str = ""
    strain:str = ""
    stage:OrganismStage = dataclasses.field(default=OrganismStage.postnatal)
    biometrics:Biometrics = dataclasses.field(default_factory=Biometrics)
    
    def __post_init__(self):
        if isinstance(self.biometrics, Biometrics):
            self.biometrics.postnatal = self.stage > OrganismStage.prenatal
                
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x.name}" if isinstance(x, Enum) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)

class Tissue():pass # leave here for it to be detected in Kate symbol viewer
Tissue = ScipyenDataclass

class Organ():pass # leave here for it to be detected in Kate symbol viewer
Organ = ScipyenDataclass

@dataclass
class BiologicalSource(ScipyenDataclass):
    from core.bgbridge import BGStructureDescriptor
    r"""Source of measurement data.
    Encapsulates the biological source for the data measured in an experiment or
    investigation.
    This may be an entire organism, an organ, tissue, individual cell, or 
    subcellular compartment.
    """
    # TODO: 2024-11-17 21:11:13 : locate and use neuronal taxonomy API
    
    # The organism of this source.
    # Contains the data related to the taxon, species, subspecies, strain, and 
    # biometrics.
    # See Organism class in this module
    # organism:Organism = dataclasses.field(default=Organism("rat"))
    organism:Organism = dataclasses.field(default_factory=Organism)
    
    # The organ where the experiment or investigation was conducted
    # The Organ class is an alias to ScipyenDataclass, therefore, it only has 
    # two fields: 'name' and 'description' (both strings)
    organ:Organ = dataclasses.field(default_factory = Organ)
    
    # The tissue where the experiment or investigation was conducted
    tissue:Tissue = dataclasses.field(default_factory = Tissue)
    
    # Type of source: ex vivo, in vitro, culture, whole organism, see BioSourceType
    # Default: BioSourceType.exvivo
    sourceType:BioSourceType = dataclasses.field(default=BioSourceType.exvivo)
    
    # Identifier of this source: this can be any meaningful combination of:
    #   animal ID, experimental date,  brain region, etc as long as they are
    #   merged into a single string which is also a valid python identifier i.e.,
    #   satisfies the following rules:
    #
    #   1) contains ONLY alphanumeric characters and underscore ('_')
    #   2) DOES NOT begin with a digit or underscore ('_')
    #
    #   e.g. TS2_1234567_01_02_22_VisCx_
    #
    #   Default: pandas.NA
    sourceID:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)

    # Specific organ structure, if relevant.
    # 
    # For now, only brain atlas api (brainglobe_atlasapi.structure) is supported; 
    # if that is not installed then the descriptor returns a shim object, see the
    # core.bgbridge module.
    #
    # NOTE: 2024-12-13 15:31:40 FIXME
    # accessing this will trigger the lazy initialization of the "mesh" object,
    # and invalidate future comparisons (e.g. see ScipyenDataclass.__eq__ and
    # ScipyenDataclass.diff)
    #
    #   NOTE: 2024-12-13 15:40:14
    #   understand how meshio obejcts are being compared - see meshio package!
    #   
    #   TODO: 2024-12-14 10:17:30 possible fix - no need for the above; because
    #   the meshio objects are dynamically generated, they will ALWAYS be different
    #   (their comparison does NOT compare actual data but rather the id of the 
    #   python object, i.e., their pointer/memory location which is never guaranteed 
    #   to be the same). Therefore I use the strategy below:
    #   a "source" is uniquely determined by its "id" (source id, not python id)
    #   and by the atlas is belongs to; therefore they can be uniquely compared
    #   for equality using only these two attributes (or rather elements of the
    #   source underlying dictionary)
    structure:BGStructureDescriptor = BGStructureDescriptor()

    # Type of cell: string, e.g. "neuron", or pandas NA.
    cellType:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA) 
    
    # Morphological cell variety: string, e.g. "bitufted" or pandas NA.
    cellMorphologicalType:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA) # e.g."pyramidal"
    
    # Additional cell descriptors: sequence of strings, or NA
    cellDescriptors:typing.Union[str, type(pd.NA), typing.Sequence[str]] = dataclasses.field(default=pd.NA)
    
    # Cell identifier - see sourceID for rules
    cellID:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    
    # Cellular compartment, where relevant e.g. "spine", "dendrite", "axon", "soma"
    cellCompartment:CellCompartment = dataclasses.field(default_factory=CellCompartment)
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Procedure(ScipyenDataclass):
    r"""An experimental procedure: what is being done during an Episode.
    
    A succession of procedures (attached to the episodes of a Schedule) 
        represents an experimental protocol.
        
    NOTE: The Treatment class is recommended for use in lieu of generic Procedure
    where procedureType is 'treatment'
    
    """
    # name:str = ""
    _:KW_ONLY
    type: ProcedureType = ProcedureType.null
    # description: str = ""
    
    # __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("type", ) )) # "name" and "description" inherited from ScipyenDataclass
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class SubstanceDosage(ScipyenDataclass):
    r"""Logical mapping between a compund (or substance) and a dose, in a Treatment.
    Fields:
    name:str. Name of the compound (free-form within Python's rules)
    dose: pq.Quantity. This can be:
        • a scalar quantity - unique dose administered during a Treatment
        • a signal-like object:
            ∘ neo.AnalogSignal - a "continuously" time-varying dose, sampled at
                regular time intervals
            ∘ neo.IrregularlySampledSignal - different doses administered at 
                discrete, possibly irregular, times
    """
    name:str = "Vehicle"
    dose: DoseDescriptor = DoseDescriptor()
    # dose: DoseDescriptor = DoseDescriptor(default=None)
    
    # Required for interconversion with HDF5
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("dose", )))
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Treatment(Procedure):
    r"""
    Encapsulates the administration of a dose of substance(s) via a specified route.
    
    name: treatment name (typically, the compound's name)
    substance: SubstanceDosage or sequence (tuple, list) of SubstanceDosage
    
    """
    name:str = "Treatment"
    # Required for interconversion with HDF5
    __match_args__ = tuple(set(Procedure.__match_args__ + ("substance", "route", "type")))
    _:KW_ONLY
    substance:typing.Union[SubstanceDosage, typing.Sequence[SubstanceDosage]] = field(default_factory=SubstanceDosage)
    # allow combination of compounds
    route:AdministrationRoute = AdministrationRoute.null
    
    type:ImmutableDescriptor = ImmutableDescriptor(default=ProcedureType.treatment)
    
    def __post_init__(self):
        super().__init__(name=self.name, description=self.description, 
                         type = ProcedureType.treatment)
        
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Episode(ScipyenDataclass):
    r"""Generic episode for frame-based data.
        NOTE: The `beginFrame` and `endFrame` fields are inclusive indices.
        To use them in indexing a sequence (or frames), add 1 (one) to the 
        `endFrame` field, e.g.:
        range(data.beginFrame, data.endFrame +1)
        An Episode is an elementary part of a Schedule, and is logically associated
        with a Procedure.
        
        The defining attributes are: `name`, `begin`, `end`, `beginFrame`, `endFrame`
        and `procedure`.
        
        In addition, the `description` attribute (a str) has an informative role
        without affecting the identity of an Episode
    """
    # name:str = ""
    _:KW_ONLY
    begin:datetime.datetime = datetime.datetime.now()
    end:datetime.datetime = datetime.datetime.now()
    beginFrame:int = 0
    endFrame:int = 0
    # description:str = ""
    procedure:typing.Optional[Procedure] = field(default = None)
    
    # __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("begin", "end", 
    #                                                               "beginFrame", "endFrame",
    #                                                               "procedure")))
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
# #         if not isinstance(other, self.__class__):
# #             return False
# #         
# #         ret = True
# #         ret &= self.name == other.name
# #         if ret:
# #             # don't compare description as this is not definitory
# #             ret &= all(getattr(self, f.name) == getattr(other, f.name) for f in list(filter(lambda x: x.name != "description", dataclasses.fields(self.__class__))))
# #             
#         return ret
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
@dataclass
class Schedule(ScipyenDataclass):
    r"""Logical grouping of a sequence of episodes.
        A Schedule can be logically considered a "protocol", where any of its
        constituent episodes may associate a Procedure. 
    """
    # name:str = ""
    _:KW_ONLY
    episodes:typing.Sequence[Episode] = field(default_factory = lambda : list())
    
    # __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("episodes",)))
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
#         if not isinstance(other, self.__class__):
#             return False
#         
#         ret = len(self.episodes) == len(other.episodes)
#         
#         if ret:
#             return all(e==e1 for (e,e1) in zip(self.episodes, other.episodes))
#         
#         return ret
    
    def __len__(self)->int:
        return len(self.episodes)
    
    def __getitem__(self, key:typing.Union[int, slice, range, tuple, list, collections.deque, str]):
        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")
            return self.episodes[key]
        
        elif isinstance(key, str):
            if len(self.episodes) == 0:
                raise KeyError(f"Episode named {key} not found")
            
            ret = list(filter(lambda x:x.name == key, self.episodes))
            
            if len(ret) == 0:
                raise KeyError(f"Episode named {key} not found")
            elif len(ret) > 1:
                scipywarn(f"Duplicate episode name ({key}) found")
                
            return ret
        
        elif isinstance(key, slice):
            return self.episodes[key]
        
        elif isinstance(key, range):
            if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
            
            return [self.episodes[k] for k in key]
        
        elif isinstance(key, (tuple, list, collections.deque)):
            if len(key) == 0:
                return list()
            elif all(isinstance(k, int) for k in key):
                if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                    raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
                return [self.episodes[k] for k in key]
            
            else:
                raise KeyError("All indices must be int")
            
        else:
            raise TypeError(f"Invalid indexing key type {type(key).__name__}")
        
    def __setitem__(self, key:typing.Union[int, slice, range, tuple, list, collections.deque], 
                    value:typing.Union[Episode, typing.Iterable[Episode]]):
        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")
            if not isinstance(value, Episode):
                raise TypeError(f"Expecting an Episode; instead, got {type(value).__name__}")
            
            self.episodes[key] = value
        
        elif isinstance(key, slice):
            if not isinstance(value, typing.Iterable):
                raise TypeError(f"The RHS of the assignment must be an iterable; instead, got {type(value).__name__}")
            if not all(isinstance(v, Episode) for v in value):
                raise TypeError(f"The RHS iterable must contain only Episode objects; instead got {unique((type(v).__name__ for v in value))}")
            l_indices = len(range(*key.indices(len(self.episodes))))
            if l_indices < len(value):
                raise ValueError(f"Too many RHS elements ({l_indices}); expecting {len(key)}")
            if l_indices > len(value):
                raise ValueError(f"Too few RHS elements ({l_indices}); expecting {len(key)}")
            
            self.episodes[key] = value
        
        elif isinstance(key, range):
            if not isinstance(value, typing.Iterable):
                raise TypeError(f"The RHS of the assignment must be an iterable; instead, got {type(value).__name__}")
            if not all(isinstance(v, Episode) for v in value):
                raise TypeError(f"The RHS iterable must contain only Episode objects; instead got {unique((type(v).__name__ for v in value))}")
            if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
            if len(key) < len(value):
                raise ValueError(f"Too many RHS elements ({l_indices}); expecting {len(key)}")
            if len(key) > len(value):
                raise ValueError(f"Too few RHS elements ({l_indices}); expecting {len(key)}")
            
            for k in key:
                self.episodes[k] = value[k]
            
        elif isinstance(key, (tuple, list, collections.deque)):
            if len(key) == 0:
                return
            elif all(isinstance(k, int) for k in key):
                if not isinstance(value, typing.Iterable):
                    raise TypeError(f"The RHS of the assignment must be an iterable; instead, got {type(value).__name__}")
                if not all(isinstance(v, Episode) for v in value):
                    raise TypeError(f"The RHS iterable must contain only Episode objects; instead got {unique((type(v).__name__ for v in value))}")
                if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                    raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
                if len(values) > len(key):
                    raise ValueError(f"Too many RHS elements ({l_indices}); expecting {len(key)}")
                if len(values) < len(key):
                    raise ValueError(f"Too few RHS elements ({l_indices}); expecting {len(key)}")
                
                for k in key:
                    self.episodes[k] = value[k]
            else:
                raise KeyError("All indices must be int")
            
        else:
            raise TypeError(f"Invalid indexing key type {type(key).__name__}")
        
    def __delitem__(self, key:typing.Union[int, slice, range, tuple, list, collections.deque, str]):
        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")
            
            del self.episodes[key]
            
        elif isinstance(key, str):
            if len(self.episodes) == 0:
                raise KeyError(f"Episode named {key} not found")
            
            ret = list(filter(lambda x:x.name == key, self.episodes))
            
            if len(ret) == 0:
                raise KeyError(f"Episode named {key} not found")
            
            elif len(ret) > 1:
                scipywarn(f"Duplicate episode name ({key}) found")
                
            keep  = [e for e in self.episodes if e.name != key]

            self.episodes[:] = keep
        
        elif isinstance(key, slice):
             del self.episodes[key]
        
        elif isinstance(key, range):
            if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
            
            keep  = [self.episodes[k] for k in range(len(self.episodes)) if k not in key]
            self.episodes[:] = keep
            
        elif isinstance(key, (tuple, list, collections.deque)):
            if len(key) == 0:
                return
            
            elif all(isinstance(k, int) for k in key):
                if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                    raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
                
                keep  = [self.episodes[k] for k in range(len(self.episodes)) if k not in key]
                self.episodes[:] = keep
            
            # elif all(isinstance(k, str) for k in key):
            #     keep  = [self.episodes[k] for k in range(len(self.episodes)) if k not in key]
            #     self.episodes[:] = keep
            
            else:
                raise KeyError("All indices must be int or str")
            
        else:
            raise TypeError(f"Invalid indexing key type {type(key).__name__}")
        
    def __iter__(self):
        return self.episodes.__iter__()
    
    def __reversed__(self):
        return self.episodes.__reversed__()
    
    def __add__(self, other):
        if isinstance(other, self.__class__):
            newepisodes = self.episodes.__add__(other.episodes)
            return self.__class__(name=self.name, episodes = newepisodes)
            
        elif isinstance(other, typing.Sequence):
            if len(other) and not all(isinstance(e, Episode)):
                raise TypeError("Can only add a sequence of Episodes")
            newepisodes = self.episodes.__add__(other)
            return self.__class__(name=self.name, episodes = newepisodes)
        
        else:
            raise TypeError(f"Invalid argument type ({type(other).__name__})")
            
    def __iadd__(self, other):
        if isinstance(other, self.__class__):
            self.episodes.__iadd__(other.episodes)
            return self
            
        elif isinstance(other, typing.Sequence):
            if len(other) and not all(isinstance(e, Episode)):
                raise TypeError("Can only add a sequence of Episodes")
            self.episodes.__iadd__(other)
            return self
        
        else:
            raise TypeError(f"Invalid argument type ({type(other).__name__})")
        
    def __mul__(self, value:int):
        return self.__class__(name=self.name, episodes = self.episodes.__mul__(value))
            
    def __imul__(self, value:int):
        self.episodes.__imul__(value)
        return self
    
    def __contains__(self, value:Episode):
        return value in self.episodes
    
    def append(self, value:Episode):
        if not isinstance(value, Episode):
            raise TypeError("A Schedule can only contain Episodes")
        
        self.episodes.append(value)
        
    def insert(self, index:int, value:Episode):
        if not isinstance(value, Episode):
            raise TypeError("A Schedule can only contain Episodes")

        self.episodes.insert(index, value)
        
    def pop(self, index:int=-1) -> Episode:
        return self.episodes.pop(index)
    
    def remove(self, value:Episode):
        if not isinstance(value, Episode):
            raise TypeError("A Schedule can only contain Episodes")
        
        self.episodes.remove(value)
        
    def reverse(self):
        self.episodes.reverse()
        
    def sort(self, *args, **kwargs):
        self.episodes.sort(*argsm **kwargs)
    
    def extend(self, value):
        if isinstance(value, self.__class__):
            self.episodes.append(value.episodes)
            
        elif isinstance(value, typing.Sequence):
            if len(value):
                if all(isinstance(v, Episode) for v in value):
                    self.episodes.append(value)
                else:
                    raise TypeError("A Schedule can only contain Episodes")
                    
        else:
            raise TypeError(f"Can only append a Schedule or a sequence of Episodes")
        
    def index(self, episode:Episode):
        if not isinstance(episode, Episode):
            raise TypeError("A Schedule can only contain Episodes")
        if episode not in self.episodes:
            raise ValueError("Episode is not contained in this Schedule")
        
        ndx = [k for k in range(len(self.episodes)) if self.episodes[k] == episode]
        
        return ndx[0]

    def count(self, episode:Episode):
        if not isinstance(episode, Episode):
            raise TypeError("A Schedule can only contain Episodes")
        
        if episode not in self.episodes:
            return 0
        
        return len(e for e in self.episodes if e == episode)
    
        
    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Group:
        
        from iolib import h5io
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
        
        attrs = {"name": getattr(self, "name")}
        
        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)
        
        if isinstance(name, str) and len(name.strip()):
            target_name = name
        
        entity = group.create_group(target_name, track_order=track_order)
        entity.attrs.update(obj_attrs)
        h5io.toHDF5(self.episodes, entity, name="episodes", 
                            oname="episodes", compression=compression,
                            chunks=chunks, track_order=track_order,
                            entity_cache=entity_cache)
        h5io.storeEntityInCache(entity_cache, self, entity)
        return entity
    
    @classmethod
    def fromHDF5(cls, entity:h5py.Group,
                             attrs:typing.Optional[dict] = None, cache:dict={}):
        
        from iolib import h5io
        if entity in cache:
            return cache[entity]
        
        attrs = h5io.attrs2dict(entity.attrs)
        
        name = attrs["name"]
        
        episodes = h5io.fromHDF5(entity["episodes"], cache)
        
        return cls(name, episodes=episodes)
    
    @singledispatchmethod
    def episode(self, ndx) -> Episode:
        raise NotImplementedError(f"Wrong index type: {type(ndx).__name__}")
    
    @episode.register(int)
    def _(self, ndx:int) -> Episode:
        if ndx >= len(self.episodes) or ndx < -1 * len(self.episodes):
            raise IndexError(f"Invalid episode index {ndx} for {len(self.episodes)}")
        
        return self.episodes[ndx]
    
    @episode.register(str)
    def _(self, name:str) -> Episode:
        episodes = [e for e in self.episodes if e.name == name]
        if len(episodes):
            return episodes[0]
        else:
            raise IndexError(f"Episode name {name} does not exist")
        
    def episodeNames(self) -> list[str]:
        return [e.name for e in self.episodes]
    
    def epsodeIndex(self, name:str) -> int:
        return self.episodeNames.index(name)
    
    def addEpisode(self, episode:Episode):
        if episode not in self.episodes:
            self.episodes.append(episode)
            
    def addEpisodes(self, episodes:typing.Sequence[Episode]):
        self.episodes.extend([e for e in episodes if e not in self.episodes])
        
    def removeEpisode(self, episode):
        if episode in self.episodes:
            self.episodes.remove(episode)
            
    @property
    def procedures(self):
        return [e.procedure for e in self.episodes]
    
def isDataclass(o:object):
    r"""Calls dataclasses.is_dataclass(o)
    In case you forget there is such a function 😃
"""
    if not isinstance(o, type):
        o = type(o)
        
    return dataclasses.is_dataclass(o)
        
def mergeDataclasses(typename:str, *args, **kwargs) -> type:
    r"""
Factory function for dynamic dataclass creation.

Purpose:
========
    
The function creates a new dataclass-like type and, optionally, an instance of
it, by merging fields from the dataclass elements in ``*args``. The elements may
be either dataclass types or instances thereof.
    
Use as a convenience to pack parameters as a new dataclass type on-the-fly, 
before instantiating it and passing the instance as parameter to a function that
expects it.
    
ATTENTION: The new class is dynamically created, with the implication that, when
the function is called at the console or in script that is NOT imported as a
module (i.e., a "merged" dataclass type is generated "on the go"), while it MAY
be possible to save an instance of the new class to disk as HDF5 file, or to 
serialise it as pickle, reading it back in a subsequent session WILL FAIL 
(simply because the new type is not available yet, unless the exact same 
type is defined by calling this function BEFORE loading the saved instance from 
HDF5 or pickle file)

NOTE: This is not a problem for "merged" dataclass types defined in one of the 
Scipyen's module automatically imported at the launch, or in a Scipyen plugin
(the "plugin" modules are always imported at the start of a Scipyen session).

However, any changes made to the definition of the merged dataclass (e.g. 
change of field names) will invalidate the saved data. In this case, the
merged dataclass will need to be instantiated again and the new "version"
pickled, or saved to HDF5, to overwrite the old pickle/HDF5 file.

WARNING: All dataclasses that are merged MUST have their field annotated.
    
Parameters:
===========
    typename:str — name of the new type. Must not be empty, and must be a valid
        Python identifier; it will be capitalized if necessary.
    
    args: two or more dataclass types or instances
    
Var-keyword parameters:
=======================
    These are passed to the dataclasses.make_dataclass() function, see Python
documentation for details.
When empty, these parameter get their dfault values as per 
``dataclasses.make_dataclass``.
    
Typically one would use the `module` keyword parameter (with a str value) to 
assign a module to the new type, other than the default ``scipyendataclasses``
so that instances of the new type can be serialized (i.e., pickled and unpickled) 
or exported to / loaded from HDF5 files (see above).
    
Returns:
=======
A tuple containing:
• the new type
• an instance of the new type, if the new type can be instantiated (i.e. all its
fields have default values), else None, in whch case the new type MUST be 
instantiated separately, after "merging"
    
If any of the args are INSTANCES of a dataclass type, then the values of their
parameters will be propagated in the returned instance of the new type.
    
Therefore one may avoid the need to instantiate the new type separately after
"merging" by supplying instances of the original dataclasses, instead of their
types, in args.
    
CAUTION: The dataclasses in args MUST have distinct field names. Fields in 
subequent elements of 'args', that have the same name as fields in args[0] will
be silently ignored. This means that this function should used to augment the 
dataclass in args[0] with non-duplicate fields from the subsequent elements of 
'args'.
    
NOTE:
    1. Any dataclsses.InitVar type of fields in args will NOT be propagated to 
    the new type. This means that the function will not be able to merge dataclasses
    with complex constructors that reply on __post_init__ or InitVar-typed fields.
    
.. _[#]
    
"""
    from copy import deepcopy
    from core.utilities import unique
    
    if not isinstance(typename, str):
        raise TypeError(f"'typename' expected a str; instead, got a {type(typename).__name__}")
    
    if len(typename.strip()) == 0 or not typename.isidentifier():
        raise ValueError(f"Invalid type name {typename}")
    
    if not all(dataclasses.is_dataclass(o) for o in args):
        raise TypeError("Expecting a sequence of dataclasses")
    
    if len(args) < 2:
        raise ValueError("At least two dataclass types or instances are required")
    
    fields = list(map(lambda f: (f.name, f.type, f), dataclasses.fields(args[0])))
    
    bases = list()
    
    master_dict = dict()
    
    argfields = dataclasses.fields(args[0])
    
    if not isinstance(args[0], type):
        for f in argfields:
            master_dict[f.name] = deepcopy(getattr(args[0], f.name))
                
    for arg in args[1:]:
        argfields = dataclasses.fields(arg)
        f_0 = list(map(lambda f: f[0], fields))
        # NOTE: 2025-04-24 22:03:31
        # dataclasses.make_dataclass does NOT allow any field duplicates
        fields.extend(list(map(lambda f: (f.name, f.type, f), filter(lambda x: x.name not in f_0, argfields))))
                
        if not isinstance(arg,type):
            for f in argfields:
                master_dict[f.name] = deepcopy(getattr(arg, f.name))
            
    kwargs.pop("bases", None) # enforce ScipyenDataclass as base class
    
    newtype = dataclasses.make_dataclass(typename, fields, bases=(ScipyenDataclass, ), **kwargs)
    
    nodefaults = list(filter(lambda f: f[2].default is dataclasses.MISSING and f[2].default_factory is dataclasses.MISSING,
                             fields))
    
    if len(nodefaults) and not all(f[0] in master_dict.keys() for f in nodefaults):
        # no value found for these fields in args, indicating that at least
        # some of them were types, not instances
        ret = None
            
    else:
        ret = newtype(**master_dict)
    
    return newtype, ret
        
    # # reminder:
    # # dataclasses.make_dataclass(cls_name, fields, *, bases=(),
    # #                            namespace=None, init=True, 
    # #                            repr=True, eq=True, order=False,
    # #                            unsafe_hash=False, frozen=False, 
    # #                            match_args=True, 
    # #                            kw_only=False, 
    # #                            slots=False, 
    # #                            weakref_slot=False, 
    # #                            module=None)
    
__all__ = ("AdministrationRoute", "BiologicalSource", "Biometrics", "BioSourceType",
           "CellCompartment","CellCompartmentType", "Episode", "Organ", "Organism", 
           "OrganismStage", "Procedure", "ProcedureType", "Schedule", 
           "SubstanceDosage", "Tissue", "Treatment")
