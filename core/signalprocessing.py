# -*- coding: utf-8 -*-
"""Functions for processing generic 1D signals (numpy array).
For signal processing on elecctorphysiology signal types (e.g. neo.AnalogSignals or datatypes.DataSignal)
please use the "ephys" module.
"""
import typing, numbers, functools
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

def scale_waveform(x:np.ndarray, num, den):
    """Scales waveform by num/den in place.
    Returns a reference to x.
    
    """
    nanx = np.isnan(x)
    if isinstance(x, pq.Quantity):
        units = x.units
        xx = x.magnitude # → this is a REFERENCE ; its changes will be reflected in x !!!
        
        if isinstance(num, pq.Quantity):
            if not scq.units_convertible(num, x):
                raise TypeError("numerator has wrong units")
            if num.units != x.units:
                num = num.rescale(x.units)
                
            num = num.magnitude
        
        if isinstance(den, pq.Quantity):
            if not scq.units_convertible(den, x):
                raise TypeError("denominator has wrong units")
            if den.units != x.units:
                den = den.rescale(x.units)
                
            den = den.magnitude
            
    else:
        if any(isinstance(v, pq.Quantity) for v in (num, den)):
            raise TypeError("num and den canot be quantities if x is not a quantity")
        xx = x
        units = None
        
    if np.any(nanx):
        scaled = xx[~nanx] * num/den
        xx[~nanx] = scaled
        
    else:
        xx *= num/den
    
    return xx if units is None else xx * units

def normalise_waveform(x:np.ndarray):
    """Waveform normalization.
    
    Keeps the waveform's orientation and polarity.
    
    Returns:
    
    • (x-x_min)/(x_max - x_min) 
        
        for a positive waveform (i.e. "upward" deflection)
    
    • (x_max - x)/(x_min - x_max) 
        for a negative waveform (i.e., "downward" deflection)
    
    The point is that waveform "min" is not its numerical minimum, but the sample 
    value closest to zero; likewise, the "max" is the sample value farthest away
    from zero.
    
    Obviously, this approach will break down if a downward deflection waveform is
    MOSTLY above zero! Such contrived example is that of a mini EPSC where the 
    "drift" in the patch or the junction potential have caused the DC current to
    drift far above zero.
    
    In this case, shoud you decide to analyze such recording, you'd better
    remove the DC drift manually before proceeding...
    
    Parameters:
    ===========
    x: 1D numpy array (i.e., a vector);
    
    Returns:
    =======
    
    Numpy array (vector) with values of `x` normalized between max and min
    
    NOTE: when x is a Python Quantity, normalization will make it dimensionless
    
    FIXME: 2022-12-13 16:57:47 This is NOT nan-friendly!
    
    """
    
    if is_positive_waveform(x):
        return (x-np.min(x))/(np.max(x)-np.min(x))

    return (np.max(x)-x)/(np.min(x)-np.max(x))

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
    #TODO
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
            
            The fractional reference levels; allowed values: [0..1]
            
            (see "f" argument to split_histogram() function in this module); 
            
            default is 0.5
            
    moment: str
            The statistical moment used to calculate the state level:
            "mean" or "mode" or a function that takes a 1D sequence of numbers
            and returns a scalar; 
            
            default is "mean"
    
    axis:   int or None 
            The axis of the array (when x.ndim > 1); default is None
            
    Returns:
    ========
    A list of reference levels, corresponding to the fractional reference 
    levels specified in "levels" argument.

    """
    from scipy import where
    
    if not isinstance(x, np.ndarray):
        raise TypeError(f"Numpy array expected; instead, got a {type(x).__name__}")
    
    if x.ndim > 1:
        if x.shape[1] > 1:
            raise ValueError(f"1D data expected; got data with shape {x.shape}")
        
        else:
            x = np.squeeze(x)
    
    bins     = kwargs.get("bins", None)
    bw       = kwargs.get("bw", None)
    adcres   = kwargs.get("adcres", None)
    adcrange = kwargs.get("adcrange", None)
    adcscale = kwargs.get("adcscale", None)
    levels   = kwargs.get("levels", 0.5)
    moment   = kwargs.get("moment", "mean")
    axis     = kwargs.pop("axis", None)
    
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
        
        
    def __guess_dc_(x_):
        levels, counts, edges, ranges = state_levels(x_)
        
        levelSizes = [np.sum(counts[level_range]) for level_range in ranges]
    
        ndx = np.argmax(levelSizes)
        val = levels[ndx]
            
        return val
        
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
                    if not scq.units_convertible(value, x):
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
                        if not scq.units_convertible(value, x):
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
                    val = __guess_dc_(xx[:,k])
                    
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
        

    if isinstance(x, (neo.AnalogSignal, sds.DataSignal)):
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
    from core import datatypes as dt
    if not isinstance(x, np.ndarray):
        raise TypeError(f"Expecting a numpy array; got {type(x).__name__} instead")
    if not dt.is_vector(x):
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

def detrend(x:typing.Union[neo.AnalogSignal, sds.DataSignal], **kwargs):
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
            if bp.size == 1 and units_convertible(bp, x):
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
    if isinstance(sig, (neo.AnalogSignal, sds.DataSignal)):
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
    
    


    
