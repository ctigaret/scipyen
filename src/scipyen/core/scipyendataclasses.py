# -*- coding: utf-8 -*-
# $Id: scipyendataclasses.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
# from abc import ABC, ABCMeta, abstractmethod
import collections
# from collections import deque, namedtuple
from functools import singledispatchmethod
import itertools
import datetime
from enum import (Enum, IntEnum, EnumMeta, Flag, auto) #noqa
import inspect
# import numbers
# import math
import dataclasses
from dataclasses import (dataclass, KW_ONLY)
# import sys, os
# import time, datetime
# import traceback
import typing
import types
# import warnings
# import weakref
import h5py
import treelib # noqa
import pathlib
from copy import (deepcopy, copy,) # noqa

#### END core python modules

#### BEGIN 3rd party modules
import pandas as pd
import quantities as pq

#### END 3rd party modules

#### BEGIN pict.core.modules
# from core import utilities
from core import scipyen_quantities as scq
# from core import xmlutils
# from core import strutils
from core.prog import (ImmutableDescriptor, scipywarn)
# from core.datazone import DataZone
# from core.datasignal import (_new_DataSignal, _new_IrregularlySampledDataSignal, DataSignal, IrregularlySampledDataSignal)
# from core import bgbridge
# from core.bgbridge import (BGStructureDescriptor, BrainGlobeAtlas)
# from core import taxonbridge
from core.taxonbridge import TaxonDescriptor
from core.typeenum import TypeEnum
from core.constants import (RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE, # noqa
                            EQUAL_NAN, GENOTYPES) # noqa

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

class ModelFunctionDescriptor:
    def __set_name__(self, obj: object, name: str):
        if len(name.strip()) == 0:
            raise ValueError("Cannot accept an empty name")
        self._name = "_"+name

    def __get__(self, obj:object, objtype:type) -> object:
        if obj is None:
            return #self._default
        return getattr(obj, self._name, None)

    def __set__(self, obj:object, value:typing.Optional[pq.Quantity] = None):
        from core import models
        if isinstance(value, types.FunctionType):
            if not models.isModelFunction(value):
                raise ValueError(f"Expecting a model function; instead, {value.__name__} is an ordinary function")

        elif value is not None:
            raise ValueError(f"Expecting a model function; instead, {value.__name__} is an ordinary function")

        setattr(obj, self._name, value)

class FileOriginDescriptor:
    r"""Use stat() to update the owner's ``file_datetime`` field, if it exists"""
    def __set_name__(self, obj:object, name:str):
        if len(name.strip()) == 0:
            raise ValueError("Cannot accept an empty name")
        self._name = "_"+name

    def __get__(self, obj:object, objtype:type) -> object:
        if obj is None:
            return #self._default
        return getattr(obj, self._name, None)

    def __set__(self, obj: object, value: typing.Optional[
            typing.Union[str, pathlib.Path,
                         typing.Sequence[typing.Union[str, pathlib.Path]]]
            ] = None):
        from iolib.navigation.filesystems import getFileCreationDateTime
        if isinstance(value, typing.Sequence) and all (isinstance(v, (str, pathlib.Path)) for v in value):
            setattr(obj, self._name, value)
            if hasattr(obj, "file_datetime"):
                obj.file_datetime = list(map(lambda f: getFileCreationDateTime(f), value))

        elif isinstance(value, (str, pathlib.Path)):
            setattr(obj, self._name, value)
            if hasattr(obj, "file_datetime"):
                obj.file_datetime = getFileCreationDateTime(value)

        elif value is None:
            setattr(obj, self._name, value)
            if hasattr(obj, "file_datetime"):
                obj.file_datetime = None

        else:
            raise TypeError(f"Expecting a str, pathlib.Path object, or a sequence of these; instead, got a {type(value).__name__}")

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

        diff_fields = tuple(filter(lambda f: type(f[1]) is not type(f[2]) or not safe_identity_test(f[1], f[2]), fields))

        if showValues:
            return dict(map(lambda f: (f[0], (f[1], f[2])), diff_fields))

        return tuple(map(lambda f: f[0], diff_fields))

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return len(self.diff(other)) == 0

    def __hash__(self) -> int:
        return hash((self.name, self.description))

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

    # def merge(self, *others) -> typing.Self:
    #     if len(others) == 0:
    #         return self
    #
    #     if not all(isDataclass(o) for o in others):
    #         raise TypeError("Expecting instances of ScipyenDataclass")
    #
    #     of = tuple(itertools.chain.from_iterable(tuple(map(lambda o: tuple(map(lambda f: (o, f.name), dataclasses.fields(o))),
    #                                                     (parameters, *extra_params)))))
    #
    #     invalid_field_names = tuple(filter(lambda x: x[1] not in self))
    #
    #     if len(invalid_field_names):
    #         raise TypeError(f"Arguments contain the following fields which are invalid for this {type(self).__name__} instance: {invalid_field_names}")
    #
    #     for (o, fname) in of:
    #         setattr(self, fname, getattr(o, fname))
    #
    #     return self

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
                attrs:typing.Optional[dict] = None, cache:dict = dict()):
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

class UltrastructureElementType(TypeEnum):
    r"""Organelles, etc.
    Excludes chemical synapse components e.g. postsynaptic density
    """
    undefined = 0
    plasmalemma = auto()
    cytosol = auto()
    actin_filament = auto()
    spine_apparatus = auto()
    myosin_filament = auto()
    actomyosin = actin_filament + myosin_filament
    microtubule = auto()
    mitotic_spindle = auto()
    centriole = auto()
    cytoskeleton = sum(
            (
                actomyosin,
                spine_apparatus,
                microtubule,
                mitotic_spindle,
                centriole,
            )
        )
    ribosome = auto() # includes polyribosomes
    lysosome = auto()
    endosome = auto()
    clathrin_coated = auto()
    dynamin_associated = auto()
    endocytotic = clathrin_coated + dynamin_associated
    secretory_vesicle = auto()
    synaptic_granule = auto()
    synaptic_vesicle = auto()
    transport_vesicle = auto()
    exocytotic = sum(
            (
                secretory_vesicle,
                synaptic_granule,
                synaptic_vesicle,
            )
        )
    endoplasmic_reticulum = auto()
    vacuole = auto()
    er = endoplasmic_reticulum
    rough_endoplasmic_reticulum = ribosome + endoplasmic_reticulum
    vesicle = endocytotic + exocytotic
    golgi_cisterna = auto()
    golgi_cis = auto()
    golgi_trans = auto()
    golgi_apparatus = sum(
            (
                golgi_cisterna,
                golgi_cis,
                golgi_trans,
            )
        )
    nuclear_envelope = auto()
    nuclear_pore = auto()
    nucleolus = auto()
    heterochromatin = auto()
    euchromatin = auto()
    chromatin = heterochromatin + euchromatin
    chromosome = auto()
    nucleus = sum(
            (
                nuclear_envelope,
                nuclear_pore,
                nucleolus,
                chromatin,
            )
        )
    inclusion = auto()
    mitochondrial_matrix = auto()
    mitochondrial_cristae = auto()
    inner_mitochondrial_membrane = mitochondrial_cristae
    outer_mitochondrial_membrane = auto()
    mitochondria = sum(
            (
                inner_mitochondrial_membrane,
                outer_mitochondrial_membrane,
                mitochondrial_matrix
            )
        )
    membrane_bound = sum(
            (
                lysosome,
                endosome,
                vesicle,
                golgi_apparatus,
                vacuole,
                nucleus,
                mitochondria
            )
        )

    organelle = sum(
            (
                membrane_bound,
                cytoskeleton,
                ribosome,
                inclusion
            )
        )

    cytoplasm = cytosol + organelle

    whole_cell = cytoplasm + plasmalemma

    other = auto()

class GeneticSex(TypeEnum):
    undefined = 0
    female = 1
    male = 2

class ProcedureType(TypeEnum):
    null = 0
    mating = auto()
    treatment = auto()
    behaviour = auto() # includes motor functions
    surgery = auto()
    biopsy = auto()
    postop = auto()
    recovery = auto()
    tagging = auto()
    weaning = auto()
    cull = auto()
    other = auto()

class DevelopmentalStage(TypeEnum):
    undefined   = 0
    zygote      = auto()
    morula      = auto()
    blastula    = auto()
    gastrula    = auto()
    embryo      = zygote | morula | blastula | gastrula # = 15
    foetal      = auto()
    prenatal = embryo | foetal # = 31
    larva       = auto()
    pup         = larva
    prepubertal = larva
    preweaning  = prepubertal
    adolescent  = auto()
    adult       = auto()
    juvenile    = larva | adolescent # = 65
    postnatal   = larva | adolescent | adult # = 99

class AdministrationRoute(Flag):
    null = 0
    bath = auto() # relates to ex vivo tissue slices
    bulk = bath
    puff = auto() # relates to ex vivo tissue slices — e.g. picospritzer, pressurized micropipette, etc
    intraperitoneal = auto()
    ip = intraperitoneal
    intramuscular = auto()
    im = intramuscular
    intravenous = auto()
    iv = intravenous
    intraarterial = auto()
    ia = intraarterial
    intracerebral = auto() # must specify target structure via atlas reference
    ic = intracerebral
    intracerebroventricular = auto()
    icv = intracerebroventricular
    intracardiac = auto()
    icd = intracardiac
    intracardioventricular = auto()
    icdv = intracardioventricular
    subcutaneous = auto()
    sc = subcutaneous
    intradermal = auto()
    idr = intradermal # id is a python keyword
    transcutaneous = auto()
    tc = transcutaneous
    peros = auto()
    gavage = peros
    oral = peros
    inhalation = auto()
    inh = inhalation
    intranasal = auto()
    ins = intranasal # 'in' is a reserved Python keyword
    intraorbital = auto()
    io = intraorbital
    eye_drops = auto()
    food_water = auto()
    other = auto()
    custom = other

class BioSourceType(TypeEnum):
    undefined   = 0
    insilico    = auto()    # biological/biophysical/mathematical model
    exvivo      = auto()    # tissue or organ sample from organism
    invitro     = auto()    # culture system, homogenate
    invivo      = auto()    # e.g. in vivo imaging, electrophysiology, etc
    # organism    = auto()    # for behaviour and systemic measurements (temperature, mass, motor function, etc)
    organ       = auto()    # e.g. isolated heart, aorta, ileum, 33
    organoid    = invitro | organ
    assembloid  = organoid # i.e, 34
    tissue      = auto()    # e.g. aortic strip, teania caeci/coli, etc
    acute_slice = exvivo | tissue # e.g. acute brain slice = exvivo | tissue = 17
    organotypic = invitro | tissue # e.g. "organotypic" slice culture = invitro | tissue  = 18
    cell        = auto()
    monolayer   = invitro | cell # dissociated cells, cultured, possibly confluent
    culture     = monolayer
    thrombocyte = auto()
    platelet    = thrombocyte
    compartment = auto()
    ultrastructure = auto()
    product     = auto()

# NOTE 2026-07-11 17:26:11
# Note to self: BioSourceType ↦ Specimen types -> parent types:
# insilico ↦ ~ any
#
# exvivo ↦ Organism
#        ↦ Organ   -> Organism
#        ↦ Tissue  -> Organ -> Organism
#        ↦ NervousSystem -> Organism
#
#        ↦ Cell -> Organ -> Organism
#               -> Tissue -> Organ -> Organism
#
#        ↦ Neuron -> NervousSystem -> Organism
#                 -> Tissue -> Organ -> Organism
#                 -> Organ -> Organism
#
# invitro ↦ BiologicalProduct -> Organism
#                             -> Organ -> Organism
#                             -> Tissue -> Organ -> Organism
#                             -> Cell -> Organ -> Organism
#                                     -> Tissue -> Organ -> Organism
#                             -> Neuron -> NervousSystem -> Organism
#                                       -> Tissue -> Organ -> Organism
#                                       -> Organ -> Organism
#         ↦ Cell -> Organ -> Organism
#                -> Tissue -> Organ -> Organism
#
#         ↦ Neuron -> NervousSystem -> Organism
#                  -> Tissue -> Organ -> Organism
#                  -> Organ -> Organism
#
# invivo  ↦ BiologicalProduct -> Organism
#                             -> Organ -> Organism
#                             -> Tissue -> Organ -> Organism
#                             -> Cell -> Organ -> Organism
#                                     -> Tissue -> Organ -> Organism
#                             -> Neuron -> NervousSystem -> Organism
#                                       -> Tissue -> Organ -> Organism
#                                       -> Organ -> Organism
#         ↦ Cell -> Organ -> Organism
#                -> Tissue -> Organ -> Organism
#
#         ↦ Neuron -> NervousSystem -> Organism
#                  -> Tissue -> Organ -> Organism
#                  -> Organ -> Organism
#
# organism ↦ Organism
#
# organ    ↦ Organ -> Organism
#
# tissue   ↦ Tissue -> Organ -> Organism
#
# cell     ↦ Cell -> Organ -> Organism
#                -> Tissue -> Organ -> Organism
#
#          ↦ Neuron -> NervousSystem -> Organism
#                   -> Tissue -> Organ -> Organism
#                   -> Organ -> Organism
# compartment ↦ CellCompartment -> Cell -> Tissue -> Organ -> Organism
#                                       -> Organ -> Organism
#
#             ↦ NeuronCompartment -> Neuron -> NervousSystem -> Organism
#                                           -> Tissue -> Organ -> Organism
#                                           -> Organ -> Organism
#
#             ↦ ChemicalSynapse -> NervousSystem -> Organism
#                               -> Tissue -> Organ -> Organism
#                               -> Organ
#
# ultrastructure ↦ UltrastructureElement -> Cell -> ...
#                                        -> Neuron -> ...
#
# product ↦ BiologicalProduct

# class Organism :
#     pass

class BioProductType(TypeEnum):
    undefined = 0
    homogenate  = auto()
    cell_fraction = auto()
    serum       = auto()
    plasma      = auto()
    blood       = serum | plasma
    secretion   = auto()
    urine       = auto()
    faeces      = auto()
    excretion   = urine | faeces
    exudate     = auto()
    pus         = auto()

class NeuronType(TypeEnum):
    r"""Generic classification of neurons beyond that of NeuroMorpho.org
    (pyramidal, non-pyramidal principal, and interneurons).
    """
    undefined = 0
    pyramidal = auto()
    stellate = auto()
    granule = auto()
    msn = auto()
    drg = auto()
    nonpyramidal = sum(
            (
                stellate,
                granule,
                msn,
                drg
            )
        )
    principal = pyramidal + nonpyramidal
    interneuron = auto()
    inhibitory = auto()
    other = auto()

class CellCompartmentType(TypeEnum):
    r"""Inspired by SWC/CNIC specification at
    http://www.neuronland.org/NLMorphologyConverter/MorphologyFormats/SWC/Spec.html

    Refers to "gross" compartments; for a more granular types see
    NeuronCompartment, AxonalCompartment and DendriticCompartment
    """
    undefined = 0
    cell = undefined
    organelle = auto()
    cilium = auto()
    flagellum = auto()
    microvillus = auto()
    filopodium = auto()
    lamellipodium = auto()
    body = auto()

class NeuronCompartmentType(TypeEnum):
    undefined = 0
    cell = undefined
    organelle = auto()
    soma = auto()
    axon = auto()
    dendrite = auto()
    chemical_synapse = auto()

class AxonalCompartmentType(TypeEnum):
    undefined = 0
    initial = auto() # axon initial segment
    node = auto() # Ranvier's node
    internode = auto() # axon segment between two consecutive Ranvier nodes
    myelin = auto() # myelin sheath
    bouton = auto() # axonal bouton, "en passant"
    terminal_bouton = auto()
    arborization = auto()
    collateral = auto()
    other = auto()

class DendriticCompartmentType(TypeEnum):
    undefined = 0
    basal = auto() # basal dendrite, shaft
    apical = auto()# apical dendrite, shaft
    fork = auto()# dendritic branch point
    end = auto()# dendritic end point
    tuft = auto()# apical tuft
    shaft = auto()
    spine = auto()
    spine_head = auto()
    spine_neck = auto()
    spine_apparatus = auto()
    other = auto()

class ChemicalSynapseUltrastructureElementType(TypeEnum):
    undefined = 0
    presynaptic_membrane = auto()
    presynaptic_cytoskeleton = auto()
    presynaptic_vesicle = auto()
    presynaptic_docked = auto()
    rrp = presynaptic_docked
    presynaptic_recycling_pool = auto()
    presynaptic_reserve_pool = auto()
    presynaptic_vesicles = sum(
            (
                presynaptic_vesicle,
                presynaptic_docked,
                presynaptic_recycling_pool,
                presynaptic_reserve_pool
            )
        )
    active_zone = auto() # presynaptic active zone
    presynaptic_compartment = sum(
            (
                presynaptic_membrane,
                presynaptic_cytoskeleton,
                presynaptic_vesicles,
                active_zone
            )
        )
    postsynaptic_membrane = auto()
    postsynaptic_cytoskeleton = auto()
    psd = auto() # postsynaptic density
    postsynaptic_compartment = sum(
            (
                postsynaptic_membrane,
                postsynaptic_cytoskeleton,
                psd
            )
        )
    perisynaptic = auto()
    extrasynaptic = auto()
    cleft = auto()

# class PostsynapticEntityType(TypeEnum):
#     undefined = 0
#     soma = auto()
#     dendrite = auto()
#     spine = auto()
#     axon = auto()

class ChemicalSynapseFunctionalType(TypeEnum):
    undefined = 0
    excitatory = auto()
    inhibitory = auto()

class ChemicalSynapseMorphologicalType(TypeEnum):
    undefined = 0
    symmetrical = auto()
    asymmetrical = auto()
    glomerulus = auto() # cerebellar glomerulus
    mossy = auto() # hippocampal mossy fibre synapse
    calyx = auto() # calyx of Held
    nmj = auto() # neuromuscular junction
    volume = auto()
    other = auto()

class Neurotransmitter(TypeEnum):
    undefined = 0
    Glutamate = auto()
    Glycine = auto()
    GABA = auto()
    Acetylcholine = auto()
    Adrenaline = auto()
    Epinephrine = Adrenaline
    Noradrenaline = auto()
    Norepinephrine = Noradrenaline
    Dopamine = auto()
    Histamine = auto()
    Serotonin = auto()
    Tyramine = auto()
    Octopamine = auto()
    Endorphins = auto()
    Endocannabinoids = auto()
    Neuropeptide = auto()
    SubstanceP = Neuropeptide
    ATP = auto()
    Purines = ATP
    NO = auto()
    EDRF = NO

# class PlasmaMembraneSpecializationType(TypeEnum):
#     undefined = 0
#     chemical_synapse = auto()
#     neural_synapse = chemical_synapse
#     gap_junction = auto() # electrical synapse
#     electrical_synapse = gap_junction
#     zonula_occludens = auto()
#     zonula_adherens = auto()
#     synapse = auto() # generic synapse including immunological synapse
#     caveolae = auto()

@dataclass
class Biometrics(ScipyenDataclass):
    # genotype of the source - keep it simple
    #
    # NOTE: avoid strings like (+/-, TSNeo/-, etc) as they don't play well when
    # importing data in, say, R
    # These are entirely conventional, and, within the same line of genetic
    # animal model they would have a well-defined meaning
    #
    genotype: typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)

    geneticSex: GeneticSex = GeneticSex.undefined
    # ID of source sex (where appropriate); one of "f", "m", "na" (case-insensitive)
    #
    stage: DevelopmentalStage = DevelopmentalStage.postnatal

    age: typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)

    #
    # NOTE: these are simply for a quick information; in the future Scipyen will
    # provide a more standardized way to store this information, hopefully more
    # suitable to some sort of database management

    weight:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    height:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)

    def __repr__(self):
        # indent = lambda x: x.replace("\n", "\n\t") # noqa
        # repr_attr = lambda x: (f": {type(x).__name__} → '{x}'" if isinstance(x, str)
        #                        else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x))
        #                        else f": {type(x).__name__} → {x.name} ({x})" if isinstance(x, Enum)
        #                        else f": {type(x).__name__} → {x}") # noqa
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

@dataclass
class Organism(ScipyenDataclass):
    taxon: TaxonDescriptor = TaxonDescriptor()
    subspecies: str = ""
    strain: str = ""

    biometrics: Biometrics = dataclasses.field(default_factory=Biometrics)
    ID: typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)

    def __repr__(self):
        # indent = lambda x: x.replace("\n", "\n\t") # noqa
        # repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x.name}" if isinstance(x, Enum) else f": {type(x).__name__} → {x}" # noqa
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    @property
    def genotype(self):
        if isinstance(self.biometrics, Biometrics):
            return self.biometrics.genotype

    @genotype.setter
    def genotype(self, val: typing.Optional[str]):
        if isinstance(self.biometrics, Biometrics):
            if isinstance(val, str) and len(val.strip()):
                self.biometrics.genotype = val
            else:
                self.biometrics.genotype = pd.NA

    @property
    def age(self):
        if isinstance(self.biometrics, Biometrics):
            return self.biometrics.age

    @age.setter
    def age(self, val: typing.Optional[pq.Quantity]):
        from core import scipyen_quantities as scq
        if isinstance(self.biometrics, Biometrics):
            if isinstance(val, pq.Quantity) and scq.checkTimeUnits(val.units):
                self.biometrics.age = val
            else:
                self.biometrics.age = pd.NA

    @property
    def sex(self):
        if isinstance(self.biometrics, Biometrics):
            return self.biometrics.geneticSex

    @sex.setter
    def sex(self, val: typing.Optional[GeneticSex]):
        if isinstance(self.biometrics, Biometrics):
            if isinstance(val, GeneticSex):
                self.biometrics.sex = val
            else:
                self.biometrics.sex = GeneticSex.undefined

    @property
    def stage(self):
        if isinstance(self.biometrics, Biometrics):
            return self.biometrics.stage

    @stage.setter
    def stage(self, val: typing.Optional[DevelopmentalStage]):
        if isinstance(self.biometrics, Biometrics):
            if isinstance(val, DevelopmentalStage):
                self.biometrics.stage = val
            else:
                self.biometrics.stage = DevelopmentalStage.undefined


    @property
    def weight(self):
        if isinstance(self.biometrics, Biometrics):
            return self.biometrics.weight

    @weight.setter
    def weight(self, val: typing.Optional[pq.Quantity]):
        if isinstance(self.biometrics, Biometrics):
            if isinstance(val, pq.Quantity):
                self.biometrics.weight = val
            else:
                self.biometrics.weight = pd.NA

    @property
    def height(self):
        if isinstance(self.biometrics, Biometrics):
            return self.biometrics.height

    @height.setter
    def height(self, val: typing.Optional[pq.Quantity]):
        if isinstance(self.biometrics, Biometrics):
            if isinstance(val, pq.Quantity):
                self.biometrics.height = val
            else:
                self.biometrics.height = pd.NA

    def getOrganism(self) -> typing.Self:
        return self

    def setOrganism(self, value: typing.Self):
        return

@dataclass
class BiologicalProduct(ScipyenDataclass):
    r"""Biological product (not cell, tissue, organ or organism)"""
    parentType: typing.ClassVar[
                typing.Tuple[ScipyenDataclass]
        ] = (Organism, )

    type: BioProductType = dataclasses.field(default = BioProductType.undefined)

    parent: Organism = dataclasses.field(default_factory = Organism)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

    def getOrganism(self):
        return self.parent

    def setOrganism(self, value: Organism | None):
        if isinstance(value, Organism):
            self.parent = value
        else:
            self.parent = Organism()

@dataclass
class Organ(ScipyenDataclass):
    parentTypes: typing.ClassVar[
                typing.Tuple[ScipyenDataclass]
        ] = (Organism, )

    parent: Organism = dataclasses.field(default_factory = Organism)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

    def getOrganism(self) -> Organism:
        if isinstance(self.parent, Organism):
            return self.parent
        return Organism()

    def setOrganism(self, value: Organism):
        # print(f"{self.__class__.__name__}.setOrganism({value})")
        if isinstance(value, Organism):
            self.parent=value
        else:
            self.parent=Organism()

@dataclass
class NervousSystem(Organ):
    r"""
    Nervous system.

    The name of this class is slightly misleading, as it encompasses ANY anatomical
    structure defined in a BrainGlobeAtlas, including those OUTSIDE the brain itself,
    e.g., spinal cord, etc.
    """
    from core.bgbridge import BGStructureDescriptor

    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (Organism, )

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
    atlasName: typing.Union[str, type(pd.NA)] = pd.NA

    structure: BGStructureDescriptor = BGStructureDescriptor()

    parent: Organism = dataclasses.field(default_factory = Organism)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

    @property
    def name(self) -> str:
        return "NervousSystem"

    @name.setter
    def name(self, val:str):
        return

    def __hash__(self) -> int:
        return hash((self.atlasName))

Brain = NervousSystem # alias for backward copmatibility

@dataclass
class Tissue(ScipyenDataclass):
    r"""Tissue"""
    parentTypes: typing.ClassVar[
                typing.Tuple[ScipyenDataclass]
        ] = (Organ, NervousSystem)

    parent: typing.Union[Organ, NervousSystem] = dataclasses.field(default_factory = Organ)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

    def getOrganism(self):
        return self.parent.getOrganism()

    def setOrganism(self, value: Organism):
        # print(f"{self.__class__.__name__}.setOrganism({value})")
        if isinstance(value, Organism):
            self.parent.setOrganism(value)
        else:
            self.parent.setOrganism(Organism())

@dataclass
class Cell(ScipyenDataclass):
    parentTypes: typing.ClassVar[
                typing.Tuple[ScipyenDataclass]
        ] = (Organ, Tissue, NervousSystem)

    cellType: typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA) # e.g., "neuron", "glia", etc

    cellSubType: typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA) # e.g."pyramidal", "astrocyte", "microglia", "muscle_fibre", etc

    parent: typing.Union[Organ, Tissue] = dataclasses.field(default_factory = Tissue)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

    def getOrganism(self):
        return self.parent.getOrganism()

    def setOrganism(self, value: Organism):
        # print(f"{self.__class__.__name__}.setOrganism({value})")
        if isinstance(value, Organism):
            self.parent.setOrganism(value)
        else:
            self.parent.setOrganism(Organism())

@dataclass
class Neuron(Cell):
    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (Organ, Tissue, NervousSystem)

    cellSubType: NeuronType = NeuronType.undefined

    parent: typing.Optional[typing.Union[Organ, Tissue, NervousSystem]] = dataclasses.field(default_factory = NervousSystem)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

    @property
    def cellType(self) -> str:
        return "Neuron"

    @cellType.setter
    def cellType(self, val:str):
        return

@dataclass
class CellCompartment(ScipyenDataclass):
    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (Cell, )

    compartmentType: CellCompartmentType = CellCompartmentType.undefined

    parent: Cell = dataclasses.field(default_factory = Cell)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

    def __repr__(self):
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def getOrganism(self):
        return self.parent.getOrganism()

    def setOrganism(self, value: Organism):
        # print(f"{self.__class__.__name__}.setOrganism({value})")
        if isinstance(value, Organism):
            self.parent.setOrganism(value)
        else:
            self.parent.setOrganism(Organism())

@dataclass
class NeuronCompartment(CellCompartment):
    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (Neuron, )

    compartmentType: NeuronCompartmentType = NeuronCompartmentType.undefined

    parent: Neuron = dataclasses.field(default_factory = Neuron)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"
        assert isinstance(self.compartmentType, NeuronCompartmentType), f"Wrong compartment type: {self.compartmentType}"

    def __repr__(self):
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

@dataclass
class AxonalCompartment(NeuronCompartment):
    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (Neuron, )

    compartmentType: AxonalCompartmentType = AxonalCompartmentType.undefined

    parent: Neuron = dataclasses.field(default_factory = Neuron)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"
        assert isinstance(self.compartmentType, AxonalCompartmentType), f"Wrong compartment type: {self.compartmentType}"

@dataclass
class DendriticCompartment(NeuronCompartment):
    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (Neuron, )

    compartmentType: DendriticCompartmentType = DendriticCompartmentType.undefined

    parent: Neuron = dataclasses.field(default_factory = Neuron)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"
        assert isinstance(self.compartmentType, DendriticCompartmentType), f"Wrong compartment type: {self.compartmentType}"

class UltrastructureElement:
    pass

@dataclass
class ChemicalSynapse(ScipyenDataclass):
    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (CellCompartment, UltrastructureElement)

    morphologicalType : ChemicalSynapseMorphologicalType = ChemicalSynapseMorphologicalType.undefined
    functionalType: ChemicalSynapseFunctionalType = ChemicalSynapseFunctionalType.undefined
    # postsynapticEntityType: PostsynapticEntityType = PostsynapticEntityType.undefined
    postsynaptic: typing.Union[CellCompartment, UltrastructureElement] = dataclasses.field(default_factory = NeuronCompartment)
    presynaptic: typing.Union[CellCompartment, UltrastructureElement] = dataclasses.field(default_factory = NeuronCompartment)
    transmitter: Neurotransmitter = Neurotransmitter.undefined
    retrograde: bool = False

    def __post_init__(self: typing.Self):
        assert isinstance(self.presynaptic, self.parentTypes), f"Wrong presynaptic component: {type(self.presynaptic).__name__}"
        assert isinstance(self.postsynaptic, self.parentTypes), f"Wrong postsynaptic component: {type(self.postsynaptic).__name__}"

    def getOrganism(self):
        if all(isinstance(p, (CellCompartment, NeuronCompartment)) for p in (self.postsynaptic, self.presynaptic)):
            organisms = tuple(map(lambda p: p.getOrganism(), (self.postsynaptic, self.presynaptic)))
            if organisms[0] == organisms[1]:
                return organisms[0]

    def setOrganism(self, organism: Organism):
        # print(f"{self.__class__.__name__}.setOrganism({organism})")
        if not isinstance(organism, Organism):
            organism = Organism()

        for parent in (self.preSynapticParent, self.postSynapticParent):
            parent.setOrganism(organism)

@dataclass
class UltrastructureElement(ScipyenDataclass):
    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (Cell, Neuron, NeuronCompartment, AxonalCompartment,
             DendriticCompartment,
             CellCompartment,
             ChemicalSynapse, Tissue, Organ)

    elementType: UltrastructureElementType = UltrastructureElementType.undefined

    parent: typing.Union[Cell, Neuron, NeuronCompartment, AxonalCompartment,
             DendriticCompartment,
             CellCompartment,
             ChemicalSynapse, Tissue, Organ] = dataclasses.field(default_factory = Cell)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

    def getOrganism(self):
        return self.parent.getOrganism()

    def setOrganism(self, value: Organism):
        # print(f"{self.__class__.__name__}.setOrganism({value})")
        if isinstance(value, Organism):
            self.parent.setOrganism(value)
        else:
            self.parent.setOrganism(Organism())

@dataclass
class ChemicalSynapseUltrastructureElement(UltrastructureElement):
    parentTypes: typing.ClassVar[
            typing.Tuple[ScipyenDataclass]
        ] = (ChemicalSynapse,)

    elementType: ChemicalSynapseUltrastructureElementType = ChemicalSynapseUltrastructureElementType.undefined # noqa

    parent: ChemicalSynapse = dataclasses.field(default_factory = ChemicalSynapse)

    def __post_init__(self: typing.Self):
        assert isinstance(self.parent, self.parentTypes), f"Wrong parent: {type(self.parent).__name__}"

@dataclass
class BiologicalSource(ScipyenDataclass):
    r"""Source of measurement data.
    Encapsulates the biological source for the data measured in an experiment or
    investigation.
    This may be an entire organism, an organ, tissue, individual cell, or
    subcellular compartment.
    """

    # The organism of this source.
    # Contains the data related to the taxon, species, subspecies, strain, and
    # biometrics.
    # See Organism class in this module
    # organism:Organism = dataclasses.field(default=Organism("rat"))
    # organism:Organism = dataclasses.field(default_factory = Organism)

    # specimenTypes: typing.ClassVar[
    #             typing.Tuple[ScipyenDataclass]
    #     ] = (
    #             Organism,
    #             Organ,
    #             NervousSystem,
    #             Tissue,
    #             Cell,
    #             Neuron,
    #             CellCompartment,
    #             NeuronCompartment,
    #             AxonalCompartment,
    #             DendriticCompartment,
    #             ChemicalSynapse,
    #             UltrastructureElement,
    #             ChemicalSynapseUltrastructureElement,
    #             BiologicalProduct,
    #         )


    # NOTE: 2026-07-12 13:46:12 TODO
    # preparing API for being more selective to what Python type of
    # specimen is allowed, contingent on the sourceType field according to the
    # class variable sourceSpecimenTypeMap.
    #
    # ATTENTION: Not implemented yet.
    # Needs (TODO):
    # 1) specimen field redefined as a descriptor field, where
    # the Python type of specimen object is checked against the
    # value of the sourceType field.
    #
    # 2) sourceType field redefined as descriptor field, where
    # the setter would also check the Python type of the specimen
    # optionally prompting to a change (or instantiate a default
    # specimen compliant with the sourceSpecimenTypeMap)
    #
    # CAUTION: Until the above is implemented, all code assumes that all specimen
    # Python types are admissible, as if sourceType was BioSourceType.undefined
    #


    sourceSpecimenTypeMap: typing.ClassVar[
        dict[BioSourceType, typing.Tuple[type]]
        ] = {
            BioSourceType.undefined: (
                                        Organism,
                                        Organ,
                                        NervousSystem,
                                        Tissue,
                                        Cell,
                                        Neuron,
                                        CellCompartment,
                                        NeuronCompartment,
                                        AxonalCompartment,
                                        DendriticCompartment,
                                        ChemicalSynapse,
                                        UltrastructureElement,
                                        ChemicalSynapseUltrastructureElement,
                                        BiologicalProduct,
                                    ),
            BioSourceType.insilico: (
                                        Organism,
                                        Organ,
                                        NervousSystem,
                                        Tissue,
                                        Cell,
                                        Neuron,
                                        CellCompartment,
                                        NeuronCompartment,
                                        AxonalCompartment,
                                        DendriticCompartment,
                                        ChemicalSynapse,
                                        UltrastructureElement,
                                        ChemicalSynapseUltrastructureElement,
                                        BiologicalProduct,
                                    ),
            BioSourceType.exvivo: (Organ, NervousSystem, Tissue,
                                   Cell, Neuron,
                                   CellCompartment,
                                   NeuronCompartment,
                                   AxonalCompartment,
                                   DendriticCompartment,
                                   ChemicalSynapse,
                                   UltrastructureElement,
                                   ChemicalSynapseUltrastructureElement,
                                   BiologicalProduct
                                   ),

            BioSourceType.invitro: (Organ, Tissue, Cell, Neuron,
                                    CellCompartment, NeuronCompartment,
                                    AxonalCompartment, DendriticCompartment,
                                    ChemicalSynapse,
                                    UltrastructureElement,
                                    ChemicalSynapseUltrastructureElement,
                                    BiologicalProduct
                                    ),

            BioSourceType.invivo: (Organism, Organ,
                                   NervousSystem,
                                   Tissue,
                                   Cell,
                                   Neuron,
                                   ),

            BioSourceType.organ: (Organ,
                                  NervousSystem
                                  ),
            BioSourceType.organoid: (Organ,
                                     NervousSystem
                                     ),
            BioSourceType.assembloid: (Organ,
                                       NervousSystem
                                       ),
            BioSourceType.tissue: (Organ,
                                   NervousSystem,
                                   Tissue
                                   ),
            BioSourceType.acute_slice: (Organ,
                                        NervousSystem,
                                        Tissue,
                                        Cell,
                                        Neuron,
                                        CellCompartment,
                                        NeuronCompartment,
                                        AxonalCompartment,
                                        DendriticCompartment,
                                        ChemicalSynapse
                                        ),
            BioSourceType.organotypic: (Organ,
                                        NervousSystem,
                                        Tissue,
                                        Cell,
                                        Neuron,
                                        CellCompartment,
                                        NeuronCompartment,
                                        AxonalCompartment,
                                        DendriticCompartment,
                                        ChemicalSynapse
                                        ),
            BioSourceType.cell: (Cell,
                                 Neuron,
                                 CellCompartment,
                                 NeuronCompartment,
                                 AxonalCompartment,
                                 DendriticCompartment,
                                 ChemicalSynapse,
                                 ChemicalSynapseUltrastructureElement,
                                 UltrastructureElement,
                                 ),

            BioSourceType.thrombocyte: (Cell,),
            BioSourceType.platelet: (Cell,),
            BioSourceType.compartment: (ChemicalSynapse,
                                        CellCompartment,
                                        NeuronCompartment,
                                        AxonalCompartment,
                                        DendriticCompartment,
                                        UltrastructureElement,
                                        ChemicalSynapseUltrastructureElement
                                        ),
            BioSourceType.ultrastructure: (UltrastructureElement,
                                           ChemicalSynapseUltrastructureElement,
                                           ),
            BioSourceType.product: (BiologicalProduct, ),
            }

    # Type of source: ex vivo, in vitro, culture, whole organism, see BioSourceType
    # Default: BioSourceType.exvivo
    sourceType:BioSourceType = dataclasses.field(
        default = BioSourceType.exvivo
        )

    # Specimen where the experiment or investigation was conducted:
    # Organ, Tissue, or Cell (if Cell, its 'parent' — Organ or Tissue — should
    # also be specified)
    # Equivalent to the unit of analysis
    specimen: typing.Union[
        Organism,
        Organ,
        NervousSystem,
        Tissue,
        Cell,
        CellCompartment,
        ChemicalSynapse,
        UltrastructureElement,
        ChemicalSynapseUltrastructureElement,
        BiologicalProduct,
        ] = dataclasses.field(
                default_factory = Cell
            )

    def __post_init__(self: typing.Self):
        # NOTE: 2026-07-12 13:32:00
        # below, keep it general
        assert isinstance(self.specimen, self.sourceSpecimenTypeMap[BioSourceType.undefined]), f"Wrong specimen: {type(self.specimen).__name__}"

    def __repr__(self):
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def getOrganism(self):
        return self.specimen.getOrganism()

    def setOrganism(self, value: Organism):
        if not isinstance(value, Organism):
            value = Organism()

        if isinstance(self.specimen, Organism):
            self.specimen = value

        else:
            self.specimen.setOrganism(value)

    @property
    def specimenTypes(self) -> tuple[type]:
        r"""For backward compatibility"""
        return self.sourceSpecimenTypeMap[BioSourceType.undefined]

# ------------------------------------------------------------------------------

class PPLProtocol: pass # noqa
class PPLProtocolStep: pass # noqa

@dataclass
class PPL(ScipyenDataclass):
    ID: str = ""
    holderName: str = ""
    holderEmail: str = ""
    protocols: list[PPLProtocol] = dataclasses.field(default_factory=list)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash((self.name, self.description, self.ID, self.holderName, self.holderEmail))

@dataclass
class PIL(ScipyenDataclass):
    ID: str = ""
    holderName: str = ""
    holderEmail: str = ""

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash((self.name, self.description, self.ID, self.holderName, self.holderEmail))

@dataclass
class PPLProtocol(ScipyenDataclass):
    ID: str = dataclasses.field(default_factory = str)
    parent: PPL = dataclasses.field(default_factory = PPL)
    steps: list[PPLProtocolStep] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        # check that the instance is among the authorized protocols of the parent
        # (a PPL)
        if len(self.parent.protocols) and self not in self.parent.protocols:
            scipywarn(f"This PPL Protocol ({self.name}, ID: {self.ID}) does not appear to be authorized in the PPL {self.parent.name} (ID: {self.parent.ID})")

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash((self.name, self.description, self.ID, self.parent))


@dataclass
class PPLProtocolStep(ScipyenDataclass):
    ID: str = dataclasses.field(default_factory = str)
    parent: PPLProtocol = dataclasses.field(default_factory = PPLProtocol)

    def __post_init__(self):
        # check that the instance is among the authorized steps of the parent
        # (a PPLProtocol)
        if len(self.parent.steps) and self not in self.parent.steps:
            scipywarn(f"This PPL Protocol Step ({self.name}, ID: {self.ID}) does not appear to be authorized in the protocol {self.parent.name} (ID: {self.parent.ID})")

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash((self.name, self.description, self.ID, self.parent))


@dataclass
class Procedure(ScipyenDataclass):
    r"""An experimental procedure: what is being done during an Episode.

    A succession of procedures (attached to the episodes of a Schedule)
        represents an experimental protocol.

    NOTE: The Treatment class is recommended for use in lieu of generic Procedure
    where procedureType is 'treatment'

    """
    # name:str = ""
    procedureType: ProcedureType = ProcedureType.null

    def __post_init__(self):
        self.regulated=False

    def __repr__(self):
        # indent = lambda x: x.replace("\n", "\n\t")
        # repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash((self.name, self.description, self.procedureType, self.parent))

@dataclass
class PPLProcedure(Procedure):
    r"""Procedure reulated under appropriate legislation"""
    ppl: PPL = dataclasses.field(default_factory=PPL)
    pil: PIL = dataclasses.field(default_factory=PIL)
    protocol: PPLProtocol = dataclasses.field(default_factory=PPLProtocol)
    protocolStep: PPLProtocolStep = dataclasses.field(default_factory=PPLProtocolStep)
    framework: str="ASPA 1986"
    # procedure: Procedure = dataclasses.field(default_factory = Procedure)

    def __post_init__(self):
        self.regulated = True

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash((self.name, self.description, self.ppl, self.pil, self.protocol, self.protocolStep, self.procedure))

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
        # indent = lambda x: x.replace("\n", "\n\t")
        # repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
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
    substance:typing.Union[SubstanceDosage, typing.Sequence[SubstanceDosage]] = dataclasses.field(default_factory=SubstanceDosage)
    # allow combination of compounds
    route:AdministrationRoute = AdministrationRoute.null

    procedureType:ImmutableDescriptor = ImmutableDescriptor(default=ProcedureType.treatment) # does not work ?!?

    def __post_init__(self):
        self.procedureType = ProcedureType.treatment
        # super().__init__(name=self.name, description=self.description,
        #                  procedureType = ProcedureType.treatment)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

@dataclass
class Episode(ScipyenDataclass):
    r"""Generic episode for frame-based data.
        An Episode is an elementary part of a Schedule, and is logically
        associated with a Procedure.

        The defining attributes are: `name`, `begin`, `end`,
        `beginFrame`, `nFrames`, and `procedure`.

        In addition, the `description` attribute (a str) has an informative role
        without affecting the identity of an Episode
    """
    _: KW_ONLY
    begin:datetime.datetime = datetime.datetime.now()
    end:datetime.datetime = datetime.datetime.now()
    beginFrame:int = 0
    nFrames:int = 0
    # description:str = ""
    procedure:typing.Optional[Procedure] = dataclasses.field(default_factory = Procedure)

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def __repr__(self):
        # indent = lambda x: x.replace("\n", "\n\t")
        # repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)

    def __hash__(self) -> int:
        return hash(
                (
                    self.name,
                    self.description,
                    self.begin,
                    self.end,
                    self.beginFrame,
                    self.nFrames,
                    self.procedure
                )
            )

@dataclass
class Schedule(ScipyenDataclass):
    r"""Logical grouping of a sequence of non-overlapping, episodes.
        The episodes are contiguous from the point of view of their data "frames"
        (sweeps, image "slices", etc).
        A Schedule is logically equivalent to an experimental "protocol",
        consisting of the sequence of procedures associated with its episodes.

    When changing the episodes inside the schedule (adding, removing, or modifying
    an episode's number of frames), the "beginFrame" attribute of the episodes
    MIGHT be adjusted to enforce contiguity (depending on the position of the
    added/removed/modified episode) in the schedule.

    CAUTION: Episodes are stored by reference. This means that the adjustments
    described above WILL be reflected in the episodes contained by other sequences
    or schedules.

    If this is NOT intended, then pass DEEP COPIES of the episodes/sequence of episodes/
    schedule to methods like __add__, __iadd__, append, extend

    Deep copies can be obtained through the ``deepcopy`` function in the standard
    library module ``copy``.

    """
    # name:str = ""
    _:KW_ONLY
    episodes:typing.Sequence[Episode] = dataclasses.field(default_factory = lambda : list())

    allowed_contents: typing.ClassVar = (Episode, )

    def __repr__(self):
        # indent = lambda x: x.replace("\n", "\n\t")
        # repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)

    def __hash__(self) -> int:
        return hash((self.name, self.description, self.episodes))

    def __eq__(self, other) -> bool:
        return super().__eq__(other)

    def __len__(self)->int:
        return len(self.episodes)

    def __getitem__(self, key:typing.Union[int, slice, range, tuple, list, collections.deque, str]):
        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")

            return self.episodes[key]

        elif isinstance(key, str):
            if len(self.episodes) == 0:
                raise KeyError(f"{self.allowed_contents[0].__name__} named {key} not found")

            ret = list(filter(lambda x:x.name == key, self.episodes))

            if len(ret) == 0:
                raise KeyError(f"{self.allowed_contents[0].__name__} named {key} not found")

            elif len(ret) > 1:
                scipywarn(f"Duplicate {self.allowed_contents[0].__name__} name ({key}) found")

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

    def __setitem__(self, key:typing.Union[int, slice, range, tuple,
                                           list, collections.deque],
                    value:typing.Union[Episode, typing.Iterable[Episode]]):
        from core.utilities import unique

        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")

            if not isinstance(value, self.allowed_contents):
                raise TypeError(f"Expecting an {self.allowed_contents[0].__name__} object; instead, got {type(value).__name__}")

            value = deepcopy(value)

            if key < len(self.episodes)-1:
                nFramesBefore = sum([e.nFrames for e in self.episodes[:key]])
                self.__adjustEpisodeBeginFrame__(value, nFramesBefore)

                if self.episodes[key].nFrames != value.nFrames:
                    delta = value.nFrames - self.episodes[key].nFrames
                    for episode in self.episodes[key+1:]:
                        episode.beginFrame += delta

            self.episodes[key] = value

        elif isinstance(key, slice):
            if not isinstance(value, typing.Iterable):
                raise TypeError(f"The RHS of the assignment must be an iterable; instead, got {type(value).__name__}")

            if not all(isinstance(v, self.allowed_contents) for v in value):
                raise TypeError(f"The RHS iterable must contain only {self.allowed_contents[0].__name__} objects; instead got {unique((type(v).__name__ for v in value))}")

            value = list(map(deepcopy, value))

            l_indices = len(range(*key.indices(len(self.episodes))))

            if l_indices < len(value):
                raise ValueError(f"Too many RHS elements ({l_indices}); expecting {len(key)}")

            if l_indices > len(value):
                raise ValueError(f"Too few RHS elements ({l_indices}); expecting {len(key)}")

            for k, index in enumerate(l_indices):
                self.__setitem__(index, value[k])

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
                self.__setitem__(k, value[k])

        elif isinstance(key, (tuple, list, collections.deque)):
            if len(key) == 0:
                return

            elif all(isinstance(k, int) for k in key):
                if not isinstance(value, typing.Iterable):
                    raise TypeError(f"The RHS of the assignment must be an iterable; instead, got {type(value).__name__}")

                if not all(isinstance(v, self.allowd_contents) for v in value):
                    raise TypeError(f"The RHS iterable must contain only {self.allowed_contents[0].__name__} objects; instead got {unique((type(v).__name__ for v in value))}")

                if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                    raise IndexError(f"Index {k} out of range for {len(self.episodes)} episodes")

                if len(value) > len(key):
                    raise ValueError(f"Too many RHS elements ({l_indices}); expecting {len(key)}")

                if len(value) < len(key):
                    raise ValueError(f"Too few RHS elements ({l_indices}); expecting {len(key)}")

                value = list(map(deepcopy, value))

                for k in key:
                    self.__setitem__(k, value[k])

            else:
                raise KeyError("All indices must be int")

        else:
            raise TypeError(f"Invalid indexing key type {type(key).__name__}")

    def __delitem__(self, key:typing.Union[int, slice, range,
                                           tuple, list, collections.deque,
                                           str]):
        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")

            if key < len(self.episodes)-1:
                nFramesBefore = sum([e.nFrames for e in self.episodes[:key]])
                for episode in self.episodes[key+1:]:
                    self.__adjustEpisodeBeginFrame__(episode, nFramesBefore)

            del self.episodes[key]

        elif isinstance(key, str):
            if len(self.episodes) == 0:
                raise KeyError(f"{self.allowed_contents[0].__name__} named {key} not found")

            ret = list(filter(lambda x:x.name == key, self.episodes))

            if len(ret) == 0:
                raise KeyError(f"{self.allowed_contents[0].__name__} named {key} not found")

            elif len(ret) > 1:
                scipywarn(f"Duplicate {self.allowed_contents[0].__name__} name ({key}) found")

            episode = ret[0]

            ndx = self.episodes.index(episode)

            if ndx < len(self.episodes)-1:
                nFramesBefore = sum([e.nFrames for e in self.episodes[:ndx]])

                for ep in self.episodes[ndx+1:]:
                    self.__adjustEpisodeBeginFrame__(ep, nFramesBefore)

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

            elif not all(isinstance(k, str) for k in key):
                raise KeyError("All indices must be int or str")

            for k in key:
                try:
                    self.__delitem__(k)

                except: # noqa
                    continue

        else:
            raise TypeError(f"Invalid indexing key type {type(key).__name__}")

    def __iter__(self) -> typing.Iterator:
        return self.episodes.__iter__()

    def __reversed__(self) -> typing.Iterator:
        r"""CAUTION: iterates episodes in reversed order WITHOUT adjustments to their beginFrame"""
        return self.episodes.__reversed__()

    def __add__(self, other):
        if isinstance(other, self.__class__):
            newepisodes = self.episodes.__add__(list(map(deepcopy, other.episodes)))

            ret = self.__class__(name=self.name, description=self.description,
                                  episodes=newepisodes)

        elif isinstance(other, typing.Sequence):
            if len(other) and not all(isinstance(e, self.allowed_contents) for e in other):
                raise TypeError(f"Can only add a sequence of {self.allowed_contents[0].__name__} objects")

            newepisodes = self.episodes.__add__(list(map(deepcopy, other)))

            ret = self.__class__(name=self.name, description=self.description,
                                  episodes=newepisodes)

        else:
            raise TypeError(f"Invalid argument type ({type(other).__name__})")

        ret.__adjustBeginFrameAllEpisodes__()

        return ret

    def __iadd__(self, other):
        if isinstance(other, self.__class__):
            self.episodes.__iadd__(list(map(deepcopy, other.episodes)))

        elif isinstance(other, typing.Sequence):
            if len(other) and not all(isinstance(e, self.allowed_contents) for e in other):
                raise TypeError(f"Can only add a sequence of {self.allowed_contents[0].__name__} objects")
            self.episodes.__iadd__(list(map(deepcopy, other)))

        else:
            raise TypeError(f"Invalid argument type ({type(other).__name__})")

        self.__adjustBeginFrameAllEpisodes__()

        return self

    def __mul__(self, value:int):
        ret = self.__class__(name=self.name, description=self.description,
                             episodes = self.episodes.__mul__(value))
        ret.__adjustBeginFrameAllEpisodes__()
        return ret

    def __imul__(self, value:int):
        self.episodes.__imul__(value)
        self.__adjustBeginFrameAllEpisodes__()
        return self

    def __contains__(self, value:Episode):
        return value in self.episodes

    @property
    def nFrames(self) -> int:
        return sum([e.nFrames for e in self.episodes])

    def append(self, value: Episode):
        if not isinstance(value, self.allowed_contents):
            raise TypeError(f"A {self.__class__.__name__} can only contain {self.allowed_contents[0].__name__} objects")

        value=deepcopy(value)

        if len(self.episodes):
            frameOffset=self.nFrames
            value.beginFrame = frameOffset

        self.episodes.append(value)

    def insert(self, index: int, value: Episode):
        if not isinstance(value, self.allowed_contents):
            raise TypeError(f"A {self.__class__.__name__} can only contain {self.allowed_contents[0].__name__} objects")

        value = deepcopy(value)

        if len(self.episodes) == 0:
            self.episodes.append(value) # will adapt value.beginFrame

        else:
            if index >= len(self.episodes):
                self.episodes.append(value)# will adapt value.beginFrame

            else:
                # list.insert(index, obj) -> inserts object BEFORE index
                if index == 0 or index <= -len(self.episodes):
                    value.beginFrame = 0 # this becomes the first episode

                else:
                    episodesBefore = self.episodes[:index] # up to and EXCLUDING episode at index
                    value.beginFrame = sum([e.nFrames for e in episodesBefore])

                self.episodes.insert(index, value)
                # how many frames, now, up to and INCUDING index (where the new episode sits)?
                # nFramesBefore = sum([e.nFrames for e in self.episodes[:index+1]])
                # now, adapt beginFrames for ALL Episode after this new one
                # for episode in self.episodes[index+1:]:
                    # episode.beginFrame += nFramesBefore

        self.__adjustBeginFrameAllEpisodes__()

    def pop(self, index:int=-1) -> Episode:
        # adjust the episodes AFTER the one to be removed
        obj = self.episodes[index]
        for episode in self.episodes[index+1:]:
            episode.beginFrame -= obj.nFrames
        # now remove the one at index and return it
        return self.episodes.pop(index)

    def remove(self, value:Episode):
        if value not in self.episodes:
            return
        ndx = self.episodes.index(value)
        for episodes in self.episodes[ndx+1:]:
            episodes.beginFrame -= value.nFrames

        self.episodes.remove(value)

    def reverse(self):
        self.episodes.reverse()

        self.__adjustBeginFrameAllEpisodes__()

    def sort(self, *args, **kwargs):
        self.episodes.sort(*args, **kwargs)
        self.__adjustBeginFrameAllEpisodes__()

    def extend(self, value):
        if isinstance(value, self.__class__):
            self.episodes.extend(list(map(deepcopy, value.episodes)))

        elif isinstance(value, typing.Sequence):
            if len(value):
                if all(isinstance(v, self.allowed_contents) for v in value):
                    self.episodes.extend(list(map(deepcopy, value)))

                else:
                    raise TypeError(f"A {self.__class__.__name__} object can only contain {self.allowed_contents[0].__name__} objects")

        else:
            raise TypeError(f"Can only append a {self.__class__.__name__} or a sequence of {self.allowed_contents[0].__name__} objects")

        self.__adjustBeginFrameAllEpisodes__()

    def index(self, episode:Episode):
        if not isinstance(episode, self.allowed_contents):
            raise TypeError(f"A {self.__class__.__name__} object can only contain {self.allowed_contents[0].__name__} objects")

        if episode not in self.episodes:
            raise ValueError(f"The specified {self.allowed_contents[0].__name__} object is not contained in this {self.__class__.__name__}")

        ndx = [k for k in range(len(self.episodes)) if self.episodes[k] == episode]

        return ndx[0]

    def clear(self):
        self.episodes.clear()

    def count(self, episode: Episode):
        if not isinstance(episode, self.allowed_contents):
            raise TypeError(f"A {self.__class__.__name__} object can only contain {self.allowed_contents[0].__name__} objects")

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

        attrs = {"name": getattr(self, "name", ""), "description": getattr(self, "description", "")}

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
        description = attrs.get("description", "")

        episodes = h5io.fromHDF5(entity["episodes"], cache)

        return cls(name=name, description=description, episodes=episodes)

    @singledispatchmethod
    def episode(self, ndx) -> Episode:
        raise NotImplementedError(f"Wrong index type: {type(ndx).__name__}")

    @episode.register(int)
    def __episode__(self, ndx:int) -> Episode:
        if ndx >= len(self.episodes) or ndx < -1 * len(self.episodes):
            raise IndexError(f"Invalid episode index {ndx} for {len(self.episodes)}")

        return self.episodes[ndx]

    @episode.register(str)
    def __episode__(self, name:str) -> Episode: # noqa
        episodes = [e for e in self.episodes if e.name == name]
        if len(episodes):
            return episodes[0]
        else:
            raise IndexError(f"Episode name {name} does not exist")

    def __adjustBeginFrameAllEpisodes__(self):
        nFrames = 0

        for k, episode in enumerate(self.episodes):
            if k == 0:
                if episode.beginFrame != 0:
                    episode.beginFrame = 0

            else:
                if episode.beginFrame != nFrames:
                    episode.beginFrame = nFrames

            nFrames += episode.nFrames

    def __adjustEpisodeBeginFrame__(self, episode: Episode, nFramesBefore: int):
        if episode.beginFrame < nFramesBefore:
            newBeginFrame = nFramesBefore - episode.beginFrame
            episode.beginFrame = newBeginFrame

        elif episode.beginFrame > nFramesBefore:
            episode.beginFrame = nFramesBefore

    def episodeNames(self) -> list[str]:
        return [e.name for e in self.episodes]

    def episodeIndex(self, name:str) -> int:
        return self.episodeNames.index(name)

    # def addEpisode(self, episode:Episode):
    #     if episode not in self.episodes:
    #         self.episodes.append(deepcopy(episode))
    #
    # def addEpisodes(self, episodes:typing.Sequence[Episode]):
    #     self.episodes.extend([e for e in episodes if e not in self.episodes])
    #
    # def removeEpisode(self, episode):
    #     if episode in self.episodes:
    #         self.episodes.remove(episode)

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
    be silently ignored. This means that this function can only be used to augment
    the dataclass in args[0] with non-duplicate fields from the subsequent elements
    of 'args'.

    """
    # from copy import deepcopy
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

def repr_attr(x):
    indent = lambda x: x.replace("\n", "\n\t") # noqa
    if isinstance(x, str):
        return f": {type(x).__name__} → '{x}'"
    elif dataclasses.is_dataclass(type(x)):
        return f": {type(x).__name__} → {indent(x.__repr__())}"
    elif isinstance(x, Enum):
        return f": {type(x).__name__} →  '{x.name}' ({x})"
    else:
        return f": {type(x).__name__} → {x}"

def getField(obj, field: dataclasses.Field) -> typing.Any:
    r"""Returns the value of a field of a dataclass instance.

    If the dataclass instance lacks an attribute named after the field, returns
    the default value defined in the field signature.

    When 'field' is a name, it is looked up in the fields of the dataclass; if
    not found, it is looked up among the properties of the object 'obj'.

    WARNING: This function makes field access insensitive to API change (i.e.
    to changes where the definition of a dataclass type would make it impossible
    to use data created with the old API)
    """
    if not isDataclass(obj):
        raise TypeError(f"'obj' expected to be a dataclass; instead, got a {type(obj).__name__}")

    if not isinstance(field, dataclasses.Field):
        raise TypeError(f"'field' expected to be a dataclass Field; instead, got a {type(field).__name__}")

    # finally, return the field value taking account its default
    return getattr(obj, field.name, field.default_factory() if field.default is dataclasses.MISSING else field.default)


def getFieldOrProperty(obj, field:typing.Union[dataclasses.Field, str],
             default: typing.Any = dataclasses.MISSING) -> typing.Any:
    r"""Returns the value of a field of a dataclass instance.

    If the dataclass instance lacks an attribute named after the field, returns
    the default value defined in the field signature.

    When 'field' is a name, it is looked up in the fields of the dataclass; if
    not found, it is looked up among the properties of the object 'obj'.

    WARNING: This function makes field access insensitive to API change (i.e.
    to changes where the definition of a dataclass type would make it impossible
    to use data created with the old API)

    CAUTION: When 'field' is a string it MAY return the value of a property;
    when 'field' resolves to a dynamic property of 'obj' this WILL result in
    code execution .
    """
    if not isDataclass(obj):
        raise TypeError(f"'obj' expected to be a dataclass; instead, got a {type(obj).__name__}")

    if isinstance(field, str):
        # resolve field by name
        if len(field.strip()) == 0:
            raise ValueError("'field' argument cannot be an empty string")

        # is there a dataclasses.Field named after 'field'?
        fields = list(filter(lambda f: f.name == field, dataclasses.fields(obj)))

        if len(fields) == 0:
            # no dataclaasses Field found -> check if it is a property
            properties = list(
                filter(
                        lambda x: x[0] == field,
                        inspect.getmembers_static(obj,
                                                  lambda x: isinstance(x, property))
                      )
                )
            if len(properties):
                field = properties[0][0]
                if default is dataclasses.MISSING:
                    # default MISSING signals we don't want to shoehorn it if
                    # field not found
                    if not hasattr(obj, field):
                        raise AttributeError(f"The {type(obj).__name__} object does not have a '{field}' attribute or property")
                    return getattr(obj, field)

                else:
                    # retrieve the field if found, else return the default
                    return getattr(obj, field, default)
            else:
                raise ValueError(f"The {type(obj).__name__} object does not have a field or property named '{field}'")

        else:
            # a dataclasses.Field with nme after field argument WAS found
            field = fields[0]

    if not isinstance(field, dataclasses.Field):
        raise TypeError(f"'field' expected to be a dataclass Field or str; instead, got a {type(field).__name__}")

    # finally, return the field value taking account its default
    ret = getattr(obj, field.name, dataclasses.MISSING)
    if ret is dataclasses.MISSING:
        if field.default_factory is not dataclasses.MISSING:
            return field.default_factory()
        elif field.default is not dataclasses.MISSING:
            return field.default
        else:
            return None
    else:
        return ret

    # ret = getattr(obj, field.name, field.default_factory if field.default is dataclasses.MISSING else field.default)
