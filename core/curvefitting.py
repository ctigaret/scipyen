# -*- coding: utf-8 -*-
"""
Wrappers around scipy.optimize

FIXME/TODO: 2022-10-25 23:57:08
Harmonize the API (this is the role of the upcoming modelfitting.py module)
"""

#### BEGIN core python modules
import os, sys, traceback, warnings, numbers, collections
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import quantities as pq
import pandas as pd
from scipy import cluster, optimize, signal, integrate #, where
import vigra
import neo
#### END 3rd party modules

#### BEGIN pict.core modules
#import imageviewer as iv
#import signalviewer as sv
from . import tiwt
from . import models
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
#from . import datatypes as dt
#from .patchneo import *
#### END pict.core modules

def fitGauss1DSum(x, y, locations, **kwargs):
    """Fits a sum of shifted 1D Gaussians.
    
    CAUTION  (TODO/FIXME): Unstable when parameters are given in floating point 
    calibrated axis units. Use with parameters given in data samples.
   
    """
    from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
    #from . import datatypes as dt
    
    if not isinstance(locations, (tuple, list, np.ndarray, numbers.Real)):
        raise TypeError("Locations expected to be a sequence of floats or a scalar")
    
    if isinstance(locations, numbers.Real):
        locations = [locations]
        
    if isinstance(x, (neo.AnalogSignal, DataSignal, pq.Quantity)):
        xx = x.magnitude.squeeze()
        
    elif isinstance(x, np.ndarray):
        xx = x.squeeze()
        
    else:
        raise TypeError("x expected to be a np.ndarray, a neo.AnalogSignal or a datatypes.DataSignal; got %s instead" % type(x).__name__)
        
    if xx.ndim > 1:
        raise TypeError("x must be a vector")
    
    #print("xx.shape: ", xx.shape)
    
    if isinstance(y, (neo.AnalogSignal, DataSignal, pq.Quantity)):
        yy = y.magnitude.squeeze()
        
    elif isinstance(y, np.ndarray):
        yy = y.squeeze()
        
    else:
        raise TypeError("y expected to be a np.ndarray, a neo.AnalogSignal or a datatypes.DataSignal; got %s instead" % type(y).__name__)
        
    if yy.ndim > 1:
        raise TypeError("y must be a vector")
    
    #print("yy.shape: ", yy.shape)
        
    if xx.size != yy.size:
        raise TypeError("Both x and y must have the same size")
    
    width = [(np.max(x) - np.min(x))/len(locations)] * len(locations)
    
    scale = [1] * len(locations)
    
    offset = 0
    
    bounds = (0, np.inf)
    
    if len(kwargs):
        if "width" in kwargs:
            width = kwargs["width"]
            
        if "offset" in kwargs:
            offset = kwargs["offset"]
            
        if "scale" in kwargs:
            scale = kwargs["scale"]
            
        if "bounds" in kwargs:
            bounds = kwargs["bounds"]
    
    
    if isinstance(width, (tuple, list)):
        if len(width) != len(locations):
            raise TypeError("When a list, 'width' must have same size as 'locations' (%d); instead it has %d" % (len(locations, len(width))))
        
        if not all([isinstance(w, numbers.Real) for w in width]):
            raise TypeError("All elements of 'width' must be scalars")
    
    elif isinstance(width, numbers.Real):
        width = [width] * len(locations)
        
    else:
        raise TypeError("'width' expected to be a sequence or a scalar; got %s instead" % type(width).__name__)
        
    if isinstance(scale, (tuple, list)):
        if len(scale) != len(locations):
            raise TypeError("When a list, 'scale' must have same size as 'locations' (%d); instead it has %d" % (len(locations, len(scale))))
        
        if not all([isinstance(s, numbers.Real) for s in scale]):
            raise TypeError("All elements of 'scale' must be scalars")
    
    elif isinstance(scale, numbers.Real):
        scale = [scale] * len(locations)
        
    else:
        raise TypeError("'scale' expected to be a sequence or a scalar; got %s instead" % type(scale).__name__)
        
    params = list()
    
    for k, l in enumerate(locations):
        params += [scale[k], l, width[k]]
        
    params.append(offset)
    
    #def __model_func__(x_, y_, *params):
        #return models.gaussianSum1D(x_, y_, *params)
    
    #popt, pcov = optimize.curve_fit(__model_func__, xx, yy, params)
    popt, pcov = optimize.curve_fit(models.gaussianSum1D, xx, yy, params, bounds = (0, np.inf))
    
    #yfit = model_func(np.linspace(np.min(xx), np.max(xx), xx.shape[0], endpoint=False), *popt)
    #yfit = __model_func__(xx, *popt)
    yfit = models.gaussianSum1D(xx, *popt)
    
    return popt, pcov, yfit
    
def fit_compound_exp_rise_multi_decay(data, p0, bounds=(-np.inf, np.inf), method="trf", loss="linear"):
    """Fits CaT model to CaT data.
    
    Parameters:
    ==========
    
    data = neo.AnalogSignal with appropriate time units
    
    p0 = initial parameters; 
        (1) a sequence (iterable) of floats, see the "parameters" argument in the
            docstring of models.exp_rise_multi_decay() function
                
            Essentially these are:
            
            [a_0, d_0, a_1, d_1, ... a_n-1, d_n-1, o, r, x0] 
            for one transient with n decay components and one rise component
            
            The length of this sequence must ne N x 2 + 3 where Nn is the number
            of decay time constants in the transient.
                
        (2) a sequence (iterable) of sequences (iterables) of numbers, see 
            "parameters" argument in the  docstring of 
            models.compound_exp_rise_multi_decay() function
                
            Essentially these are:
            
        [[a_0_0, d_0_0, a_1_0, d_1_0, ... a_n0-1_0, d_n0-1_0, o_0, r_0, x0_0],
        [a_0_1, d_0_1, a_1_1, d_1_1, ... a_n1-1_1, d_n1-1_1, o_1, r_1, x0_1], 
        .
        .
        .
        [a_0_m-1, d_0_m-1, a_1_m-1, d_1_m-1, ... a_nm-1_m-1, d_nm-1_m-1, 0_m-1, r_m-1, x0_m-1]
        ]

        For m transients, each with their own (possibly different) numbers of decays.

        The length of each individual sequence above must satisfy N_m x 2 + 3 where N_m 
        is the number of decay time constants of the mth transient.
                        
            In either case:
            a   = scale
            d   = tau decay
            o   = offset
            r   = tau rise
            x0  = delay (onset)

        NOTE: models.compound_exp_rise_multi_decay calls models.exp_rise_multi_decay
                    behind the scenes

    bounds: 2-tuple of data, each of the same layout as p0, or  2 -tuple of 
        floats (they will be broadcasted along p0 elements)
    
    Returns:
    =======
    fittedCurve: the fitted curve of the EPSCaT (compound or not)
    
    fittedComponentCurves: a list of fitted curves, one for each EPSCaT component:
        for single-component EPSCaTs, there is only one element in this list and 
        if identical to the fittedCurve
        
        
    result: a dict that contains the following:

    result["Fit"]: the result of the fitting routine
    result["Coefficients"]: fitted coefficients (same organization as p0)
    result["Rsq"]: the R2 of the entire EPSCaT fit
    
    """
    #from . import datatypes as dt
    from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
    
    if not isinstance(data, (neo.AnalogSignal, DataSignal)):
        raise TypeError("Data to be fitted must be a neo.AnalogSignal, or a datatypes.DataSignal; got %s instead" % type(data).__name__)
    
    if data.ndim == 2 and data.shape[1] > 1:
        raise ValueError("Data must contain a single channel")
    
    if not isinstance(p0, (tuple, list)):
        raise TypeError("Initial parameters expected to be a list; got %s instead" % type(p0).__name__)
    
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
        raise TypeError("bounds expected a 2-tuple or a 2-element list")
    
    # find out where NaNs are in data
    
    realDataNdx = ~np.isnan(data)
    
    ydata = data.magnitude[realDataNdx] # from now on we're dealing with a plain numeric numpy array
    
    realDataNdx = np.squeeze(realDataNdx)

    if isinstance(data, neo.AnalogSignal):
        domaindata = data.times.magnitude
        
    else:
        domaindata = data.domain.magnitude
    
    xdata  = domaindata[realDataNdx]
    
    # to correct for the onset parameters!
    if all(realDataNdx):
        deltaOnset = 0
        
    else:
        deltaOnset = xdata[0]
    
    # reset xdata to start at 0
    xdata -= deltaOnset
    
    componentDecays = dict() # holds the number of decay components in for each epscat in the compound
                             # set up as a dict so that it can be passed as **kwargs
                             # to the __cost_fun__

    # work on a local copy of p0; linearize initial parameters; deal bounds
    x0 = list()
    lo = list()
    up = list()
    
    l0 = bounds[0]
    u0 = bounds[1]
    
    if all([isinstance(p_, (tuple, list)) for p_ in p0]):
        p_init = list()
        
        for k, p_ in enumerate(p0):
            componentDecays[k] = models.check_rise_decay_params(p_)
            
            pl = list()
            pl[:] = p_[:]
            p_init.append(pl)
            
            p_init[k][-1] -= deltaOnset # correct for shift due to NaNs
            
            for i in p_init[k]:
                x0.append(i)
                
        if isinstance(l0, numbers.Real):
            lo[:] = [l0] * len(x0) # easy because p0 has already been linearized in x0
            
        elif isinstance(l0, (tuple, list)):
            if all([isinstance(l, numbers.Real) for l in l0]):
                # lower bounds l0 are a sequence of floats
                if all([len(l0) == len(p) for p in p0]): 
                    # this will only happen when all EPSCaT components have same number of decays
                    ll = [l0] * len(p0)
                    for k in ll:
                        for kl in k:
                            lo.append(kl)
                            
                else:
                    raise TypeError("Lower bounds (bounds[0]) sequence layout incompatible with intial parameter values layout")
                
            elif all([isinstance(l, (tuple, list)) for l in l0]):
                # lower bounds l0 are a sequence of sequences
                #print("l0 %s" % l0)
                for k, l in enumerate(l0):
                    if len(l) != len(p0[k]):
                        raise TypeError("Incompatible length of lower bounds (bounds[0]) sequence for component %d" % k)
                    
                    if all([isinstance(l_, numbers.Real) for l_ in l]):
                        lo += l
                        
                    else:
                        raise TypeError("Expecting a subsequence of real scalars in lower bounds (bounds[0])")
                    
            else:
                raise TypeError("Lower bounds (bounds[0]) expected a real scalar, a sequence of real scalars, or a sequence of sequences of real scalars")
            
        else:
            raise TypeError("Lower bounds (bounds[0]) expected a real scalar, a sequence of real scalars, or a sequence of sequences of real scalars")
        
        
        if isinstance(u0, numbers.Real):
            up[:] = [u0] * len(x0) # easy because p0 has already been linearized in x0
            
        elif isinstance(u0, (tuple, list)):
            if all([isinstance(l, numbers.Real) for l in u0]):
                # l0 is a sequence of floats
                if all([len(u0) == len(p) for p in p0]): 
                    # this will only happen when all EPSCaT components have same number of decays
                    ll = [u0] * len(p0)
                    for k in ll:
                        for kl in k:
                            up.append(kl)
                            
                else:
                    raise TypeError("Upper bounds (bounds[1]) sequence layout incompatible with intial parameter values layout")
                
            elif all([isinstance(l, (tuple, list)) for l in u0]):
                for k, l in enumerate(u0):
                    if len(l) != len(p0[k]):
                        raise TypeError("Incompatible length of upper bounds (bounds[1]) sequence for component %d" % k)
                    
                    if all([isinstance(l_, numbers.Real) for l_ in l]):
                        up += l
                        
                    else:
                        raise TypeError("Expecting a subsequence of real scalars in upper bounds (bounds[1])")
                    
            else:
                raise TypeError("Upper bounds (bounds[1]) expected a real scalar, a sequence of real scalars, or a sequence of sequences of real scalars")
            
        else:
            raise TypeError("Upper bounds (bounds[1]) expected a real scalar, a sequence of real scalars, or a sequence of sequences of real scalars")
        
    elif all([isinstance(p_, numbers.Real) for p_ in p0]):
        componentDecays[0] = models.check_rise_decay_params(p_init)
        
        p_init = list()
        p_init[:] = p0[:]
        
        p_init[-1] -= deltaOnset # correct for NaNs
        
        for i in p_init:
            x0.append(i)
            
        if isinstance(l0, numbers.Real):
            lo[:] = [l0] * len(p0)
            
        elif isinstance(l0, (tuple, list)):
            if all([isinstance(l, numbers.Real) for l in l0]) and len(l0) == len(p0):
                    lo[:] = l0[:]
                    
            else:
                raise TypeError("Mismatch between the number of lower bounds and that of initial values")
            
        else:
            raise TypeError("When intial values are a sequence of real scalars, lower bounds are expected to be a real scalar of a sequence of real scalars of the same length")
            
            
        if isinstance(u0, numbers.Real):
            up[:] = [u0] * len(p0)
            
        elif isinstance(u0, (tuple, list)):
            if all([isinstance(u, numbers.Real) for u in u0]) and len(u0) == len(p0):
                up[:] = u0[:]
        
            else:
                raise TypeError("Mismatch between the number of upper bounds and that of initial values")
            
    else:
        raise TypeError("Incompatible parameter list; expected to be a sequence of real scalars or a sequence of sequences of real scalars")
        
    bnds = (lo, up)
    
    def __cost_fun__(x, t, y, *args, **kwargs): # returns residuals!
        decaysDict = kwargs["decays"]
        if len(decaysDict) > 1:
            x_ = list()
            start = 0
            for k in decaysDict.keys():
                npars = decaysDict[k] * 2 + 3
                stop  = start + npars
                x_.append([x[start:stop]])
                start += npars
                
        else:
            x_ = [x]
            
            
        (yf, yc) = models.compound_exp_rise_multi_decay(t, x_)
        
        ret = y-yf
        
        return ret
        
    
    # parse parameters -- they can be a list of lists
    # also correct for onset shift in case of NaNs at the beginning
        
    #print("x0: %s" % x0)
    # NOTE: 2017-07-03 15:42:26
    # res is a scipy.optimize.OptimizeResult
    res = optimize.least_squares(__cost_fun__, x0, args=(xdata, ydata), 
                                method=method, loss=loss, bounds = bnds, 
                                kwargs={"decays":componentDecays})
    
    if len(componentDecays) > 1:
        res_x = list()
        start = 0
        for k in componentDecays.keys():
            npars = componentDecays[k] * 2 + 3
            stop = start + npars
            res_x.append(list(res.x[start:stop].flatten()))
            start += npars
            
    else:
        res_x = [list(res.x.flatten())]
            
    # NOTE: 2018-02-01 09:25:57
    # fC  = the fitted curve for the compound EPSCaT
    # fCC = _LIST_ of fitted curves for individual EPSCaT components
    # each of these curves is a 1D numpy array (column vector)
    (fC, fCC) = models.compound_exp_rise_multi_decay(xdata, res_x)
    
    
    # NOTE: 2018-09-17 10:28:43
    # Here, the R² is computed for the entire fit; 
    # The R² for individual components is computed further below, see NOTE: 2018-09-17 10:29:54
    rsq = list()
    
    sst = np.sum( (ydata - ydata.mean()) ** 2.)
    
    sse = np.sum((fC - ydata) ** 2.)
    
    rsq.append( 1 - sse/sst)
    
    result = collections.OrderedDict()
    result["Fit"] = res
    result["Coefficients"] = res_x
    result["Rsq"] = rsq
    
    initialSupport = np.full((data.shape[0],), np.NaN)
    
    fittedCurve = initialSupport.copy()
    
    fittedCurve[realDataNdx] = fC
    
    fittedComponentCurves = list()
    
    for k in range(len(fCC)):
        fittedComponent = initialSupport.copy()
        fittedComponent[realDataNdx] = fCC[k]
        fittedComponentCurves.append(fittedComponent)
        
        # NOTE: 2018-09-17 10:29:54
        # calculate r-squared for individual EPSCaT components
        # we do this on individual windows defined as (x0_n-1, x0_n)
        # for EPSCaT component n-1
        
        #print("fCC %d shape" %k, fCC[k].shape)
        
        test_start = res_x[k][-1]
        
        if k == len(fCC)-1:
            test_stop = int(ydata.shape[0]-1)
            #test_stop = int(data.magnitude.shape[0]-1)
            
        else:
            test_stop  = int(res_x[k+1][-1])
            
        test_window = (xdata >= test_start) & (xdata <= test_stop)
        #test_window = (domaindata >= test_start) & (domaindata <= test_stop)
            
        sst = np.sum((ydata[test_window] - ydata[test_window].mean()) ** 2.)
        #sst = np.sum((data.magnitude[test_window] - data.magnitude[test_window].mean()) ** 2.)

        sse = np.sum((fCC[k][test_window] - ydata[test_window]) ** 2.)
        #sse = np.sum((fittedComponent[test_window] - data.magnitude[test_window]) ** 2.)
        
        rsq.append(1-sse/sst)
    
    # NOTE: 2017-07-03 17:04:22
    # NOW you can restore shift
    if len(componentDecays) > 1:
        for k in range(len(result["Coefficients"])):
            result["Coefficients"][k][-1] += deltaOnset
            
    else:
        #res.x[-1] += deltaOnset
        result["Coefficients"][0][-1] += deltaOnset
    
    return fittedCurve, fittedComponentCurves, result

def fit_Event_model(data, p0, **kwargs):
    """Fits a Clements & Bekkers '97 waveform through the data.
    
    Parameters:
    ==========
    data: 1D array-like; the data to be fitted
    
    p0: 1D array-like (or sequence) with the initial values for the waveform 
        model parameters (a.k.a the independent variables)
    
        The model parameters are a, b, x₀, τ₁, τ₂ (all float scalars). Hence p0
        must contain five scalars in the same order as shown here.
    
    Var-keyword parameters
    ======================
    
    These collect the named parameters and the args and kwargs passed directly
    to scipy.optimize.least_squares(). For a complete description please see the 
    documentation of scipy.optimize.least_squares()
    
    jac
    bounds
    method
    ftol
    xtol
    gtol
    x_scale
    loss
    f_scale
    max_nfev
    diff_step
    tr_solver
    tr_options
    jac_sparsity
    verbose
    args
    
    The var-keyword parameters not listed above are passed as `kwargs` parameter
    to the least_squares() function.
    
    Returns:
    ========
    fittedCurve: numpy array
    
    result: dict with the mapping:
        "Fit"           → the result of scipy.optimize.least_squares
        "Coefficients"  → the fitted parameters for the Clements & Bekkers '97 model
        "Rsq"           → the R² of the fit (goodness of fit)
    
    
    """
    # TODO/FIXME: 2022-10-25 23:33:58
    # allow lower/upper bounds individually for each parameter
    from core import datatypes as dt
    from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
    
    jac         = kwargs.pop("jac",         "2-point")
    bounds      = kwargs.pop("bounds",      (-np.inf, np.inf))
    method      = kwargs.pop("method",      "trf")
    ftol        = kwargs.pop("ftol",        1e-8)
    xtol        = kwargs.pop("xtol",        1e-8)
    gtol        = kwargs.pop("gtol",        1e-8)
    x_scale     = kwargs.pop("x_scale",     1.0)
    loss        = kwargs.pop("loss",        "linear")
    f_scale     = kwargs.pop("f_scale",     1.0)
    max_nfev    = kwargs.pop("max_nfev",    None)
    diff_step   = kwargs.pop("diff_step",   None)
    tr_solver   = kwargs.pop("tr_solver",   None)
    tr_options  = kwargs.pop("tr_options",  {})
    jac_sparsity= kwargs.pop("jac_sparsity",None)
    verbose     = kwargs.pop("verbose",     0)
    
    if not isinstance(data, (neo.AnalogSignal, DataSignal)):
        raise TypeError("Data to be fitted must be a neo.AnalogSignal, or a datatypes.DataSignal; got %s instead" % type(data).__name__)
    
    if data.ndim == 2 and data.shape[1] > 1:
        raise ValueError("Data must contain a single channel")
    
    if not isinstance(p0, (tuple, list)):
        raise TypeError("Initial parameters expected to be a list; got %s instead" % type(p0).__name__)
    
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
        raise TypeError("bounds expected a 2-tuple or a 2-element list")
    
    def __cost_fun__(x, t, y, *args, **kwargs):  # returns residuals
        yf = models.Clements_Bekkers_97(t, x)
        
        ret = y-yf
        
        return ret
    
    # not used here, but remove it from kwargs anyway
    args        = kwargs.pop("args",        ()) 
    
    
    
    # find out where NaNs are in data
    realDataNdx = ~np.isnan(data)
    
    ydata = data.magnitude[realDataNdx]
    
    realDataNdx = np.squeeze(realDataNdx)
    
    if isinstance(data, neo.AnalogSignal):
        domaindata = data.times.magnitude
        
    else:
        domaindata = data.domain.magnitude
    
    xdata  = domaindata[realDataNdx]
    
    # to correct for the onset parameters!
    if all(realDataNdx):
        deltaOnset = 0
        
    else:
        deltaOnset = xdata[0]
    
    # reset xdata to start at 0
    xdata -= deltaOnset
    

    x0 = p0
    lo = list()
    up = list()
    
    l0 = bounds[0]
    u0 = bounds[1]
    
    if isinstance(l0, numbers.Real):
        lo = [l0] * len(p0)
        
    elif isinstance(l0, (tuple, list)):
        if len(l0) not in (1, len(p0)):
            raise ValueError(f"Incorrect number of lower bounds; expecting 1 or {len(p0)}, got {len(l0)} instead")

        if all(isinstance(l, numbers.Real) for l in l0):
            if len(l0) == 1:
                lo = [l0[0]] * len(p0)
            else:
                lo = [l for l in l0]

        elif all(isinstance(l, np.ndarray) and l.size == 1 and l.dtype == np.dtype(float) for l in l0):
            if len(l0) == 1:
                lo = [float(l)] * len(p0)
            else:
                lo = [float(l) for l in l0]
                
    elif isinstance(l0, np.ndarray):
        if l0.size not in (1, len(p0)):
            raise ValueError(f"Incorrect number of lower bounds; expecting 1 or {len(p0)}, got {l0.size} instead")
        
        if not dt.is_vector(l0):
            raise ValueError("Lower bounds must be a vector")
        
    elif isinstance(l0, pd.Series):
        if len(l0) not in (1, len(p0)):
            raise ValueError(f"Incorrect number of lower bounds; expecting 1 or {len(p0)}, got {l0.size} instead")
        
        lo = [float(l.magnitude) if isinstance(l, pq.Quantity) else float(l) for l in l0]
            
    else:
        raise ValueError(f"Incorrect lower bounds specified {l0}")
    
    if isinstance(u0, numbers.Real):
        up = [u0] * len(p0)
        
    elif isinstance(u0, (tuple, list)):
        if len(u0) not in (1, len(p0)):
            raise ValueError(f"Incorrect number of upper bounds; expecting 1 or {len(p0)}, got {len(u0)} instead")

        if all(isinstance(l, numbers.Real) for l in u0):
            if len(u0) == 1:
                up = [u0[0]] * len(p0)
            else:
                up = [l for l in u0]

        elif all(isinstance(l, np.ndarray) and l.size == 1 and l.dtype == np.dtype(float) for l in u0):
            if len(u0) == 1:
                up = [float(l)] * len(p0)
            else:
                up = [float(l) for l in u0]
                
    elif isinstance(u0, np.ndarray):
        if u0.size not in (1, len(p0)):
            raise ValueError(f"Incorrect number of upper bounds; expecting 1 or {len(p0)}, got {u0.size} instead")
        
        if not dt.is_vector(u0):
            raise ValueError("Lower bounds must be a vector")
        
    elif isinstance(u0, pd.Series):
        if len(u0) not in (1, len(p0)):
            raise ValueError(f"Incorrect number of upper bounds; expecting 1 or {len(p0)}, got {u0.size} instead")
        
        up = [float(l.magnitude) if isinstance(l, pq.Quantity) else float(l) for l in u0]
            
    else:
        raise ValueError(f"Incorrect upper bounds specified {u0}")
    
    
    bnds = (lo, up)
    
    # NOTE: 2022-10-30 14:39:57
    # solve a non-linear least-squares problem with bounds on the variables
    # x0 is the initial "guess" (initial values for model parameters, a.k.a the 
    # independent variables)
    res = optimize.least_squares(__cost_fun__, x0, args=(xdata, ydata), jac=jac,
                                 bounds = bounds, method=method, loss=loss,
                                 ftol=ftol, xtol=xtol, gtol=gtol, x_scale=x_scale,
                                 f_scale=f_scale, max_nfev=max_nfev, 
                                 diff_step=diff_step, tr_solver=tr_solver,
                                 tr_options=tr_options, jac_sparsity=jac_sparsity,
                                 verbose=verbose, kwargs=kwargs)
    
    res_x = list(res.x.flatten())
    
    # create fitted curve
    fC = models.Clements_Bekkers_97(xdata, res_x)
    
    sst = np.sum( (ydata - ydata.mean()) ** 2.)
    
    sse = np.sum((fC - ydata) ** 2.)
    
    # R² for the entire fit
    rsq = 1 - sse/sst # only one R²
    
    result = collections.OrderedDict()
    result["Fit"] = res
    result["Coefficients"] = res_x
    result["Rsq"] = rsq
    
    # reconstruct final fitted curve (REMEMBER: we have taken out the NaNs!)
    initialSupport = np.full((data.shape[0],), np.NaN)
    
    fittedCurve = initialSupport.copy()
    
    fittedCurve[realDataNdx] = fC
    
    return fittedCurve, result

def fit_Event_wave(data, wave):
    """R² between data and a template waveform
    
    Not a curve fit but a measure of how well the data is matched by the waveform
    template - used when detecting mEPSCs using a template waveform (rather than
                a synthetic mEPSC which is a realization of the Clements & Bekkers '97
                waveform)
    """
    
    if not isinstance(data, (neo.AnalogSignal, DataSignal)):
        raise TypeError("Data to be fitted must be a neo.AnalogSignal, or a datatypes.DataSignal; got %s instead" % type(data).__name__)
    
    if data.ndim == 2 and data.shape[1] > 1:
        raise ValueError("Data must contain a single channel")
    
    
    if not isinstance(wave, (neo.AnalogSignal, DataSignal)):
        raise TypeError("Data to be fitted must be a neo.AnalogSignal, or a datatypes.DataSignal; got %s instead" % type(data).__name__)
    
    if wave.ndim == 2 and wave.shape[1] > 1:
        raise ValueError("Data must contain a single channel")
    
    if data.size != wave.size:
        raise ValueError("Both data and wave must have the same size")
    
    sst = np.sum((data.magnitude.flatten() - data.magnitude.flatten().mean()) ** 2.)
    
    sse = np.sum((wave.magnitude.flatten() - data.magnitude.flatten()) ** 2.)
    
    return 1 - sse/sst
    
    
    
def fit_nsfa(data, p0, **kwargs):
    jac         = kwargs.pop("jac",         "2-point")
    bounds      = kwargs.pop("bounds",      (-np.inf, np.inf))
    method      = kwargs.pop("method",      "trf")
    ftol        = kwargs.pop("ftol",        1e-8)
    xtol        = kwargs.pop("xtol",        1e-8)
    gtol        = kwargs.pop("gtol",        1e-8)
    x_scale     = kwargs.pop("x_scale",     1.0)
    loss        = kwargs.pop("loss",        "linear")
    f_scale     = kwargs.pop("f_scale",     1.0)
    max_nfev    = kwargs.pop("max_nfev",    None)
    diff_step   = kwargs.pop("diff_step",   None)
    tr_solver   = kwargs.pop("tr_solver",   None)
    tr_options  = kwargs.pop("tr_options",  {})
    jac_sparsity= kwargs.pop("jac_sparsity",None)
    verbose     = kwargs.pop("verbose",     0)
    
    def __cost_fun__(x, t, y, *args, **kwargs):  # returns residuals
        yf = models.nsfa(t, x)
        
        ret = y-yf
        
        return ret
    
    args        = kwargs.pop("args",        ()) 
   
    realDataNdx = ~np.isnan(data)
    
    ydata = data.magnitude[realDataNdx]
    
    realDataNdx = np.squeeze(realDataNdx)
    
    if isinstance(data, neo.AnalogSignal):
        domaindata = data.times.magnitude
        
    else:
        domaindata = data.domain.magnitude
    
    xdata  = domaindata[realDataNdx]
    
    x0 = p0
    lo = list()
    up = list()
    
    l0 = bounds[0]
    u0 = bounds[1]
    
    if isinstance(l0, numbers.Real):
        lo = [l0] * len(p0)
        
    elif isinstance(l0, (tuple, list)):
        if len(l0) not in (1, len(p0)):
            raise ValueError(f"Incorrect number of lower bounds; expecting 1 or {len(p0)}, got {len(l0)} instead")

        if all(isinstance(l, numbers.Real) for l in l0):
            if len(l0) == 1:
                lo = [l0[0]] * len(p0)
            else:
                lo = [l for l in l0]

        elif all(isinstance(l, np.ndarray) and l.size == 1 and l.dtype == np.dtype(float) for l in l0):
            if len(l0) == 1:
                lo = [float(l)] * len(p0)
            else:
                lo = [float(l) for l in l0]
                
    elif isinstance(l0, np.ndarray):
        if l0.size not in (1, len(p0)):
            raise ValueError(f"Incorrect number of lower bounds; expecting 1 or {len(p0)}, got {l0.size} instead")
        
        if not dt.is_vector(l0):
            raise ValueError("Lower bounds must be a vector")
        
    elif isinstance(l0, pd.Series):
        if len(l0) not in (1, len(p0)):
            raise ValueError(f"Incorrect number of lower bounds; expecting 1 or {len(p0)}, got {l0.size} instead")
        
        lo = [float(l.magnitude) if isinstance(l, pq.Quantity) else float(l) for l in l0]
            
    else:
        raise ValueError(f"Incorrect lower bounds specified {l0}")
    
    if isinstance(u0, numbers.Real):
        up = [u0] * len(p0)
        
    elif isinstance(u0, (tuple, list)):
        if len(u0) not in (1, len(p0)):
            raise ValueError(f"Incorrect number of upper bounds; expecting 1 or {len(p0)}, got {len(u0)} instead")

        if all(isinstance(l, numbers.Real) for l in u0):
            if len(u0) == 1:
                up = [u0[0]] * len(p0)
            else:
                up = [l for l in u0]

        elif all(isinstance(l, np.ndarray) and l.size == 1 and l.dtype == np.dtype(float) for l in u0):
            if len(u0) == 1:
                up = [float(l)] * len(p0)
            else:
                up = [float(l) for l in u0]
                
    elif isinstance(u0, np.ndarray):
        if u0.size not in (1, len(p0)):
            raise ValueError(f"Incorrect number of upper bounds; expecting 1 or {len(p0)}, got {u0.size} instead")
        
        if not dt.is_vector(u0):
            raise ValueError("Lower bounds must be a vector")
        
    elif isinstance(u0, pd.Series):
        if len(u0) not in (1, len(p0)):
            raise ValueError(f"Incorrect number of upper bounds; expecting 1 or {len(p0)}, got {u0.size} instead")
        
        up = [float(l.magnitude) if isinstance(l, pq.Quantity) else float(l) for l in u0]
            
    else:
        raise ValueError(f"Incorrect upper bounds specified {u0}")
    
    
    bnds = (lo, up)
    
    res = optimize.least_squares(__cost_fun__, x0, args=(xdata, ydata), jac=jac,
                                 bounds = bounds, method=method, loss=loss,
                                 ftol=ftol, xtol=xtol, gtol=gtol, x_scale=x_scale,
                                 f_scale=f_scale, max_nfev=max_nfev, 
                                 diff_step=diff_step, tr_solver=tr_solver,
                                 tr_options=tr_options, jac_sparsity=jac_sparsity,
                                 verbose=verbose, kwargs=kwargs)
    
    res_x = list(res.x.flatten())

    fC = models.nsfa(xdata, res_x)
    
    sst = np.sum( (ydata - ydata.mean()) ** 2.)
    
    sse = np.sum((fC - ydata) ** 2.)
    
    # R² for the entire fit
    rsq = 1 - sse/sst # only one R²
    
    result = collections.OrderedDict()
    result["Fit"] = res
    result["Coefficients"] = res_x
    result["Rsq"] = rsq
    
    initialSupport = np.full((data.shape[0],), np.NaN)
    
    fittedCurve = initialSupport.copy()
    
    fittedCurve[realDataNdx] = fC
    
    return fittedCurve, result

                     
                     
