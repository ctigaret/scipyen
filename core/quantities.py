import inspect, typing
from math import (log, inf, nan)
from pandas import NA
from numpy import log10
import numpy as np
import quantities as pq
from traitlets import Bunch
import operator
from functools import (reduce, partial, cache)

_pqpfx = sorted(inspect.getmembers(pq.prefixes, lambda x: isinstance(x, (float, int))) + [("deca", pq.prefixes.deka)], key = lambda x: x[1])

def make_prefix_symbol(pfx):
    if pfx.endswith("a"):
        if pfx in ("deka", "deca"):
            return "da"
        return pfx[0].upper()
    
    if pfx == "micro":
        return "u"
    
    if pfx.endswith("bi"):
        return pfx[0].upper() + pfx[-1]
    
    return pfx[0]

AllPrefixes = dict(((p[0], dict((("symbol", make_prefix_symbol(p[0])), ("mantissa", 2 if p[0].endswith("bi") else 10), ("exponent", int(log(p[1], 2) if p[0].endswith("bi") else int(log10(p[1])))), ("value", p[1])))) for p in _pqpfx))

DecimalPrefixes = dict((k,v) for k,v in AllPrefixes.items() if v["mantissa"] == 10)

DecimalPowers = dict((v["exponent"], {("name", k), ("symbol", v["symbol"])}) for k,v in DecimalPrefixes.items())

BinaryPrefixes = dict((k,v) for k,v in AllPrefixes.items() if v["mantissa"] == 2)

BinaryPowers = dict((v["exponent"], {("name", k), ("symbol", v["symbol"])}) for k,v in BinaryPrefixes.items())


def make_scaled_unit_quantity(quantity:pq.Quantity, power:typing.Union[int, str], base:int=10):
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
    
    if isinstance(power, str):
        if power not in prefixes.keys():
            raise ValueError(f"Power {power} is invalid")
        
        name = "%s%s" % (power, quantity.units.dimensionality)
        symbol = "%s%s" % (prefixes[power]["symbol"], quantity.units.dimensionality)
        power = prefixes[power]["exponent"]
        
    elif isinstance(power, int):
        if power not in powers.keys():
            raise ValueError(f"Power {power} is invalid")
        
        name = "%s%s" % (powers[power]["name"], quantity.units.dimensionality)
        symbol = "%s%s" % (powers[power]["symbol"], quantity.units.dimensionality)
        
    else:
        raise TypeError(f"power expected to be a str or an int; got {type(power).__name__} instead")
    
    factor = pow(base, power)
    
    return pq.UnitQuantity(name, factor * quantity, symbol=symbol)

#NOTE: do not confuse with pq.au which is one astronomical unit !!!
arbitrary_unit = arbitraryUnit = ArbitraryUnit = a_u = pq.UnitQuantity('arbitrary unit', 1. * pq.dimensionless, symbol='a.u.')

pixel_unit = pixelUnit = PixelUnit = pixel = pu = pix = px = pq.UnitQuantity('pixel', 1. * pq.dimensionless, symbol='pixel')

day_in_vitro = div = DiV = pq.UnitTime("day in vitro", 1 * pq.day, symbol = "div")
week_in_vitro = wiv = WiV = pq.UnitTime("week in vitro", 1 * pq.week, symbol = "wiv")

postnatal_day = pnd = PnD = pq.UnitTime("postnatal day", 1 * pq.day, symbol = "pnd")
postnatal_week = pnw = PnW = pq.UnitTime("postnatal week", 1 * pq.week, symbol = "pnw")
postnatal_month = pnm = PnM = pq.UnitTime("postnatal month", 1 * pq.month, symbol = "pnm")

embryonic_day = emd = EmD = pq.UnitTime("embryonic day", 1 * pq.day, symbol = "emd")
embryonic_week = emw = EmW = pq.UnitTime("embryonic week", 1 * pq.week, symbol = "emw")
embryonic_month = emm = EmM = pq.UnitTime("embryonic month", 1 * pq.month, symbol = "emm")

# NOTE: 2017-07-21 16:05:38
# a dimensionless unit for channel axis (when there are more than one channel in the data)
# NOTE: NOT TO BE CONFUSED WITH THE UNITS OF THE DATA ITSELF!
channel_unit = channelUnit = ChannelUnit = channel = cu = pq.UnitQuantity("channel", 1. * pq.dimensionless, symbol="channel")

space_frequency_unit = spaceFrequencyUnit = sfu = sf = pq.UnitQuantity('space frequency unit', 1/pq.m, symbol='1/m')

# NOTE: 2021-10-22 21:54:33
# angle_frequency_unit is not to be confused with angular frequency which is 
# radian/s (or Hz, if you consider radian to be dimensionless)
# thus 1 angle frequency unit equals one cycle per radian -- another form of 
# space frequency; here 'cycle' is distinct from the pq.cycle which is derived
# form radians
angle_frequency_unit = angleFrequencyUnit = afu = af = pq.UnitQuantity('angle frequency unit', 1/pq.rad, symbol='1/rad')

# these are too useful to leave out
kiloohm = kohm = make_scaled_unit_quantity(pq.ohm, "kilo")
megaohm = Mohm = make_scaled_unit_quantity(pq.ohm, "mega")
gigaohm = Gohm = make_scaled_unit_quantity(pq.ohm, "giga")

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
custom_unit_symbols[kohm.symbol] = kohm
custom_unit_symbols[Mohm.symbol] = Mohm
custom_unit_symbols[Gohm.symbol] = Gohm

# NOTE: the string argument refers to the prefix to be prepended to the original
# unit string

# TODO some other useful units TODO

custom_quantities = ((mb, eval(mb)) for mb in dir() if isinstance(eval(mb), pq.Quantity))

for cq in custom_quantities:
    if cq[1].symbol not in custom_unit_symbols:
        custom_unit_symbols[cq[1].symbol] = cq[1]
    pq.unit_registry[cq[0]] = cq[1]
    setattr(pq, cq[0], cq[1])

del(custom_quantities, cq, _pqpfx)

def get_units():
    """REturns all units definitions in the Python Quantities package, augmented.
    
    """
    ret = dict()
    unitsmodules = [(k,v) for (k,v) in pq.units.__dict__.items() if inspect.ismodule(v)]
    
    _upriority = ("length", "time", "temperature", "mass", "substance", "information", "other")
    
    for module in unitsmodules:
        # check for all quantities
        # some modules of compound units might also show up as containing irreducible units (when simplified) so we need
        # to take this into account
        
        module_units = list([(kn, kv) for kn, kv in module[1].__dict__.items() if isinstance(kv, pq.UnitQuantity)])
        
        # NOTE: UnitQuantity, as well as Dimensionality are hashable object types
        # hence they can be used as dict keys
        
        if len(module_units):
            ugroup = module[0].capitalize()
            units = set(u[1] for u in module_units)
            ir_units = set(u[1] for u in module_units if isinstance(u[1], pq.unitquantity.IrreducibleUnit) and type(u[1]).__name__.replace("Unit","") == ugroup)
            der_units = units - ir_units
            ret[ugroup]=dict()
            ret[ugroup]["irreducibles"] = ir_units
            ret[ugroup]["derived"] = der_units
            if ugroup.lower() == "time":
                ret[ugroup]["derived"] = ret[ugroup]["derived"] | {day_in_vitro, week_in_vitro, postnatal_day, postnatal_month, postnatal_week, embryonic_day, embryonic_month, embryonic_week}
            elif ugroup.lower() == "frequency":
                ret[ugroup]["derived"] = ret[ugroup]["derived"] | {angle_frequency_unit, space_frequency_unit}
            elif ugroup == "electromagnetism":
                ret[ugroup]["derived"] = ret[ugroup]["derived"] | {kiloohm, megaohm, gigaohm}
                
            
        # reverse-locate irreducibles
        
        irreducibles = dict()
        for k, v in ret.items():
            if len(v["irreducibles"]):
                for i in v["irreducibles"]:
                    if i not in irreducibles:
                        irreducibles[i] = set()
                    irreducibles[i].add(k)
                    
        derived = dict()
        for k, v in ret.items():
            if len(v["derived"]):
                for i in v["derived"]:
                    if i not in derived:
                        derived[i] = set()
                    derived[i].add(k)
                    
    ret["other"]={"irreducibles": {arbitrary_unit, pixel_unit, channel_unit},
                  "derived": set()}
            
    return ret, irreducibles, derived

UNITS_DICT, IRREDUCIBLES, DERIVED = get_units()
        
def unitFamilies():
    return [k for k in UNITS_DICT]

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
        return unit_quantity_from_name_or_symbol(parts[0])
    elif len(parts) == 2:
        # will raise if x is wrong
        val = eval(parts[0])
        unit = unit_quantity_from_name_or_symbol(parts[1])
        return val * unit
    else:
        raise ValueError(f"Expecting a str of the form '<number><space><UnitQuantity symbol>'; indtead, got {x}")

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
def name_from_unit(u, as_key:bool=False):
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
                
                derdims = unique([(u._reference.dimensionality, tuple(v)) for u, v in DERIVED.items()], 
                                key = lambda x: x[1])
                
                indices = index_of([d[0] for d in derdims], u._reference.dimensionality, 
                                multiple=True, comparator = operator.eq)
                
                if isinstance(indices, list) and len(indices):
                    physQuants = unique(reduce(lambda x, y: x + y, (derdims[k][1] for k in indices)))
                    if len(physQuants):
                        physQname = physQuants[0]
                        if physQname == "electromagnetism":
                            if "ampere" in d_name:
                                return "Current" if not as_key else "I"
                            
                            if "coulomb" in d_name:
                                return "Charge" if not as_key else "Q"
                            
                            if "farad" in d_name:
                                return "Capacitance" if not as_key else "C"
                            
                            if "volt" in d_name:
                                return "Potential" if not as_key else "Psi"
                                
                            if "siemens" in d_name:
                                return "Conductance" if not as_key else "G"
                                
                            if "ohm" in d_name:
                                return "Resistance" if not as_key else "R"
                                
                        return physQname.capitalize() if not as_key else physQname[0].upper()
                
                if "arbitrary unit" in d_name:
                    return "Quantity" if not as_key else "?"
                    #d_name = "A.U."
                
                if d_name in ("Celsius", "Kelvin", "Fahrenheit"):
                    return "Temperature" if not as_key else "T"
                    
                if d_name in ("arcdegree"):
                    return "Angle" if not as_key else "Theta"
                    
                if "volt" in d_name:
                    return "Potential" if not as_key else "Psi"
                    
                if "ampere" in d_name:
                    return "Current" if not as_key else "I"
                    
                if "siemens" in d_name:
                    return "Conductance" if not as_key else "G"
                    
                if "ohm" in d_name:
                    return "Resistance" if not as_key else "R"
                    
                if "coulomb" in d_name:
                    return "Charge" if not as_key else "Q"
                    
                if "farad" in d_name:
                    return "Capacitance" if not as_key else "C"
                    
                if "hertz" in d_name:
                    return "Frequency" if not as_key else "f"
                
                if any([v in d_name for v in ("meter", "foot", "mile", "yard")]):
                    return "Length" if not as_key else "L"
                    
                if "postnatal" in d_name:
                    return "Age"
                    
                if "in vitro" in d_name:
                    return "Age in vitro" if not as_key else "aiv"
                    
                if "embryonic" in d_name:
                    return "Embryonic age" if not as_key else "ed"
                    
                if any([v in d_name for v in ("second", "minute", "day","week", "month", "year")]):
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
            
def check_time_units(value):
    if not isinstance(value, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("Expecting a python UnitQuantity or Quantity; got %s instead" % type(value).__name__)
    
    ref = pq.s
    
    return value._reference.dimensionality == ref.dimensionality
    
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
    
def units_convertible(x, y):
    """Checks that the units of python Quantities x and y are identical or convertible to each other.
    NOTE: To check that x and y have IDENTICAL units simply call 'x.units == y.units'
    """
    if not isinstance(x, (pq.Quantity, pq.UnitQuantity)):
        raise TypeError("x expected to be a python Quantity; got %s instead" % type(x).__name__)
    
    if not isinstance(y, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("y expected to be a python UnitQuantity or Quantity; got %s instead" % type(y).__name__)
    
    return x._reference.dimensionality == y._reference.dimensionality

def unit_quantity_from_name_or_symbol(s):
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
        
