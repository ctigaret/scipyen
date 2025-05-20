# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Wrappers around scipy.optimize

FIXME/TODO: 2022-10-25 23:57:08
Harmonize the API (this is the role of the upcoming modelfitting.py module)
"""

#### BEGIN core python modules
import os, sys, traceback, warnings, numbers, collections, typing, types, inspect
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import quantities as pq
import pandas as pd
from scipy import cluster, optimize, signal, integrate, linalg #, where
from core.vigra_patches import vigra
import neo
#### END 3rd party modules

#### BEGIN pict.core modules
#import imageviewer as iv
#import signalviewer as sv
from . import tiwt
from . import models
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core import datatypes
from core import prog
# from core.traitcontainers import DataBag
#from .patchneo import *
#### END pict.core modules

def fitGauss1DSum(x, y, locations, **kwargs):
    r"""Fits a sum of shifted 1D Gaussians.
    
    CAUTION  (TODO/FIXME): Unstable when parameters are given in floating point 
    calibrated axis units. Use with parameters given in data samples.
   
    """
    from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
    #from . import datatypes  
    
    if not isinstance(locations, (tuple, list, np.ndarray, numbers.Real)):
        raise TypeError("Locations expected to be a sequence of floats or a scalar")
    
    if isinstance(locations, numbers.Real):
        locations = [locations]
        
    if isinstance(x, (neo.AnalogSignal, DataSignal, pq.Quantity)):
        xx = x.magnitude.squeeze()
        
    elif isinstance(x, np.ndarray):
        xx = x.squeeze()
        
    else:
        raise TypeError("x expected to be a np.ndarray, a neo.AnalogSignal or a datasignal.DataSignal; got %s instead" % type(x).__name__)
        
    if xx.ndim > 1:
        raise TypeError("x must be a vector")
    
    #print("xx.shape: ", xx.shape)
    
    if isinstance(y, (neo.AnalogSignal, DataSignal, pq.Quantity)):
        yy = y.magnitude.squeeze()
        
    elif isinstance(y, np.ndarray):
        yy = y.squeeze()
        
    else:
        raise TypeError("y expected to be a np.ndarray, a neo.AnalogSignal or a datasignal.DataSignal; got %s instead" % type(y).__name__)
        
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
    r"""Fits CaT model to CaT data.
    
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
    #from . import datatypes  
    from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
    
    if not isinstance(data, (neo.AnalogSignal, DataSignal)):
        raise TypeError("Data to be fitted must be a neo.AnalogSignal, or a datasignal.DataSignal; got %s instead" % type(data).__name__)
    
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
    r"""Fits a Clements & Bekkers '97 waveform through the data.
    
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
    from core import datatypes
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
        raise TypeError("Data to be fitted must be a neo.AnalogSignal, or a datasignal.DataSignal; got %s instead" % type(data).__name__)
    
    if data.ndim == 2 and data.shape[1] > 1:
        raise ValueError("Data must contain a single channel")
    
    if not isinstance(p0, (tuple, list)):
        raise TypeError("Initial parameters expected to be a list; got %s instead" % type(p0).__name__)
    
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
        raise TypeError("bounds expected a 2-tuple or a 2-element list")
    
    def __cost_fun__(x, t, y, *args, **kwargs):  # returns residuals
        r""" x: sequence of model params
            t: independent variable
            y: the data (dependent variable)
        """
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
        
        if not  datatypes.is_vector(l0):
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
        
        if not  datatypes.is_vector(u0):
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
    r"""R² between data and a template waveform
    
    Not a curve fit but a measure of how well the data is matched by the waveform
    template - used when detecting mEPSCs using a template waveform (rather than
                a synthetic mEPSC which is a realization of the Clements & Bekkers '97
                waveform)
    """
    
    if not isinstance(data, (neo.AnalogSignal, DataSignal)):
        raise TypeError("Data to be fitted must be a neo.AnalogSignal, or a datasignal.DataSignal; got %s instead" % type(data).__name__)
    
    if data.ndim == 2 and data.shape[1] > 1:
        raise ValueError("Data must contain a single channel")
    
    
    if not isinstance(wave, (neo.AnalogSignal, DataSignal)):
        raise TypeError("Data to be fitted must be a neo.AnalogSignal, or a datasignal.DataSignal; got %s instead" % type(data).__name__)
    
    if wave.ndim == 2 and wave.shape[1] > 1:
        raise ValueError("Data must contain a single channel")
    
    if data.size != wave.size:
        raise ValueError("Both data and wave must have the same size")
    
    sst = np.sum((data.magnitude.flatten() - data.magnitude.flatten().mean()) ** 2.)
    
    sse = np.sum((wave.magnitude.flatten() - data.magnitude.flatten()) ** 2.)
    
    return 1 - sse/sst
    
    
def scale_fit_wave(x, y, p0 = 1, method="nelder-mead"):
    r""" Finds a scale factor of y such that it matches x.
    
    The objective function being minimized is the scalar product x - p0 * y
    
    Parameters:
    ----------
    x: 1D vector to compare against
    y: 1D vector with the same shape as x, which is to be scaled such that 
        p * y ≈ x 
    
        in other words, 

        Σ(x - p*y)² ≈ 0                                                 (1)
    
    p0: initial value of `p`
    
    Returns:
    --------
    a scipy.optimize.OptimizeResult data.
    When optimization was successful, the `x` attribute of the result is the 
    parameter value p that satisfies (1)
    
    WARNING: THIS FUNCTION DOES NOT SCALE ANY OF THE WAVES PASSED TO IT.
    One should first inspect the `success` attribute  of the result, then if 
    True, use the value of the `x` attribute of the result to scale the wave in 
    `y` 
    
    """
    if not all(isinstance(x, np.ndarray) for v in (x,y)):
        raise TypeError("Expecting two numpy arrays")
    
    if not all( datatypes.is_vector(v) for v in (x,y)):
        raise ValueError("Expecting two vectors")
    
    if x.ndim != y.ndim or x.shape != y.shape:
        raise ValueError(f"x and y must have the same dimensionality and shape; gpt x with {x.ndim} dimensions and {x.shape} shape, and y with {y.ndim} dimensions and {y.shape} shape")

    def __wave_fun__(x_, a, b):
        r"""x_: scale; 
           a : original wave
           b: wave to be scaled"""
        y = a - x_ * b
        return np.dot(y.T, y)
    
    res = optimize.minimize(__wave_fun__, p0, args = (x,y),
                            method = method)
    
    return res

def scale_fit_wave2(x, y, p0 = (1,0)):
    r"""Two-params version """
    def __wave_fun__(x_, y_, a, b):
        y = a - x_*b+y_
        return np.dot(y.T, y)
    
    if not all(isinstance(x, np.ndarray) for v in (x,y)):
        raise TypeError("Expecting two numpy arrays")
    
    if not all( datatypes.is_vector(v) for v in (x,y)):
        raise ValueError("Expecting two vectors")
    
    if x.ndim != y.ndim or x.shape != y.shape:
        raise ValueError(f"x and y must have the same dimensionality and shape; gpt x with {x.ndim} dimensions and {x.shape} shape, and y with {y.ndim} dimensions and {y.shape} shape")

    scale, offset = p0
    res = optimize.minimize(__wave_fun__, (scale, offset), args = (x,y),
                            method=method)
    return res
    
def fit_nsfa(data, p0, **kwargs):
    r"""Fit the parabola y = x * i - x²/N + b through the observed variable data.
    Parameters:
    ===========
    data: the observed variable
    p0: tuple with the model parameters i, N, b
    
    Var-keyword parameters:
    =======================
    x: the independent variable
    
    The following are passed directly to scipy.optimize.least_squares:
    bounds, jac, method, ftol, xtol, gtol, x_scale, loss, f_scale, max_nfev,
    diff_step, tr_solver, tr_optoins, jac_sparsity, verbose
    
    (see scipy manual for details)
    
    Defaults are:
    
    jac          = "2-point"
    bounds       = -np.inf, np.inf
    method       = "trf"
    ftol         = 1e-8
    xtol         = 1e-8
    gtol         = 1e-8
    x_scale      = 1.0
    loss         = "linear"
    f_scale      = 1.0
    max_nfev     = None
    diff_step    = None
    tr_solver    = None
    tr_options   = {}
    jac_sparsity = None
    verbose      = 0
    
    
    """
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
    x           = kwargs.pop("x",           None)
    
    def __cost_fun__(x, t, y, *args, **kwargs):  # returns residuals
        yf = models.nsfa(t, x)
        
        ret = y-yf
        
        return ret
    
    args        = kwargs.pop("args",        ()) 
   
    realDataNdx = ~np.isnan(data)
    
    if isinstance(data, neo.core.basesignal.BaseSignal):
        ydata = data.magnitude[realDataNdx]
    
        realDataNdx = np.squeeze(realDataNdx)
    
        if isinstance(data, neo.AnalogSignal):
            domaindata = data.times.magnitude
            
        else:
            domaindata = data.domain.magnitude
        
        xdata  = domaindata[realDataNdx]
        
    else:
        if not isinstance(x, np.ndarray): 
            raise TypeError(f"When data id a numpy array, x must be given as a numpy array")
        
        if x.shape != data.shape:
            raise ValueError(f"x shape {x.shape} is different to to data shape {data.shape}")
        
        ydata = data[realDataNdx]
        xdata = x[realDataNdx]
    
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
        
        if not  datatypes.is_vector(l0):
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
        
        if not  datatypes.is_vector(u0):
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

                     
def fit_model(data, func, p0, *args, **kwargs):
    r"""Generic fitting function.
    Applies scipy.optimize.least_squares to minimize the residuals between the 
    model function `func` and measurements in `data`.
    
    WARNING: This function uses scipy.optimize.least_squares directly to perform
    non-linear least-squares fitting (with or without constraints), and is highly
    dependent on a good guess of the initial coefficient values.
    
    As an alternative for exponential decay fitting, you could try the scikit-guess
    package.
    
    Positional parameters:
    =====================
    data: 1D or 2D array-like, numeric - the "dependent" variable to be fitted.
        When ``data`` is a 2D array, the variables must be arranged in columns,
        with the number of rows being the number of observations. Think of it
        as "channels" in a multi-channel signal.
    
        This can be a neo.AnalogSignal. If the signal has more than one channel,
        the index of the channel to be fitted can be specified in the var-keyword 
        ``channel``.
    
    func: python function that takes a scalar ('x') and a sequence ('p') of 
        model parameters, and returns a scalar; the signature is:
    
        func(x, p, /, *args, **kwargs)
    
        NOTE: This function can be one of the ``*_model`` functions defined in 
        Scipyen's ``core.models`` module.
    
    p0: sequence of initial values for the coefficients in the model realized by
    `func` - in the same order as expected by func
    
    Var-keyword parameters (**kwargs):
    =================================
    
    x: the independent variable, array-like, with the same shape as `data`.
        This is mandatory when ``data`` is a generic numpy array or Quantity array.
    
        When ``data`` is a neo.AnalogSignal, this can be omitted, because the 
        signal object provides its own independent data (the "domain") in the 
        ``times`` attribute.
    
    channel: int, default is 0; this is useful to select the channel from a 
        multi-channel signal
    
    fargs: tuple with var-positional parameters to `func`
    
    fkwargs: dict with keyword parameters to `func`
    
    coeff_names: tuple with model parameter names or symbols (str)
    
    
    The following are passed directly to scipy.optimize.least_squares:
    bounds, jac, method, ftol, xtol, gtol, x_scale, loss, f_scale, max_nfev,
    diff_step, tr_solver, tr_options, jac_sparsity, verbose
    
    (see scipy manual for details)
    
    Defaults are:
    
    bounds       = -np.inf, np.inf
    jac          = "2-point"
    method       = "trf"
    ftol         = 1e-8
    xtol         = 1e-8
    gtol         = 1e-8
    x_scale      = 1.0
    loss         = "linear"
    f_scale      = 1.0
    max_nfev     = None
    diff_step    = None
    tr_solver    = None
    tr_options   = {}
    jac_sparsity = None
    verbose      = 0
    
    Returns:
    ========
    
    WARNING: Since 2025-05-19 12:09:54 the second element in the tuple is a 
    types.SimpleNamespace, and NOT a collections.OrderedDict anymore!
    
    A tuple: (fitted curve, types.SimpleNamespace) where:
    
    • fitted curve is the realization of the model in `func` using the fitted 
        parameters and the independent variable `x`
    
    • the OrderedDict has the following keys:
    
        Model           ↦ `func` module.name
        Fit             ↦ the fit result output by scipy.optimize.least_squares
        Coefficients    ↦ a tuple with fitted model parameter values
        Rsq             ↦ R² correlation coefficient between the fitted curve 
                         and the `data`
    
    
    """
    from dataclasses import MISSING # flag for badly-formed annotations
    
    channel     = kwargs.pop("channel",     0)
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
    x           = kwargs.pop("x",           None)
    fargs       = kwargs.pop("fargs",       tuple())
    fkwargs     = kwargs.pop("fkwargs",     dict())
    
    
    funcSignature = prog.signature_as_dict(func)
    
    args_annots = prog.get_positional_named_annotations(func)
    
#     compress_annot = lambda x: x[0] if len(x) else MISSING
#     
#     args_annots = list(map(lambda i: (i[0], i[1]), funcSignature["positional"].items())) + \
#                   list(map(lambda i: (i[0], compress_annot(tuple(set(i[1])-{inspect._empty}))), funcSignature["named"].items()))
    
    assert len(args_annots) >= 1, f"Invalid func signature {funcSignature}"
    assert all(len(v) == 2 and v[1] not in (MISSING, inspect._empty) for v in args_annots), f"Bad or missing type annotations for 'func' {func}"

    # check first argument
    atypes = set()
    prog.unwind_type_sig(args_annots[0][1], atypes)
    assert any(t in atypes for t in (np.ndarray, float)), f"First argument to 'func' {func} must be a float or an np.ndarray; instead, got {args_annots[0][1]}"
        
    to_unpack:bool = True
    
    if len(args_annots) == 2:
        atypes.clear()
        prog.unwind_type_sig(args_annots[1][1], atypes)
        # 1) is this a Sequence? then it must be unpacked
        if any(t in atypes for t in (typing.Sequence, typing.Sequence[float|np.ndarray], typing.Sequence[float, typing.Sequence[np.ndarray]])):
            to_unpack = False
        else:
            # only take scalar np.ndarrays or floats; cannot check for scalars
            # as the arguments are not present, but check for types
            assert any(t in atypes for t in (np.ndarray, float, np.ndarray | float)), f"Second argument to 'func' {func} should require a float or an np.ndarray, or a sequence of such; instead, got {args_annots[0][1]}"
            
    elif len(args_annots) > 2:
        # only take scalar ndarrays or floats; here, only checking types as arguments 
        # aren't available yet
        for k, aa in enumerate(args_annots):
            atypes.clear()
            prog.unwind_type_sig(aa[1], atypes)
            assert any(t in atypes for t in (np.ndarray, float, np.ndarray | float)), f"Argument {k+1} argument to 'func' {func} should require a float or an np.ndarray; instead, got {args_annots[0][1]}"
        to_unpack = True
        
    # print(f"prog.fit_model: to_unpack = {to_unpack}")
        
    def __cost_fun__(x0, t, y):  # returns residuals
        yf = func(t, *x0, **fkwargs) if to_unpack else func(t, x0, **fkwargs)
        return y-yf
    
    args        = kwargs.pop("args",        ()) 
   
    realDataNdx = ~np.isnan(data)
    
    # ### prepare the signal
    if isinstance(data, neo.core.basesignal.BaseSignal):
        if data.shape[1] > 1:
            if channel < -data.shape[1] or channel >= data.shape[1]:
                raise ValueError(f"Invalid channel specified ({channel}) for data with {data.shape[1]} channels")
            data = data[:,channel]
            
        ydata = data.magnitude[realDataNdx]
    
        realDataNdx = np.squeeze(realDataNdx)
    
        if isinstance(data, neo.AnalogSignal):
            domaindata = data.times.magnitude
            
        else:
            domaindata = data.domain.magnitude
        
        xdata  = domaindata[realDataNdx]
        
    else:
        if not isinstance(x, np.ndarray): 
            raise TypeError(f"When data is a numpy array, x must be given as a numpy array")
        
        assert(data.ndim in (1,2)), f"Arrays with {data.ndim} dimensions are not supported"
        
        if data.ndim == 2 and data.shape[1] > 1:
            if channel < -data.shape[1] or channel >= data.shape[1]:
                raise ValueError(f"Invalid channel specified ({channel}) for data with {data.shape[1]} channels")
            data = data[:,channel]
            
        if x.shape != data.shape:
            raise ValueError(f"x shape {x.shape} is different to to data shape {data.shape}")
        
        
        ydata = data[realDataNdx]
        xdata = x[realDataNdx]
    
    x0 = p0 # sequence of initial values for the model parameters
    
    coeff_names = kwargs.pop("coeff_names", None)
    
    # ### prepare fit coefficients
    if isinstance(coeff_names, typing.Sequence):
        if len(coeff_names) == 0:
            coeff_names = [f"Coefficient {k}" for k in range(len(p0))]
        else:
            if len(coeff_names) < len(p0):
                coeff_names = tuple([n for n in coeff_names] + [f"Coefficient_{k}" for k in range(len(p0)-len(coeff_names))])
                
            elif len(coeff_names) > len(p0):
                coeff_names = coeff_names[0:len(p0)]
                
    else:
        coeff_names = [f"Coefficient {k}" for k in range(len(p0))]
        
    # ### prepare constraints (bounds)
    lo = list()
    up = list()
    
    if isinstance(bounds, typing.Sequence) and len(bounds) == 2:
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
            
            if not datatypes.is_vector(l0):
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
            
            if not  datatypes.is_vector(u0):
                raise ValueError("Lower bounds must be a vector")
            
        elif isinstance(u0, pd.Series):
            if len(u0) not in (1, len(p0)):
                raise ValueError(f"Incorrect number of upper bounds; expecting 1 or {len(p0)}, got {u0.size} instead")
            
            up = [float(l.magnitude) if isinstance(l, pq.Quantity) else float(l) for l in u0]
                
        else:
            raise ValueError(f"Incorrect upper bounds specified {u0}")
        
        bounds = optimize.Bounds(lo, up, keep_feasible = [True] * len(lo))
        
    elif not isinstance(bounds, optimize.Bounds):
        raise TypeError(f"'bounds' expected to be a pair of sequences or an optimize.Bounds object; instead, got a {type(bounds).__name__}")
    
    # print(f"bounds: {bounds}")
    
    # CAUTION: do NOT confuse x0 here with a delay coefficient; here, x0 is the 
    # sequence of initial coefficient values
    res = optimize.least_squares(__cost_fun__, x0, args=(xdata, ydata), jac=jac,
                                 bounds = bounds, method=method, loss=loss,
                                 ftol=ftol, xtol=xtol, gtol=gtol, x_scale=x_scale,
                                 f_scale=f_scale, max_nfev=max_nfev, 
                                 diff_step=diff_step, tr_solver=tr_solver,
                                 tr_options=tr_options, jac_sparsity=jac_sparsity,
                                 verbose=verbose, kwargs=kwargs)
    
    res_x = list(res.x.flatten())

    # generate the fitted curve
    fC = func(xdata, *res_x, *fargs, **fkwargs) if to_unpack else func(xdata, *res_x, *fargs, **fkwargs)
    
    sst = np.sum( (ydata - ydata.mean()) ** 2.) # sum of squares about the mean in the data (total sum of squares)
    
    sse = np.sum((fC - ydata) ** 2.) # sum of squared errors (sum of squared residuals, Sum of Squares Due to Error)
    
    # Coefficient of determination R² for the entire fit
    rsq = 1 - sse/sst # only one R²
    
    df_res = fC.size - len(x0)
    df_tot = fC.size - 1
    
    arsq = 1 - sse * df_tot / (sst * df_res)
    
    rmse = np.sqrt(sse/fC.size)
    
    coefficients = types.SimpleNamespace({"Names": coeff_names,
                                          "Initial": types.SimpleNamespace({"values": x0, "bounds": bounds}),
                                          "Fitted": res_x,
                                          "GoF": types.SimpleNamespace({"Rsq": rsq, "R2adj": arsq, "SSE": sse, "RMSE": rmse})})
    
    
    # result = collections.OrderedDict()
    # NOTE: 2025-05-18 10:05:48 switching to SimpleNamespace
    # TODO: 2025-05-18 10:06:06 propagate this to other fit_* functions in this module
    result = types.SimpleNamespace({"ModelFunction": f"{func.__module__}.{func.__name__}",
                                   "Fit": res,
                                   "Coefficients": coefficients})
    
    initialSupport = np.full((data.shape[0],), np.NaN)
    
    fittedCurve = initialSupport.copy()
    
    fittedCurve[realDataNdx] = fC
    
    return fittedCurve, result

    
def guess_init_biexp(x:np.ndarray, y:np.ndarray, is_sorted:bool=True):
    r"""A crude implementation of Jacquelin's method of integral equation regression
for the biexponential function
    
        y = b ⋅ exp(p𝑥) + c ⋅ exp(q𝑥)
    
    
    CAUTION Only use as an initial guess for the time constants when fitting 
    a biexponential decay model, with τ0 = 1/np.abs(P), and τ1 = 1/np.abs(q)
    
    The biexponential decay model is
    
        y = α + βexp(-x/τ0) + δexp(-x/τ1)
    
    It follows that τ0, τ1 must be > 0 (strictly), and the lower bounds for 
    their initial values must be > 0
    
    Returns:
    ========
    An approximation of b, p, c, q as a 4-tuple
    
    Of these, only p and q are of use , as above (NOTE that the biexponential
    decay model contains an "additive bias" α which is NOT guessed; typically, 
    this is the value of the first sample in the signal, or a "baseline" average)
    
"""
    # ### BEGIN implementation of Jacquelin
    #
    x,y = skg_preprocess(x,y,is_sorted)
    # ξ = x-x[0]
    ξ = x
    
    s = np.zeros(y.shape)
    s[1:] = np.cumsum(0.5* np.diff(x) * (y[1:] + y[:-1])) # mid-point approximation (mid-point rule less error term f``(0.5*(xₖ - xₖ₋₁))(xₖ - xₖ₋₁)³/24)
    
    ss = np.zeros(y.shape) 
    ss[1:] = np.cumsum(0.5* np.diff(x) * (s[1:] + s[:-1]))
    
    Σssₖ2  = np.dot(ss, ss)
    Σssₖsₖ = np.dot(ss, s) 
    Σssₖξₖ = np.dot(ss, ξ) 
    Σssₖyₖ = np.dot(ss, y) 
    Σssₖ   = ss.sum()      
    Σsₖ2   = np.dot(s, s)  
    Σsₖξₖ  = np.dot(s, ξ)  
    Σsₖyₖ  = np.dot(s, y)  
    Σsₖ    = s.sum()       
    Σξₖ2   = np.dot(ξ, x)  
    Σξₖ    = ξ.sum()        
    Σξₖyₖ  = np.dot(ξ, y)   
    Σyₖ    = y.sum()        
    n      = y.shape[0]     
    
    # Step 1
    𝐌ᵀ𝐌 = np.zeros((4, 4))
    
    𝐌ᵀ𝐌[0,:] = [Σssₖ2,  Σssₖsₖ, Σssₖξₖ, Σssₖ]
    𝐌ᵀ𝐌[1,:] = [Σssₖsₖ, Σsₖ2,   Σsₖξₖ,  Σsₖ ]
    𝐌ᵀ𝐌[2,:] = [Σssₖξₖ, Σsₖξₖ,  Σξₖ2,   Σξₖ ]
    𝐌ᵀ𝐌[3,:] = [Σssₖ,   Σsₖ,    Σξₖ,    n   ]
    
    𝐌ᵀ𝚪 = np.array([Σssₖyₖ, Σsₖyₖ, Σξₖyₖ, Σyₖ])
    
    A, B, C, D = np.dot(np.linalg.pinv(𝐌ᵀ𝐌), 𝐌ᵀ𝚪) # D «should» be y[0] 
    
    B2A = B**2 + 4*A # ∵ A = -pq and B = (p+q)
    
    p = 0.5 * (B + np.sqrt(B2A))
    q = 0.5 * (B - np.sqrt(B2A))

    # Step 2
    β = np.exp(p*x)
    η = np.exp(q*x)
    
    Σβₖ2  = np.dot(β, β) 
    Σβₖηₖ = np.dot(β, η)
    Σηₖ2  = np.dot(η, η)
    Σβₖyₖ = np.dot(β, y)
    Σηₖyₖ = np.dot(η, y)
    
    𝐌ᵀ𝐌   = 𝐌ᵀ𝐌[:2,:2]
    𝐌ᵀ𝐌[0,:] = [Σβₖ2,  Σβₖηₖ]
    𝐌ᵀ𝐌[1,:] = [Σβₖηₖ, Σηₖ2 ]
    
    𝐌ᵀ𝚪 = np.array([Σβₖyₖ, Σηₖyₖ])
    
    b, c = np.dot(np.linalg.pinv(𝐌ᵀ𝐌), 𝐌ᵀ𝚪)#, overwrite_a=True, overwrite_b = False)
    
    return (b, c, p, q)#, A, B, C, D)
    # return (b, c, p, q, A, B, C, D)
    #
    # ### END   implementation of Jacquelin 
    
def guess_init_biased_biexp(x, y, is_sorted:bool=True):#
    r"""returns a, b, p, c, q """
    x,y = skg_preprocess(x,y,is_sorted)
    ξ = x
    # ω = x*(0.5*x - x[0])
    ω = 0.5*x**2
    s = np.zeros(y.shape)
    s[1:] = np.cumsum(0.5* np.diff(x) * (y[1:] + y[:-1])) # mid-point approximation (mid-point rule less error term f``(0.5*(xₖ - xₖ₋₁))(xₖ - xₖ₋₁)³/24)
    ss = np.zeros(y.shape) 
    ss[1:] = np.cumsum(0.5* np.diff(x) * (s[1:] + s[:-1]))
    
    Σssₖ2  = np.dot(ss, ss)
    Σssₖsₖ = np.dot(ss, s) 
    Σssₖξₖ = np.dot(ss, ξ) 
    Σssₖωₖ = np.dot(ss, ω) 
    Σssₖyₖ = np.dot(ss, y) 
    Σssₖ   = ss.sum()      
    Σsₖ2   = np.dot(s, s)  
    Σsₖξₖ  = np.dot(s, ξ)  
    Σsₖωₖ  = np.dot(s, ω)  
    Σsₖyₖ  = np.dot(s, y)  
    Σsₖ    = s.sum()       
    Σξₖ2   = np.dot(ξ, ξ)  
    Σξₖωₖ  = np.dot(ξ, ω)  
    Σξₖ    = ξ.sum()        
    Σξₖyₖ  = np.dot(ξ, y)   
    Σωₖyₖ  = np.dot(ω, y)   
    Σωₖ2   = np.dot(ω, ω)
    Σωₖ    = ω.sum() 
    Σyₖ    = y.sum()        
    n      = y.shape[0]     
    
    # Step 1
    
    𝐌ᵀ𝐌 = np.zeros((5, 5))
    𝐌ᵀ𝐌[0,:] = [Σssₖ2,  Σssₖsₖ, Σssₖξₖ, Σssₖωₖ, Σssₖ]
    𝐌ᵀ𝐌[1,:] = [Σssₖsₖ, Σsₖ2,   Σsₖξₖ,  Σsₖωₖ,  Σsₖ ]
    𝐌ᵀ𝐌[2,:] = [Σssₖξₖ, Σsₖξₖ,  Σξₖ2,   Σξₖωₖ,  Σξₖ ]
    𝐌ᵀ𝐌[3,:] = [Σssₖωₖ, Σsₖωₖ,  Σξₖωₖ,  Σωₖ2,   Σωₖ ]
    𝐌ᵀ𝐌[4,:] = [Σssₖ,   Σsₖ,    Σξₖ,    Σωₖ,    n   ]
    
    𝐌ᵀ𝚪 = np.array([Σssₖyₖ, Σsₖyₖ, Σξₖyₖ, Σωₖyₖ, Σyₖ])
    
    A, B, C, D, E = np.dot(np.linalg.pinv(𝐌ᵀ𝐌), 𝐌ᵀ𝚪) # BUG 2025-05-18 18:24:32 the problem here is that A must be ≥ 0!
    B2A = B**2 + 4*A # ∵ A = -pq and B = (p+q)
    p = 0.5 * (B + np.sqrt(B2A))
    q = 0.5 * (B - np.sqrt(B2A))
    
    # Step 2
    β = np.exp(p*x)
    η = np.exp(q*x)
   
    Σβₖ2  = np.dot(β, β) 
    Σβₖηₖ = np.dot(β, η)
    Σβₖ   = β.sum()
    Σηₖ2  = np.dot(η, η)
    Σηₖ   = η.sum()
    Σβₖyₖ = np.dot(β, y)
    Σηₖyₖ = np.dot(η, y)
    
    𝐌ᵀ𝐌   = 𝐌ᵀ𝐌[:3,:3]
    𝐌ᵀ𝐌[0,:] = [n,   Σβₖ,   Σηₖ  ]
    𝐌ᵀ𝐌[0,:] = [Σβₖ, Σβₖ2,  Σβₖηₖ]
    𝐌ᵀ𝐌[1,:] = [Σηₖ, Σβₖηₖ, Σηₖ2 ]
    
    𝐌ᵀ𝚪 = np.array([Σyₖ, Σβₖyₖ, Σηₖyₖ])
    a, b, c = np.dot(np.linalg.pinv(𝐌ᵀ𝐌), 𝐌ᵀ𝚪)
    
    return a, b, p, c, q #, A, B, C, D, E
    
def guess_init_two_exp_prod(x:np.ndarray, y:np.ndarray, is_sorted:bool=True):
    r""" y  = a + b × exp(xc) × exp(xd)
    
    This function can be "trivialized" to a single exponential:
    y  = a + b × exp(x(c+d)) = a + b × exp(xζ)
    
    However, here I consider this as a "branching" process where the decay is the 
    net result of two individual decay "modes" occurring simultaneously, each with
    its own  "partial" time constant.
    
    - d/dt 𝐍(t) = 𝐍λ₁ + 𝐍λ₂ = 𝐍(λ₁ + λ₂) with the solution:
    
    𝐍(t) = 𝐍₀ ⋅ exp(-t⋅(λ₁ + λ₂)) = 𝐍₀ ⋅ exp(-t⋅λᵪ)) where λᵪ = (λ₁ + λ₂)
    
    Even if this can be "trivialized" as above, only finding ζ leaves us with an 
    infinity of solutions in c & d.
    
    For such a "double-exponential" decay (as is also usually known, but prone
    to being confused with a sum of two exponentials) I apply Jacquelin's 
    method of using integral equations to reduce a non-linear least-squares 
    (iterative) curve fitting problem to a linear system problem, thus bypassing 
    the need to guess the initial values for the coefficients (the two time constants
    AND the additive and multiplicative bias).
    
    It is likely that a least-squares iterative fitting approach would give
    a much better result in terms of the sum of squared error; however, this function
    is pretty quick and therefore helpful in guessing the initial coefficient values
    for a non-linear least-squares fitting problem solver.
    
    NOTE 1: This is DIFFERENT from the ("true"?) double exponential function treated 
    by Jacquelin, which is effectively a sum of exponentials, and not a product,
    like here.
    
    NOTE 2: This function does NOT take into account a "delay" coefficient (see
    core.curvefitting.fit_model() and core.models.generic_compound_exponential_decay()
    functions in Scipyen) which — granted — introduces a further complication in 
    the non-linear least squares problem (however, this later problem can be
    annulled by setting the domain of a signal to start at 0 and fit with a version
    of the model without "delay" coefficient)
    
    NOTE 3: The name of this function is chosen to avoid the ambiguity of the 
    "double exponential" name, and to reflect the fact that in most circumstances
    this function would be used to determine the set of initial coefficient values
    for a non-linear least-squares fitting problem using the biased product of
    two exponentials
    
    NOTE 4: About time constants:
    
    The time constant τ of a decay process is the inverse of the coefficient at
    the exponent. Thus, using the notations above, τ₁ = 1/λ₁ and τ₂ = 1/λ₂. It
    follows that the COMBINED time constant τᵪ is:
                            
        τᵪ = (λ₁ + λ₂)⁻¹ = (τ₁ × τ₂ / (τ₁ + τ₂)
    
    Therefore, when applying this function to determine initial values for traditional
    curve fitting, remember to calculate the inverse of the last two coefficients
    returned.
    
    Parameters:
    ===========
    x, y, 1D vectors ie., with shape (N,)
    sort:bool When True (default), x,y must have been sorted in increasing order
        of x i.e., monotonically increasing in x, which is essential for the 
        application of the integral equations method; this is usually "baked-in" 
        in biological signals e.g. electrophysiology data, so the default is True.
        When False, the data will be sorted accordingly...
    
    Returns:
    ========
    A 4-tuple of coefficients a, b, c, d.

    The "c" and "d" coefficients are the inverse of exponential decay constants
    (time constants, see NOTE 4). Therefore, to be used with the 
    generic_compound_exponential_decay* functions in this module they must be
    inverted (α = a, β = b, τ₁ = 1/c, τ₂ = 1/d)
    
    """
    x,y = skg_preprocess(x,y,is_sorted)
    
    # Step 1
    # this follows Jacquelin treatment of a single exponential function, which is
    # the trivial form explained above.
    #
    # Because the two exponential factors are KEPT SEPARATE, we need two extra 
    # terms in the linear equations (we have FOUR unknowns), such that the matrix 
    # 𝐌 (see below) has four columns, which nevertheless are pairs of the same thing:
    # M[:,:2] is x-x[0]; M[:,2:] is the Sk (numeric integral of y); the vector 𝐘
    # stays the same (y-y[0]).
    
    M = np.empty(y.shape + (4, ))
    
    M[:,0] = M[:,1] = x-x[0]
    M[0,2:] = 0.                    # first element in the numeric integral is always 0, read Jacquelin's paper
    M[1:,2] = M[1:,3] = np.cumsum(0.5* np.diff(x) * (y[1:] + y[:-1]))
    
    Y = y - y[0]
    
    # solve for A, B, c, d, where A = -ac; B = -ad
    (A, B, c, d), *_ = linalg.lstsq(M, Y, overwrite_a=True, overwrite_b = False)
    
    # a = -A/c # might also use a = -B/d; they are close but NOT equal! Instead, use "a" from Step 2
    
    # Step 2: solve for a, b
    # ### the system of equatios here is:
    # ###   a₂ + b₂ × θ = y ≡ 1×a₂ + θ×b₂ = y.
    # ###
    # ### where θ = exp(xc)⋅exp(xd) = exp(x(c+d)), and we already know c and d
    # ###   with the "unknowns" being a₂ and b₂, whereas the "coefficients" being 1 and θ
    # ### hence
    # ###   𝐌 ×  ⃗ξ  = y ( ⃗ξ  = the vector [a₂, b₂]) ⇒  ⃗ξ  = 𝐌⁻¹ ⋅ y 
    # ### 
    # dump the last two columns of M
    M = M[:,:2]
    
    M[:,0] = 1.
    M[:,1] = np.exp(x * (c+d))
    
    (a, b), *_ = linalg.lstsq(M, y, overwrite_a=True, overwrite_b=False)
    
    return (a, b, c, d)
    
def skg_exp_fit(x, y, is_sorted=True):
    r"""Alternative to skg.exp.exp_fit(…): 'Exponential fit of the form :math:`A + Be^{Cx}`.'
    Implements
    .. [1] Jacquelin, Jean. "\ :ref:`ref-reei`\ ",
       :ref:`pp. 15-18. <reei2-sec2>`,
       https://www.scribd.com/doc/14674814/Regressions-et-equations-integrales
"""
    
    # ### BEGIN comparison with skg.exp.exp_fit in jupyter console:
    #
    # In [1]: %timeit a, b, c = skg.exp.exp_fit(x,y)
    # 713 μs ± 8.01 μs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
    # 
    # In [2]: %timeit a1, b1, c1 = crvf.skg_exp_fit(x,y)
    # 373 μs ± 7.87 μs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
    #
    # In [3]: assert np.all(np.isclose([a, b, c], [a1, b1, c1]))
    #
    # ### END   comparison with skg.exp.exp_fit:
    
    # ### BEGIN NOTE: What the original scikit-guess exp.exp_fit() function does:
    #
    # M = np.hstack(𝐱[:,np.newaxis], 𝐬[:,np.newaxis])
    # with 𝐱 and 𝐬 defined as below, then solves via lstsq
    #
    # 𝐌 ×  ⃗𝛏𝐯 =  ⃗𝐲                                                           (†)
    #
    # where: 
    # 
    #  ⃗𝛏 is  ⃗𝐱 - x[0]
    #                                    
    #  ⃗𝐬 is the numeric approximation of:
    #
    #   x 
    #   ∫f(u)du = a(x-x₀) + (b/c)(exp(cx)-exp(cx₀))                          (‡)
    #   x₀
    #
    # which is the definite integral of the model function f(x) = a + b⋅exp(cx)
    # 
    # and  ⃗𝐲 is the "real data" vector
    #
    # In a nutshell, given the data vector  ⃗𝐲 and its domain (or independent 
    # variable) vector  ⃗𝐱, Jaqcuelin's paper transforms the problem of fitting
    # the "model" function  ⃗𝐟(x) through the data  ⃗𝐲  into a linear regression 
    # problem that uses integral equations, in order to find out the coefficient 
    # set {a, b, c} that minimizes the sum of squared errors between the data
    # ⃗𝐲 and the model ⃗𝐟(x)
    #
    # That is, it calculates an approximative solution to an integral equation.
    #
    # • the linear regression system uses an approximation of  ⃗𝐟(x) by a
    #   linear combination of integrals of the model function  ⃗𝐟(x):
    #
    #   ⃗𝐟(x) = a + b⋅exp(c⋅ ⃗𝐱)                                               (1)
    #
    #   From (1): exp(c⋅x₀) = (f(x₀)-a)/b                                    (2)
    #
    #            x
    #   ⃗𝐉(x) = ∫ ⃗𝐟(u)du = ( ⃗𝐱-x₀)⋅a + (exp(c⋅ ⃗𝐱)-exp(cx₀))⋅b/c               (3)
    #            x₀
    #   
    #            x
    #   ⃗𝐉(x) = ∫ ⃗𝐟(u)du = ( ⃗𝛏⋅a + (exp(c⋅ ⃗𝐱)-exp(cx₀))⋅b/c                  (3a)
    #            x₀
    #   
    #   In (3), replace exp(cx₀) with the rhs of (2):
    #   
    #   ⃗𝐉(x) = ( ⃗𝐱 - x₀)⋅a + (( ⃗𝐟(x) - a)/b)⋅b/c - exp(cx₀)⋅b/c
    #        = (ac⋅ ⃗𝐱 - acx₀ +  ⃗𝐟(x) - a - b⋅exp(c₀))/c
    #        = ((ac⋅( ⃗𝐱 - x₀)) +  ⃗𝐟(x) - f(x₀))/c                            (4)
    #
    # ⟹ c⋅ ⃗𝐉(x) = ( ⃗𝐱 - x₀)⋅ac +  ⃗𝐟(x) - f(x₀)                               (5)
    #   c⋅ ⃗𝐉(x) = ac⋅ ⃗𝛏 +  ⃗𝐟(x) - f(x₀)                                     (5a)
    #
    # ⟹ ⃗𝐟(x) - f(x₀) = -ac⋅( ⃗𝐱 - x₀) + c ⃗𝐉(x)                                (6)
    #   ⃗𝐟(x) - f(x₀) = -ac⋅ ⃗𝛏 + c⋅ ⃗𝐉(x)                                     (6a)
    #
    # In (6), let:
    #
    #   A = -ac                                                             (7a)
    #   B = c                                                               (7b)
    #
    # then, (6) becomes:
    # 
    #   ⃗𝐟(x) - f(x₀) = A⋅( ⃗𝐱 - x₀) + B⋅ ⃗𝐉(x)
    #
    # ⟹ ⃗𝐟(x) = A⋅( ⃗𝐱 - x₀) + B⋅ ⃗𝐉(x) + f(x₀)                                 (8)
    #   ⃗𝐟(x) = A⋅ ⃗𝛏 + B⋅ ⃗𝐉(x) + f(x₀)                                       (8a)
    #
    # • The minimization problem: find A, B for the global minimum of (9) below:
    #
    #           ₙ₋₁
    #   Σ( ⃗𝛜²) = Σ(εₖ)² = Σ[( ⃗𝐟 (x) -  ⃗𝐲)²]                                  (9)
    #           ᵏ⁼⁰
    # Assuming f(x₀) = y₀, (9) becomes:
    #
    #   Σ( ⃗𝛜² ) = Σ[(A⋅( ⃗𝐱 - x₀)    + B⋅ ⃗𝐉(x) + y₀ -  ⃗𝐲 )²]
    #
    #           = Σ[(A⋅( ⃗𝐱 - x₀)    + B⋅ ⃗𝐉(x) - ( ⃗𝐲 -y₀) )²]                (10)
    #           = Σ[(A⋅ ⃗𝛏 + B⋅ ⃗𝐉(x) -  ⃗𝛄 )²]                               (10a)
    #             with  ⃗𝛏 =  ⃗𝐱 - x₀ and  ⃗𝛄  =  ⃗𝐲 - y₀
    #
    # The approach in skg.exp.exp_fit is to treat (10) as a system of linear 
    # equations:
    #
    #   Σ[(A⋅( ⃗𝐱 - x₀) + B⋅ ⃗𝐈 (x) - ( ⃗𝐲 -y₀))²] = 0, i.e.:
    #   Σ[(A⋅ ⃗𝛏 + B⋅ ⃗𝐈(x) -  ⃗𝛄)²] = 0
    #
    # of the form  ⃗𝐯 ⋅ 𝐌 =  ⃗𝛄 and "solve" it (``linalg.lstsq``)
    #
    # The matrix 𝐌 is the 𝒏 × 2 matrix [ ⃗𝐱 - x₀   ⃗𝐈(x) ] = [ ⃗𝛏   ⃗𝐈(x)], 
    #           where 𝒏 is the cardinality of  ⃗𝐲  (same as that of  ⃗𝐱 )
    # ⃗𝐯 is the "solution" vector [A B], with A = -ac and B = c,
    #
    # Step 1: calculating a and c:
    #
    #     ⃗𝐯       ×             𝐌              =       ⃗𝛄 :
    #                ⎵                      ⎵     ⎵          ⎵ 
    #               |  x₀   - x₀     I(x₀)   |   |  y₀ - y₀   |
    #   ⎵      ⎵    |  x₁   - x₀     I(x₁)   | = |  y₁ - y₀   |
    #  |  A  B  | × |      ⋮           ⋮     |   |     ⋮      |
    #   ⎴      ⎴    |      ⋮           ⋮     |   |     ⋮      |
    #               |  xₙ₋₁ - x₀     I(xₙ₋₁) |   |  yₙ₋₁ - y₀ |
    #                ⎴                      ⎴     ⎴          ⎴ 
    # i.e.,:
    #                ⎵             ⎵     ⎵     ⎵ 
    #               |  ξ₀   I(x₀)   |   |  γ₀   |
    #   ⎵      ⎵    |  ξ₁   I(x₁)   | = |  γ₁   |
    #  |  A  B  | × |  ⋮    ⋮       |   |  ⋮    |
    #   ⎴      ⎴    |  ⋮    ⋮       |   |  ⋮    |
    #               |  ξₙ₋₁ I(xₙ₋₁) |   |  γₙ₋₁ |
    #                ⎴             ⎴     ⎴     ⎴ 
    # thus, "solving"  ⃗𝐯 = 𝐌⁻¹ ×  ⃗𝐘:
    #
    #     ⃗𝐯       =         𝐌⁻¹       ×     ⃗𝛄 :
    #
    #                ⎵             ⎵ ⁻¹  ⎵     ⎵ 
    #               |  ξ₀   I(x₀)   |   |  γ₀   |
    #   ⎵      ⎵    |  ξ₁   I(x₁)   | × |  γ₁   |
    #  |  A  B  | × |  ⋮    ⋮       |   |  ⋮    |
    #   ⎴      ⎴    |  ⋮    ⋮       |   |  ⋮    |
    #               |  ξₙ₋₁ I(xₙ₋₁) |   |  γₙ₋₁ |
    #                ⎴             ⎴     ⎴     ⎴ 
    #
    # is followed by calculating a, c from  ⃗𝐯  using (7)
    #
    # Step 2: calculate b from a second system of equations obtained by 
    # replacing c in (1):
    #
    # Again, this yields the following linear regression:
    #
    #  ₙ₋₁                       ₙ₋₁
    #   Σ(εₖ)² = Σ( ⃗𝐟(x) -  ⃗𝐲)² = Σ(a+b⋅exp(c⋅xₖ) - yₖ)²                    (11)
    #  ᵏ⁼⁰                       ᵏ⁼⁰
    #
    # In (11) let:
    #
    #   ⃗𝛉(x) = exp(c ⃗𝐱)                                                     (12)
    #
    # Then (11) becomes:
    #
    #  ₙ₋₁       ₙ₋₁                    ₙ₋₁    
    #   Σ(εₖ)² =  Σ(a + b⋅θₖ - yₖ)²  =   Σ(a⋅1 + b⋅θₖ - yₖ)²                (13)
    #  ᵏ⁼⁰       ᵏ⁼⁰                    ᵏ⁼⁰    
    #
    #  Which is also treated as a system of linear equations:
    #
    #      ⃗𝐰₁     ×      𝐌       =     ⃗𝐲 :
    #                ⎵        ⎵     ⎵     ⎵ 
    #               |  1₀ θ₀   |   |  y₀   |
    #   ⎵      ⎵    |  1₁ θ₁   | = |  y₁   |
    #  |  a  b  | × |  ⋮  ⋮    |   |  ⋮    |
    #   ⎴      ⎴    |  ⋮  ⋮    |   |  ⋮    |
    #               |  1  θₙ₋₁ |   |  yₙ₋₁ |
    #                ⎴        ⎴    ⎴     ⎴ 
    #
    #  Solution: 
    #      ⃗𝐰₁     =      𝐌⁻¹     ×     ⃗𝐲 :
    #
    #                ⎵        ⎵⁻¹   ⎵     ⎵ 
    #               |  1₀ θ₀   |   |  y₀   |
    #   ⎵      ⎵    |  1₁ θ₁   | × |  y₁   |
    #  |  a  b  | = |  ⋮  ⋮    |   |  ⋮    |
    #   ⎴      ⎴    |  ⋮  ⋮    |   |  ⋮    |
    #               |  1  θₙ₋₁ |   |  yₙ₋₁ |
    #                ⎴        ⎴     ⎴     ⎴ 
    #
    # And the function returns (a, b, c) with a,b from Step 2 and c from Step 1
    # ∎
    # ### END   NOTE: What the original scikit-guess exp.exp_fit() function does:
    #
    # ### BEGIN NOTE: THIS function uses the normal equtions method of Jacquelin:
    #
    # Step 1: find out a, c
    # ---------------------
    #
    # In equation (10b) above:
    #           ₙ₋₁
    #   Σ( ⃗𝛜²) = Σ([(A⋅ ⃗𝛏 + B⋅ ⃗𝐈(x) -  ⃗𝛄 )²]
    #           ᵏ⁼⁰
    #
    # can be rewritten as
    #           ₙ₋₁
    #   Σ( ⃗𝛜²) = Σ(εₖ)² = Σ[( ⃗𝐠(x) -  ⃗𝛄)²]                                  (14)
    #           ᵏ⁼⁰
    #
    # where  ⃗𝐠(x)  = A⋅ ⃗𝛏 + B⋅ ⃗𝐈(x)
    #
    # Eq (14) is regarded as argmin ⃗𝛜(x) = ||𝐌⋅ ⃗𝐯 - 𝚪||₂, where  ⃗𝐯 is the 
    # "solution" vector, and 𝚪 is the matrix [  ⃗𝛄 ].
    #
    # ∴  ⃗𝛜(x) = (𝐌⋅ ⃗𝐯 - 𝚪)ᵀ(𝐌⋅ ⃗𝐯 - 𝚪)                                       (15)
    #
    # By the normal equations theorem: ∇ ⃗𝛜(x) = 2𝐌ᵀ𝐌⋅ ⃗𝐯  - 2𝐌ᵀ⋅𝚪
    #
    # At the global mimimum, ∇ ⃗𝛜(x) = 0
    #
    # ∴ 𝐌ᵀ𝐌⋅ ⃗𝐯  = 𝐌ᵀ⋅𝚪                                                      (16)
    #
    #  𝐌 is the matrix [ ⃗𝛏   ⃗𝐬 ], where  ⃗𝛏 and ⃗𝐬  are as above
    #  ⃗𝐯 is the solution vector [A B] with A, B as in (7)
    #
    #                 ₙ₋₁
    # With Σ(⋅) being  Σ(⋅), ⃗𝐯 being [A, B]ᵀ and by definition of the dot product:
    #                 ᵏ⁼⁰
    #
    #  ⃗𝐚⋅ ⃗𝐚 = Σ(aₖ²)
    #         ᵏ
    #  ⃗𝐚⋅ ⃗𝐛 = Σ(aₖbₖ)
    #         ᵏ
    #            𝐌ᵀ   ×      𝐌
    #          ⎵   ⎵                  ⎵               ⎵     ⎵               ⎵
    #         |  ⃗𝛏  |                |  ⃗𝛏 ⋅ ⃗𝛏   ⃗𝛏 ⋅ ⃗𝐬  |   | Σ(ξₖ²)  Σ(ξₖsₖ) |
    #   𝐌ᵀ𝐌 = |     | ×  [ ⃗𝛏   ⃗𝐬 ] = |                 | = |                 |
    #         |  ⃗𝐬  |                |  ⃗𝐬 ⋅ ⃗𝛏   ⃗𝐬 ⋅ ⃗𝐬  |   | Σ(ξₖsₖ) Σ(sₖ²)  |
    #          ⎴   ⎴                  ⎴               ⎴     ⎴               ⎴
    #
    #  
    #            𝐌ᵀ   ×  𝚪
    #          ⎵   ⎵             ⎵       ⎵     ⎵       ⎵
    #         |  ⃗𝛏  |           |  ⃗𝛏 ⋅ ⃗𝛄  |   | Σ(ξₖγₖ) |
    #   𝐌ᵀ𝚪 = |     | × [ ⃗𝛄 ] = |         | = |         |
    #         |  ⃗𝐬  |           |  ⃗𝐬 ⋅ ⃗𝛄  |   | Σ(sₖγₖ) |
    #          ⎴   ⎴             ⎴       ⎴     ⎴       ⎴
    # and 
    #          ⎵ ⎵
    #         | A |
    #    ⃗𝐯  = |   |
    #         | B |
    #          ⎴ ⎴
    # ∴ (15) can be written as:
    #
    #         𝐌ᵀ𝐌         ×   ⃗𝐯   =     𝐌ᵀ𝚪 
    #  ⎵               ⎵     ⎵ ⎵     ⎵       ⎵
    # | Σ(ξₖ²)  Σ(ξₖsₖ) |   | A |   | Σ(ξₖγₖ) |
    # |                 | × |   | = |         |                             (17)
    # | Σ(ξₖsₖ) Σ(sₖ²)  |   | B |   | Σ(sₖγₖ) |
    #  ⎴               ⎴     ⎴ ⎴     ⎴       ⎴
    # Solving for  ⃗𝐯  as above yields a, c
    #
    # Step 2: find out b
    # ------------------
    #
    # This applies the normal equation method again:
    #
    # Reqrite eq (13) as
    #
    #           ₙ₋₁
    #   Σ( ⃗𝛜²) = Σ(εₖ)² = Σ[( ⃗𝐠(x) -  ⃗𝐲)²]                                  (18)
    #           ᵏ⁼⁰
    # with
    #   ⃗𝐠(x) = a + b⋅ ⃗𝛉  = a⋅ ⃗𝐈  + b⋅ ⃗𝛉 ,
    #   ⃗𝛉 = exp(c⋅ ⃗𝐱 )
    #   ⃗𝐈 the unit vector: I[k] = 1, k = 0 … n-1
    #
    # Let  ⃗𝐰 the "solution" vector [a b] at the global minimum of (18)
    # 
    # ∴ (16) becomes
    #
    #            𝐌ᵀ   ×      𝐌
    #          ⎵   ⎵                  ⎵               ⎵     ⎵            ⎵
    #         |  ⃗𝐈  |                |  ⃗𝐈 ⋅ ⃗𝐈   ⃗𝐈 ⋅ ⃗𝛉  |   | 𝒏     Σ(θₖ)  |
    #   𝐌ᵀ𝐌 = |     | ×  [ ⃗𝐈   ⃗𝛉 ] = |                 | = |              | (19)
    #         |  ⃗𝛉  |                |  ⃗𝛉 ⋅ ⃗𝐈   ⃗𝛉 ⋅ ⃗𝛉  |   | Σ(θₖ) Σ(θₖ²) |
    #          ⎴   ⎴                  ⎴               ⎴     ⎴            ⎴
    #
    # remember:
    #  1. the dot product of a unit vector with another vector is the sum of 
    #     the elements of the 'other' vector
    #  2. ∴ the dot product of a unit vector with itself is its cardinality
    #  
    #            𝐌ᵀ   ×  𝚪
    #          ⎵   ⎵             ⎵       ⎵     ⎵       ⎵
    #         |  ⃗𝐈  |           |  ⃗𝐈 ⋅ ⃗𝐲  |   | Σ(yₖ)   |
    #   𝐌ᵀ𝚪 = |     | × [ ⃗𝐲 ] = |         | = |         |                   (20)
    #         |  ⃗𝛉  |           |  ⃗𝛉 ⋅ ⃗𝐲  |   | Σ(θₖyₖ) |
    #          ⎴   ⎴             ⎴       ⎴     ⎴       ⎴
    # and 
    #          ⎵ ⎵
    #         | a |
    #    ⃗𝐰  = |   |                                                         (21)
    #         | b |
    #          ⎴ ⎴
    # And now, the linear regression is 𝐌ᵀ𝐌 ×  ⃗𝐰  = 𝐌ᵀ𝚪 
    #
    #  ⎵            ⎵     ⎵ ⎵     ⎵       ⎵
    # | 𝒏     Σ(θₖ)  |   | a |   | Σ(yₖ)   |
    # |              | × |   | = |         |                                (22)
    # | Σ(θₖ) Σ(θₖ²) |   | a |   | Σ(θₖyₖ) |
    #  ⎴            ⎴     ⎴ ⎴     ⎴       ⎴
    # ### END   NOTE: What THIS function does:
    x, y = skg_preprocess(x, y, is_sorted)
    
    # ### BEGIN Step 1
    #
    s = np.zeros(y.shape)      #  ⃗𝐬 
    s[1:] = np.cumsum(0.5 * np.diff(x)*(y[1:] + y[:-1]))
    
    ξ = x-x[0]                 #  ⃗𝛏 
    γ = y-y[0]                 #  ⃗𝛄 
    
    ξs = np.dot(ξ, s)          # Σ(ξₖ⋅sₖ) = Σ(ξₖsₖ)
    γξ = np.dot(γ, ξ)          # Σ(γₖ⋅ξₖ) = Σ(ξₖγₖ)
    γs = np.dot(γ, s)          # Σ(γₖ⋅sₖ) = Σ(sₖγₖ)
    
    𝐌ᵀM = np.zeros((2,2))      # See eq (17) (Eq 11 in Jacquelin obtained 
                               # through the normal equation method)
                               
    𝐌ᵀM[0,0] = np.dot(ξ, ξ)    # Σ(ξₖ²)
    𝐌ᵀM[0,1] = ξs              # Σ(ξₖ⋅sₖ)
    𝐌ᵀM[1,0] = ξs              # Σ(ξₖ⋅sₖ) = Σ(sₖ⋅ξₖ)
    𝐌ᵀM[1,1] = np.dot(s, s)    # Σ(sₖ²)
    
    𝐌ᵀΓ = np.array([γξ, γs])
    
    𝐯 = np.dot(np.linalg.pinv(𝐌ᵀM), 𝐌ᵀΓ)
    a, c = -𝐯[0]/𝐯[1], 𝐯[1]
    
    #
    # ### END   Step 1
    
    # ### BEGIN Step 2
    #
    n = y.shape[0]
    θ = np.exp(c*x)
    Σθ = np.sum(θ)                            # Σ(θₖ)
    𝐌ᵀM[0,0] = n
    𝐌ᵀM[0,1] = Σθ
    𝐌ᵀM[1,0] = Σθ
    𝐌ᵀM[1,1] = np.dot(θ, θ)                     # Σ(θₖ²)
    
    𝐌ᵀΓ = np.array([np.sum(y), np.dot(y,θ)])    # Σ(yₖ) Σ(yₖ⋅θₖ)    see (20)
    
    a, b = np.dot(np.linalg.pinv(𝐌ᵀM), 𝐌ᵀΓ)     # NOTE: unpack "solution"  ⃗𝐰  directly
    #
    # ### END   Step 2

    return (a, b, c)
    
def skg_preprocess(x,y, is_sorted=True):
    r"""skg._util.skg_preprocess copied shamelessly here"""

    x = np.asfarray(x).ravel()
    y = np.asfarray(y).ravel()
    
    assert x.shape == y.shape, "Vectors must have the same size"
    
    if not is_sorted:
        ind = np.argsort(x)
        x = x[ind]
        y = y[ind]
        
    return x, y
