import inspect, typing
#from collections import OrderedDict
from math import log
from numpy import log10
#import numpy as np
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


#del(module_mmb)
