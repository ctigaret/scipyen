"""Synthetic imaging data (image simulations)
"""
#### BEGIN core python modules
import collections 
import inspect
import traceback
import warnings
import bisect
import numbers
import math
from enum import Enum, IntEnum
#### BEGIN core python modules

#### BEGIN 3rd party modules
import numpy as np
import numpy.matlib as mlib
import pandas as pd
import quantities as pq
from scipy import optimize, signal, integrate
import vigra
import neo
#### END 3rd party modules

#### BEGIN pict.core modules
from core import (datatypes as dt, signalprocessing as sgp, curvefitting as crvf,
                  models, strutils, )

# NOTE: 2020-10-08 09:45:31
# inside core.utilities, safeWrapper below is imported from core.prog
from core.utilities import (safeWrapper, counter_suffix, unique, )
from core.quantities import (units_convertible, check_time_units)

#from .patchneo import neo
from neo.core import baseneo
from neo.core import basesignal
from neo.core import container

from ephys import ephys

from . import vigrautils as vu
from . import imageprocessing as imgp
from imaging.vigrautils import concatenateImages
#### END pict.core modules




def synthetic_transients(duration, sampling_frequency, *args, **kwargs):
    """Generates an idealized time-varying signal described by exponential rise & decay functions.
    
    
    Parameters:
    ===========
    duration            : float scalar, interpreted as having dimensionality of t or samples
    sampling_frequency  : float scalar, interpreted as having dimensionality of 1/t or 1/samples; must be > 0
    
    Variadic parameters:
    ====================
    
    *args               : list of parameters for the models.compound_exp_rise_multi_decay() function
                        used to generate an EPSP waveform
                        
    **kwargs            : var-keyword parameters (see waveform_signal for details)
    special keyword parameters:
        asSignal        : boolean, False by default
        
        NOTE: when True, this will ALWAYS generate a neo.AnalogSignal, as "domain_units"
        will be pre-set to pq.s
    
    
    
    The function uses models.compound_exp_rise_multi_decay to generate the waveform.
    
    Depending on the model parameters in *args, this can be used to generate
    any combination of exponential rise + decay time-varying waveforms that make physiological
    sense, e.g.:
    
    an excitatory/inhibitory postsynaptic current or potential, an action potential
    including afterhyperpolarization potential(s), afterhyperpolarization current,
    etc.
    
    The model parameters are expected to be passed as a sequence of sequences, 
    with each inner sequence containing model parameters for an individual waveform.
    
    EXAMPLE 1: generate a combination of an EPSP and a backpropagated AP
    (separated by 10 ms) followed by an AHP:
    
    parameters = [[0.1, 0.03, 0, 0.005, 0.25],[1, 0.005, 0, 0.0005, 0.26], [-0.1, 0.07, 0, 0.01, 0.27]]
    
    NOTE  there are three inner sequences: the first simulates an EPSP; the second
    simulates an AP, and the third simulated an AHP
    
    epsp_bap = simulations.synthetic_transients(1, 1000, parameters, asSignal=True, units=pq.mV, sampling_rate=1000 * pq.Hz, name="EPSP+bAP")
    
    EXAMPLE 2: generate a train of five EPSPs with identical rise & decay times,
    delivered at 100 Hz
    
    parameters = [[0.1, 0.05, 0, 0.005, 0.25 + k*0.01] for k in range(5)]
    
    epsp_train = simulations.synthetic_transients(1, 1000, parameters, asSignal=True, units=pq.mV, sampling_rate=1000 * pq.Hz, name="EPSP train")

    See also models.compound_exp_rise_multi_decay for details 
    
    EXAMPLE 3: generate a train of epsp+ap at 100 Hz, delivered at 5 Hz (200 ms intervals):
    
    parameters0 = [[0.1, 0.05, 0, 0.005, 0.05], [1, 0.005, 0, 0.0005, 0.06]] # initial epsp+bap
    
    parameters = list()
    
    for k in range(5):
        p0 = parameters0[0].copy()
        p1 = parameters0[1].copy()
        p0[-1] += k * 0.2
        p1[-1] += k * 0.2
        parameters.append(p0)
        parameters.append(p1)
        
    parameters
    
        [[0.1, 0.05, 0, 0.005, 0.1],
         [1, 0.005, 0, 0.0005, 0.11],
         [0.1, 0.05, 0, 0.005, 0.30000000000000004],
         [1, 0.005, 0, 0.0005, 0.31],
         [0.1, 0.05, 0, 0.005, 0.5],
         [1, 0.005, 0, 0.0005, 0.51],
         [0.1, 0.05, 0, 0.005, 0.7000000000000001],
         [1, 0.005, 0, 0.0005, 0.7100000000000001],
         [0.1, 0.05, 0, 0.005, 0.9],
         [1, 0.005, 0, 0.0005, 0.91]]
         
    ltp_train = simulations.synthetic_transients(1, 1000, parameters, asSignal=True, units=pq.mV, sampling_rate=1000 * pq.Hz, name="LTP train")
     
    """
    def __f__(x, *args, **kwargs):
        y = models.compound_exp_rise_multi_decay(x, *args, **kwargs)
        return y[0]
    
    asSignal = kwargs.get("asSignal", False)
    
    
    if asSignal:
        if "domain_units" not in kwargs.keys():
            kwargs["domain_units"] = pq.s
            
    if isinstance(duration, pq.Quantity):
        if len(duration.magnitude.flatten()) != 1:
            raise TypeError("duration expected to be a scalar; got %s instead" % duration)
        
        if not check_time_units(duration):
            raise TypeError("When a quantity, duration muste have time units; got %s instead" % duration.units)
        
        kwargs["domain_units"] = duration.units
        
        if isinstance(sampling_frequency, pq.Quantity):
            if len(sampling_frequency.magnitude.flatten()) != 1:
                raise TypeError(("sampling_frequency expected to be a scalar;  got %s instead" % sampling_frequency))
            
            if not units_convertible(duration, 1/sampling_frequency):
                raise TypeError("duration (%s) and sampling_frequency (%s) have incompatible units" % (duration.units, sampling_frequency.units))
            
            sampling_frequency = sampling_frequency.rescale(1/duration.units).magnitude
            
        elif not isinstance(sampling_frequency, (float, int)):
            raise TypeError("samplign_frequency expected to be a float, int, or a scalar Python Quantity; got %s instead" % type(sampling_frequency).__name__)
        
        duration = duration.magnitude
        
    elif isinstance(duration, (float, int)):
        if isinstance(sampling_frequency, pq.Quantity):
            if len(sampling_frequency.magnitude.flatten()) != 1:
                raise TypeError(("sampling_frequency expected to be a scalar; got %s instead" % sampling_frequency))
            
            kwargs["domain_units"] = 1/sampling_frequency.units
            
            sampling_frequency = sampling_frequency.magnitude
        
    else:
        raise TypeError("duration expected to be a float, int, or a scalar Python Quantity; got %s instead" % type(duration).__name__)
        
    return waveform_signal(duration, sampling_frequency, __f__, *args, **kwargs)
    
    
def synthetic_spine(field_width, spatial_resolution, *args, **kwargs):
    def __f__(x, *argw, **kwargs):
        return models.gaussianSum1D(x, *args, **kwargs)
    
    asSignal = kwargs.get("asSignal", False)
    
    if asSignal:
        if "domain_units"not in kwargs.keys():
            kwargs["domain_units"] = pq.um
            
    if isinstance(field_width, pq.Quantity):
        if len(field_width.magnitude.flatten()) != 1:
            raise TypeError("field_width expected to be a scalar")
            
        kwargs["domain_units"] = field_width.units
        
        if isinstance(spatial_resolution, pq.Quantity):
            if len(spatial_resolution.magnitude.flatten()) != 1:
                raise TypeError("spatial_resolution expected to be a scalar")
            
            if not units_convertible(width, spatial_resolution):
                raise TypeError("field_width and spatial_resolution have incompatible units")
            
            # rescale resolution units to width units
            spatial_resolution = spatial_resolution.rescale(width.units).magnitude
                
        elif not isinstance(spatial_resolution, (float, int)):
            raise TypeError("spatial_resolution expected to be a float, int, or a Python Quantity; got %s instead" % type(spatial_resolution).__name__)
    
        field_width = field_width.magnitude
        
    elif isinstance(field_width, (float, int)):
        if isinstance(spatial_resolution, pq.Quantity):
            if len(spatial_resolution.magnitude.flatten()) != 1:
                raise TypeError("spatial_resolution expected to be a scalar")
            
            kwargs["domain_units"] = spatial_resolution.units
            
            spatial_resolution = spatial_resolution.magnitude
            
    else:
        raise TypeError("field_width expected to be a float, int, or a scalar Python Quantity; got %s instead" % type(field_width).__name__)
            
        
    return waveform_signal(field_width, 1/spatial_resolution, __f__, *args, **kwargs)


def synthetic_EPSCaT_linescan(field_width, duration, 
                              spatial_resolution,  sampling_frequency, 
                              spine_parameters, epscat_parameters, 
                              space_units = None, time_units = None, data_units = pq.dimensionless,
                              twoChannels=False,
                              addChannelAxis=True,
                              returnCalibration=False):
    """Generates a synthetic 2D EPSCaT as a vigra.VigraArray
    
    Parameters:
    ===========
    
    field_width : spatial extent where the synthetic spines are to be generated:
                float value, or a scalar Python Quantity where units SHOULD be "um"
    
    duration    : temporal extent of the entire EPSCaT signal containing synthetic EPSCaT waveforms
                float value, or a scalar Python Quantity where units SHOULD be "s"
                
    spatial_resolution : size of a "pixel" (sample) in the spatial domain 
                either float or a scalar Python Quantity with units convertible to 
                those of field_width
                
    sampling_frequency : sampling frequency of the time domain
                either flooat or a scalar Python Quantity with units convertible to
                the inverse of duration's units
                
    spine_parameters: a sequence of parameters for the models.gaussianSum1D function
    
                see models.gaussianSum1D() docstring for details
    
    epscat_parameters: a sequence of parameters for the models.compound_exp_rise_multi_decay function
    
                see models.compound_exp_rise_multi_decay() docstring for details
                
    Named parameters (keywords):
    Default values indicated (in parenthesis are default values if field_width and duration are floats)
    ============================
    
    space_units = None (pq.um)
    time_units  = None (pq.s)
    data_units  = pq.dimensionless
    
    addChannelAxis: boolean (default True) adds a singleton channel axis as the last axis
    
    returnCalibration: boolean, default False:
                When True, also returns the datatypes.AxesCalibration object for the axistags
                if the result
                
    twoChannels : boolean (default is False)
        When True, the result will be two-channel image with the "spine" on channel 0 and the 
        epscat on channel 1 (a channel axis will be automatically inserted in the image
        regardless of the value of addChannelAxis parameter)
        
        When False, the result will be a single-channel images containing the synthetic
        EPSCaT linescan
    
    Returns:
    ========
    When returnCalibration is False (default):
        a vigra.VigraArray containing the outer product of the synthetic spine(s) 
            (on the horizontal space axis) with the synthetic epscat (on the vertical temporal axis)
            
    When returnCalibration is True, returns a tuple:
    
        (image, axiscalibration) where image is as above, and axiscalibration is a
        datatypes.AxesCalibration object for the image axes (axistags property). 
        
        NOTE that in any case the image axistags will contain a calibration data in 
        their decsription properties
    
    
    
    """
    
    if space_units is None:
        if isinstance(field_width, pq.Quantity):
            space_units = field_width.units
            
            field_width = field_width.magnitude
            
        else:
            space_units = pq.um
            
    if time_units is None:
        if isinstance(duration, pq.Quantity):
            time_units = duration.units
            
            duration = duration.magnitude
            
        else:
            time_units = pq.s
    
    # NOTE: 2018-09-14 14:13:56
    # below, we get each signal as a tuple (y,x) of numpy arrays (vector columns)
    # NOTE the order
    epscat = synthetic_transients(duration, sampling_frequency, epscat_parameters)[1] 
    
    spine  = synthetic_spine(field_width, spatial_resolution, *spine_parameters)[1]
    
    axistags = vigra.AxisTags(vigra.AxisInfo("x", vigra.AxisType.Space, resolution=spatial_resolution), 
                              vigra.AxisInfo("t", vigra.AxisType.Time, resolution=1/sampling_frequency))
    
    linescan = vigra.VigraArray(np.outer(spine, epscat), axistags = axistags)
    
    if twoChannels:
        spine2D = vigra.VigraArray(np.outer(spine, np.ones_like(epscat)), axistags = axistags)
        
        result = concatenateImages(spine2D, linescan, axis = "c") 
        
    else:
        result = linescan
    
    if addChannelAxis and result.channelIndex == linescan.ndim:
        linescan = linescan.insertChannelAxis()
    
    axiscal = dt.AxesCalibration(result)
    axiscal.setUnits(space_units, "x")
    axiscal.setResolution(spatial_resolution, "x")
    axiscal.setUnits(time_units, "t")
    axiscal.setResolution(1/sampling_frequency, "t")
    
    if result.channelIndex < result.ndim:
        # by default there is only one channel
        axiscal.setUnits(data_units, "c", 0)
        axiscal.setOrigin(np.min(result), "c", 0)
        axiscal.setResolution(np.finfo(float).eps, "c", 0)
    
    axiscal.calibrateAxes()
    
    if returnCalibration:
        return result, axiscal
    
    else:
        return result
        



