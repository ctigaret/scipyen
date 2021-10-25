import inspect, typing
from math import log
from numpy import log10
import numpy as np
import quantities as pq

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

#def prefix_dict(name, value):
    #symbol = make_prefix_symbol(name)
    
    #exponent = int(log(value, 2)) if name.endswith("bi") else int(log10(value))
    
    
    

#sipfx = ("yotta", "zetta", "exa", "peta", "tera", 
         #"giga", "mega", "kilo", "hecto", "deka", 
         #"deci", "centi", "milli", "micro", "nano",
         #"pico", "femto", "atto", "zepto", "yotto",)

#SI_prefix = sipfx

#sisymb = ("Y", "Z", "E", "P", "T", "G", "M", "k", "h", "da",
          #"d", "c", "m", "mu", "n", "p", "f", "a", "z", "y",)

#SI_symbols = sisymb

#exps = tuple([k for k in range(24,2,-3)] + [2,1,-1,-2] + [k for k in range(-3, -37, -3)])
#exponents_of_10 = exps

#DecimalPrefixes = dict([(p, dict([("exponent", e), ("symbol", s)])) for (p,e,s) in zip(sipfx, exps, sisymb)])

AllPrefixes = dict(((p[0], dict((("symbol", make_prefix_symbol(p[0])), ("mantissa", 2 if p[0].endswith("bi") else 10), ("exponent", int(log(p[1], 2) if p[0].endswith("bi") else int(log10(p[1])))), ("value", p[1])))) for p in _pqpfx))

DecimalPrefixes = dict((k,v) for k,v in AllPrefixes.items() if v["mantissa"] == 10)

DecimalPowers = dict((v["exponent"], {("name", k), ("symbol", v["symbol"])}) for k,v in DecimalPrefixes.items())

BinaryPrefixes = dict((k,v) for k,v in AllPrefixes.items() if v["mantissa"] == 2)

BinaryPowers = dict((v["exponent"], {("name", k), ("symbol", v["symbol"])}) for k,v in BinaryPrefixes.items())


def make_scaled_unit_quantity(quantity:pq.Quantity, power:typing.Union[int, str], base:int=10) -> pq.Quantity:
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

day_in_vitro = div = DiV = pq.UnitQuantity("day in vitro", 1 * pq.day, symbol = "div")
week_in_vitro = wiv = WiV = pq.UnitQuantity("week in vitro", 1 * pq.week, symbol = "wiv")

postnatal_day = pnd = PnD = pq.UnitQuantity("postnatal day", 1 * pq.day, symbol = "pnd")
postnatal_week = pnw = PnW = pq.UnitQuantity("postnatal week", 1 * pq.week, symbol = "pnw")
postnatal_month = pnm = PnM = pq.UnitQuantity("postnatal month", 1 * pq.month, symbol = "pnm")

embryonic_day = emd = EmD = pq.UnitQuantity("embryonic day", 1 * pq.day, symbol = "emd")
embryonic_week = emw = EmW = pq.UnitQuantity("embryonic week", 1 * pq.week, symbol = "emw")
embryonic_month = emm = EmM = pq.UnitQuantity("embryonic month", 1 * pq.month, symbol = "emm")

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

def quantity2str(x, precision = 2, format="f"):
    if not isinstance(x, (pq.Quantity, pq.UnitQuantity)):
        raise TypeError("Expecting a python Quantity or UnitQuantity; got %s instead" % type(x).__name__)
    
    if x.magnitude.flatten().size != 1:
        raise TypeError("Expecting a scalar quantity; got a quantity of size %d instead" % x.magnitude.flatten().size)
    
    if not isinstance(precision, int):
        raise TypeError("precision expected to be an int; got %s instead" % type(precision).__name__)
    
    if precision <= 0:
        raise ValueError("precision must be strictly positive; got %d instead" % precision)
    
    mag_format = "%d" % precision
    
    fmt = "%." + mag_format + format
    
    return " ".join([fmt % x.magnitude, x.units.dimensionality.string])

def name_from_unit(u):
    """
    FIXME make it more intelligent!
    """
    d_name = ""
    
    if not isinstance(u, (pq.UnitQuantity, pq.Quantity)):
        return d_name
        #raise TypeError("Expecting a Quanity or UnitQuanity; got %s instead" % type(u).__name__)
    
    unitQuantity = [k for k in u.dimensionality.keys()]
    
    
    if len(unitQuantity):
        unitQuantity = unitQuantity[0] 
    
        d_name = unitQuantity.name
        
        if d_name in ("Celsius", "Kelvin", "Fahrenheit"):
            d_name = "Temperature"
            
        elif d_name in ("arcdegree"):
            d_name = "Angle"
            
        elif "volt" in d_name:
            d_name = "Potential"
            
        elif "ampere" in d_name:
            d_name = "Current"
            
        elif "siemens" in d_name:
            d_name = "Conductance"
            
        elif "ohm" in d_name:
            d_name = "Resistance"
            
        elif "coulomb" in d_name:
            d_name = "Capacitance"
            
        elif "hertz" in d_name:
            d_name = "Frequency"
        
        elif any([v in d_name for v in ("meter", "foot", "mile","yard")]):
            d_name = "Length"
            
        elif any([v in d_name for v in ("second", "minute", "day","week", "month", "year")]):
            d_name = "Time"
            
    return d_name
            
    
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
            ret = eval(s, pq.__dict__)
            
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
        
