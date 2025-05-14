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
import os, sys, traceback, warnings, numbers, collections, typing
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
    
    A tuple: (fitted curve, collections.OrderedDict) where:
    
    • fitted curve is the realization of the model in `func` using the fitted 
        parameters and the independent variable `x`
    
    • the OrderedDict has the following keys:
    
        Model           ↦ `func` module.name
        Fit             ↦ the fit result output by scipy.optimize.least_squares
        Coefficients    ↦ a tuple with fitted model parameter values
        Rsq             ↦ R² correlation coefficient between the fitted curve 
                         and the `data`
    
    
    """
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
    
    def __cost_fun__(x0, t, y):  # returns residuals
        yf = func(t, x0, **fkwargs)
        ret = y-yf
        
        return ret
    
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

    fC = func(xdata, res_x, *fargs, **fkwargs)
    
    sst = np.sum( (ydata - ydata.mean()) ** 2.) # sum of squares about the mean in the data (total sum of squares)
    
    sse = np.sum((fC - ydata) ** 2.) # sum of squared errors (sum of squared residuals, Sum of Squares Due to Error)
    
    # Coefficient of determination R² for the entire fit
    rsq = 1 - sse/sst # only one R²
    
    df_res = fC.size - len(x0)
    df_tot = fC.size - 1
    
    arsq = 1 - sse * df_tot / (sst * df_res)
    
    rmse = np.sqrt(sse/fC.size)
    
    
    result = collections.OrderedDict()
    result["Model"] = f"{func.__module__}.{func.__name__}"
    result["Fit"] = res
    result["Coefficients"] = res_x
    result["InitialCoefficients"] = {"values": x0, "bounds": bounds}
    result["Coefficient Names"] = coeff_names
    result["GoF"] = dict()
    result["GoF"]["Rsq"] = rsq
    result["GoF"]["R2adj"] = arsq
    result["GoF"]["SSE"] = sse
    result["GoF"]["RMSE"] = rmse
    
    initialSupport = np.full((data.shape[0],), np.NaN)
    
    fittedCurve = initialSupport.copy()
    
    fittedCurve[realDataNdx] = fC
    
    return fittedCurve, result

def guess_init_two_exp_sum(x:np.ndarray, y:np.ndarray, is_sorted:bool=True):
    r"""y ( x ) = a + b exp( p x ) + c exp( q x)
    Returns:
    WARNING: Work in progress, DO NOT USE
    ========
    4-tuple: (a, b, p, c, q)
    """
    # 4-tuple: (b, p, c, q)
    x,y = skg_preprocess(x,y,is_sorted)
    # ### params to optimize: b, p, c, q
    # ### params to optimize: a, b, p, c, q NOTE: 2025-05-12 10:07:03 - Lecca … Scarpa (2021) Math Meth Appl Sci 44: 10154 — 10171
    
    # see NOTE: 2025-05-12 10:07:03
    # ###  ⃗θ = (a, b, c, p, q)
    # ### y( ⃗θ;t ) = A⋅SS(t) + B⋅S(t) + C⋅t + D = a + b⋅exp(pt) + c⋅exp(qt)
    # ### with A = pq; B = (p+q)
    #
    # ### but in Jacquelin's Double exponential regression paper:
    # ### y(b, p, c, q; t) = -A⋅SS(t) + B⋅S(t) + C⋅t + D = b⋅exp(pt) + c⋅exp(qt)
    # ### with A = -pq; B = -(p+q) !!!
    
    #                    ₙ₋₁
    # all sums below are  Σ ⋅
    #                    ⁱ⁼⁰
    
    # also, REMEMBER in numpy x @ y is np.dot(x,y) whebn both x, y are 1D vectors of compatible shapes
    S = np.zeros(y.shape)
    S[1:] = np.cumsum(0.5* np.diff(x) * (y[1:] + y[:-1])) # mid-point approximation (mid-point rule less error term f``(0.5*(xₖ - xₖ₋₁))(xₖ - xₖ₋₁)³/24)
    
    S2 = np.zeros(y.shape)          # SS in Lecca et al, and in Jacquelin
    S2[1:] = np.cumsum(0.5* np.diff(x) * (S[1:] + S[:-1]))
    
    xx   = x  * x
    S2S2 = np.dot(S2, S2)            # Σ(S2ᵢ*S2ᵢ)    = Σ(S2ᵢ²)
    S2S  = np.dot(S2, S)             # Σ(S2ᵢ*Sᵢ) 
    S2x  = np.dot(S2, x)             # Σ(S2ᵢ*xᵢ)
    S2x2 = np.dot(S2, x**2)          # Σ(S2ᵢ*xᵢ²)    Lecca et al 2021
    S2y  = np.dot(S2, y)             # Σ(S2ᵢ*yᵢ)
    SS   = np.dot(S, S)              # Σ(Sᵢ²)
    Sx   = np.dot(S, x)              # Σ(Sᵢ*xᵢ)    
    Sx2  = np.dot(S, xx)             # Σ(Sᵢ*xᵢ²)     Lecca et al 2021
    Sy   = np.dot(S, y)              # Σ(Sᵢ*yᵢ)
    Σx2  = np.dot(x, x)              # Σ(xᵢ²)        Lecca et al 2021
    Σx3  = np.dot(xx, x)             # Σ(xᵢ³)        Lecca et al 2021
    Σx4  = np.dot(xx, xx)            # Σ(xᵢ⁴)        Lecca et al 2021
    xy   = np.dot(x, y)              # Σ(xᵢ*yᵢ) = np.dot(x, y)
    x2y  = np.dot(xx, y)             # Σ(xᵢ² * yᵢ)   Lecca et al 2021
    ΣS   = S.sum()                   # Σ(Sᵢ)
    ΣS2  = S2.sum()                  # Σ(S2ᵢ)
    Σx   = x.sum()                   # Σ(xᵢ)
    Σy   = y.sum()                   # Σ(yᵢ)
    n    = x.shape[0]                # 
    
    # ### implementation of Lecca et al 2021 algorithm
    
    M = np.zeros((5,5)) # includes additive "bias"
    
                                                            #  _  NOTE: 𝑡 in Lecca is here 𝑥;                              ̅ 
    M[0,:] = [S2S2,     S2S,    S2x2,   S2x,    ΣS2]        # | Σ(Sᵢ2²)      Σ(S2ᵢ*Sᵢ)    Σ(Sᵢ2*xᵢ²)   Σ(S2ᵢ*Sᵢ)     Σ(S2ᵢ) |           
    M[1,:] = [S2S,      SS,     Sx2,    Sx,     ΣS]         # | Σ(S2ᵢ*Sᵢ)    Σ(Sᵢ²)       Σ(Sᵢ*xᵢ²)    Σ(Sᵢ*xᵢ)      Σ(Sᵢ)  |
    M[2,:] = [S2x2,     Sx2,    Σx4,    Σx3,    Σx2]        # | Σ(S2ᵢ*xᵢ²)   Σ(Sᵢ*xᵢ²)    Σ(xᵢ⁴)       Σ(xᵢ³)        Σ(xᵢ²) |
    M[3,:] = [S2x,      Sx,     Σx3,    Σx2,    Σx]         # | Σ(S2ᵢ*xᵢ)    Σ(Sᵢ*xᵢ)     Σ(xᵢ³)       Σ(xᵢ²)        Σ(xᵢ)  |
    M[4,:] = [ΣS2,      ΣS,     Σx2,    Σx,     n]          # | Σ(S2ᵢ)       Σ(Sᵢ)        Σ(xᵢ²)       Σ(xᵢ)         n      |
                                                            #  ̅                                                            ̅ 
    
    Y = np.array([S2y,  Sy,     x2y,    Σx2,    Σy])
    
    return (M, Y)
    
    (A, B, C, D, E), *_ = linalg.lstsq(M, Y, overwrite_a = True, overwrite_b = False)
    
    print(f"A = {A}, B = {B}, C = {C}, D = {D}")
    
    sqB2A = np.sqrt(B**2 + 4*A)

    p = 0.5 * (B + sqB2A)
    q = 0.5 * (B - sqB2A)
    
    print(f"p = {p}, q = {q}")
    
    β = np.exp(p*x)
    η = np.exp(q*x)
    
    print(β, η)
    
    Σβ = β.sum()                            # Σ(βᵢ)
    Ση = η.sum()                            # Σ(ηᵢ)
    Σβη = β @ η         # np.dot(β, η)      # Σ(βᵢ * ηᵢ)
    Σβ2 = β @ β         # np.dot(β, β)      # Σ(βᵢ * βᵢ)
    Ση2 = η @ η         # np.dot(η, η)      # Σ(ηᵢ * ηᵢ)
    Σβy = β @ y         # np.dot(β, y)      # Σ(βᵢ * yᵢ)
    Σηy = η @ y         # np.dot(η, y)      # Σ(ηᵢ * yᵢ)
    
    Q = np.zeros((3,3))
    Q[0,:] = [n,  Σβ,  Ση]
    Q[1,:] = [Σβ, Σβ2, Σβη]
    Q[2,:] = [Ση, Σβη, Ση2]
    
    V = np.array([Σy, Σβy, Σηy])
    
    (a, b, c), *_ = linalg.lstsq(Q, V, overwrite_a = True, overwrite_b = False)
    
    return (a, b, p, c, q)
    
def guess_init_two_exp_sum_J(x:np.ndarray, y:np.ndarray, is_sorted:bool=True):
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
    # ### BEGIN crude implementation of Jacquelin
    #
    x,y = skg_preprocess(x,y,is_sorted)
    
    S = np.zeros(y.shape)
    S[1:] = np.cumsum(0.5* np.diff(x) * (y[1:] + y[:-1])) # mid-point approximation (mid-point rule less error term f``(0.5*(xₖ - xₖ₋₁))(xₖ - xₖ₋₁)³/24)
    
    S2 = np.zeros(y.shape)          # SS in Lecca et al, and in Jacquelin
    S2[1:] = np.cumsum(0.5* np.diff(x) * (S[1:] + S[:-1]))
    
    S2S2  = np.dot(S2, S2)      # ΣSSₖ²
    S2S   = np.dot(S2, S)       # ΣSSₖSₖ
    S2x   = np.dot(S2, x)       # ΣSSₖxₖ
    S2y   = np.dot(S2, y)       # ΣSSₖyₖ
    S2sum = S2.sum()            # ΣSSₖ
    SS    = np.dot(S, S)        # ΣSₖ²
    Sx    = np.dot(S, x)        # ΣSₖxₖ
    Sy    = np.dot(S, y)        # ΣSₖyₖ
    Ssum  = S.sum()             # ΣSₖ
    xx    = np.dot(x, x)        # Σxₖ²
    xsum  = x.sum()             # Σxₖ
    xy    = np.dot(x, y)        # Σxₖyₖ
    ysum  = y.sum()             # Σyₖ
    n     = y.shape[0]          # card(y) cardinality
    
    #               M                    soln        ⃗Y 
    #  ⎵                           ⎵     ⎵ ⎵     ⎵      ⎵
    # |  ΣSSₖ²  ΣSSₖSₖ  ΣSSₖxₖ ΣSSₖ |   | A |   | ΣSSₖyₖ |
    # |  ΣSSₖSₖ ΣSₖ²    ΣSₖxₖ  ΣSₖ  | × | B | = | ΣSₖyₖ  |
    # |  ΣSSₖxₖ ΣSₖxₖ   Σxₖ²   Σxₖ  |   | C |   | Σxₖyₖ  |
    # |  ΣSSₖ   ΣSₖ     Σxₖ    n    |   | D |   | Σyₖ    |
    #  ⎴                           ⎴     ⎴ ⎴     ⎴      ⎴
    
    
    M = np.zeros((4, 4))
    
    M[0,:] = [S2S2,  S2S,  S2x,  S2sum]
    M[1,:] = [S2S,   SS,   Sx,   Ssum ]
    M[2,:] = [S2x,   Sx,   xx,   xsum ]
    M[3,:] = [S2sum, Ssum, xsum, n    ]
    
    Y = np.array([S2y, Sy, xy, ysum])
    
    # (A, B, C, D), *_ = linalg.lstsq(M, Y, overwrite_a=True, overwrite_b = False)
    A, B, C, D = np.dot(np.linalg.pinv(M), Y)
    
    B2A = B**2 + 4*A
    
    p = 0.5 * (B + np.sqrt(B2A))
    q = 0.5 * (B - np.sqrt(B2A))

    β = np.exp(p*x)
    η = np.exp(q*x)
    
    Σββ = np.dot(β, β)
    Σβη = np.dot(β, η)
    Σηη = np.dot(η, η)
    Σβy = np.dot(β, y)
    Σηy = np.dot(η, y)
    M = M[:2,:2]
    M[0,:] = [Σββ, Σβη]
    M[1,:] = [Σβη, Σηη]
    
    Γ = np.array([Σβy, Σηy])
    
    # (b, c), *_ = linalg.lstsq(M, Γ, overwrite_a=True, overwrite_b = False)
    
    b, c = np.dot(np.linalg.pinv(M), Γ)#, overwrite_a=True, overwrite_b = False)
    
    return (b, c, p, q, A, B, C, D)
    #
    # ### END   crude implementation of Jacquelin
    
    M = np.empty(y.shape + (4, ))
    M[:,3] = 1.
    M[:,2] = x
    M[0,:2] = 0
    M[1:,1] = np.cumsum(0.5* np.diff(x) * (y[1:] + y[:-1]))
    M[0,0] = 0.                   
    M[1:,0] = np.cumsum(0.5* np.diff(x) * (M[1:,1] + M[:-1,1]))
    
    (A, B, C, D), *_ = linalg.lstsq(M, y, overwrite_a=True, overwrite_b = False)
    
    B2A = B**2 + 4*A
    
    p = 0.5 * (B + np.sqrt(B2A))
    q = 0.5 * (B - np.sqrt(B2A))
    
    M = M[:,:2]
    M[:,0] = np.exp(p * x)
    M[:,1] = np.exp(q * x)
    
    exp_p = np.exp(p * x)
    exp_q = np.exp(p * x)
    
    (b, c), *_ = linalg.lstsq(M, y, overwrite_a=True, overwrite_b = False)
    
    return (b, c, p, q)

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
    
    # ### BEGIN snippet of skg.exp.exp_fit for one exponential
    # ### BEGIN explanation for dummies (like myself)
    # ### Remember:
    # ### in Jacquelin's paper the definite integral (∫ˣₓ₁,) x₁ is actually x[0]
    # ### 
    # ### eq 6 is the clincher: 
    # ### 
    # ### y - (a + b⋅exp(cx₁)) = -a⋅c(x-x₁) + c ⋅ ∫ˣₓ₁ y(u)du  i.e.:
    # ### y - (a + b⋅exp(cx₁)) = -a⋅c(x-x₁) + c ⋅ S
    # ### 
    # ### where a + b⋅exp(cx₁) = y₁ = y[0]
    # ### 
    # ### with x₁ = x[0] ⟹ a + b⋅exp(cx[0]) = y[0], hence:
    # ### 
    # ### y - y[0] = -a⋅c(x-x[0]) + c ⋅ Sₖ, with Sₖ the numeric integral (eq 7):
    # ### 
    # ###                               S₀ = 0 for k == 0
    # ###                               Sₖ = Sₖ₋₁ + 1/2 (yₖ + yₖ₋₁) (xₖ - xₖ₋₁) for k ∈ [1…n-1]
    # ### 
    # ### NOTE for below: let A = -ac, let B = c
    # ### 
    # ### y - y[0] = -a⋅c(x-x[0]) + c ⋅ Sₖ, with Sₖ the numeric integral (eq 7):
    # ### 
    # ### eq 9:
    # ###
    # ### Σⁿₖ₌₁ ε²ₖ = Σⁿₖ₌₁ (yₖ - y₁)² = Σⁿₖ₌₁ (A(xₖ - x₁) + BSₖ - (yₖ - y₁))² ↝ 0
    # ### 
    # ### becomes
    # ### 
    # ### Σⁿ⁻¹ₖ₌₀ ε²ₖ = Σⁿ⁻¹ₖ₌₀ (A(xₖ - x₀) + BSₖ - (yₖ - y₀))², with the A(⋯) and BSₖ terms in matrix M, and the (yₖ - y₀) term in vector Y
    # ###
    # ### The condition is to minimize ε i.e. Σⁿ⁻¹ₖ₌₀ ε²ₖ = 0 ⟹
    # ###
    # ### (yₖ - y₁) = A(xₖ - x₁) + BSₖ ≡ (y - y[0]) = A(x - x[0]) + BSₖ ≡
    # ###                              ≡ 𝐘 = 𝐀𝒙 + BSₖ 
    # ### For each 𝒙 we have:
    # ### 
    # ###   Ax + Bs = y ⇒ a system of 𝒏 linear equation (one for each xₖ, yₖ sample pairs)
    # ### 
    # ###  In matrix form: NOTE: here the "unknowns" are A and B (the "variables")
    # ###   and the "coefficients" — "constants" are 
    # ### 
    # ###   𝒙 and 𝒔 on the lhs, and 𝒚 on the rhs
    # ### 
    # ###  albeit transorfmed as above: 𝒙 = x - x[0], 𝒚 = y - y[0], ans 𝒔 calculated as Sₖ above
    # ###           
    # ###          𝐌             coeffs         𝐘
    # ###    _              _                      
    # ###   |  x₀,    s₀     |    _   _     ⎴  y₀,  ⎴
    # ###   |  x₁,    s₁     |   |  A  |    |  y₁,   |
    # ###   |  x₂,    s₂     | ⋅ |     | =  |  y₂,   |
    # ###   |  ⋮,     ⋮      |   |  B  |    |  ⋮,    |
    # ###   |  xₙ₋₁,  sₙ₋₁   |   -    -     |  yₙ₋₁, |
    # ###    -               -               ⎵      ⎵
    # ### 
    # ###   The solution is:
    # ###               _              _ (-1)    _      _
    # ###    _   _     |  x₀,    s₀     |       |  y₀,   |
    # ###   |  A  |    |  x₁,    s₁     |       |  y₁,   |
    # ###   |     | =  |  x₂,    s₂     |   ⋅   |  y₂,   |
    # ###   |  B  |    |  ⋮,     ⋮      |       |  ⋮,    |
    # ###   -    -     |  xₙ₋₁,  sₙ₋₁   |       |  yₙ₋₁, |
    # ###              -               -        -       -
    # ###  i.e.:
    # ### 
    # ###  coeffs = (A,B) = 𝐌⁻¹ ⋅ 𝐘 = inv(𝐌) * 𝐘    NOTE: coeffs is a two-vector of floats: (A, B)
    # ### 
    # ### ⟹ (A,B) = lstsq(𝐌, 𝐘)
    # ###
    # ### fill up the matrix 𝐌 with
    # ### 
    # ### Column 0: xₖ - x₀ (the <<factor>> of A)       Column 1: Sₖ (the <<factor>> of B)
    # ###                                               Sₖ = Sₖ₋₁ + 1/2 (yₖ + yₖ₋₁) (xₖ - xₖ₋₁) eq 7 in Jacquelin's paper
    # ###
    # ### 0                                             0                                           # S₀ = 0
    # ### x[1] - x[0]                                   ((x[1] - x[0]) * (y[1] + y[0]))/2 + 0       # S₀ + 1/2 (y₁ + y₀) (x₁ - x₀)
    # ### x[2] - x[0]                                   ((x[2] - x[1]) * (y[2] + y[1]))/2 + 
    # ###                                               ((x[1] - x[0]) * (y[1] + y[0]))/2 + 0       # S₁ + 1/2 (y₂ + y₁) (x₂ - x₁)
    # ### ⋮                                             
    # ### x[-1] - x[0]                                  cumsum(0.5 * diff(x) * (y[1:] + y[:-1]))
    # ###
    # ### i.e.
    # ### Column 0:                                     Column 1:
    # ### x - x[0]                                      cumsum(0.5 * diff(x) * (y[1:] + y[:-1]))
    # ###
    # ### and the 𝐘 vector is y - y[0]
    # ###
    # ### END   explanation for dummies

    # ### Step 1: find out the A = "-ac" and B = "c" coefficients
    
    # M = empty(y.shape + (2,), dtype=y.dtype)
    # subtract(x, x[0], out=M[:, 0])                                    # ### place x-x[0] in 1st column, see above
    # M[0, 1] = 0                                                       # ### place Sₖ     in 2nd column, see above
    # cumsum(0.5 * diff(x) * (y[1:] + y[:-1]), out=M[1:, 1])            # ### set M[0,1] to 0 because S[0] = 0, see above
    # 
    # Y = y - y[0]                                                      # ### the 𝐘 vector
    # 
    # ### This is scipy.linalg.lstsq: computes least-squares solution to Ax = b
    # ### i.e., solution is x such that |b - Ax| is minimized
    # ### function syntax (basic): x = lstsq(A, b)
    # ### 'A' (the 'lhs') here is M; 'b' (the 'rhs') here is Y
    # (A, B), *_ = lstsq(M, Y, overwrite_a=True, overwrite_b=True)      # ### solve for A, B
    # 
    # a, c = -A / B, B                                                  # ### calculate coefficients a, c
    # 
    #
    # ### Step 2: find out the "b" coefficient and the new "a"
    #
    # M[:, 0].fill(1.0)
    # exp(c * x, out=M[:, 1])
    # 
    #
    # (a, b), *_ = lstsq(M, y, overwrite_a=True, overwrite_b=False)
    # 
    # out = array([a, b, c])
    # 
    # return out
    
    # ### END   snippet of skg.exp.exp_fit for one exponential
    
def skg_exp_fit(x, y, is_sorted=True):
    r"""implementation test skg.exp.exp_fit"""
    x, y = skg_preprocess(x, y, is_sorted)
    
    # step 1
    X = x-x[0]
    _Y = y-y[0]
    Sk = np.zeros(y.shape)
    Sk[1:] = np.cumsum(0.5 * np.diff(x)*(y[1:] + y[:-1]))
    XSk = np.dot(X, Sk)
    _YX = np.dot(_Y, X)
    _YSk = np.dot(_Y, Sk)
    M = np.zeros((2,2)) # Eq 11 in Jacquelin
    M[0,0] = np.dot(X, X)
    M[0,1] = XSk
    M[1,0] = XSk
    M[1,1] = np.dot(Sk, Sk)
    
    Y = np.array([_YX, _YSk])
    
    (A, B), *_ = linalg.lstsq(M, Y, overwrite_a=True, overwrite_b=True)
    a, c = -A/B, B
    
    # step 2
    n = y.shape[0]
    θ = np.exp(c*x)
    θsum = np.sum(θ)
    M[0,0] = n
    M[0,1] = θsum
    M[1,0] = θsum
    M[1,1] = np.dot(θ, θ)
    
    Y[0] = np.sum(y)
    Y[1] = np.dot(y,θ)
    
    (a, b), *_ = linalg.lstsq(M, Y, overwrite_a=True, overwrite_b=False)

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
