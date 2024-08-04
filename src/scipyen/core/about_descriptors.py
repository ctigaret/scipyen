# NOTE: 2024-08-02 22:14:19
# the 'neo' model — from baseneo (documentation)
# :_necessary_attrs: A list of tuples containing the attributes that the
#                     class must have. The tuple can have 2-4 elements.
#                     The first element is the attribute name.
#                     The second element is the attribute type.
#                     The third element is the number of  dimensions
#                     (only for numpy arrays and quantities).
#                     The fourth element is the dtype of array
#                     (only for numpy arrays and quantities).
#                     This does NOT include the attributes holding the
#                     parents or children of the object.
# 
# 
# A) Descriptors that contain POD types (int, str, float, datetime) the specification is:
#     (str, type) ↔ (name, value type)
# 
# B) Descriptors that contain numpy ndarray types, the specification is as below:
# 1) pq.Quantity:
#     (str, <type>¹, int) ↔ (name, pq.Quantity¹, ndim²)
# 
#     ¹ in most cases this is pq.Quantity; it can also be a tuple of types, 
#         containing subclasses of pq.Quantity for increased stringency, see 
#         'view.py' example further below
# 
# 
#     ² ndim can be:
#         0 for scalar Quantity objects; 
# 
#         1 for signal-like objects ("vectors") (this doesn't seem to be enforced,
#             as one can set the data to a 2D array, where each "column vector" 
#             can be considered a "channel", although I think the authors' 
#             intention was to have one channel/signal i.e. one 1D array)
#         (vectors), whereas 
# 
#         3 in the case of:
#             • image data in imagesequence, where the data is supposed to be 
#                 a "sequence" of 2D planes (hence 3D)
#             • waveforms in spiketrain, where data is supposed to be:
#                 spike (axis 0), channel (axis 1) and spike time domain (axis 3)
#                 (each spike occurs at the spike time stamp in the spiketrain)
# 
# 2) (generic) numpy ndarray (pn.ndarray):
#     (str, <type>³, int, np.dtype) ↔ (name, np.ndarray, ndim, dtype c'tor⁴)
# 
#     ³ always np.ndarray
# 
#     ⁴ e.g. np.dtype('U'), np.dtype('i') — see 'view.py' example below
# 
# All this boils down to:
# 
# (name, type or types, ndim, dtype)
# 
# and here are some examples:
# 
# from 'baseneo.py':
# _necessary_attrs = ()
# _recommended_attrs = (('name', str),
#                         ('description', str),
#                         ('file_origin', str))
# 
# from 'block.py':
# _recommended_attrs = ((('file_datetime', datetime),
#                         ('rec_datetime', datetime),
#                         ('index', int)) +
#                         Container._recommended_attrs)
# 
# 
# from 'analogsignal.py':
# _necessary_attrs = (('signal', pq.Quantity, 2),
#                     ('sampling_rate', pq.Quantity, 0),
#                     ('t_start', pq.Quantity, 0))
# 
# 
# from 'view.py':
# _necessary_attrs = (
#     ('index', np.ndarray, 1, np.dtype('i')),
#     ('obj', ('AnalogSignal', 'IrregularlySampledSignal'), 1)
# )
# 
# from imagesequence
# _necessary_attrs = (
#     ("image_data", pq.Quantity, 3),
#     ("sampling_rate", pq.Quantity, 0),
#     ("spatial_scale", pq.Quantity, 0),
#     ("t_start", pq.Quantity, 0),
# )
# 
# 
# my model:
#     0     1                            2     3                4      5
# (name, type or types or predicates, ndim )
# (name, type or types or predicates, ndim, dtype or dtypes)
# (name, type or types or predicates, ndim, dtype or dtypes, units)
# (name, type or types or predicates, ndim, dtype or dtypes, units, default)
# 
# define POD type = one of number.Numbers, str, bytes, bytearray
# define DC type = any type with a default constructor (i.e. no arguments)
#     -> all POD types are also DC types
# 
# 
# CAUTION: type(MISSING)() is not MISSING ! So when acceptable type is 
#     type(MISSING) just pass MISSING (don't call `type(MISSING)()`)
# 
#     Do the same for type(pd.NA) and type(None) !
# 
# PSEUDOCODE:
# ==========
# 
# MASTER RULE: x[0] is always a str — the name of the decriptor

import numpy as np
import quantities as pq
import pandas as pd
from dataclasses import MISSING
from core.datatypes import NoData

default_value = NoData
acceptable_types = NoData
acceptable_lengths = noData
acceptable_element_types = NoData
acceptable_ndims = NoData
acceptable_shapes = NoData
acceptable_units = NoData
acceptable_dtypes = NoData

name = x[0]
# RULES:
if len(x) == 2:                                                                 # rules family A
    if isinstance(x[1], type):                                                  # rule A.1
        acceptable_types = (x[1], )
        
        if allow_nodata:
            default_value = None
        else:
            if x[1] issubclass(type(MISSING)):
                default_value = MISSING
            elif x[1] issubclass(type(pd.NA)):
                default_value = pd.NA
            elif x[1] issubclass(type(None)):
                default_value = None
            elif x[1] issubclass(pq.Quantity):
                default value = pq.dimensionless
            else:
                try:
                    default_value = x[1]()
                except:
                    scipywarn(f"The type {x[1].__name__} does not have a default constructor; a default value must be supplied")
                    raise
        
    elif isinstance(x[1], tuple) and all(isinstance(t, type) for t in x[1]):    # rule A.2
        acceptable_types = x[1]
        if allow_nodata:
            default value = None
        else:
            if x[1][0] is type(MISSING):
                default_value = MISSING
            elif x[1][0] is type(pd.NA):
                default_value = pd.NA
            elif x[1][0] is type(NoneType):
                default_value = None
            elif x[1][0] is pq.Quantity:
                default value = pq.dimensionless
            else:
                try:
                    default_value = x[1]()
                except:
                    scipywarn(f"The type {x[1].__name__} does not have a default constructor; a default value must be supplied")
                    raise
        
    else:                                                                       # rule A.3
        default_value = x[1]
        acceptable_types = (type(x[1]), )
        
elif len(x) == 3:                                                                 # rules family B -> x[1] MUST be a type or tuple of types; 
    # when x[1] is a tuple of types x[2] can only provide a default value of 
    # one of the types in x[1]
    # otherwise, x[2] can specify (mutually exclusive) the acceptable:
    #   length          — when x[2] is an int and x[1] in (bytes, bytearray, str, deuque, dict, list, tuple, set)
    #   ndim            — when x[2] is an int and x[1] in (np.ndarray, )
    #   shape           — when x[2] is a tuple of int and x[1] in (np.ndarray, )
    #   element types   — when x[2] is a type or tuple of types and x[1] in (bytes, bytearray, str, deuque, dict, list, tuple, set)
    #   default value

    if isinstance(x[1], type):                                                  # rule B.1
        if issubclass(x[1], (str, bytes, bytearray, dict, set, tuple, list, deque)):
            if isinstance(x[2], int) and x[2] >= 0:
                acceptable_lengths = (x[2], )

            elif x[1] in (dict, set, tuple, list, deque): # factoring out
                if isinstance(x[2], type):
                    acceptable_element_types = (x[2], ) # also used for value types in a dict

                elif isinstance(x[2], tuple) and all(isinstance(v, type) for v in x[2]):
                    acceptable_element_types = x[2] # also used for value types in a dict

            elif isinstance(x[2], x[1]):
                    default_value = x[2]
                    
            elif not allow_nodata:
                raise DescriptorException() # mismatch between specified type and default value

        elif issubclass(x[1], np.ndarray): # or derived (pq.Quantity, VigraArray, neo.BaseSignal):
            # x[2] is either ndim, shape, dtype, or units, 
            if isinstance(x[2], int) and x[2] >= 0:
                acceptable_ndims = (x[2], ) # ignored for neo.BaseSignal & derived

            elif isinstance(x[2], np.dtype):
                acceptable dtypes = (x[2], )

            # to avoid ambiguity for pq.Quantity, the units, if specified, must
            #   be given as a mapping "units" ↦ Quantity or tuple of Quantity, or
            #   as a tuple of Quantity; in this way, a default value can be given
            #   (tbh, the mapping approach can be extended to all ndarray parameters)
            elif isinstance(x[2], dict) and x[1] is pq.Quantity:
                units = x[2].get("units", None)
                if isinstance(units, pq.Quantity):
                    acceptable_units = (units, )
                    
                elif isinstance(units, tuple) and all(isinstance(u, pq.Quantity) for u in units):
                    acceptable_units = units

            elif isinstance(x[2], tuple):
                if all(isinstance(v, int) and v>=0 for v in x[2]): # shape
                    acceptable_shapes = (x[2], ) # ignored for neo.BaseSignal & derived

                elif all(isinstance(v, no.dtype) for v in x[2]): # dtypes
                    acceptable_dtypes = (x[2], )

                elif all(isinstance(v, pq.Quantity) for v in x[2]): # units
                    acceptable_units = tuple([v.units for v in x[2]])

        elif isinstance(x[2], x[1]):
            default value = x[2]

        elif not allow_nodata:
            raise DescriptorException()

    elif isinstance(x[1], tuple) and all(isinstance(t, type) for t in x[1]):    # rule B.2
        if isinstance(x[2], x[1]):
            default_value = x[2]

        elif not allow_nodata:
            raise DescriptorException # mismatch between specified type and default value
        
    else:
        raise DescriptorException()

elif len(x) == 4:                                                               # rules family C
    # x[1] MUST be a type, nothing else
    if not isinstance(x[1], type):
        raise DecriptorException()
    # Applies rule B.1
    acceptable_types = (x[1], )
    if issubclass(x[1], (str, bytes, bytearray, dict, set, tuple, list, deque)):
        if isinstance(x[2], int) and x[2] >= 0:
            acceptable_lengths = (x[2], )
            if x[1] in (dict, set, tuple, list, deque):
                if isinstance(x[3], type):
                    acceptable_element_types = (x[3], ) # also used for value types in a dict
                elif isinstance(x[3], tuple) and all(isinstance(v, type) for v in x[3]):
                    acceptable_element_types = x[3] # also used for value types in a dict
            elif issubclass(x[1], np.ndarray):
                # TODO see case of ndarray in B.1
                elif isinstance(x[3], x[1]):
                    default_value = x[3]
                elif not allow_nodata:
                    raise DescriptorException() # need default value
                else:
                    pass  # ignore x[3]

            elif isinstance(x[3], x[1]):
                default value = x[3]
            elif not allow_nodata:
                raise DescriptorException # need default value
            else:
                pass  # ignore x[3]
                

        elif x[1] in (dict, set, tuple, list, deque):
            if isinstance
            if isinstance(x[2], type):
                acceptable element types = (x[2], ) # also used for value types in a dict

            elif isinstance(x[2], tuple) and all(isinstance(v, type) for v in x[2]):
                acceptable element types = x[2] # also used for value types in a dict

        else:
            raise DescriptorException # mismatch between specified type and default value


D) len(x) == 5 -- propagate A,B,C see what we do with x[4]


so, the "floating" terms are as follows (where 'x' is the spec tuple):
len(x) == 2 ⇒ 
    1 -> 5 (default) ← conflicts with (A)
    poss workaround: if x[1] is a POD type (number.Numbers, str, bytes, bytearray)
        then apply rule 1
    1 -> is 1 if len(x) == 3


therefore:

0 -> str always
1 -> type, tuple of types, predicate(s)
2 -> ndim if (1) indicates np.ndarray
    -> len if (1) indicates str, bytes, bytearray, dict, set, tuple, list
