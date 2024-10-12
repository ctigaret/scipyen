# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Functions for processing generic 1D signals (numpy array).
For signal processing on elecctorphysiology signal types (e.g. neo.AnalogSignals or datatypes.DataSignal)
please use the "ephys" module.
"""
import typing, numbers, functools, warnings, traceback
#### BEGIN 3rd party modules
import numpy as np
import scipy
import pandas as pd
import quantities as pq
import neo
#### END 3rd party modules

#### BEGIN scipyen core modules
from . import curvefitting as crvf
from . import quantities as scq
from . import datasignal as sds
from .datasignal import DataSignal, IrregularlySampledDataSignal
from . import prog as prog
from .prog import (safeWrapper, with_doc)
#### END scipyen core modules

def simplify_2d_shape(xy:np.ndarray, max_points:int = 5, k:int = 3):
    """Creates an simplified version of a 2D shape defined by x,y coordinate array
    
    Parameters:
    ===========
    xy a 2D numpy array with x,y coordinates stored row-wise: 
        column 0 has x coordinates, column 1 has y coordinates)
        
    max_points: int (default 5) or None
        When an int: this indicates the maximum number of adjacent points in xy
            having with non-identical coordinates. 
        
        If such sequences of points are found, and they are longer than max_points,
            the function calculates a B-spline interpolation for each sequence.
        
        These interpolations may be used to approximate the curve in that region.
        
        When None, no attempt to identify sequence of adjacent points, and no 
            B-spline interpolations will be calculated.
        
        
    k (int) the degree of B-spline used to interpolate sequences of adjacent points
        (see the decsriptions of max_points)
    
    Returns:
    ========
    
    ret: 2D numpy array of points in the xy array with ALMOST unique coordinates
        (they may be identical in at most ONE coordinate, x OR y)
        
    splines: list of 2-element tuples, as many as there are sequences of adjacent
        curve points longer than max_points, containing the result of parametric 
        B-spline interpolation of these sequence (see scipy.interpolate.splprep)
        as follows:
        
        In each tuple:
        element 0 is a tuple (t,c,k) containing the vector of knots (t), 
                                                    the B-spline coefficients, (c)
                                                    and the degree of the spline. (k)
                                                    
        element 1 is an array of the values of the parameter that can be used
            to evaluating the spline with scipy.interpolate.splev, given the 
            "tck" tuple
            
        NOTE: the B-spline coefficients in the "tck" tuple are stored as a list 
            of vector arrays with the X coordinate in the first array and Y 
            coordinate in the second array.
            
            For cubic B-splines (the default) there are four such coefficients.
            
            In relation to pictgui.PlanarGraphics objects, these represent the 
            x and y coordinates, respectively, of the:
            
            1) the start point, 
            2) first control point,
            3) second control point,
            4) the end point.
            
            Both start at end points ARE on the actual segment of the xy array
            that has been interpolated by the spline. 
            
            The two control points and the end point correspond to the 
            parameters for the QtGui.QPainterPath.cubicTo() function.
            
            They can be used to construct a pictgui.Cubic as:
            
            Cubic(ep.x, ep.y, cp1.x, cp1.y, cp2.x, cp2.y)
            
            where "ep" is the end point and "cp1", "cp2" are the control points
            
            To add a pictgui.Cubic object to a non-empty pictgui.Path,
            construct the pictgui.Cubic as above, then append it to the Path.
            
            If the pictgui.Cubic object needs to be the first in a Path, then 
            add a pictgui.Move object constructed using start_point.x, start_point.y
            then construct the pictgui.Cubic object as above and add it to the
            Path.
    
    """
    
    from scipy import interpolate
    
    # print(f"simplify_2d_shape: xy.shape = {xy.shape}")
    
    # 0) get the indices of ALMOST ALL points with unique x & y
    xd = np.diff(xy, axis = 0)
    
    # NOTE  2019-03-26 20:57:58
    # do this so that we take both the first AND the last points in series of
    # adjacent points with identical XY coords (otherwise we end up with only one
    # of them, ehther the first, or the last, depending where the nan has been 
    # placed)
    xd1 = np.insert(xd, 0, np.full((1,2), np.nan), axis=0)
    xd2 = np.append(xd, np.full((1,2), np.nan), axis = 0)

    # unq_xy_ndx contains the indices in the original xy array, or "ALMOST UNIQUE" points.
    # That is, points that differ by at least ONE coordinate. These include 
    # ENDS (i..e, first & last point) of stretches of adjacent points with 
    # identical XY coordinates (for these ends, either X or Y are identical,
    # but never both)
    unq_xy_ndx = np.where((xd1[:,0] != 0) & (xd1[:,1] != 0) | \
                          (xd2[:,0] != 0) & (xd2[:,1] != 0))[0]
    
    #unique_xy_ndx = np.where((xd1[:,0] != 0) & (xd1[:,1] != 0))[0]
    
    splines = list()
    
    if unq_xy_ndx.size == 0: 
        return xy, splines               # no reason to go further
    
    # flag indices for unique nonadjacent point separated
    
    ret = xy[unq_xy_ndx,]                            # NOTE: integer array indexing!
    
    if max_points is None or (isinstance(max_points, int) and max_points < 1):
        return ret, splines
    
    # 
    # find out if there are stretches of more than max_points with different 
    # coordinates that are adjacent in the original xy array
    # 
    
    # flag indices for unique & non-adjacent points:
    # for adjacent points, their indices in the original xy array differ by 1 
    # (unity)
    dundx = np.diff(unq_xy_ndx, axis=0) 
    
    # NOTE: 2019-03-26 20:58:11
    # apply the rationale explained at NOTE  2019-03-26 20:57:58
    dundx0 = np.insert(dundx, 0, 0)
    dundx1 = np.append(dundx, 0)
    
    dundx_nadj = (dundx0 != 1) | (dundx1 != 1)          # NOTE:  will have 0 at adjacent points
    
    #
    # adjacent points (but with different coordinates) have contiguous indices
    # in the original xy array; find out those indices
    #
    
    # contains indices into the unq_xy_ndx array, for those non-adjacent points
    # that have unique XY coordinates, OR are located at both ends of the
    # intervals of adjacent non-unique points,  see NOTE  2019-03-26 20:57:58
    nadj_unq_xy_ndx = np.where(dundx_nadj)[0]
    
    if len(nadj_unq_xy_ndx):
    
        # differentiate again => the distance (in samples) bewteen (almost) unique pts
        nadj_unq_xy_ndx_d = np.diff(nadj_unq_xy_ndx, axis=0, prepend=0)
        
        # contains indices in unq_xy_ndx where the distance from prev index in 
        # the same is >= max_points
        
        long_stretch_end_indirect_ndx = np.where(nadj_unq_xy_ndx_d > max_points)[0]
        
        if len(long_stretch_end_indirect_ndx):
            long_stretch_start_indirect_ndx = long_stretch_end_indirect_ndx - 1
            
            long_stretch_end_ndx = nadj_unq_xy_ndx[long_stretch_end_indirect_ndx,]
            long_stretch_start_ndx = nadj_unq_xy_ndx[long_stretch_start_indirect_ndx,]
            
            long_stretch_start = unq_xy_ndx[long_stretch_start_ndx,]
            long_stretch_stop = unq_xy_ndx[long_stretch_end_ndx,]
            
            adjacent_runs = np.vstack((long_stretch_start, long_stretch_stop))
            
            #the actual small segment we want to spline interpolate ((parametric 2D)
            curves = [xy[adjacent_runs[0,k]:adjacent_runs[1,k]] for k in range(adjacent_runs.shape[1])]
            
            # parametric 1D cubic spline representation (NOT bivariate spline !)
            splines = [interpolate.splprep([curve[:,0], curve[:,1]]) for curve in curves]
        
    return ret, splines
    
def zero_crossings(x:np.ndarray):
    """Returns the zero crossings of x waveform, with grid accuracy.
    
    For good results "x" should be filtered first (e.g. smoothed with a boxcar)
    
    Parameters:
    ==========
        x: 1D numpy array or sequence;
    
    Returns:
    ========
    
    A sequence of indices where x crosses 0.
    
    """
    #from scipy import where
    
    if isinstance(x, np.ndarray) and len(x.shape) > 1:
        if x.ndim > 2 or x.shape[1] > 1:
            raise TypeError("Expecting a vector")
        
        x = np.squeeze(x)
        
    return np.where(x[:-1] * x[1:] < 0)[0] # because where() returns a tuple which
                                           # for 1D data has only one element
                                        
def value_crossings(x:np.ndarray, value:float):
    """Returns the sample indices, in a waveform, that cross an arbitrary value.
    
    Similar to zero_crossings, for a value != zero
    
    """
    if isinstance(x, np.ndarray) and len(x.shape) > 1:
        if x.ndim > 2 or x.shape[1] > 1:
            raise TypeError("Expecting a vector")
        
        x = np.squeeze(x)
        
    x_ = x - value
    
    return zero_crossings(x_)

def linear_range_map(x, range_max, ymin, ymax):
    yrange = ymax-ymin
    if x > range_max:
        x = range_max
        
    if x < 0:
        x = 0
        
    return ymin + yrange * x/range_max

def inverse_linear_range_map(y, range_max, ymin, ymax):
    yrange = ymax-ymin
    
    if y > ymax:
        y = ymax
        
    if y < ymin:
        y = ymin
        
    return (y - ymin) * range_max / yrange
    
                                        
def generate_bin_width(adcres:float=15, adcrange:float=10, adcscale:float=1):
    """Define a histogram bin width according to the ADC used to collect the data.
    
    adcres = integer, optional: 
        ADC resolution (in bits) i.e. the width of the quantization bins used
        by the ADC.
        
        default = 15 (for Axon Digidata 1550)
        
    adcrange = ADC input range (V); 
        optional, default is 10 for Axon Digitata 1550
        
    n = adcscale factor (integer)
    
    Returns n * ADC_bin_width, where ADC_bin_width = adcrange/(2**adcres)

    See IEEE Std 181-2011: 
        IEEE Standard for Transitions, Pulses, and Related Waveforms
        p.16
    """
    
    return adcscale * adcrange/(2**adcres)

def is_positive_waveform(x:np.ndarray):
    """A positive waveform has the majority of its samples >= 0
    FIXME: this is  not robust enough against various waveforms! 
    Parameters:
    ==========
    x: 1D numpy array (i.e., a vector)
    """
    if not isinstance(x, np.ndarray):
        raise TypeError(f"Expecting a np.ndarray object or a derived type; got {type(x).__name__} instead")
    
    if len(x.shape)> 1:
        if x.ndim > 2 or x.shape[1] > 1:
            raise TypeError(f"Expecting a vector; got an array with shape {x.shape} instead")
        
        x = np.squeeze(x)
        
    xPos = np.where(x >= 0)[0]
    xNeg = np.where(x <  0)[0]
    
    return len(xPos) > len(xNeg)

def scale_waveform(x:np.ndarray, α, β):
    """Scales waveform by a rational factor (α/β).
    Returns a reference to x, which is modified in place.
    
    Parameters:
    ==========
    x: the signal (waveform)
    α, β: floats
    
    """
    nanx = np.isnan(x)
    if isinstance(x, pq.Quantity):
        units = x.units
        xx = x.magnitude # → this is a REFERENCE ; its changes will be reflected in x !!!
        
        if isinstance(α, pq.Quantity):
            if not scq.unitsConvertible(α, x):
                raise TypeError("numerator has wrong units")
            if α.units != x.units:
                α = α.rescale(x.units)
                
            α = α.magnitude
        
        if isinstance(β, pq.Quantity):
            if not scq.unitsConvertible(β, x):
                raise TypeError("denominator has wrong units")
            if β.units != x.units:
                β = β.rescale(x.units)
                
            β = β.magnitude
            
    else:
        if any(isinstance(v, pq.Quantity) for v in (α, β)):
            raise TypeError("α and β canot be quantities if x is not a quantity")
        xx = x
        units = None
        
    if np.any(nanx):
        scaled = xx[~nanx] * α/β
        xx[~nanx] = scaled
        
    else:
        xx *= α/β
    
    return xx if units is None else xx * units

def normalise_waveform(x:np.ndarray, axis:typing.Optional[int]=None, rng:typing.Optional[typing.Union[float, np.ndarray]] = None):
    """Waveform normalization.
    
    
    Parameters:
    ===========
    x: numpy array (i.e., a vector)
    
    axis: int with vale in range(-(x.ndim), x.ndim), or None
        When axis is -1 the last axis is used.
    
    rng: float, optional (default is None). The normalization range
    
    Returns:
    =======
    • For a positive waveform (i.e. "upward" deflection)

        ∘ (x-x_min)/abs(rng) when rng is a float, else:

        ∘ (x-x_min)/(x_max - x_min) 
    
    • For a negative waveform (i.e., "downward" deflection)

        ∘ (x_max - x)/abs(rng) when rng is a float, else:

        ∘ (x_max - x)/(x_min - x_max) 
    
    Keeps the waveform's orientation and polarity.
    
    WARNING
    When x is a quantities.Quantity, the result is a dimensioness Quantity!
    WARNING
    
    The point is that waveform "min" is not its numerical minimum, but the sample 
    value closest to zero; likewise, the "max" is the sample value farthest away
    from zero.
    
    Obviously, this approach will break down if a downward deflection waveform is
    MOSTLY above zero! Such contrived example is that of a mini EPSC where the 
    "drift" in the patch or the junction potential have caused the DC current to
    drift far above zero.
    
    In this case, shoud you decide to analyze such recording, you'd better
    remove the DC drift manually before proceeding...
    
    NOTE: when x is a Python Quantity, normalization will make it dimensionless
    
    FIXME: 2022-12-13 16:57:47 This is NOT nan-friendly!
    
    """
    from core import datatypes
    if x.ndim != 1:
        if x.ndim == 2:
            if min(x.shape) != 1:
                raise NotImplementedError("Only 1D vectors are supported")
        else:
            raise NotImplementedError("Only 1D vectors are supported")
        
            
    # def __nrm__(x, ref, r):
    #     return (x-ref)/r
        
#     #### BEGIN deal with the rng parameter
#     if isinstance(x, pq.Quantity):
#         if isinstance(rng, float):
#             rng = rng * x.units
#             
#         elif isinstance(rng, np.ndarray):
#             if rng.size != 1:
#                 raise ValueError("rng must be a scalar")
#             
#             if isinstance(rng, pq.Quantity):
#                 if not scq.unitsConvertible(x, rng):
#                     raise TypeError(f"rng quantity ({rng.units.dimensionality}) is incompatible with x quantity ({x.units.dimensionality})")
#                 if rng.units != x.units:
#                     rng.rescale(x.units)
#                     
#             else:
#                 rng = rng * x.units
#                 
#         elif rng is not None:
#             raise TypeError(f"Bad rng type ({type(rng).__name__})")
#                 
#     elif isinstance(x. np.ndarray):
#         if isinstance(rng, np.ndarray):
#             if rng.size != 1:
#                 raise ValueError("rng must be a scalar")
#             
#             if isinstance(rng, pq.Quantity):
#                 rng = float(rng.magnitude[0])
#             
#         if not isinstance(rng, float) and rng is not None:
#             raise TypeError(f"Bad rng type ({type(rng).__name__})")
#         
#     if rng is None:
#         rng = abs(x.min()-x.max())
# #         if x.ndim == 1:
# #             rng = abs(x.min()-x.max())
# #             
# #         else:
# #             raise NotImplementedError(f"arrays with {x.ndim} dimensions are not supported")
# #             if axis is None:
# #                 rng = abs(x.min()-x.max())
# #                 
# #             else:
# #                 if not isinstance(axis, int):
# #                     raise TypeError(f"axis expected to be an int or None; got {type(axis).__name__} instead")
# #                 dims = x.ndim
# #                 if axis not in range( -dims, dims):
# #                     raise ValueError(f"Bad axis {axis} for x with {x.ndim} dimensions")
# #                 
# #                 rng = np.abs(x.max(axis=axis) - x.min(axis=axis)) # rng is a quantity if x is a quantity
#     #### END deal with the rng parameter
#     
#     if is_positive_waveform(x):
#         return (x-np.min(x))/rng
#     
#     return (np.max(x)-x)/rng
# 
# #     if x.ndim == 1:
# #         if is_positive_waveform(x):
# #             return (x-np.min(x))/rng
# #         
# #         return (np.max(x)-x)/rng
# #         # return (x-np.min(x))/(np.max(x)-np.min(x))
# #         
# #     else:
# #         raise NotImplementedError(f"arrays with {x.ndim} dimensions are not supported")
#         # FIXME: 2022-12-22 11:50:13
#         # should revisit this
# #         if axis is None:
# #             if isinstance(x, pq.Quantity):
# #                 ispos = is_positive_waveform(x.magnitude.flatten())
# #             else:
# #                 ispos = is_positive_waveform(x.flatten())
# #                 
# #             if ispos:
# #                 return (x-np.min(x))/rng
# #             
# #             return (np.max(x)-x)/rng
# #         
# #         else:
# #             if isinstance(x, pq.Quantity):
# #                 xx_ = x.magnitude
# #             else:
# #                 xx_ = x
# #             
# #             # ispos = [is_positive_waveform(x.magnitude[dt.array_slice(x, {axis:k})] for k in xx_.shape[axis])]
# #             
# #             ret = x.copy()
# #             print(f"rng = array {rng.shape}: {rng}")
# #             
# #             # NOTE: 2022-12-22 12:15:06
# #             # this is WRONG: axis indicates the axis along shich we calculate min max
# #             for k in range(x.shape[axis]):
# #                 ret[dt.array_slice(xx_, {axis:k})] = normalise_waveform(x[dt.array_slice(xx_, {axis:k})], axis = -1, rng=rng[k])
        
        
    #### BEGIN original code
    if is_positive_waveform(x):
        return (x-np.min(x))/(np.max(x)-np.min(x))
    
    return (np.max(x)-x)/(np.min(x)-np.max(x))
    #### END original code

def data_range(x:np.ndarray, **kwargs):
    """The difference between a signal max and min values.
    
    Var-keyword parameters:
    =======================
    
    axis: None or a valid axis index (for 0 to x.ndim) - passed directly to
        `np.min(...)` and `np.max(...)`
    
    Returns:
    ========
    
    A scalar (when axis is None) or an array with x.ndim-1 dimensions.
    
    """
    axis = kwargs.pop("axis", None)
    return np.max(x, axis=axis) - np.min(x, axis=axis)

def waveform_amplitude(x:np.ndarray, method:str="direct", axis=None):
    """Calculates the amplitude of a waveform.
    
    Parameters:
    ==========
    x: numpy array (numeric)
    
    Keyword parameters:
    ===================
    method:str, one of "direct", "levels". Default is "direct"
    
        "direct": amplitude is the absolute value of the range of x
            (i.e. max - min) excluding NaNs
            
        "levels": amplitude if the ansolute difference between two state levels
            of the signal x (see state_levels() function in this module)
    
    axis: None or a valid axis index (for 0 to x.ndim)
    
    Returns:
    ========
    
    A scalar (when `axis` is None) or an array with x.ndim-1 dimensions.
    
    """
    if not isinstance(x, np.ndarray):
        raise TypeError("Expecting a np.ndarray object or a derived type; got %s instead" % type(x).__name__)
    
    # NOTE: 2022-10-23 16:49:59
    # might want to do this, below
#     if len(x.shape)> 1:
#         if x.ndim > 2 or x.shape[1] > 1:
#             raise TypeError("Expecting a vector; got an array with shape %s" % x.shape)
#         
#         x = np.squeeze(x)
        
    if not isinstance(method, str):
        return TypeError("method expected to be a str; got %s instead" % type(method).__name__)
    
    if method.lower() not in ("direct", "levels"):
        return ValueError("method expected to be 'direct' or 'levels'; got %s instead" % method)
    
    if x.size == 0:
        if isinstance(x, pq.Quantity):
            return 0. * x.units
        
        return 0.
    
    if method.lower() == "direct":
        return np.abs(np.nanmax(x, axis=axis) - np.nanmin(x, axis=axis))
        
    else:
        # FIXME/TODO 2022-10-23 16:56:59
        # CAUTION is we preserve the shape of the array, sl will be we'll get 
        sl = state_levels(x, axis=axis)
        
        return np.abs(np.diff(sl[0]))
        
def shorth_estimator(x:np.ndarray):
    """Shorth estimator for step-like waveforms.
    See IEEE Std 181-2011: 
        IEEE Standard for Transitions, Pulses, and Related Waveforms
        Section 5.2.2
    """
    # TODO 2023-05-17 11:50:52
    from scipy import cluster
    cbook, dist = cluster.vq.kmeans(x, 2) # get the two state occurrences
    
def split_histogram(counts, f):
    """ Histogram splitter 
    See IEEE Std 181-2011: 
        IEEE Standard for Transitions, Pulses, and Related Waveforms
        Section 5.2.1.3
        
    Arguments:
    ==========
    counts: sequence or numpy array of histogram bin counts
    
    f = scalar, or list or tuple of fractional reference levels, 

        when a scalar, "f" must be a float numbr betwen 0 and 1 (inclusive)
            
            "f" is then augmented to [f, 1-f]
        
        when a sequence of scalars, the following conditions must be satisfied:
        
            * if len(f) == 1 this is treated as the case where "f" is a scalar
            
            * else:
            
                * len(f) >= 2
        
                * for each level value f_j in "f", 0 <= f_j <= 1
            
                * sum(f) == 1
        
    Returns:
    ========
    
    A list of range objects into the "count" sequence, each corresponding
    to the bins in each specified fractional level.
    
    """
    #from numbers import Real, Integral
    from scipy import where
    
    def __splitter__(c, f0, f1):
        lo = where(c>0)[0][0]
        hi = where(c>0)[0][-1]
        
        r0 = range(int(f0 * (hi-lo)+1))
        r1 = range(int(lo + f1*(hi-lo)+1), int(hi+1))
        
        return r0, r1
    
    if isinstance(f, float):
        if f > 0 and f < 1:
            f = [f, 1-f]
            
        elif f == 0 or f == 1: #just one level
            r_lo = r_hi = range(len(counts))
            return r_lo, r_hi
        
        else:
            raise ValueError("A single level fraction must be between 0 and 1; got %f instead" % (f))

    elif isinstance(f, (tuple, list, np.ndarray)):
        if len(f) == 1:
            if f[0] > 0 and f[0] < 1:
                f = [f[0], 1-f[0]]
                
            elif f[0] == 0 or f[0] == 1: # just one level
                r_lo = r_hi = range(len(counts))
                return r_lo, r_hi
                
            else:
                raise ValueError("A single level fraction must be between 0 and 1; got %f instead" % (f[0]))

        elif len(f) ==2:
            
            if any([j < 0 for j in f]):
                raise ValueError("Level fractions cannot have negative values. Got %s" % str(f))
            
            if np.sum(f) != 1:
                if np.sum(f) < 1: # augument if sum less than one
                    fs = np.sum(f)
                    f = [f_ for f_ in f]
                    f.append(1-fs)
                else:
                    raise ValueError("Level fractions must sum to 1; instead, they sum to %f" % (np.sum(f)))
            
        else: # allow for multiple level fractions
            if any([j < 0 for j in f]):
                raise ValueError("Level fractions cannot have negative values. Got %s" % str(f))
            
            if np.sum(f) != 1:
                if np.sum(f) < 1: # augument if sum less than one
                    fs = np.sum(f)
                    f = [f_ for f_ in f]
                    f.append(1-fs)
                else:
                    raise ValueError("Level fractions must sum to 1; instead, they sum to %f" % (np.sum(f)))
    
    else:
        raise ValueError("Level fractions must be specified as a single scalar between 0 and 1 (inclusive) or as a sequence of scalars that must add up to 1")
    
    
    ranges = list()
    
    r_hi = range(len(counts))
    
    rs = 0
    if0 = 1
    
    for k in range(len(f)-1):
        if0 *= f[k]
        if1 = 1-if0
        c = counts[r_hi]
        r_lo, r_hi = __splitter__(c, if0, if1)
        if0 = if1
        r_ = range(r_lo.start + rs, r_lo.stop + rs)
        r_hi =range(r_.stop, len(counts))
        rs += r_.stop
        ranges.append(r_)
        
    ranges.append(r_hi)
        
    return ranges
    
def state_levels(x:np.ndarray, **kwargs):
    """Calculate states from a 1D waveform.
See IEEE Std 181-2011: 
    IEEE Standard for Transitions, Pulses, and Related Waveforms

Parameters:
-----------

x = np.ndarray (usually, a column vector; when a 2D array, then the function
    is applied on the given `axis` (or on flattened array if `axis` is None))

Var-keyword parameters:
----------------------

bins:  int or None;
        
        number of bins (default: 100)
        
        When None is passed here, the function attempts to calculate the 
        numbr of histogram bins according to ADC parameters specified , as
        described below.
        
bw:     float;
        
        bin width (used if bins is None)
        
adcres, adcrange, adcscale : float scalars
        
        used when bins is None AND bw is None
        
        These are passed as arguments to generate_bin_width() function (in this module)
        
        Their default values are, respectively: 15 bit, 10 V, and 1 (for Axon Digidata 1550)
        
levels: float or sequence of floats
        
        The fractional reference levels; allowed values are in the interval 
        [0,1] (see "f" argument to split_histogram() function in this module); 
        default is 0.5.
        
moment: str
        The statistical moment used to calculate the state level:
        "mean" or "mode" or a function that takes a 1D sequence of numbers
        and returns a scalar; default is "mean"

axis:   int
        The axis of the array (when x.ndim > 1); default is 0
        
Returns:
========
sLevels: A list of reference levels, corresponding to the fractional reference 
            levels specified in "levels" argument.
counts: histogram counts
edges: histogram edges
ranges: ranges of count values for the two levels


    """
    from scipy import where
    
    if not isinstance(x, np.ndarray):
        raise TypeError(f"Numpy array expected; instead, got a {type(x).__name__}")
    
    bins     = kwargs.get("bins", None)
    bw       = kwargs.get("bw", None)
    adcres   = kwargs.get("adcres", None)
    adcrange = kwargs.get("adcrange", None)
    adcscale = kwargs.get("adcscale", None)
    levels   = kwargs.get("levels", 0.5)
    moment   = kwargs.get("moment", "mean")
    axis     = kwargs.pop("axis", 0)
    
    if axis < 0 or axis >= x.ndim:
        raise ValueError(f"Bad axis index {axis} for an array of {x.ndim} dimensions")
    
    # TODO/FIXME 2023-05-17 11:58:40
    # allow data with ndim == 2
    if x.ndim > 1:
        if x.shape[1] > 1:
            raise ValueError(f"1D data expected; got data with shape {x.shape}")
        
        else:
            x = np.squeeze(x)
    
    # TODO/FIXME: 2022-10-23 16:54:42
    # might want to preserve their shape, because as of now, we use the `axis`
    # parameter
    # notNaNndx = np.squeeze(~np.isnan(x))
    notNaNndx = ~np.isnan(x)
    #print(notNaNndx.shape)

    real_x = x[notNaNndx]
    #print(real_x.shape)
    
    # FIXME/TODO: 2022-10-23 16:59:19
    # this was originlly intended to work on 1D, or flattened nD, arrays
    # 
    # now, since we use the `axis` parameter, x_min, x_max and x_range are not 
    # scalars any more, unless `axis` is None!
    # 
    # in faxt x_min, x_max, and x_range will each be a (n-1)D array !!!
    
    x_min = real_x.min(axis=axis)
    x_max = real_x.max(axis=axis)
    
    x_range = x_max-x_min
    
    if bins is None:
        if bw is None:
            if adcres is None:
                adcres = 15 # Axon Digidata 1550: 32bit data
                
            if adcrange is None:
                adcrange = 10 # Axon Digidata 1550
                
            if adcscale is None:
                adcscale = 1
            
            bw = generate_bin_width(adcres, adcrange, adcscale)
        
        if isinstance(real_x, pq.Quantity):
            bins = int(x_range.magnitude//bw)
            
        else:
            bins = int(x_range//bw)
            
    if isinstance(bins, int):
        if bins < 1:
            raise ValueError("When specified, 'bins' must be > 1; got %d instead" % bins)
        
        bw = x_range/bins
        
    # print("state_levels bins:", bins)
            
    sLevels = list()
        
    counts, edges = np.histogram(real_x, bins)
    
    ranges = split_histogram(counts, levels)
    
    if isinstance(moment, str):
        if moment == "mean":
            sLevels = [sum(counts[r]*edges[r])/sum(counts[r]) for r in ranges]
            
        elif moment == "mode":
            # get the left edge of the bin with highest count in its range
            sLevels = [edges[where(counts[r] == np.max(counts[r]))[0][0]] for r in ranges]
            
        else:
            raise ValueError ("Moment specified by an invalid string (%s); expecting 'mean' or 'mode'" % (moment))
        
    elif type(moment).__name__ == "function":
        raise NotImplementedError("Not yet implemented")
        pass
    else:
        raise TypeError("Moment must be specified by a string ('mean' or 'mode') or a unary function; got %s instead" % type(moment).__name__)
    
    return sLevels, counts, edges, ranges

def remove_dc(x, value:typing.Optional[typing.Union[pq.Quantity, np.ndarray]] = None, channel:typing.Optional[int] = None):
    """Returns a copy of x with DC offset removed.
    
    This provides a similar functionality to scipy.signal.detrend with parameters
    `axis`= 0 and `type` = "constant", except that the offset value can be either
    passed manually, or determined from the state levels of the signal (see below).
    
    NOTE: 
    • scipy.signal.detrend with `type` = "constant" just removes the signal's 
        mean value
    • unlike scipy.signal.detrend, this function ALWAYS works on axis 0 i.e., it
        accepts 1D signals with shape (N, ) and 2D signals with shape (N,M),
        where:

        N is the number of samples in the signal
        M is the number of channels (the channels in 2D signals are columns)
    
    Parameters:
    ===========
    x: numpy ndarray with maximum two dimesions.
    
        1D signal with possibly more than one channel
    
    value: scalar float, python Quantity, numpy array, sequence of float, or None (default)
            The constant value (DC) to subtract from the signal x
    
            When array-like, it must have size of 1 or as many channel indices were specvified
    
            When None, the DC level is estimated using the following algorithm:
    
            1) the signal (or specified channel) is parsed to determine two
            state levels (low and high)
    
            2) the state level where most of the signal's samples belong is 
                taken as the "DC" or "baseline" level, based on the assumption
                than most of the signal is composed of this level
    
            WARNING: This breaks down if the assumption above does not hold.
    
    channel: int, sequence of int or None (default); when None, removes offset 
            from all channels; otherwise, channel must be a valid index (or a 
            sequence of unique valid indices) in the half open interval 
    
            [ -x.size[1], x.size[1] )
    
    Returns:
    ========
    
    A copy of the signal `x` with the DC ("baseline") removed.
    
    """
    if not isinstance(x, np.ndarray):
        raise TypeError(f"Expecting a numpy array; got {type(x).__name__} instead")
    if x.ndim > 2:
        raise ValueError(f"Expecting an array of maximum 2D; instead, got an array with {x.ndim} dimensions")
    
    if isinstance(x, pq.Quantity):
        xx = x.magnitude
        
    else:
        xx = x
        
        
#     def __guess_dc_(x_):
#         levels, counts, edges, ranges = state_levels(x_)
#         
#         levelSizes = [np.sum(counts[level_range]) for level_range in ranges]
#     
#         ndx = np.argmax(levelSizes)
#         val = levels[ndx]
#             
#         return val
        
    yy = np.full_like(xx, np.nan)
    
    if xx.ndim ==2:
        if isinstance(channel, int) and channel not in range(-x.shape[1], x.shape[1]):
            raise ValueError(f"Channel index {channel} outside range ({-x.shape[1]}, {x.shape[1]})")
        
        elif isinstance(channel, (tuple, int)) and all(isinstance(c, int) for c in channel):
            if any(c not in range(-x.shape[1], x.shape[1])):
                raise ValueError(f"At leqsty one channel index in {channel} is outside the range ({-x.shape[1]}, {x.shape[1]})")
            
        elif channel is not None:
            raise TypeError(f"Channel expected to be an int or None; got {type(channel).__name__} instead")
        
        if isinstance(value, (pq.Quantity, np.ndarray)):
            if isinstance(channel, int) and len(value) > 1:
                raise ValueError(f"Value must be a scalar")
            
            elif isinstance(channel, (tuple, list)) and len(value) not in (1, len(channel)):
                raise ValueError(f"Mismatch between number of values and specified channels")
            
            elif channel is None and value.size not in (1, x.shape[1]):
                raise ValueError(f"Mismatch between number of values and signal channels")
            
            if isinstance(value, pq.Quantity) and isinstance(x, pq.Quantity):
                if isinstance(x, pq.Quantity):
                    if not scq.unitsConvertible(value, x):
                        raise TypeError(f"Value units {value.units} are incompatible with signal units {x.units}")
                    value = float(value.rescale(x.units))
                else:
                    value = float(value)
                
                
        elif isinstance(value, (tuple, list)):
            if not all(isinstance(v, number.number) for v in value):
                raise TypeError(f"When a regular sequence, value must contain numbers")
            
            if isinstance(channel, (tuple, list)) and len(value) not in (1, len(channel)):
                raise ValueError(f"Mismatch between number of values and specified channels")
            
            elif channel is None and len(value) not in (1, x.shape[1]):
                raise ValueError(f"Mismatch between number of values and specified channels")
            
        if channel is None:
            for k in range(xx.shape[1]):
                if isinstance(value, float):
                    val = value
                    
                elif isinstance(value, pq.Quantity):
                    if value.size != 1:
                        raise TypeError("When channel is not specified, value must be a scalar")
                    
                    if isinstance(x, pq.Quantity):
                        if not scq.unitsConvertible(value, x):
                            raise TypeError(f"Value units {value.units} are incompatible with signal units {x.units}")
                        
                        val = float(value.rescale(x.units))
                        
                    else:
                        val = float(value)
                    
                elif isinstance(value, np.ndarray):
                    if value.size != 1:
                        raise TypeError("When channel is not specified, value must be a scalar")
                    
                    val = float(value)
                    
                elif isinstance(value, (tuple, list)) and all(isinstance(v, float) for v in value):
                    val = value[0]
                        
                elif value is None:
                    val = estimate_dc(xx[:,k])
                    
                yy[:,k] = xx[:,k] - val

        elif isinstance(channel, int):
            yy[:,:] = xx[:,:]
            
            if isinstance(value, float):
                val = value
                
            elif isinstance(value, (tuple, list, np.ndarray)):
                val = value[0]
                
            else:
                val = __guess_dc_(xx[:,channel])
                
            yy[:,channel] = xx[:,channel] - val
            
        elif isinstance(channel, (tuple, list)):
            yy[:,:] = xx[:,:]
            
            for k,c in enumerate(channel):
                if isinstance(value, float):
                    val = value
                    
                elif isinstance(value, (tuple, list, np.ndarray)):
                    val = value[0] if len(value)==1 else value[k]
                    
                else:
                    val = __guess_dc_(xx[:,c])
                    
                yy[:,c] = xx[:,c] - val
            
    else:
        if isinstance(value, float):
            val = value
            
        elif isinstance(value, (tuple, list, np.ndarray)):
            val = value[0]
            
        else:
            val = __guess_dc_(xx)
                
        yy = xx - val
        

    if isinstance(x, (neo.AnalogSignal, DataSignal)):
        klass = x.__class__
        
        ret = klass(yy, units = x.units, t_start=x.t_start, sampling_rate=x.sampling_rate)
        ret.segment = x.segment
        ret.array_annotations = x.array_annotations
        
    elif isinstance(x, pq.Quantity):
        ret = yy * x.units
        
    else:
        ret = yy
        
    return ret
        
        
        
    

def nansize(x, **kwargs):
    """
    Sample size for data containing np.nan
    
    Var-keyword parameters:
    =======================
    axis: int in [0, x.ndim) or None (default), in which case the function works
        on a flattened view of `x`
    
    keepdims:bool, default is True. 
        When True, the axes which are reduced are left in the result.
    
    """
    axis = kwargs.pop("axis", None)
    keepdims = kwargs.pop("keepdims", True)
    
    ret = np.sum(~np.isnan(x), axis=axis, keepdims=keepdims)
    
    return ret

def maxmin(x:np.ndarray, **kwargs):
    """
    Parameters:
    ===========
    x: numpy array;
    
    Var-keyword parameters:
    =======================
    axis: int in [0, x.ndim) or None (default), in which case the function works
        on a flattened view of `x`
    
    max_first:bool, default is True
        When Talse, return np.min(x), np.max(x)
    
    Returns:
    ========
    A tuple (min, max) when max_first is False , else (max, min), where:
        min if the result of np.nanmin along the specified axis
        max is the result of np.nanmax along the specified axis
    
    NOTE: These are scalars when:
            • x.shape is (n,1) and `axis` is 0, or None 
            • x.shape is (1,n) and `axis` is 1, or None
            • x.shape is (n,)  and `axis` is 0 or None
            • x.shape is () or () (i.e. x is a numpy scalar with x.ndim == 0) 
                               and `axis` is 0 or None
    """
    axis = kwargs.pop("axis", None)
    
    max_first = kwargs.pop("max_first", True)
    
    if not isinstance(max_first, bool): # avoid ambiguities
        max_first = False
    
    mx, mn = np.nanmax(x, axis=axis), np.nanmin(x, axis=axis)
    
    return (mx, mn) if max_first else (mn, mx)

def minmax(x:np.ndarray, **kwargs):
    """ Returns maxmin(x, max_first=False)
        
        Var-keyword parameters:
        =====================
        axis: int in [0, x.ndim) or None (default), in which case the function works 
            on a flattened view of `x`.
        
    """
    axis = kwargs.pop("axis", None)
    return maxmin(x, axis = axis, max_first = False)

def argmaxmin(x:np.ndarray, **kwargs):
    """CAUTION: x must not contain NaNs.
    
    Var-keyword parameters:
    =======================
    axis: int in [0, x.ndim) or None (default), in which the function works on a
        flattened view of `x`
    
    
    max_first:bool, default is True
        When Talse, return np.min(x), np.max(x)
    
    """
    axis = kwargs.pop("axis", None)
    max_first = kwargs.op("max_first", True)
    
    amx, amn = np.argmax(x, axis=axis), np.argmin(x, axis=axis)
    return (amx, amn) if max_first else (amn, amx)

def argminmax(x:np.ndarray, **kwargs):
    """ 
        Returns argmaxmin(x, max_first=False)
        
        Var-keyword parameters:
        =====================
        axis: int in [0, x.ndim) or None (default), in which the function works on a
            flattened view of `x`
        
        
    """
    axis = kwargs.pop("axis", None)
    return argmaxmin(x, axis=axis, max_first=False)
    
def sem(x:np.ndarray, **kwargs):
    """ Standard error of the mean (SEM) for array x

    Var-keyword parameters:
    =====================
    axis: int in [0, x.ndim) or None (default), in which the function works on a
        flattened view of `x`
    
    ddof: int, degrees of freedom (default is 1)

    keepdims::bool, default is True
    
    NOTE: `ddof` and `keepdims` are passed directly to `np.std(...)`
    """
    ddof = kwargs.pop("ddof", 1)
    axis = kwargs.pop("axis", None)
    keepdims = kwargs.pop("keepdims", True)
    
    if axis is None:
        sz = np.size(x)
        
    else:
        sz = x.shape[axis]
        
    if isinstance(x, pq.Quantity):
        x = x.magnitude
        
    if isinstance(x, (pd.DataFrame, pd.Series)):
        ret = np.std(x, ddof=ddof, axis=axis, out=None) / np.sqrt(sz-ddof)
    else:
        ret = np.std(x, ddof=ddof, axis=axis, out=None, keepdims=keepdims) / np.sqrt(sz-ddof)
    
def nansem(x:np.ndarray, **kwargs):
    """SEM for data containing np.nan

    Var-keyword parameters:
    =====================
    axis: int in [0, x.ndim) or None (default), in which the function works on a
        flattened view of `x`
    
    ddof: int, degrees of freedom (default is 1)

    keepdims::bool, default is True
    
    NOTE: `ddof` and `keepdims` are passed directly to `np.nanstd(...)`
    """
    ddof = kwargs.pop("ddof", 1)
    axis = kwargs.pop("axis", None)
    keepdims = kwargs.pop("keepdims", False)
    
    sz = nansize(x, axis=axis, keepdims=keepdims)
    
    return np.nanstd(x, ddof=ddof, axis=axis, keepdims=keepdims) / np.sqrt(sz-ddof)

def rms(x:np.ndarray, **kwargs):
    """Root-mean-square of x
    
    Parameters:
    ===========
    x: 1D numpy array
    
    """
    from core import datatypes
    if not isinstance(x, np.ndarray):
        raise TypeError(f"Expecting a numpy array; got {type(x).__name__} instead")
    if not  datatypes.is_vector(x):
        raise ValueError(f"Expecting a vector; instead, got data with shape: {x.shape}")
    
    return np.sqrt(np.linalg.norm(x)/x.size)
    
#     if isinstance(x, pq.Quantity):
#         xdot = np.dot(np.abs(x.magnitude).T, np.abs(x.magnitude))
#     else:
#         xdot = np.dot(x.T, x)
#         
#     return np.sqrt(xdot/x.size)

#     if isinstance(xsq, pq.Quantity):
#         return np.sqrt(xsq.magnitude/x.size)
#     
#     return np.sqrt(xsq/x.size)

def detrend(x:typing.Union[neo.AnalogSignal, DataSignal], **kwargs):
    """Detrend a signal.
    
    Delegates to scipy.signal.detrend
    
    Parameters:
    ===========
    x: neo.AnalogSignal or DataSignal
    
    Var-keyword parameters (see also scipy.signal.detrend)
    ======================================================
    axis: int, default is 0 (unlike scipy.signal.detrend qhere the default is the last axis, -1)
    
    type: str "linear" or "constant"; optional, default is "constant"
        The default ("constant") subtracts x.mean(axis=axis) from `x`; "linear"
        subtracts from `x` a linear least-squares fit to `x`.
    
    bp: array-like of int, or a scalar Quantity in signals' units; optional, 
        default is None.
    
        When bd is a sequence of int, it represents the break points (given in 
            sample numbers, or indices into `x`, NOT domain axis coordinates) 
            between which a piecewise linear interpolation will be performed on
            `x`. This pieceqise linear interpolation will be subtracted from `x`
            when the `type` parameter(see above) is "linear".
    
        When bs is a scalar quantity (in signal units) AND `type` is "constant"
            then the value of bp will be subtracted from `x` instead of its 
            mean.
    
    
    In a nutshell:
        
    `type`          `bp`                Result:
    --------------------------------------------
    "linear"        <sequence of int>  `x` after suubtracting a piecewise linear
                                        interpolation between samples with indices
                                        in bp
                    
                    <anything else>    `x` after subtracting a linear 
                                        interpolation along the specified axis
    
    "constant"      <scalar quantity    `x` after subtracting bp value
                    in signal's units>     
    
                    <anything else>     `x` after subtracting its mean
    
                    
            When given, and `type` is "linear" an piecewise linear fit is 
            performed on `x` between each break points.
    
    Returns:
    =======
    A detrended copy of the signal.
        
    NOTE: unlike scipy.signal.detrend, which ONLY works on plain numpy arrays, 
    this function does NOT modify the signal in-place.
    
    """
    axis = kwargs.pop("axis", 0)
    detrend_type = kwargs.pop("type", "constant")
    bp = kwargs.pop("bp", 0)
    # overwrite_data = kwargs.pop("overwrite_data", True)
    
    func = functools.partial(scipy.signal.detrend, axis=axis, bp=bp,
                             type=detrend_type, overwrite_data=False)
    
    if detrend_type.lower() == "linear":
        if bp is None or isinstance(bp, typing.Sequence) and all(isinstance(v, int) for v in bp):
            ret = func(x.magnitude)
            
        else:
            raise TypeError(f"Unexpected 'bp' value ({bp}) for {detrend_type} detrending")
        
    elif detrend_type.lower() == "constant":
        if isinstance(bp, pq.Quantity):
            if bp.size == 1 and scq.unitsConvertible(bp, x):
                return x-bp
            else:
                raise TypeError(f"Wrong constant value in bp: {bp} for {detrend_type} detrending")
            
        elif bp is not None:
            raise TypeError(f"Unexpected 'bp' value ({bp}) for {detrend_type} detrending")
            
        ret = func(x.magnitude)
                
    ret = type(x)(ret, t_start = x.t_start, units = x.units, 
                    sampling_rate = x.sampling_rate, 
                    file_origin = x.file_origin, 
                    name=x.name, description = x.description)
    
    ret.segment = x.segment
    ret.array_annotations = x.array_annotations
    ret.annotations.update(x.annotations)
    
    return ret

def sosfilter(sig:typing.Union[pq.Quantity, np.ndarray], kernel:np.ndarray):
    if isinstance(sig, (neo.AnalogSignal, DataSignal)):
        ret = scipy.signal.sosfiltfilt(kernel, sig.magnitude, axis=0)
            
        klass = sig.__class__
        name = sig.name
        if isinstance(name, str) and len(name.strip()):
            name = f"{name}_filtered"
        else:
            name = "filtered"
        ret = klass(ret, units = sig.units, t_start =  sig.t_start,
                            sampling_rate = sig.sampling_rate,
                            name=name, 
                            description = f"{sig.description} filtered")
        
    else:
        ret = scipy.signal.sosfiltfilt(kernel, sig, axis=0)
                
    return ret
    
    
def estimate_dc(x_):
    levels, counts, edges, ranges = state_levels(x_)
    
    levelSizes = [np.sum(counts[level_range]) for level_range in ranges]

    ndx = np.argmax(levelSizes)
    val = levels[ndx]
        
    return val
        

@safeWrapper
def convolve(sig, w, **kwargs):
    """1D convolution of neo.AnalogSignal sig with kernel "w".
    
    Parameters:
    -----------
    
    sig : neo.AnalogSignal; if it has multiple channels, the convolution is
        applied for each channel
        
    w : 1D array-like
    
    Var-keyword parameters are passed on to the scipy.signal.convolve function,
    except for the "mode" which is always set to "same"
    """
    
    from scipy.signal import convolve
    
    name = kwargs.pop("name", "")
    
    units = kwargs.pop("units", pq.dimensionless)
    
    kwargs["mode"] = "same" # force "same" mode for convolution
    
    if sig.shape[1] == 1:
        ret = neo.AnalogSignal(convolve(sig.magnitude.flatten(), w, **kwargs),\
                            units = sig.units, \
                            t_start = sig.t_start, \
                            sampling_period = sig.sampling_period,\
                            name = "%s convolved" % sig.name)
        
    else:
        csig = [convolve(sig[:,k].magnitude.flatten(), w, **kwargs)[:,np.newaxis] for k in range(sig.shape[1])]
        
        ret = neo.AnalogSignal(np.concatenate(csig, axis=1),
                               units = sig.units,
                               t_start = sig.t_start,
                               sampling_period = sig.sampling_period,
                               name = "%s convolved" % sig.name)
        
    ret.annotations.update(sig.annotations)
    
    return ret

    
@safeWrapper
def parse_step_waveform_signal(sig, method="state_levels", **kwargs):
    """Parse a step waveform -- containing two states ("high" and "low").
    
    DEPRECATED: Please use detect_boxcar(…) instead.
    
    Typical example is a depolarizing curent injection step (or rectangular pulse)
    
    Parameters:
    ----------
    sig = neo.AnalogSignal with one channel (i.e. sig.shape[1]==1)
    
    Named parameters:
    -----------------
    box_size = length of smoothing boxcar window (default, 0)
    
    method: str, one of "state_levels" (default) or "kmeans"
    
    The following are used only when methos is "state_levels" and are passed 
    directly to signalprocessing.state_levels():
    
    adcres,
    adcrange,
    adcscale
    
    Returns:
    
    down: quantity array of high to low transitions times (in units of signal.times)
    up:  the same, for low to high transition times (in units of signal.times)
    inj: scalar quantity: the amplitude of the transition (in units of the signal)
    centroids: numpy array with shape (2,1): the centroid values i.e., the mean values
        of the two state levels
        
        
    """
    # FIXME 2023-06-18 22:09:23
    # Currently this function does almost the same thing as detect_boxcar.
    # TODO 2023-06-18 22:10:21 merge codes into one function !
    
    from scipy import cluster
    from scipy.signal import boxcar
    
    warnings.warn("This function is DEPRECATED. Please use 'detect_boxcar'",category=warnings.DeprecationWarning)
    
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("Expecting an analogsignal; got %s instead" % type(sig).__name__)
    
    if sig.ndim == 2 and sig.shape[1] > 1:
        raise ValueError("Expecting a signal with one channel, instead got %d" % sig.shape[1])
    
    box_size = kwargs.pop("box_size", 0)
    
    if box_size > 0:
        window = boxcar(box_size)/box_size
        sig_flt = convolve(sig, window)
        #sig_flt = convolve(np.squeeze(sig), window, mode="same")
        #sig_flt = neo.AnalogSignal(sig_flt[:,np.newaxis], units = sig.units, t_start = sig.t_start, sampling_rate = 1/sig.sampling_period)
    else:
        sig_flt = sig
        
    # 1) get transition times from injected current
    # use filtered signal, if available
    
    if method == "state_levels":
        levels = kwargs.pop("levels", 0.5)
        adcres = kwargs.pop("adcres", 15)
        adcrange = kwargs.pop("adcrange", 10)
        adcscale = kwargs.pop("adcrange", 1e3)
    
        centroids, cnt, edg, rng = state_levels(sig_flt.magnitude, levels = levels, 
                                    adcres = adcres, 
                                    adcrange = adcrange, 
                                    adcscale = adcscale)
        
        centroids = np.array(centroids).T[:,np.newaxis]
        
    else:
        centroids, distortion = cluster.vq.kmeans(sig_flt, 2)
        centroids = np.sort(centroids, axis=0)
    
    #print(centroids)
    
    if len(centroids) == 0:
        return None, None, None, None, None
    
    label, dst = cluster.vq.vq(sig, centroids) # use un-filtered signal here
    edlabel = np.ediff1d(label, to_begin=0)
    
    down = sig.times[np.where(edlabel == -1)]
    
    up  = sig.times[np.where(edlabel == 1)]

    # NOTE: 2017-08-31 23:04:26 FYI: depolarizing = down > up 
    # in current-clamp, a depolarizing current injection is an outward current 
    # which therefore goes up BEFORE it goes back down, hence down is later than
    # up 
    
    # the step amplitude
    #amplitude = np.diff(centroids.ravel()) * sig.units
    amplitude = np.diff(centroids.flatten()) * sig.units
    
    return down, up, amplitude, centroids, label

@safeWrapper
def resample_pchip(sig, new_sampling_period, old_sampling_period = 1):
    """Resample a signal using a piecewise cubic Hermite interpolating polynomial.
    
    Resampling is calculated using scipy.interpolate.PchipInterpolator, along the
    0th axis.
    
    Parameters:
    -----------
    
    sig: numpy ndarray, python Quantity array or numpy array subclass which has 
        the attribute "sampling_period"
    
    new_sampling_period: float scalar
        The desired sampling period after resampling
        
    old_sampling_period: float scalar or None (default)
        Must be specified when sig is a generic numpy ndarray or Quantity array.
        
    Returns:
    --------
    
    ret: same type as sig
        A version of the signal resampled along 0th axis:
        
        * upsampled if new_sampling_period < old_sampling_period
        
        * downsampled if new_sampling_period > old_sampling_period
        
    When new_sampling_period == old_sampling_period, returns a reference to the
        signal (no resampling is performed and no data is copied).
        
        CAUTION: In this case the result is a REFERENCE to the signal, and 
                 therefore, any methods that modify the result in place will 
                 also modify the original signal!
    
    """
    # for upsampling this will introduce np.nan at the end
    # we replace these values wihtt he last signal sample value
    from scipy.interpolate import PchipInterpolator as pchip
    
    from . import datatypes
    
    if isinstance(sig, (neo.AnalogSignal, DataSignal)):
        if isinstance(new_sampling_period, pq.Quantity):
            if not scq.unitsConvertible(new_sampling_period, sig.sampling_period):
                raise TypeError("new sampling period units (%s) are incompatible with those of the signal's sampling period (%s)" % (new_sampling_period.units, sig.sampling_period.units))
            
            new_sampling_period.rescale(sig.sampling_period.units)
            
        else:
            new_sampling_period *= sig.sampling_period.units
    
        if sig.sampling_period > new_sampling_period:
            scale = sig.sampling_period / new_sampling_period
            new_axis_len = int(np.floor(len(sig) * scale))
            descr = "Upsampled"
            
        elif sig.sampling_period < new_sampling_period:
            scale = new_sampling_period / sig.sampling_period
            new_axis_len = int(np.floor(len(sig) // scale))
            descr = "Downsampled"
            
        else: # no resampling required; return reference to signal
            return sig
        
        new_times, new_step = np.linspace(sig.t_start.magnitude, sig.t_stop.magnitude, 
                                          num=new_axis_len, retstep=True, endpoint=False)
        
        #print("ephys.resample_pchip new_step", new_step, "new_sampling_period", new_sampling_period)
        
        assert(np.isclose(new_step, float(new_sampling_period.magnitude)))
        
        interpolator = pchip(sig.times.magnitude.flatten(), sig.magnitude.flatten(), 
                             axis=0, extrapolate=False)
        
        new_sig = interpolator(new_times)
        
        new_sig[np.isnan(new_sig)] = sig[-1,...]
        
        ret = sig.__class__(new_sig, units=sig.units,
                            t_start = new_times[0]*sig.times.units,
                            sampling_period=new_sampling_period,
                            name = sig.name,
                            description="%s %s %d-fold" % (sig.name, descr, scale))
        
        ret.annotations.update(sig.annotations)
    
        return ret
    
    else:
        if old_sampling_period is None:
            raise ValueError("When signal is a generic array the old sampling period must be specified")
        
        if isinstance(old_sampling_period, pq.Quantity):
            old_sampling_period = old_sampling_period.magnitude
            
        if isinstance(new_sampling_period, pq.Quantity):
            new_sampling_period = new_sampling_period.magnitude
            
        if old_sampling_period > new_sampling_period:
            scale = int(old_sampling_period / new_sampling_period)
            new_axis_len = sig.shape[0] * scale
            
        elif old_sampling_period < new_sampling_period:
            scale = int(new_sampling_period / old_sampling_period)
            new_axis_len = sig.shape[0] // scale
            
        else: # no resampling required; return reference to signal
            return sig
        
        t_start = 0
        
        t_stop = sig.shape[0] * old_sampling_period
        
        new_times, new_step = np.linspace(sig.t_start.magnitude, sig.t_stop.magnitude, 
                                          num=new_axis_len, retstep=True, endpoint=False)
        
        assert(np.isclose(new_step,float(new_sampling_period.magnitude)))
        
        interpolator = pchip(sig.times.magnitude.flatten(), sig.magnitude.flatten(), 
                             axis=0, extrapolate=False)
        
        ret = interpolator(new_times)
        
        ret[np.isnan(ret)] = sig[-1, ...]
        
        return ret

@safeWrapper
def diff(sig, n=1, axis=-1, prepend=False, append=True):
    """Calculates the n-th discrete difference along the given axis.
    
    Calls numpy.diff() under the hood.
    
    Parameters:
    ----------
    sig: numpy.array or subclass
        NOTE: singleton dimensions will be squeezed out
    
    Named parameters:
    -----------------
    These are passed directly to numpy.diff(). 
    The numpy.diff() documentation is replicated below highlighting any differences.
    
    n: int, optional
        The number of times values are differenced. 
        If zero the input is returned as is.
        
        Default is 1 (one)
    
    prepend, append: None or array-like, or bool
        Values to prepend/append to sig along the axis PRIOR to performing the 
        difference!
        
        NOTE:   When booleans, a value of True means that prepend or append will
        take, respectively, the first or last signal values along difference axis.
        
                A value of False is equivalent to None.
                
        NOTE:   "prepend" has default False; "append" has default True
        
    
    """
    if not isinstance(axis, int):
        raise TypeError("Axis expected to be an int; got %s instead" % type(axis).__name__)
    
    # first, squeeze out the signal's sigleton dimensions
    sig_data = np.array(sig).squeeze() # also copies the data; also we can use plain arrays
    #sig_data = sig.magnitude.squeeze() # also copies the data
    
    if isinstance(append, bool):
        if append:
            append_ndx = [slice(k) for k in sig_data.shape]
            append_ndx[axis] = -1
            
            append_shape = [slice(k) for k in sig_data.shape]
            append_shape[axis] = np.newaxis
            
            append = sig_data[tuple(append_ndx)][tuple(append_shape)]
            
        else:
            append = None
            
    if isinstance(prepend, bool):
        if prepend:
            prepend_ndx = [slice(k) for k in sig_data.shape]
            prepend_ndx[axis] = 0
            
            prepend_shape = [slice(k) for k in sig_data.shape]
            prepend_shape[axis] = np.newaxis
            
            prepend = sig_data[tuple(prepend_ndx)][tuple(prepend_shape)]
            
        else:
            prepend = None
            
    diffsig = np.diff(sig_data, n = n, axis = axis, prepend=prepend, append=append)
    
    ret = neo.AnalogSignal(diffsig, 
                           units = sig.units/(sig.times.units ** n),
                           t_start = 0 * sig.times.units,
                           sampling_rate = sig.sampling_rate,
                           name = sig.name,
                           description = "%dth order difference of %s" % (n, sig.name))
    
    ret.annotations.update(sig.annotations)
    
    return ret

@safeWrapper
def gradient(sig:[neo.AnalogSignal, DataSignal, np.ndarray], n:int=1, axis:int=0):
    """ First order gradient through central differences.
    
    Parameters:
    ----------
    
    sig: numpy.array or subclass
        The signal; can have at most 2 dimensions.
        When sig.shape[1] > 1, the gradient is calculated across the specified axis
    
    n: int; default is 1 (one)
        The spacing of the gradient (see numpy.gradient() for details)
    
    axis: int; default is 0 (zero)
        The axis along which the gradient is calculated;
        Can be -1 (all axes), 0, or 1.
        
        TODO/FIXME 2019-04-27 10:07:26: 
        At this time the function only supports axis = 0
        
    Returns:
    -------
    
    ret: neo.AnalogSignal or DataSignal, according to the type of "sig".
    
    
    """
    diffsig = np.array(sig) # for a neo.AnalogSignal this also copies the signal's magnitude
    
    if diffsig.ndim == 2:
        for k in range(diffsig.shape[1]):
            diffsig[:,k] = np.gradient(diffsig[:,k], n, axis=0)
            
        diffsig /= (n * sig.sampling_period.magnitude)
            
    elif diffsig.ndim == 1:
        diffsig = np.gradient(diffsig, n, axis=0)
        diffsig /= (n * sig.sampling_period.magnitude)
            
    else:
        raise TypeError("'sig' has too many dimensions (%d); expecting 1 or 2" % diffsig.ndim)
        
    if isinstance(sig, DataSignal):
        ret = DataSignal(diffsig, 
                            units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = sig.name,
                            description = "Gradient of %s over %d samples along axis %d" % (sig.name, n, axis))
 
    else:
        ret = neo.AnalogSignal(diffsig, 
                            units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = sig.name,
                            description = "Gradient of %s over %d samples along axis %d" % (sig.name, n, axis))
 
    ret.annotations.update(sig.annotations)
    
    return ret
    
@safeWrapper
def ediff1d(sig:[neo.AnalogSignal, DataSignal, np.ndarray], to_end:numbers.Number=0, to_begin:[numbers.Number, type(None)]=None):
    """Differentiates each channel of an analogsignal with respect to its time basis.
    
    Parameters:
    -----------
    
    sig: neo.AnalogSignal, numpy.array, or Quantity array
    
    
    Named parameters (see numpy.ediff1d):
    -------------------------------------
    Passed directly to numpy.ediff1d:
    
    to_end: scalar float, or 0 (default) NOTE: for numpy.ediff1d, the default is None
    
    to_begin: scalar float, or None (default)
    
    Returns:
    --------
    DataSignal or neo.AnalogSignal, according to the type of "sig"
    
    """
    
    diffsig = np.array(sig) # for a neo.AnalogSignal this also copies the signal's magnitude
    
    if diffsig.ndim == 2:
        for k in range(diffsig.shape[1]):
            diffsig[:,k] = np.ediff1d(diffsig[:,k], to_end=to_end, to_begin=to_begin)# to_end = to_end, to_begin=to_begin)
            
    elif diffsig.ndim == 1:
        diffsig = np.ediff1d(diffsig, to_end=to_end, to_begin=to_begin)
            
    else:
        raise TypeError("'sig' has too many dimensions (%d); expecting 1 or 2" % diffsig.ndim)
        
    diffsig /= sig.sampling_period.magnitude
    
    if isinstance(sig, DataSignal):
        ret = DataSignal(diffsig, units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = sig.name,
                            description = "First order forward difference of %s" % sig.name)
    
        
    else:
        ret = neo.AnalogSignal(diffsig, units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = sig.name,
                            description = "First order forward difference of %s" % sig.name)
    
    ret.annotations.update(sig.annotations)
    
    return ret

@safeWrapper
def forward_difference(sig:[neo.AnalogSignal, DataSignal, np.ndarray], n:int=1, to_end:numbers.Number=0, to_begin:[numbers.Number, type(None)]=None):
    """Calculates the forward difference along the time axis.
    
    Parameters:
    -----------
    
    sig: neo.AnalogSignal, numpy.array, or Quantity array
    
    
    Named parameters (see numpy.ediff1d):
    -------------------------------------
    
    n: int;
        number of samples in the difference.
        
        Must satisfy 0 <= n < len(sig) -2
        
        When n=0 the function returns a reference to the signal.
        
        When n=1 (the default), the function calls np.ediff1d() on the signal's 
            magnitude and the result is divided by signals sampling period
        
        When n > 1 the function calculates the forward difference 
            
            (sig[n:] - sig[:-n]) / (n * sampling_rate)
            
        Values of n > 2 not really meaningful.
            
    to_end: scalar float, or 0 (default) NOTE: for numpy.ediff1d, the default is None
    
    to_begin: scalar float, or None (default)
    
    Returns:
    --------
    DataSignal or neo.AnalogSignal, according to the type of "sig"
    
    """
    
    def __n_diff__(ary, n, to_b, to_e):
        dsig = ary[n:] - ary[:-n]
        
        shp = [s for s in ary.shape]
        
        if to_end is not None:
            if to_begin is None:
                shp[0] = n
                dsig = np.append(dsig, np.full(tuple(shp), to_e), axis=0)
                
            else:
                to_start = n//2
                to_stop = n - to_start
                
                shp[0] = to_start
                dsig = np.insert(dsig, np.full(tuple(shp), to_b), axis=0)
                
                shp[0] = to_stop
                dsig = np.append(dsig, np.full(tuple(shp), to_e), axis=0)
                
        else:
            if to_end is None:
                shp[0] = n
                dsig = np.insert(dsig, np.full(tuple(shp), to_b), axis=0)
                
            else:
                to_start = n//2
                to_stop = n - to_start
                
                shp[0] = to_start
                dsig = np.insert(dsig, np.full(tuple(shp), to_b), axis=0)
                
                shp[0] = to_stop
                dsig = np.append(dsig, np.full(tuple(shp), to_e), axis=0)
                
        return dsig
        
    
    if not isinstance(n, int):
        raise TypeError("'n' expected to be an int; got %s instead" % type(n).__name__)
    
    if n < 0: 
        raise ValueError("'n' must be >= 0; got %d instead" % n)
    
    diffsig = np.array(sig) # for a neo.AnalogSignal this also copies the signal's magnitude
    
    if diffsig.ndim == 2:
        if n >= diffsig.shape[0]:
            raise ValueError("'n' is too large (%d); should be n < %d" % (n, diffsig.shape[0]))
        
        if n == 0:
            return sig
        
        elif n == 1:
            for k in range(diffsig.shape[1]):
                diffsig[:,k] = np.ediff1d(diffsig[:,k], to_end=to_end, to_begin=to_begin)# to_end = to_end, to_begin=to_begin)
                
            diffsig /= sig.sampling_period.magnitude
            
        else:
            for k in range(diffsig.shape[1]):
                diffsig[:,k] = __n_diff__(diffsig[:,k], n=n, to_e=to_end, to_b=to_begin)# to_end = to_end, to_begin=to_begin)
            
            diffsig /= (n * sig.sampling_period.magnitude)
            
    elif diffsig.ndim == 1:
        if n >= len(diffsig):
            raise ValueError("'n' is too large (%d); should be < %d" % (n, len(diffsig)))
        
        if n == 0:
            return sig
        
        elif n == 1:
            diffsig = __n_diff__(diffsig, n=n, to_e = to_end, to_b = to_begin)
            #diffsig = np.ediff1d(diffsig, to_end=to_end, to_begin=to_begin)
            diffsig /= sig.sampling_period.magnitude
            
        else:
                    
            diffsig /= (n * sig.sampling_period.magnitude)
            
    else:
        raise TypeError("'sig' has too many dimensions (%d); expecting 1 or 2" % diffsig.ndim)
        
        
    if isinstance(sig, DataSignal):
        ret = DataSignal(diffsig, units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = "%s_diff(1)" % sig.name,
                            description = "Forward difference (%dth order) of %s" % (n, sig.name))
 
    else:
        ret = neo.AnalogSignal(diffsig, units = sig.units / sig.times.units, 
                            t_start = sig.t_start, 
                            sampling_period = sig.sampling_period, 
                            name = "%s_diff(1)" % sig.name,
                            description = "Forward difference (%dth order) of %s" % (n, sig.name))
 
    ret.annotations.update(sig.annotations)
    
    return ret

def root_mean_square(x, axis = None):
    """ Computes the RMS of a signal.
    
    Positional parameters
    =====================
    x = neo.AnalogSignal, neo.IrregularlySampledSignal, or datatypes.DataSignal
    
    Named parameters
    ================
    
    axis: None (defult), or a scalar int, or a sequence of int: index of the axis,
            in the interval [0, x.ndim), or None (default)
            
            When a sequence of int, the RMS will be calculated across all the
            specified axes
    
        When None (default) the RMS is calculated for the flattened signal array.
        
        This argument is passed on to numpy.mean
        
    Returns: a scalar float
    RMS = sqrt(mean(x^2))
    
    """
    from . import datatypes 
    
    if not isinstance(x, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
        raise TypeError("Expecting a neo.AnalogSignal, neo.IrregularlySampledSignal, or a datatypes.DataSignal; got %s instead" % type(x).__name__)
    
    if not isinstance(axis, (int, tuple, list, type(None))):
        raise TypeError("axis expected to be an int or None; got %s instead" % type(axis).__name__)
    
    if isinstance(axis, (tuple, list)):
        if not all([isinstance(a, int) for a in axis]):
            raise TypeError("Axis nindices must all be integers")
        
        if any([a < 0 or a > x.ndim for a in axis]):
            raise ValueError("Axis indices must be inthe interval [0, %d)" % x.ndim)
    
    if isinstance(axis, int):
        if axis < 0 or axis >= x.ndim:
            raise ValueError("Invalid axis index; expecting value between 0 and %d ; got %d instead" % (x.ndim, axis))
        
    return np.sqrt(np.mean(np.abs(x), axis=axis))
    
def signal_to_noise(x, axis=None, ddof=None, db=True):
    """Calculates SNR for the given signal.
    
    Positional parameters:
    =====================
    x = neo.AnalogSignal, neo.IrregularlySampledSignal, or datatypes.DataSignal
    
    Named parameters
    ================
    
    axis: None (defult), or a scalar int, or a sequence of int: index of the axis,
            in the interval [0, x.ndim), or None (default)
            
            When a sequence of int, the RMS will be calculated across all the
            specified axes
    
        When None (default) the RMS is calculated for the flattened signal array.
        
        This argument is passed on to numpy.mean and numpy.std
        
    ddof: None (default) or a scalar int: delta degrees of freedom
    
        When None, it sill be calculated from the size of x along the specified axes
        
        ddof is passed onto numpy.std (see numpy.std for details)
        
    db: boolean, default is True
        When True, the result is expressed in decibel (10*log10(...))
        
    """
    from . import datatypes  

    if not isinstance(x, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
        raise TypeError("Expecting a neo.AnalogSignal, neo.IrregularlySampledSignal, or a datatypes.DataSignal; got %s instead" % type(x).__name__)
    
    if not isinstance(axis, (int, tuple, list, type(None))):
        raise TypeError("axis expected to be an int or None; got %s instead" % type(axis).__name__)
    
    if isinstance(axis, (tuple, list)):
        if not all([isinstance(a, int) for a in axis]):
            raise TypeError("Axis nindices must all be integers")
        
        if any([a < 0 or a > x.ndim for a in axis]):
            raise ValueError("Axis indices must be inthe interval [0, %d)" % x.ndim)
    
    if isinstance(axis, int):
        if axis < 0 or axis >= x.ndim:
            raise ValueError("Invalid axis index; expecting value between 0 and %d ; got %d instead" % (x.ndim, axis))
        
    if not isinstance(ddof, (int, type(None))):
        raise TypeError("ddof expected to be an int or None; got %sinstead" % ype(ddof).__name__)
    
    if ddof is None:
        if axis is None:
            ddof = 1
            
        elif isinstance(axis, int):
            ddof = 1
            
        else:
            ddof = len(axis)
            
    else:
        if ddof < 0:
            raise ValueError("ddof must be >= 0; got %s instead" % ddof)
        
        
    rms = root_mean_square(x, axis=axis)
    
    std = np.std(x, axis=axis, ddof=ddof)
    
    ret = rms/std
    
    if db:
        return np.log10(ret.magnitude.flatten()) * 20 
    
    return ret


@safeWrapper
def resample_poly(sig, new_rate, p=1000, window=("kaiser", 5.0)):
    """Resamples signal using a polyphase filtering.
    
    Resampling uses polyphase filtering (scipy.signal.resample_poly) along the
    0th axis.
    
    Parameters:
    ===========
    
    sig: neo.AnalogSignal or datatypes.DataSignal
    
    new_rate: either a float scalar, or a Python Quantity 
            When a Python Quantity, it must have the same units as signal's 
            sampling RATE units.
            
            Alternatively, if it has the same units as the signal's sampling 
            PERIOD, its inverse will be taken as the new sampling RATE.
             
            NOTE: It must be strictly positive i.e. new_rate > 0
             
            When new_rate == sig.sampling_rate, the function returns a copy of sig.
             
            Otherwise, the function returns a copy of sig where all columns are resampled via
            scipy.signal.resample_poly
    
    p: int
        factor of precision (default 1000): power of 10 used to calculate up/down sampling:
        up = new_rate * p / signal_sampling_rate
        down = p
        
    window: string, tuple, or array_like, optional
        Desired window to use to design the low-pass filter, or the FIR filter 
        coefficients to employ. see scipy.signal.resample_poly() for details
    
    """
    from scipy.signal import resample_poly as resample
    
    using_rate=True
    
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("First parameter expected to be a neo.AnalogSignal; got %s instead" % type(sig).__name__)
    
    if isinstance(new_rate, numbers.Real):
        new_rate = new_rate * sig.sampling_rate.units
        
    elif isinstance(new_rate, pq.Quantity):
        if new_rate.size > 1:
            raise TypeError("Expecting new_rate a scalar quantity; got a shaped array %d" % new_res)
        
        if new_rate.units != sig.sampling_rate.units:
            if new_rate.units == sig.sampling_period.units:
                using_rate = False
                
            else:
                raise TypeError("Second parameter should have the same units as signal's sampling rate (%s); it has %s instead" % (sig.sampling_rate.units, new_rate.units))
                
    
    if new_rate <= 0:
        raise ValueError("New sampling rate (%s) must be strictly positive !" % new_rate)
    
    p = int(p)
    
    if using_rate:
        if new_rate == sig.sampling_rate:
            return sig.copy()
        
        up = int(new_rate / sig.sampling_rate * p)
        
    else:
        if new_rate == sig.sampling_period:
            return sig.copy()
            
        up = int(sig.sampling_period / new_rate * p)
    
    if using_rate:
        ret = neo.AnalogSignal(resample(sig, up, p, window=window), 
                               units = sig.units, 
                               t_start = sig.t_start,
                               sampling_rate = new_rate)
        
    else:
        ret = neo.AnalogSignal(resample(sig, up, p, window=window), 
                               t_start = sig.t_start,
                               units = sig.units, 
                               sampling_period = new_rate) 
        
    ret.name = sig.name
    ret.description = "%s resampled %f fold on axis 0" % (sig.name, up)
    ret.annotations = sig.annotations.copy()
    
    return ret


@safeWrapper
def remove_signal_offset(sig):
    if not isinstance(sig, neo.AnalogSignal):
        raise TypeError("Expecting an AnalogSignal; got %s instead" % type(sig).__name__)
    
    return sig - sig.min()

@safeWrapper
def batch_normalise_signals(*arg):
    ret = list()
    for sig in arg:
        ret.append(peak_normalise_signal(sig))
        
    return ret

@safeWrapper
def batch_remove_offset(*arg):
    ret = list()
    for sig in arg:
        ret.append(remove_signal_offset(sig))

    return ret
    
@safeWrapper
def peak_normalise_signal(sig:typing.Union[neo.AnalogSignal, np.ndarray],
                          minVal:typing.Optional[typing.Union[numbers.Number, pq.Quantity]]=None,
                          maxVal:typing.Optional[typing.Union[numbers.Number, pq.Quantity]]=None,
                          axis:typing.Optional[int] = None,
                          minIndex:typing.Optional[int] = None,
                          maxIndex:typing.Optional[int] = None):
    """Returns a peak-normalized copy of the I(V) curve
    
    Positional parameters:
    ----------------------
    
    sig = AnalogSignal with Im data (typically, a time slice corresponding to the
            Vm ramp)
            
    minVal, maxVal = the min and max values to normalize against;
    
    Returns:
    -------
    
    AnalogSignal normalized according to:
    
            ret = (sig - minVal) / (maxVal - minVal)
    
    """

    # NOTE: 2023-10-19 09:20:59
    # allow individual specification of either minVal or maxVal
    #
    # when either minVal or maxVal are NOT given:
    # • allow specification of axis where the mising extremum can be found
    #   default is None
    # • when array (sig) size along the axis for finding the extremum or extrema
    #   (see above) is > 1 request the index along that axis where the missing
    #   extremum should be taken from (e.g. for a column-wise multi-channel signal,
    #   you may want the extremum to be taken from th 1st column, etc)
    #
    #   However, we allow normalization of each "channel" to its own extrema by
    #   specifying minIndex and maxIndex as being None (the default)
                        
    if minVal is None:
        minVal = sig.min(axis)
        # if isinstance(sig, (neo.AnalogSignal, pq.Quantity)):
        #     minVal = sig.min(axis)
        # else:
        #     raise TypeError("When signal is not an analog signal both minVal must be specified")
            
    elif isinstance(minVal, numbers.Number):
        if isinstance(sig, (neo.AnalogSignal, pq.Quantity)):
            minVal *= sig.units
        
    elif isinstance(minVal, pq.Quantity):
        if minVal.size > 1:
            # TODO/FIXME 2023-10-19 09:32:10
            # what if size of minVal is same as sig.shape[axis]?
            raise ValueError("minVal must be scalar")
        
        if isinstance(sig, (neo.AnalogSignal, pq.Quantity)):
            if not scq.unitsConvertible(minVal, sig):
                raise ValueError(f"Units of minVal ({minVal.units}) are incompatible with signal units ({sig.units})")
                
            if minVal.units != sig.units:
                minVal = minVal.rescale(sig.units)
                
        else:
            minVal = float(minVal) # FIXME: see TODO/FIXME 2023-10-19 09:32:10
        
    else:
        raise TypeError("minVal must be a scalar number or quantity")
        
    if maxVal is None:
        maxVal = sig.max(axis)
        # if isinstance(sig, (neo.AnalogSignal, pq.Quantity)):
        #     maxVal = sig.max(axis)
        # else:
        #     raise TypeError("When signal is not an analog signal both minVal must be specified")
            
    elif isinstance(maxVal, numbers.Number):
        if isinstance(sig, (neo.AnalogSignal, pq.Quantity)):
            maxVal *= sig.units
        
    elif isinstance(maxVal, pq.Quantity):
        if maxVal.size > 1:
            # TODO/FIXME 2023-10-19 09:31:33
            # this is OK when axis is None, but what if maxVal.size
            # what if size of maxVal is same as sig.shape[axis]?
            raise ValueError("maxVal must be scalar")
        
        if isinstance(sig, (neo.AnalogSignal, pq.Quantity)):
            if not scq.unitsConvertible(maxVal, sig):
                raise ValueError(f"Units of maxVal ({maxVal.units}) are incompatible with signal units ({sig.units})")
                
            if maxVal.units != sig.units:
                maxVal = maxVal.rescale(sig.units)
                
        else:
            maxVal = float(maxVal) # FIXME: see TODO/FIXME 2023-10-19 09:31:33
        
    else:
        raise TypeError("maxVal must be a scalar number or quantity")
        
            
    return (sig - minVal)/(maxVal - minVal)

def correlate(in1, in2, **kwargs):
    """Calls scipy.signal.correlate(in1, in2, **kwargs).
    
    Correlation mode is by default set to "same", but can be overridden.
    
    Parameters
    
    ----------
    
    in1 : neo.AnalogSignal, neo.IrregularlySampledSignal, datatypes.DataSignal, or np.ndarray.
    
        Must be a 1D signal i.e. with shape (N,) or (N,1) where N is the number 
        of samples in "in1"
    
        The signal for which the correlation with "in2" is to be calculated. 
        
        Typically this is the longer of the signals to correlate.
        
    in2 : neo.AnalogSignal, neo.IrregularlySampledSignal, datatypes.DataSignal, or np.ndarray
    
        Must be a 1D signal, i.e. with shape (M,) or (M,1) where M is the number 
        of samples in "in2"
        
        The signal that "in1" is correlated with (typically, shorter than "in1")
        
    Var-keyword parameters
    
    -----------------------
    
    method : str {"auto", "direct", "fft"}, optional; default is "auto"
        Passed to scipy.signal.correlate
        
    name : str
        The name attribute of the result
        
    units : None or a Python Quantity or UnitQuantity. Default is None.
    
        These is mandatory when "a" is a numpy array
    
        The units of the returned signal; when None, the units of the returned 
        signal are pq.dimensionless (where "pq" is an alias for Python quantities
        module)
    
    Returns
    
    -------
    
    ret : object of the same type as "in1"
        Contains the result of correlating "in1" with "in2".
        
        When "in1" is a neo.AnalogSignal, neo.IrregularlySampledSignal, or datatypes.DataSignal,
        ret will have "times" attribute copied from "in1" and with "units" attribute
        set to dimensionless, unless specified explicitly by "units" var-keyword parameter.
        
        
    NOTE
    
    ----
    
    The function correlates the magnitudes of the signals and does not take into
    account their units, or their definition domains (i.e. "times" attribute).
    
    See also:
    --------
    scipy.signal.correlate
    
    """
    
    from scipy.signal import correlate
    
    from . import datatypes  
    
    name = kwargs.pop("name", "")
    
    units = kwargs.pop("units", pq.dimensionless)
    
    mode = kwargs.pop("mode", "same") # let mdoe be "same" by default but allow it to be overridden
    
    if in1.ndim > 1 and in1.shape[1] > 1:
        raise TypeError("in1 expected to be a 1D signal")
    
    if in2.ndim > 1 and in2.shape[1] > 1:
        raise TypeError("in2 expected to be a 1D signal")
    
    if isinstance(in1, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
        in1_ = in1.magnitude.flatten()
        
    else:
        in1_ = in1.flatten()

    if isinstance(in2, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
        in2_ = in2.magnitude.flatten()
        
    else:
        in2_ = in2.flatten()
        
    in2_ = np.flipud(in2_)
        
    corr = correlate(in1_, in2_, mode=mode, **kwargs)
    
    if isinstance(in1, (neo.AnalogSignal, DataSignal)):
        ret = neo.AnalogSignal(corr, t_start = in1.t_start,
                                units = units, 
                                sampling_period = in1.sampling_period,
                                name = name)
    
        if isinstance(in2, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
            ret.description = "Correlation of %s with %s" % (in1.name, in2.name)
            
        else:
            ret.description = "Correlation of %s with an array" % in1.name
            
        return ret
    
    elif isinstance(in1, neo.IrregularlySampledSignal):
        ret = neo.IrregularlySampledSignal(corr, 
                                            units=units,
                                            times = in1.times,
                                            name = name)
    
        if isinstance(in2, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal)):
            ret.description = "Correlation of %s with %s" % (in1.name, in2.name)
            
        else:
            ret.description = "Correlation of %s with an array" % in1.name
            
        return ret

    else:
        return corr

@safeWrapper
@with_doc(state_levels, use_header=True)
def detect_boxcar(x:typing.Union[neo.AnalogSignal, DataSignal], 
                  minampli:typing.Optional[float] = 1., 
                  channel:typing.Optional[int] = None,
                  up_first:bool=True,
                  **kwargs) -> tuple:
    """Detection of boxcar or step (Heaviside) waveforms in a signal.
    
Parameters:
===========
x: signal-like object
    
minampli: float: a minimum value of boxcar amplitude (useful for noisy signals)
    default is 1 (see NOTE 1).
    
channel: required when the signal 'x' has more than one channel (or traces);
    selects a single trace (or channel) along the 2nd axis (axis 1)

    (remember, a signal is a 2D array and its traces are column vectors, 
    with axis 0 the 'domain' (time, etc) and channels - or traces - indexed
    on axis 1)

up_first: bool default is True
    When True, the upward transitions times are in the first element of the 
        returned tuple (see below), and the downward transition times are in
        the second element.

    When False, the order is reversed (down, then up).

    NOTE: This allows the caller to pre-empt which transition time stamps 
    are returned first, although it is easy to determine this post-hoc, by
    comparing the time stamps.
    
Var-keyword parameters:
=======================
• method: str; default is 'kmeans'; valid values are 'kmeans', 'state_levels',
    'states' ('states' is an alias/shorthand for 'state_levels')
    
When 'method' is 'states' or 'state_levels', the following keyword parameters
control the behaviour of the state_levels(…) function :
    
• box_size
• levels
• adcres, adcrange, adcscale
• moment
• bins, bw     
    
When 'method' is 'kmeans' the function passes he kmeans parameter 'k_or_guess' to
2 (i.e. classify 'x' data in levels). 

The following keyword parameters control the behaviour of kmeans(…):
    
• iter
• thresh → NOTE: do not confuse with 'minampli'
• check_finite
• seed
    
Returns:
========
A 6-tuple (t0, t1, amplitude, centroids, label, upward) , 

where:

• t0, t1 are the domain values² for the transitions between the low ('lo') and 
    high ('hi') states, as follows:
        
    variable:   Transition:     Condition:
    ------------------------------------------------
    t0          lo → hi         up_first == True
                hi → lo         up_first == False

    t1          hi → lo         up_first == True
                lo → hi         up_first == False
    ------------------------------------------------

• amplitude: the amplitude of the boxcar
• centroids: the mean value of each of the low and high states    
• label: numpy array (vector) of same size as the signal in 'x', with values of
    0 or 1, indicating which state the samples in 'x' belong to:
    
    Samples in 'label' with value 0 correspond to the samples in 'x' belonging
    to the 'low' state.
        
    Samples in 'label' with value 1 correspond to the samples in 'x' belonging
    to the 'high' state.
    
• upward: a bool indicating the direction of the boxcar (True ⇒ the boxcar is
an upward deflection)
    
What this function does:
========================
The function detects step transitions between two distinct states — "low" and 
"high" —  in a regularly sampled signal (a.k.a "analog" signal).
    
A transition may be unique (a.k.a a "step", or Heaviside function) or followed
by a transition in the opposite direction to the first (a.k.a "boxcar" function:
a boxcar is effectively a series of two step transitions in opposite directions).
    
Boxcar and/or step waveforms are typically used to represent TTL-like signals
(e.g., "digital trigger signals", with widths in the order of ms) but can also
be used with digital-to-analog (DAC) command signals (e.g., a "step" change in 
holding potential or injected current).

Optionally the transitions can be detected subject to a minimum amplitude¹.
    
The state transitions are detected using an algorithm selected from among:
    
• the kmeans algorithm (see documentation for scipy.cluster.vq.kmeans(…) 
    function).
    
• a histogram-based method (see documentation for state_levels(…) function in 
    this module).

By default, the 'method' parameter is set to 'kmeans'.
    
Optionally the float parameter 'minampli' specifies the minimum difference between
signal's clusters for it to be considered as containing an embedded TTL-like
waveforms. By default, this is 1.0

The function is useful in detecting the ACTUAL time of a trigger (be it 
"emulated" in the ADC command current/voltage or in the digital output "DIG") 
when this differs from what was intended in the protocol (e.g. in Clampex,
there is a padding before and after the actual signal, and the size of the 
padding is about 

Limitations and ways to work around them:
=========================================
The samples in 'x' must fall in one of two distinct levels for the detection to
work. This prerequisite has the following implications:

• multiple boxcars in the signal can be detected as long as they have the same
amplitude and direction (i.e., either upward or downward);

• the signal can have at most one step function in a given direction; if the
signal also contains one or more boxcars, then the step function occurs AFTER the 
boxcars and has the same direction and amplitude as the boxcars.
    
To work around these limitations one can pass a "slice" of the signal, containing
only the boxcar waveforms of interest, to this function.
    
Another possibility is to use "lower-level" code, e.g. by invoking 'kmeans' with
a higher number of putative levels (the 'k_or_guess' parameter) or 'state_levels'
with a tuple of fractional levels (the 'levels' parameter) and work out the
location, direction, and amplitude of transitions from the result.
    
To keep code simple, this function only deals with two well-separated state
levels in the signal.
    
Finally, for signals with several detected boxcars, one may use the results to
figure out the boxcar widths and filter the detected boxcars subject to width
constraints.
    
NOTES:
=====
¹ To avoid false detection in noisy signals.
    
² When the signals are in time domain, these are simply the times of the
    transitions

        
    """
    # FIXME 2023-06-18 22:09:23
    # Currently this function does almost the same thing as parse_step_waveform_signal.
    # TODO 2023-06-18 22:10:21 merge codes into one function !
    from scipy import (cluster, signal)
    from scipy.signal.windows import boxcar
    # try:
    #     from scipy.signal import boxcar
    # except:
    #     from scipy.signal.windows import boxcar
    # finally:
    #     raise

    if not isinstance(x, neo.AnalogSignal):
        raise TypeError("Expecting a neo.AnalogSignal object; got %s instead" % type(x).__name__)
    
    # WARNING: algorithm fails for noisy signals with no TTL waveform
    
    # NOTE: 2023-06-19 08:54:33
    # merging with parse_step_waveform_signal
    
    # NOTE: 2023-06-19 08:55:01
    # Test signal shape -> we need a single-trace signal; although we could 
    # possibly work on multi-trace (or multi-channel) signals, this would 
    # complicate things too much, so let;s make sure we only select one trace 
    # from a multi-trace signal
    if x.ndim == 2 and x.shape[1] > 1:
        if not isinstance(channel, int):
            raise ValueError(f"Expecting a signal with one channel, instead got {sig.shape[1]}, but 'channel' was not specified")
        
        sig = x[:,channel] # a single-trace view of x
        
    else:
        sig = x
            
    # NOTE: 2023-06-19 08:56:25
    # optionally smooth the data with a boxcar filter
    
    box_size = kwargs.pop("box_size", 0)
    
    if not isinstance(box_size, int):
        raise TypeError(f"boxcar filter size must be an int; instead, got {type(box_size).__name__}")
    
    if box_size < 0:
        raise ValueError(f"boxcar filter size must be >= 0")
    
    if box_size > 0:
        bckernel = boxcar(box_size)/ box_size # generate a boxcar kernel
        sig_filt = convolve(sig, bckernel)
        
    else:
        sig_filt = sig
        
    method = kwargs.pop("method", "kmeans") # better default
    
    if not isinstance(method, str):
        raise TypeError(f"'methd' expected to be a str; instead, got {type(method).__name__}")
    
        
    # NOTE: 2023-06-19 08:59:37
    # from here onwards we work on sig_filt!
    
    # NOTE: 2023-06-19 09:00:05
    # get the transition levels - first check what method we use
    
    if method.lower() not in ("kmeans", "state_levels", "states"):
        raise ValueError(f"'method' {method} is invalid; expecting one of 'state_levels' or 'kmeans'")
    
    try:
        if method.lower() in ("state_levels", "states"):
            # print("detect_boxcar using state_levels")
            # NOTE: 2023-07-02 15:57:07
            # remove the kwargs normally expected by kmeans(…)
            #
            kwargs.pop("iter", None)
            kwargs.pop("thresh", None)
            kwargs.pop("check_finite", None)
            kwargs.pop("seed", None)
            
            # NOTE: make sure we have got OUR defaults here
            levels = kwargs.pop("levels", 0.5)
            kwargs["levels"] = levels
            
            # NOTE: 2023-06-19 09:04:30
            # TODO code to get these values from the ABF file (via pyabfbridge?)
            # TODO and similarly, from CED (for CED, the code still needs to be written)
            # TODO write documentation hint on how these numbers can be obtained
            # outside this function (ie., before calling it); 
            adcres = kwargs.pop("adcres", 15)
            kwargs["adcres"] = adcres
            adcrange = kwargs.pop("adcrange", 10)
            kwargs["adcrange"] = adcrange
            adcscale = kwargs.pop("adcrange", 1e3)
            kwargs["adcscale"] = adcscale
        
            # NOTE: 2023-06-19 09:09:44
            # state_levels is a histogrm method to determine distinct 'levels' 
            # in the signal, see IEEE Std 181-2011: IEEE Standard for Transitions, 
            # Pulses, and Related Waveforms
            #
            # here we pass the default moment (the 'mean'), axis (0, i.e. the 
            # data axis), bins (100) and bw (bin width, None) ⇒ we don't need to 
            # find these in the kwargs
            # 
            # returns:
            # • centroids: a list of reference levels - same as cbook with the
            #   kmeans method below, but IS NOT an array, and the values may 
            #   differ slightly
            # • cnt: numpy array (int): histogram counts (i.e. the histogram
            #   "column" values) in increasing order of the bins
            # • edg: numpy array (float) of histogram edges
            # • rng: list of ranges (one per level) within the cnt array
            #   indicates the range of column indices that fall inside each level
            
            centroids, cnt, edg, rng = state_levels(sig_filt.magnitude,
                                                    **kwargs)
            
            if len(centroids) == 0:
                return (None, None, None) if return_levels else (None, None)
                
            cbook = np.array(centroids).T[:,np.newaxis]
            
        else:
            # NOTE 2023-07-02 16:01:04
            # remove keyword params normally expected by state_levels(…)
            kwargs.pop("bins", None)
            kwargs.pop("bw", None)
            kwargs.pop("levels", None)
            kwargs.pop("adcres", None)
            kwargs.pop("adcrange", None)
            kwargs.pop("adcscale", None)
            levels = kwargs.pop("levels", 2)
            # print("detect_boxcar using kmeans")
            cbook, dist = cluster.vq.kmeans(sig_filt, levels, **kwargs) # two levels
            cbook = np.array(cbook, dtype=float)
            
        # the boxcar amplitude
        # BUG: 2023-07-03 23:01:53 FIXME
        # this is WRONG for more than two levels!
        amplitude = np.diff(cbook, axis=0) * sig.units
        
        if isinstance(minampli, numbers.Number):
            if isinstance(sig, pq.Quantity):
                minampli = minampli * sig.units
                
        elif isinstance(minampli, pq.Quantity):
            if minampli.size != 1:
                raise ValueError("Threshold must be a scalar")
            
            if isinstance(sig, pq.Quantity):
                if not scq.unitsConvertible(sig, minampli):
                    raise ValueError("Threshold and signal have incompatible units")
                
                if minampli.units != sig.units:
                    minampli = minampli.rescale(sig.units)
                    
            else:
                minampli = minampli.magnitude.flatten()[0]
                
        # print(f"threshold = {minampli*sig.units}")
        
        if np.all(np.abs(amplitude) < minampli):
            return (None, None, None, None, None, None)
            
        code, cdist = cluster.vq.vq(sig, sorted(cbook)) # use un-filtered signal here
        
        # diffcode = np.diff(code)
        diffcode = np.ediff1d(code, to_begin=0)
        
        # indices of up transitions (lo → hi)
        ndx_lo_hi = np.where(diffcode ==  1)[0].flatten() # transitions from low to high
        
        # print(f"ndx_lo_hi = {ndx_lo_hi}, size = {ndx_lo_hi.size}")
        
        # indices of down transitions (hi → lo)
        ndx_hi_lo = np.where(diffcode == -1)[0].flatten() # hi -> lo transitions
        
        # print(f"ndx_hi_lo = {ndx_hi_lo}, size = {ndx_hi_lo.size}")
        
        if ndx_lo_hi.size:
            times_lo_hi = np.array([x.times[k] for k in ndx_lo_hi]) * x.times.units # up transitions
        else:
            times_lo_hi = None
            
        if ndx_hi_lo.size:
            times_hi_lo = np.array([x.times[k] for k in ndx_hi_lo]) * x.times.units # down transitions
        else:
            times_hi_lo = None
            
        
            
        if all(v is not None for v in (times_lo_hi, times_hi_lo)):
            if times_lo_hi.size == times_hi_lo.size: # signal has boxcars only
                if times_lo_hi.size == 1:
                    upward = times_lo_hi[0] <= times_hi_lo[0]# if up_first else times_lo_hi[0] > times_hi_lo[0]
                    
                else:
                    upward = times_lo_hi <= times_hi_lo #if up_first else times_lo_hi > times_hi_lo
                    
            else:
                minlen = min(v.size for v in (times_lo_hi, times_hi_lo))
                if minlen == 1:
                    upward = times_lo_hi[0] <= times_hi_lo[0] #if up_first else times_lo_hi[0] > times_hi_lo[0]
                else:
                    upward = times_lo_hi[0:minlen] <= times_hi_lo[0:minlen]# if up_first else times_lo_hi[0:minlen] <= times_hi_lo[0:minlen]
                    
                    lastup = times_lo_hi[-1] > times_hi_lo[-1] #if up_first else times_lo_hi[-1] > times_hi_lo[-1]
                    upward = np.append(upward, lastup)
                    
        else:
            upward = True if times_lo_hi is not None else False
                
    except Exception as e:
        traceback.print_exc()
        times_lo_hi = None
        times_hi_lo = None

        amplitude = None
        cbook = None
        code = None
        
        upward = None
        
    # when there are all boxcars, times_lo_hi and times_hi_lo have the same length
    # where there is just one steap (Heaviside) then one of times_lo_hi and times_hi_lo
    # is None
    # where there are only Heaviside steps there will be several levels in the 
    # waveform, (one step after another) - A CONDITION NOT DEALT WITH HERE
    #
    # when there can be at most one step of the same direction
    
        
    if up_first:
        return times_lo_hi, times_hi_lo, amplitude, cbook, code, upward
    
    # emulates parse_step_waveform_signal
    return times_hi_lo, times_lo_hi, amplitude, cbook, code, upward

