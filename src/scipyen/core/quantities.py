# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
This modules complements the Quantities package with additional unit quantities
and exposes some much needed constants (as shorthand¹, but NOTE that values are
slightly different - TODO/FIXME):
R   : universal gas constant (molar gas constant)  8.31446261815324 * J/(K mol)
F   : Faraday constant 96485.33212331001 C/mol
qe  : elementary charge 1.602176634e-19 C
N_A : Avogadro constant 6.02214076e23 mol⁻¹
    (NAME avoids clashes with pandas.NA "not available" type)

¹ NOTE: These are aready contained in the "constants" module of the Quantities 
package, as UnitConstant objects, but some are bound to rather "verbose" symbols
e.g.:

pq.constants.R
pq.constants.Faraday_constant
pq.constants.e
pq.constants.Avogadro_constant

"""
import inspect, typing, traceback, warnings, types, dataclasses
from math import (log, inf, nan)
from pandas import NA
from numpy import log10
import numpy as np
import quantities as pq
from traitlets import Bunch
import operator
from functools import (reduce, partial, cache)
import more_itertools

from core import unicode_symbols
from core.unicode_symbols import uchar
from core.prog import BaseDescriptorValidator

_pqpfx = sorted(inspect.getmembers(pq.prefixes, lambda x: isinstance(x, (float, int))) + [("deca", pq.prefixes.deka)], key = lambda x: x[1])

def makePrefixSymbol(pfx):
    if pfx.endswith("a"):
        if pfx in ("deka", "deca"):
            return "da"
        return pfx[0].upper()
    
    if pfx == "micro":
        # return "u"
        return "μ"
    
    if pfx == "nano":
        return "n"

    if pfx == "femto":
        return "f"
    
    if pfx == "atto":
        return "a"
    
    if pfx == "zepto":
        return "z"
    
    if pfx.endswith("bi"):
        return pfx[0].upper() + pfx[-1]
    
    return pfx[0]

AllPrefixes = dict(((p[0], dict((("symbol", makePrefixSymbol(p[0])), ("mantissa", 2 if p[0].endswith("bi") else 10), ("exponent", int(log(p[1], 2) if p[0].endswith("bi") else int(log10(p[1])))), ("value", p[1])))) for p in _pqpfx))

DecimalPrefixes = dict((k,v) for k,v in AllPrefixes.items() if v["mantissa"] == 10)

DecimalPowers = dict((v["exponent"], {("name", k), ("symbol", v["symbol"])}) for k,v in DecimalPrefixes.items())

BinaryPrefixes = dict((k,v) for k,v in AllPrefixes.items() if v["mantissa"] == 2)

BinaryPowers = dict((v["exponent"], {("name", k), ("symbol", v["symbol"])}) for k,v in BinaryPrefixes.items())


def makeScaledUnitQuantity(quantity:pq.Quantity, power:typing.Optional[typing.Union[int, str]]=None, base:int=10, scale:typing.Union[int, float] = 1., symbol:typing.Optional[str]=None, name:typing.Optional[str] = None):
    """Create custom quantity as a scaled version of an existing quantity
    
    The function generates a new quantity, scaled by base^power * scale.
    
    When power is specified, a pre-defined prefix is appended to the unit
    
    Parameters:
    ==========
    
    quantity: an existing Quantity, to be scaled
    
    power: the power of the prefix (optional); when given, it represents the 
            power of the prefix (e.g. 'kilo', 'mega', 'micro', 'nano', etc)
            NOTE: these are powers of base (see below)
            
            When None (the default) a power prefix will not be applied
            
    base: 10 (default) or 2 (only makes sense for scaled binary quantities e.g. 'kibi', etc)
    
    scale: a scaling factor that will multiply the original quantity to obtain the new one
        default is 1.0
        
    symbol: optional, default is None; the symbol of the new unit
        When power is specified, this parameter should be left as default.
        
    name: optional default is None
        Recommended when power is None
    
    """
                                  
    if base not in (2, 10):
        raise ValueError(f"Incorrect base {base}; expecting 2 or 10")
    
    if base == 2:
        prefixes = BinaryPrefixes
        powers = BinaryPowers
        
    else:
        prefixes = DecimalPrefixes
        powers = DecimalPowers
    
    if not isinstance(quantity, pq.Quantity):
        raise TypeError("base_quantity expected to be a Quantity; got %s instead" % type(base_quantity).__name__)
    
    if power is not None:
        if isinstance(power, str):
            if power not in prefixes.keys():
                raise ValueError(f"Power {power} is invalid")
            
            name = "%s%s" % (power, quantity.units.dimensionality)
            if not isinstance(symbol, str) or len(symbol.strip())==0:
                symbol = "%s%s" % (prefixes[power]["symbol"], quantity.units.dimensionality)
            power = prefixes[power]["exponent"]
            
        elif isinstance(power, int):
            if power not in powers.keys():
                raise ValueError(f"Power {power} is invalid")
            
            name = "%s%s" % (powers[power]["name"], quantity.units.dimensionality)
            if not isinstance(symbol, str) or len(symbol.strip())==0:
                symbol = "%s%s" % (powers[power]["symbol"], quantity.units.dimensionality)
            
        else:
            raise TypeError(f"power expected to be a str or an int; got {type(power).__name__} instead")
    
        factor = pow(base, power)
        
    else:
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = str(quantity.units.dimensionality)
        factor = 1.0
        
    if not isinstance(symbol, str) or len(symbol.strip())==0:
        symbol = name
        
    return pq.UnitQuantity(name, factor * scale * quantity, symbol=symbol)

#NOTE: do not confuse with pq.au which is one astronomical unit !!!
arbitrary_unit = arbitraryUnit = ArbitraryUnit = a_u = pq.UnitQuantity('arbitrary unit', 1. * pq.dimensionless, symbol='a.u.')

pixel_unit = pixelUnit = PixelUnit = pixel = pu = pix = px = pq.UnitQuantity('pixel', 1. * pq.dimensionless, symbol='pixel')

day_in_vitro = div = DiV = makeScaledUnitQuantity(pq.day, symbol = "div", name = "day_in_vitro")
postnatal_day = pnd = PnD = makeScaledUnitQuantity(pq.day, symbol = "pnf", name = "postnatal_day")
embryonic_day = emd = EmD = makeScaledUnitQuantity(pq.day, symbol = "emd", name = "embryonic_day")
week_in_vitro = wiv = WiV = makeScaledUnitQuantity(pq.week, symbol = "wiv", name = "week_in_vitro")
postnatal_week = pnw = PnW = makeScaledUnitQuantity(pq.week, symbol = "pnw", name = "postnatal_week")
embryonic_week = emw = EmW = makeScaledUnitQuantity(pq.day, symbol = "emw", name = "embryonic_week")
postnatal_month = pnm = PnM = makeScaledUnitQuantity(pq.month, symbol = "pnm", name = "postnatal_month")
embryonic_month = emm = EmM = makeScaledUnitQuantity(pq.month, symbol = "emm", name = "embryonic_month")

# NOTE: 2017-07-21 16:05:38
# a dimensionless unit for channel axis (when there are more than one channel in the data)
# NOTE: NOT TO BE CONFUSED WITH THE UNITS OF THE DATA ITSELF!
channel_unit = channelUnit = ChannelUnit = channel = cu = pq.UnitQuantity("channel", 1. * pq.dimensionless, symbol="channel")

# NOTE: 2023-05-18 14:20:01 ATTENTION
# defined as one cycle per unit length
space_frequency_unit = spaceFrequencyUnit = sfu = sf = makeScaledUnitQuantity(1/pq.m, name='space_frequency_unit', symbol='1/m')

# NOTE: 2021-10-22 21:54:33 ATTENTION:
# "angle_frequency_unit" is not to be confused with "angular frequency" (ω) which is 
# radian/s (or Hz, if you consider radian to be dimensionless)
#
# Here, 1 angle frequency unit is defined as one cycle per radian -- another form of 
# space frequency; here 'cycle' is distinct from "pq.cycle" which is derived
# from radians
angle_frequency_unit = angleFrequencyUnit = afu = af = makeScaledUnitQuantity(1/pq.rad, name='angle_frequency_unit', symbol='1/rad')

# these are too useful to leave out
microohm = μohm = μΩ = makeScaledUnitQuantity(pq.ohm, "micro", symbol="μΩ")
millioohm = mohm = mΩ = makeScaledUnitQuantity(pq.ohm, "milli", symbol="mΩ")
kiloohm = kohm = kΩ = makeScaledUnitQuantity(pq.ohm, "kilo", symbol = "kΩ")
megaohm = Mohm = MΩ = makeScaledUnitQuantity(pq.ohm, "mega", symbol = "MΩ")
gigaohm = Gohm = GΩ = makeScaledUnitQuantity(pq.ohm, "giga", symbol="GΩ")

# NOTE: the string argument refers to the prefix to be prepended to the original
# unit string

# TODO some other useful units TODO
# NOTE: 2023-05-18 16:17:59
# if you want to add new custom quantities, write the code between the BEGIN / END 
# lines below
# ### BEGIN custom units
Φₑ = radiant_flux_unit = rfu = makeScaledUnitQuantity(pq.W, name = "radiant_flux_unit", symbol='W')
radiant_flux_density_unit = flux_density_unit = rfdu = fdu = makeScaledUnitQuantity(pq.W/(pq.m**2), name="radiant_flux_density_unit",symbol='W⋅m⁻²')
Φₑν = spectral_flux_frequency_unit = sffu = makeScaledUnitQuantity(pq.W*(pq.Hz**(-1)), name="spectral_flux_frequency_unit",symbol='W⋅Hz⁻¹')
Φₑλ = spectral_flux_wavelength_unit = sfwu = makeScaledUnitQuantity(pq.W*(pq.m**(-1)), name="spectral_flux_wavelength_unit",symbol='W⋅m⁻¹')
ΦE = electric_flux_unit = efu = makeScaledUnitQuantity(pq.V * pq.m, name = "electric_flux_unit", symbol="V⋅m")
flow_unit = flow = f_u = makeScaledUnitQuantity((pq.m**3)/pq.s, name="flow unit", symbol="m³⋅s⁻¹")
μM = makeScaledUnitQuantity(1e-6 * pq.mol/pq.L, name="μM", symbol = "μM")
μm = makeScaledUnitQuantity(1e-6 * pq.m, name="μm", symbol = "μm")
μV = makeScaledUnitQuantity(1e-6 * pq.V, name="μV", symbol = "μV")
pV = makeScaledUnitQuantity(1e-12 * pq.V, name="pV", symbol = "pV")
fV = makeScaledUnitQuantity(1e-15 * pq.V, name="pV", symbol = "pV")
μA = makeScaledUnitQuantity(1e-6 * pq.A, name="μA", symbol = "μA")
μC = makeScaledUnitQuantity(1e-6 * pq.C, name="μC", symbol = "μC")
μS = makeScaledUnitQuantity(1e-6 * pq.S, name="μS", symbol = "μS")
wpv = makeScaledUnitQuantity(pq.kg/pq.L, name="weight per volume")#, symbol = "kg⋅L⁻¹")
wpw = makeScaledUnitQuantity(pq.kg/pq.L, name="weight per weight")#, symbol = "kg⋅kg⁻¹")
vpv = makeScaledUnitQuantity(pq.L/pq.L, name="volume per volume")#, symbol = "kg⋅kg⁻¹")

# NOTE: 2023-05-18 16:17:50
# testing currency units
Pound_Sterling = pq.UnitCurrency("Pound_Sterling", symbol="£")
US_Dollar = pq.UnitCurrency("US_Dollar", symbol="$")
Euro = pq.UnitCurrency("Euro", symbol = "€")
# ### END custom units



# ** DON'T FORGET to add their symbol to the custom_unit_symbols dict AND to the
# appropriate sets BELOW **
#
# NOTE: 2023-05-18 12:36:23
# necessary to register new quantities with pq
custom_unit_symbols = dict()
custom_unit_symbols[arbitrary_unit.symbol] = arbitrary_unit
custom_unit_symbols[pixel_unit.symbol] = pixel_unit
custom_unit_symbols[channel_unit.symbol] = channel_unit
custom_unit_symbols[space_frequency_unit.symbol] = space_frequency_unit
custom_unit_symbols[angle_frequency_unit.symbol] = angle_frequency_unit
custom_unit_symbols[div.symbol] = div
custom_unit_symbols[wiv.symbol] = wiv
custom_unit_symbols[pnd.symbol] = pnd
custom_unit_symbols[pnw.symbol] = pnw
custom_unit_symbols[pnm.symbol] = pnm
custom_unit_symbols[emd.symbol] = emd
custom_unit_symbols[emw.symbol] = emw
custom_unit_symbols[emm.symbol] = emm
custom_unit_symbols[μΩ.symbol] = μΩ
custom_unit_symbols[mΩ.symbol] = mΩ
custom_unit_symbols[kΩ.symbol] = kΩ
custom_unit_symbols[MΩ.symbol] = MΩ
custom_unit_symbols[GΩ.symbol] = GΩ
custom_unit_symbols[μM.symbol] = μM
custom_unit_symbols[μm.symbol] = μm
custom_unit_symbols[μV.symbol] = μV
custom_unit_symbols[μA.symbol] = μA
custom_unit_symbols[μC.symbol] = μC
custom_unit_symbols[μS.symbol] = μS
custom_unit_symbols[radiant_flux_unit.symbol] = radiant_flux_unit
custom_unit_symbols[radiant_flux_density_unit.symbol] = radiant_flux_density_unit
custom_unit_symbols[spectral_flux_frequency_unit.symbol] = spectral_flux_frequency_unit
custom_unit_symbols[spectral_flux_wavelength_unit.symbol] = spectral_flux_wavelength_unit
custom_unit_symbols[electric_flux_unit.symbol] = electric_flux_unit
custom_unit_symbols[flow_unit.symbol] = flow_unit
custom_unit_symbols[Euro.symbol] = Euro
custom_unit_symbols[Pound_Sterling.symbol] = Pound_Sterling
custom_unit_symbols[US_Dollar.symbol] = US_Dollar

# Family sets for custom quantities defined above

custom_unit_families = dict()
custom_unit_families["time"] = {"irreducible": set(),
                                "derived": {day_in_vitro, embryonic_day, postnatal_day, week_in_vitro, embryonic_week, postnatal_week, embryonic_month, postnatal_month}}
custom_unit_families["frequency"] = {"irreducible": set(),
                                     "derived": {space_frequency_unit, angle_frequency_unit}}
custom_unit_families["energy"] = {"irreducible": set(),
                                  "derived": {radiant_flux_unit, spectral_flux_frequency_unit}}
custom_unit_families["electromagnetism"] = {"irreducible": set(),
                                            "derived": {spectral_flux_wavelength_unit, electric_flux_unit}}
custom_unit_families["flow"] = {"irreducible": set(),
                                "derived": {flow_unit}}
custom_unit_families["currency"] = {"irreducible": {Euro, Pound_Sterling, US_Dollar},
                                    "derived": set()}
custom_unit_families["dose"] = {"irreducible": set(),
                                "derived": {wpv, wpw, vpv}}


# NOTE: 2023-05-18 12:46:33
# The units in the Quantities package are implicitly orrganized in families by
# modules. This leaves no straightforward way in which custom quantities can be 
# added to these specific quantities, unless the custom quantity is a generated
# using makeScaledUnitQuantity()

# grab the custom quantities def'ed above, so far
__custom_quantities__ = list((mb, eval(mb)) for mb in dir() if isinstance(eval(mb), pq.Quantity))

for cq in __custom_quantities__:
    if cq[1].symbol not in custom_unit_symbols:
        custom_unit_symbols[cq[1].symbol] = cq[1]
    pq.unit_registry[cq[0]] = cq[1]
    setattr(pq, cq[0], cq[1])

del(cq, _pqpfx)
# better keep __custom_quantities__
# del(__custom_quantities__, cq, _pqpfx)

# universal gas constant
R = 8.31446261815324 * pq.J/(pq.K * pq.mol)

# Faraday constant
F = 96485.33212331001 * pq.C/pq.mol

# elementary charge
qe = 1.602176634e-19 * pq.C

# Avogadro constant
N_A = 6.02214076e23 * pq.mol**(-1)

def getConstants():
    ret = dict()
    
    modules = [(k,v) for (k,v) in pq.constants.__dict__.items() if inspect.ismodule(v) and k not in ("_codata", "_utils")]
    
    for (modname, module) in modules:
        ret[modname] = set([v for v in module.__dict__.values() if isinstance(v, pq.UnitConstant)])
        
    return ret

def getUnits():
    """Collects all units definitions.
    Units are defined in the Python Quantities package and augmented in this module.
    Must be called AFTER importing this module, so that it contains the custom 
    uniqt quantities defined in this module.
    
    Returns:
    ========
    
    unit_dict: mapping family name ↦ mapping irreducible ↦ set, derived ↦ set
    irreducible: mapping UnitQuantity ↦ family name
    derived: mapping UnitQuantity ↦ family name
    """
    
    unitsmodules = [(k,v) for (k,v) in pq.units.__dict__.items() if inspect.ismodule(v)] # + [pq.unitquantity]
    
    # _upriority = ("length", "time", "temperature", "mass", "substance", "information", "other")
    
    # get the main families of unit quantities:
    uq = [(k,v) for (k,v) in pq.unitquantity.__dict__.items() if isinstance(v, type) and issubclass(v, pq.UnitQuantity)]
    
    main_families = sorted([u[1].__name__.replace("Unit", "") for u in uq if u[1].__name__.startswith("Unit") and not any(u[1].__name__.endswith(s) for s in ("Constant", "Quantity", "LuminousIntensity"))])
    
    ret = dict((k, {"irreducible":set(), "derived":set()}) for k in main_families)
    
    for module in unitsmodules:
        # check for all quantities
        # some modules of compound units might also show up as containing irreducible units (when simplified) so we need
        # to take this into account
        
        module_units = list([(kn, kv) for kn, kv in module[1].__dict__.items() if isinstance(kv, pq.UnitQuantity)])
        
        # NOTE: UnitQuantity, as well as Dimensionality are hashable object types
        # hence they can be used as dict keys
        
        if len(module_units):
            ufamily = module[0].capitalize()
            units = set(u[1] for u in module_units)
            
            imported = [u[1] for u in module_units if type(u[1]).__name__.replace("Unit", "") not in (ufamily, "Quantity")]
            
            for u in imported:
                _fam = type(u).__name__.replace("Unit", "")
                
                if _fam == "LuminousIntensity":
                    _fam = "Electromagnetism"
                
                if _fam not in ret:
                    ret[_fam] = {"irreducible":set(), "derived":set()}
                    
                if isinstance(u, pq.unitquantity.IrreducibleUnit):
                    ret[_fam]["irreducible"].add(u)
                else:
                    ret[_fam]["derived"].add(u)
                    
            local = units - set(imported)
                    
            ir_units = set(u for u in local if isinstance(u, pq.unitquantity.IrreducibleUnit) ) # and type(u[1]).__name__.replace("Unit","") == ufamily)
            
            der_units = local - ir_units
            
            if ufamily not in ret:
                ret[ufamily]={"irreducible":set(), "derived":set()}
            
            ret[ufamily]["irreducible"] |= ir_units
            ret[ufamily]["derived"] |= der_units

    # add the custom quantities
    for family in custom_unit_families:
        f = family.capitalize()
        if f in ret:
            if "derived" not in ret[f]:
                ret[f]["derived"] = set()
                
            for u in custom_unit_families[family]["derived"]:
                ret[f]["derived"].add(u)
                
            if "irreducible" not in ret[f]:
                ret[f]["irreducible"] = set()
                
            for u in custom_unit_families[family]["irreducible"]:
                ret[f]["irreducible"].add(u)
        else:
            ret[f] = custom_unit_families[family]
                    
    ret["Other"]={"irreducible": {arbitrary_unit, pixel_unit, channel_unit, pq.dimensionless},
                  "derived": set()} 
    
    result = dict(sorted([(k,v) for (k,v) in ret.items()]))
    
    for v in result.values():
        v["irreducible"] = set(sorted(list(v["irreducible"]), key = lambda x: x.name))
        v["derived"] = set(sorted(list(v["derived"]), key = lambda x: x.name))
    
    # reverse-locate irreducible
    irreducible = dict()
    for k, v in result.items():
        if len(v["irreducible"]):
            for i in v["irreducible"]:
                if i not in irreducible:
                    irreducible[i] = set()
                irreducible[i].add(k)
                
    # similarly, grab the derived ones
    derived = dict()
    for k, v in result.items():
        if len(v["derived"]):
            for i in v["derived"]:
                if i not in derived:
                    derived[i] = set()
                derived[i].add(k)
                
    return result, irreducible, derived

UNITS_DICT, IRREDUCIBLES, DERIVED = getUnits()

UNITS_DICT["Dose"]["irreducible"] |= UNITS_DICT["Concentration"]["irreducible"]
UNITS_DICT["Dose"]["irreducible"] |= UNITS_DICT["Substance"]["irreducible"]
UNITS_DICT["Dose"]["derived"] |= UNITS_DICT["Concentration"]["derived"]
UNITS_DICT["Dose"]["derived"] |= UNITS_DICT["Substance"]["derived"]

CONSTANTS = getConstants()
        
def constantsFamilies():
    return list(CONSTANTS.keys())

def getUnitConstantFamily(c:pq.UnitConstant):
    if not isinstance(c, pq.UnitConstant):
        raise TypeError(f"Expecting a UnitConstant; instead, got {type(c).__name__}")
    
    families = [f for f, v in CONSTANTS.items() if c in v]
    
    if len(families) > 1:
        return set(families)
    
    elif len(families) == 1:
        return families[0]
    
def familyConstants(family:str):
    if family not in CONSTANTS:
        raise ValueError(f"Family {family} is not a family of constants; valid constants families are {constantsFamilies()}\n\n\t(see {__name__}.constantsFamilies())")
    
    return CONSTANTS[family]

def unitFamilies():
    return list(UNITS_DICT.keys())

def isCompound(x:pq.Quantity | pq.UnitQuantity):
    if len(x.dimensionality) == 0:
        return False
    elif len(x.dimensionality) == 1:
         base = list(x.dimensionality.keys())[0]
         return isCompound(base.definition)
     
    else:
         return True
         
def getBaseUnitQuantities(x:pq.Quantity | pq.UnitQuantity):
    xdim = x.dimensionality
    ret = list()
    if len(xdim) == 1:
        base = list(xdim.keys())[0]
        if isinstance(base, pq.UnitQuantity):
            if base._reference.dimensionality == base.dimensionality:
                ret.append(base)
                
            else:
                bdef = base.definition
                if not isinstance(bdef, pq.UnitQuantity) or isCompound(bdef):
                    bases = getBaseUnitQuantities(bdef)
                    if isinstance(bases, list):
                        ret.extend(bases)
                    else:
                        ret.append(bases)
                else:
                    ret.append(base)
        else:
            bases = getBaseUnitQuantities(base.definition)
            if isinstance(bases, list):
                ret.extend(bases)
            else:
                ret.append(bases)
        
    else:
        for base in xdim.keys():
            bbase = getBaseUnitQuantities(base)
            if isinstance(bbase, list):
                ret.extend(bbase)
            else:
                ret.append(bbase)
    return ret
            
def getUnitFamily(unit:typing.Union[pq.Quantity, pq.UnitQuantity]):
    """
    Retrieves the family of units for this quantity
    """
    if isinstance(unit, pq.UnitQuantity):
        udim_pw = [(unit, 1)]
    elif isinstance(unit, pq.Quantity):
        udim_pw = list(unit.dimensionality.items())
    else:
        raise TypeError(f"Expecting a Quantity or UnitQuantity; got {type(unit).__name__} instead")
    
    families = list()
    ndims = len(udim_pw)
    
    for u, p in udim_pw:
        ufamily = list()
        for family, contents in UNITS_DICT.items():
            uset = contents["irreducible"] | contents["derived"]
            if u in uset:
                if p > 1:
                    fml = f"{family} ** {p}"
                elif p < 0:
                    fml = f"{family} ** ({p})"
                else:
                    fml = family
                    
                ufamily.append(fml)
                
        families.append(ufamily)
        
    return "; ".join(list(map(lambda x: " * ".join(x), more_itertools.partial_product(*families))))
        
    # family_exprs = list(msp)
    # ret = list()
    # for k in range()
    # for ufamily in families:
    #     ret.append(" * ".join(ufamily))
        
    # return "; ".join(ret)
    
#     for family in UNITS_DICT:
#         uset = UNITS_DICT[family]["irreducible"] | UNITS_DICT[family]["derived"]
#         udims = [u.dimensionality for u in uset]
#         
#         if u in udims:
#             families.append(family)
# 
#         else: # see if the reference unit is in one of the reference units in the family
#             urefs = [u_._reference.units for u_ in uset]
#             uref = unit._reference.units
#             if uref in urefs:
#                 families.append(family)
            
    
#     elif len(families) > 1:
#         return sorted(list(set(families)))
#     
#     return families
        
    
def familyUnits(family:str, kind:typing.Optional[str]=None):
    if family not in UNITS_DICT:
        raise ValueError(f"{family} is not a valid UnitQuantity family; valid units families are {list(UNITS_DICT.keys())}\n\n\t(see {__name__}.UNITS_DICT)")
    
    if kind is None:
        return UNITS_DICT[family]["irreducible"] | UNITS_DICT[family]["derived"]
    
    elif isinstance(kind, str):
        if kind == "irreducible":
            return UNITS_DICT[family]["irreducible"]
        
        elif kind == "derived":
            return UNITS_DICT[family]["derived"]
        else:
            raise ValueError(f"Invalid UnitQuantity kind : {kind}; expecting one of 'irreducible' or 'derived', or None")
        
    else:
        raise TypeError(f"UnitQuantity kind expected to be None or a str; instead, got {type(kind).__name__}")
    
    
def quantity2scalar(x:typing.Union[int, float, complex, np.ndarray, pq.Quantity]):
    """
    """
    if isinstance(x, (complex, float, int)) or x == np.nan:
        return x
    
    if isinstance(x, np.ndarray):
        if x.size != 1:
            raise TypeError(f"Expecting a scalar; instead, got an array with size {x.size}")
        
        if isinstance(x, pq.Quantity): # this is derived from numpy array
            v = x.magnitude
        else:
            v = x[0]
    
    
        if v.dtype.name.startswith("complex"):
            return complex(v)
        
        if v.dtype.name.startswith("float"):
            return float(v)
        
        if v.dtype.name.startswith("int"):
            return int(v)
    
        raise TypeError(f"Expecting a numeric dtype; got {v.dtype} instead")
    
    raise TypeError(f"Expecting a scalar int float, complex, numpy array or Pyhon quantities.Quantity; got {type(x).__name__} instead")

def str2quantity(x:str):
    """Reconstruct a scalar quantity or dimensionality from a str.
    Performs the reverse of quantity2str.
    
    Parameters:
    ==========
    x: str of the format "<[number][space]>[unit symbol]" where the part between
        angle brackets is optional
    
    Example 1. Converting a scalar quantity:
    ========================================
    a = 1 * pq.pA
    
    b = quantity2str(a, precision=4, format="f") → "1.0000 pA"
    
    The round-trip is completed (with loss of precision) by str2quantity:
    
    str2quantity(b) → array(1.)*pA
    
    Example 2: Converting a dimensionality:
    =======================================
    
    b1 = quantity2str(a.dimensionality) → "pA"
    
    Round-trip:
    
    str2quantity(b1) → UnitCurrent('picoampere', 0.001 * nA, 'pA')
    
    """
    if not isinstance(x, str):
        raise TypeError(f"Expecting a str; got {type(x).__name__} instead")
    parts = x.split()
    if len(parts) == 1:
        # just a dimensionality str
        # NOTE: will raise if str is incorrect
        return unitQuantityFromNameOrSymbol(parts[0])
    elif len(parts) == 2:
        # will raise if x is wrong
        val = eval(parts[0])
        unit = unitQuantityFromNameOrSymbol(parts[1])
        return val * unit
    else:
        raise ValueError(f"Expecting a str of the form '<number><space><UnitQuantity symbol>'; indtead, got {x}")

def shortSymbol(x:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality]) -> str:
    """Returns the (short) symbol of this quantity's units)
    E.g., 'V', 'mV', '1/Hz'
    """
    if isinstance(x, pq.UnitQuantity):
        return x.symbol
    
    if isinstance(x, pq.Quantity):
        x = x.dimensionality
        
    dimstr = f"{x}"
    if dimstr == "dimensionless":
        return ""
    
    pfx = list(AllPrefixes.keys())
    
    mypfx = list(filter(lambda x: dimstr.startswith(x), pfx))
    
    if len(mypfx):
        mypfx = mypfx[0]
        res = dimstr.split(mypfx)
        if len(res) > 1:
            sfx = res[-1]
            if sfx in ("ohm"):
                sfx = "Ω"
            return "".join([AllPrefixes[mypfx]["symbol"], sfx])
    
    return dimstr
        
unitSymbol = shortSymbol

def prettySymbol(x:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality]) -> str:
    if isinstance(x, pq.Quantity):
        x = x.dimensionality
        
    delim = uchar("\\cdot")
    
    def _pretty_power_(v):
        if v > 1 or v < 0:
            vv = f"{v}"
            # print(f"{v}: {vv}")
            return "".join([uchar(f"\\^{v_}") for v_ in vv]) 
        
        return ""
    
    return delim.join(list(map(lambda v: f"{v[0]}{_pretty_power_(v[1])}", list((k.symbol, p) for k,p in x.items()))))
       

def quantity2str(x:typing.Union[pq.Quantity, pq.UnitQuantity, pq.dimensionality.Dimensionality], precision:int = 2, format:str="f"):
    """Returns a str representation of a scalar Quantity or Dimensionality.
    Useful to store quantities via json/yaml etc.
    WARNING: There will be loss of precision!
    
    The returned string has the form:
    
    <[number][space]>[unit symbol] where the part between angle brackets is optional
    
    Parameters:
    ===========
    x: scalar Quantity or Dimensionality
    
    Example 1. Converting a scalar quantity:
    ========================================
    a = 1 * pq.pA
    
    b = quantity2str(a, precision=4, format="f") → "1.0000 pA"
    
    The round-trip is completed (with loss of precision) by str2quantity:
    
    str2quantity(b) → array(1.)*pA
    
    Example 2: Converting a dimensionality:
    =======================================
    
    b1 = quantity2str(a.dimensionality) → "pA"
    
    Round-trip:
    str2quantity(b1) → UnitCurrent('picoampere', 0.001 * nA, 'pA')
    
    """
    if not isinstance(x, (pq.Quantity, pq.UnitQuantity, pq.dimensionality.Dimensionality)):
        raise TypeError("Expecting a python Quantity or UnitQuantity; got %s instead" % type(x).__name__)
    if isinstance(x, pq.dimensionality.Dimensionality):
        return x.string
    
    if x.magnitude.flatten().size != 1:
        raise TypeError("Expecting a scalar quantity; got a quantity of size %d instead" % x.magnitude.flatten().size)
    
    if not isinstance(precision, int):
        raise TypeError("precision expected to be an int; got %s instead" % type(precision).__name__)
    
    if precision <= 0:
        raise ValueError("precision must be strictly positive; got %d instead" % precision)
    
    mag_format = "%d" % precision
    
    fmt = "%." + mag_format + format
    
    return " ".join([fmt % x.magnitude, x.units.dimensionality.string])

#@cache
def nameFromUnit(u, as_key:bool=False):
    """
    FIXME make it more intelligent!
    """
    from core.utilities import unique, index_of
    
    d_name = "Quantity" if not as_key else "Qq"
    
    if not isinstance(u, (pq.UnitQuantity, pq.Quantity)):
        #return d_name
        raise TypeError("Expecting a Quantity or UnitQuantity; got %s instead" % type(u).__name__)
        
    dim = u.dimensionality
    
    if len(dim.keys()) == 0:
        return "Dimensionless"
    
    unitQuantity = list(dim.keys()) # [k for k in dim.keys()]
    unitQuantityPower = list(dim.items()) # [k for k in dim.keys()]
    #unitPowers
    
    if len(unitQuantity) == 1: # irreducible
        unitQuantity = unitQuantityPower[0][0] 
        power = unitQuantityPower[0][1]
        
        if power == 1:
            irrdims = unique([type(u).__name__.replace("Units", "") for u in IRREDUCIBLES])
            
            physQname = type(unitQuantity).__name__.replace("Unit", "")
            
            if physQname in irrdims:
                if as_key:
                    if physQname in ("Time", "Mass" , "Length"):
                        return physQname[0].lower()
                    elif physQname == "Substance":
                        return "n"
                    else:
                        return physQname[0]
                    
                return physQname
            
            else:
                d_name = unitQuantity.name
                
                # print(f"d_name = {d_name}")
                
                derdims = unique([(u._reference.dimensionality, tuple(v)) for u, v in DERIVED.items()], 
                                key = lambda x: x[1])
                
                # print(f"derdims = {derdims}")
                
                indices = index_of([d[0] for d in derdims], u._reference.dimensionality, 
                                multiple=True, comparator = operator.eq)
                
                # print(f"indices = {indices}")
                
                
                if isinstance(indices, list) and len(indices):
                    physQuants = unique(reduce(lambda x, y: x + y, (derdims[k][1] for k in indices)))
                    if len(physQuants):
                        physQname = physQuants[0]
                        if physQname == "electromagnetism":
                            if "ampere" in d_name.lower():
                                return "Current" if not as_key else "I"
                            
                            if "coulomb" in d_name.lower():
                                return "Charge" if not as_key else "Q"
                            
                            if "farad" in d_name.lower():
                                return "Capacitance" if not as_key else "C"
                            
                            if "volt" in d_name.lower():
                                return "Potential" if not as_key else "Psi"
                                
                            if "siemens" in d_name.lower():
                                return "Conductance" if not as_key else "G"
                                
                            if "ohm" in d_name.lower():
                                return "Resistance" if not as_key else "R"
                                
                        return physQname.capitalize() if not as_key else physQname[0].upper()
                
                if "arbitrary unit" in d_name.lower():
                    return "Quantity" if not as_key else "?"
                    #d_name = "A.U."
                
                if d_name in ("Celsius", "Kelvin", "Fahrenheit"):
                    return "Temperature" if not as_key else "T"
                    
                if d_name in ("arcdegree"):
                    return "Angle" if not as_key else "Theta"
                    
                if "volt" in d_name.lower():
                    return "Potential" if not as_key else "Psi"
                    
                if "ampere" in d_name.lower():
                    return "Current" if not as_key else "I"
                    
                if "siemens" in d_name.lower():
                    return "Conductance" if not as_key else "G"
                    
                if "ohm" in d_name.lower():
                    return "Resistance" if not as_key else "R"
                    
                if "coulomb" in d_name.lower():
                    return "Charge" if not as_key else "Q"
                    
                if "farad" in d_name.lower():
                    return "Capacitance" if not as_key else "C"
                    
                if "hertz" in d_name.lower():
                    return "Frequency" if not as_key else "f"
                
                if any([v in d_name.lower() for v in ("meter", "foot", "mile", "yard")]):
                    return "Length" if not as_key else "L"
                    
                if "postnatal" in d_name.lower():
                    return "Age"
                    
                if "in vitro" in d_name.lower():
                    return "Age in vitro" if not as_key else "aiv"
                    
                if "embryonic" in d_name.lower():
                    return "Embryonic age" if not as_key else "ed"
                    
                if any([v in d_name.lower() for v in ("second", "minute", "day","week", "month", "year")]):
                    return "Time" if not as_key else "t"
                    
                return "Quantity" if not as_key else "?"
                
        else:
            derdims = unique([(u._reference.dimensionality, tuple(v)) for u, v in DERIVED.items()], 
                            key = lambda x: x[1])
            
            indices = index_of([d[0] for d in derdims], u._reference.dimensionality, 
                               multiple=True, comparator = operator.eq)
            
            if len(indices):
                physQuants = unique(reduce(lambda x, y: x + y, (derdims[k][1] for k in indices)))
                
                return physQuants[0].capitalize() if not as_key else physQuants[0][0]
            
            else:
                return f"Unknown Quantity {u.dimensionality.string}" if not as_key else "?"
            
    else:
        derdims = [(u._reference.dimensionality, tuple(v)) for u, v in DERIVED.items()]

        ndx = index_of([d[0] for d in derdims], u._reference.dimensionality, multiple=True, comparator=operator.eq)
        
        if len(ndx):
            physQuants = unique(reduce(lambda x, y: x+y, (derdims[k][1] for k in ndx)))
            if len(physQuants):
                return physQuants[0].capitalize() if not as_key else physQuants[0][0]

        else:
            return f"Compound Quantity {u.dimensionality.string}" if not as_key else "?"
        
def checkDosageUnits(value):
    if not isinstance(value, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("Expecting a python UnitQuantity or Quantity; got %s instead" % type(value).__name__)

    acceptable_families = ["Mass", "Volume", "Concentration", "Dose", "Substance"]

    families = getUnitFamily(value)
    
    return any(f in families for f in acceptable_families)
    
    
    
    # test if this is a Mass, Volume¹, Concentration, Compound, or Substance unit
    #
    # ¹ a dosing based exclusively on volume is theoretically possible, although
    # impractical
    
            
def checkTimeUnits(value):
    if not isinstance(value, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("Expecting a python UnitQuantity or Quantity; got %s instead" % type(value).__name__)
    
    ref = pq.s
    
    return value._reference.dimensionality == ref.dimensionality

def checkElectricalCurrentUnits(value):
    if not isinstance(value, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("Expecting a python UnitQuantity or Quantity; got %s instead" % type(value).__name__)
    
    ref = pq.A
    
    return value._reference.dimensionality == ref._reference.dimensionality

def checkElectricalPotentialUnits(value):
    if not isinstance(value, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("Expecting a python UnitQuantity or Quantity; got %s instead" % type(value).__name__)
    
    ref = pq.V
    
    return value._reference.dimensionality == ref._reference.dimensionality
    
def conversion_factor(x:pq.Quantity, y:pq.Quantity):
    """Calculates the conversion factor from y units to x units.
    Alternative to pq.quantity.get_conversion_factor()
    
    """
    if not isinstance(x, pq.Quantity):
        raise TypeError("x expected to be a python Quantity; got %s instead" % type(x).__name__)
    
    if not isinstance(y, pq.Quantity):
        raise TypeError("y expected to be a python Quantity; got %s instead" % type(y).__name__)
    
    if x._reference.dimensionality != y._reference.dimensionality:
        raise TypeError("x and y have incompatible units (%s and %s respectively)" % (x.units, y.units))

    x_dim = pq.quantity.validate_dimensionality(x)
    y_dim = pq.quantity.validate_dimensionality(y)
    
    if x_dim != y_dim:
        try:
            cf = pq.quantity.get_conversion_factor(x_dim, y_dim)
            
        except AssertionError:
            raise ValueError("Cannot convert from %s to %s" % (origin_dim.dimensionality, self_dim.dimensionality))
        
        return cf
    
    else:
        return 1.0
    
def unitsConvertible(x: pq.Quantity, y: pq.Quantity) -> bool:
    """Checks that the units of python Quantities x and y are identical or convertible to each other.
    NOTE: To check that x and y have IDENTICAL units simply call 'x.units == y.units'
    """
    if not isinstance(x, (pq.Quantity, pq.UnitQuantity)):
        raise TypeError("x expected to be a python Quantity; got %s instead" % type(x).__name__)
    
    if not isinstance(y, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("y expected to be a python UnitQuantity or Quantity; got %s instead" % type(y).__name__)
    
    return x._reference.dimensionality == y._reference.dimensionality

def checkRescale(x: pq.Quantity, y: pq.Quantity) -> pq.Quantity:
    """Checks that units of `x` are convertible to units of `y`.
    
    Returns `x` rescaled to units of `y`, or raises AssertionError if `x` units 
    and `y` units are not convertible to each other (or not identical)
    
    """
    assert(unitsConvertible(x,y)), f"Cannot convert {x.units} to {y.units}"
    
    return x if x.units == y.units else x.rescale(y.units)

def unitQuantityFromNameOrSymbol(s):
    if not isinstance(s, str):
        raise TypeError("Expecting a string; got %s instead" % type(s).__name__)
    
    try:
        # easy way first
        return pq.unit_registry[s]
    
    except:
        #traceback.print_exc()
        try:
            ret = eval(s, pq.__dict__) # this accepts dimensionality strings
            
        except:
            #traceback.print_exc()
            if s in custom_unit_symbols.keys():
                ret = custom_unit_symbols[s]
                
            elif s in [u.name for u in custom_unit_symbols.values()]:
                ret = [u for u in custom_unit_symbols.values() if u.name == s]
                
            else:
                warnings.warn("Unknown unit quantity %s" % s, RuntimeWarning)
                
                ret = pq.dimensionless
            
        return ret
        
def nSamples(t:pq.Quantity, s:pq.Quantity) -> int:
    """Returns the number of samples in a time interval `t` for sampling rate `s`"""
    assert isinstance(t, pq.Quantity) and checkTimeUnits(t), f"{t} should be a time quantity (i.e. a 'duration')"
    assert isinstance(s, pq.Quantity) and checkTimeUnits(1./s), f"sampling rate {s} is not a frequency quantity"
    return int(t.rescale(pq.s) * s.rescale(pq.Hz))
    
class QuantityDescriptorValidator(BaseDescriptorValidator):
    """Descriptor validator for Python quantities, to be used in dataclass types"""
    def __init__(self, name:str, default = dataclasses.MISSING,
                 default_factory = dataclasses.MISSING, 
                 validator:typing.Optional[types.FunctionType]=None):
        # NOTE: 2024-08-20 11:20:48 Strategy
        #
        # Since dataclasses CANNOT do not accept mutable types as fields, 
        # this Descriptor will either:
        # a) generate a factory function based on the supplied 'default' (when default is not MISSING), OR
        # b) use the default 0-argument function supplied as 'default_factory'
        #
        # Therefore we emulate the behaviour of 'dataclasses.field' function to 
        # ensure that 'default' and 'default_factory' are NOT both supplied at 
        # the same time (but either can have their default values here, of dataclasses.MISSING)
        
        # I then use a custom __get__ method (see below) so that the dataclass 
        # parsing "sees" the factory function and not the atual default value 
        # (which is mutable, and therefore not acceptable as a dataclass field.
        
        # ATTENTION 2024-08-20 11:47:59 The down side of this is that the __set__
        # (called by the dataclass mechanism) and therefore self.validate() must 
        # also accept a factory function as above.
        #
        # I guess I can live with that...
        
        # NOTE: 2024-08-20 11:17:25
        # Adopt behaviour of dataclasses.field(…)
        if default is not dataclasses.MISSING and default_factory is not dataclasses.MISSING:
            raise ValueError(f"At least one of default and default_factory must be dataclasses.MISSING; instead, got default: {type(default).__name__} and default_factory: {type(default_factory).__name__}")
        
        if isinstance(default, pq.Quantity):
            # a default is supplied -- verify is the right thing
            if not checkTimeUnits(default):
                raise TypeError(f"Expecting a time quantity")
            
            # then use it to construct a NEW quantity, so that new instances of 
            # this descriptor don't point to the same default!
            my_default_factory = lambda: pq.Quantity(default.magnitude * default.units)
            default = dataclasses.MISSING # override default for super().__init__() below
            
        elif default is dataclasses.MISSING:
            if inspect.isfunction(default_factory):
                argspec = inspect.getfullargspec(default_factory)
                if len(argspec.args):
                    raise TypeError(f"Expecting 'default_factory to 0 arguments")
                
                if len(argspec.kwonlyargs):
                    raise TypeError(f"Expecting a factory without keyword arguments")
                
                if any(v is not None for v in (argspec.varargs, argspec.varkw, argspec.defaults, argspec.kwonlydefaults)):
                    raise TypeError("Expecting default_factory to be a 0-argument function or dataclasses.MISSING")
                
                d = default_factory()

                if not isinstance(d, pq.Quantity):
                    raise TypeError(f"Expecting the 'default_factory' to be a python Quantity factory function; instead, got a factory for {type(d).__name__}")
                
                if not checkTimeUnits(d):
                    raise TypeError(f"Expecting the 'default_factory' to be a factory for time quantity; instead it generates {d.units} units")
                
                my_default_factory = default_factory
                
            elif default_factory is dataclasses.MISSING: 
                my_default_factory = lambda: 0*pq.s
            else:
                raise TypeError("Expecting default_factory to be a 0-argument function or dataclasses.MISSING")
            
        else:
            raise TypeError(f"'default expected to be a python Quantity or dataclasses,.MISSING; instead, got {type(default).__name__}")
        
        super().__init__(name, default, use_private=True)
        
        self.default_factory = my_default_factory
        if inspect.isfunction(validator):
            fargs = inspect.getfullargspec(validator)
            if len(fargs.args) != 1:
                raise TypeError("'validator' function must accept exactly one positional argument")
            self.validator = validator
        else:
            self.validator = dataclasses.MISSING
            
    def __get__(self, obj, objtype=None) -> object:
        """Implements access to a data descriptor value (attribute access).
        Customized to resolve to a default factory function for the Python's
        dataclass mechanism.
        
        """
        # print(f"{self.__class__.__name__}.__get__: {self.private_name} (public name: {self.public_name}) for {type(obj).__name__} object")
        if obj is None:
            # NOTE: 2024-08-20 11:15:23
            # this gets checked by the dataclasse parsing mechanism so we need to 
            # return the factory here, instead of the mutable Quantity
            ret = self.default_factory 
        else:
            # NOTE: 2024-08-20 11:14:54
            # THAT's the way to do it
            # here, we actually need a puython quantity instance, which may be a
            # realization of the default factory
            ret = getattr(obj, self.private_name, self.default_factory)

            # WARNING: the setter may have assigned a quantity, so we need to check this
            if inspect.isfunction(ret):
                ret = ret()
            
        return ret
        
    def validate(self, value):
        """"""
        # NOTE: 2024-08-20 11:51:01
        # see ATTENTION 2024-08-20 11:47:59 for why this also accepts a factory
        # function
        if isinstance(value, pq.Quantity):
            if inspect.isfunction(self.validator):
                if not self.validator(value):
                    raise TypeError(f"'value' has wrong units: {value.units}")
            
        elif inspect.isfunction(value):
            argspec = inspect.getfullargspec(value)
            if len(argspec.args):
                raise TypeError("Expecting a factory without arguments")
            
            if len(argspec.kwonlyargs):
                raise TypeError("Expecting a factory without keyword arguments")
            
            if any(v is not None for v in (argspec.varargs, argspec.varkw, argspec.defaults, argspec.kwonlydefaults)):
                raise TypeError("Expecting a factory with no arguments at all")
            
            d = value()

            if not isinstance(d, pq.Quantity):
                raise TypeError(f"Expecting a python Quantity factory function; instead, got a factory for {type(d).__name__}")
            
            if inspect.isfunction(self.validator):
                if not self.validator(d):
                    raise TypeError(f"th factory generates a quantity with wrong units {d.units}")
         
        else:
            raise TypeError(f"Expecting a python Quantity or a Quantity functor; instead, got {type(value).__name__}")
