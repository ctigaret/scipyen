""" Collection of 1D and nD functions and helper functions, for use in model fitting.

WARNING: This module is on its way to deprecation, and it wil be superseded by
modelfitting.py in the (hopefully not too distant) future.

For now, stick with THIS module.

"""
import typing
import numpy as np
import quantities as pq
import numbers
from core import quantities as scq
from core.datatypes import is_vector

def check_rise_decay_params(x):
    """Returns the number of decay components for a exp-rise-multi-decay transient.
    x = iterable with model parameters (see exp_rise_multi_decay())
    """
    if np.remainder(len(x)-3, 2) != 0:
        raise ValueError("Unexpected number of elements in the parameters vector; must be 2n + 3 where n is the number of decay components; instead got %d elements" % len(parameters))
    
    return (len(x)-3) // 2

def generic_exp_decay(x, y0, α, x0, τ):
    """Realizes y = α × exp(-(x-x₀)/τ) + y₀
    
    NOTE: Python 3 only supports a subset of the unicode character set for 
    identifiers (or variable names). 
    
    For example, the following are invalid variable names: 'a₀' or 'α₀', although
    they MAY be used in documetation; on the other hand the following ARE valid:
    'a0', 'a_0', 'α0', or 'α_0'

    To insert unicode characters in variable names in Scipyen's console, use
    '\'followed by 'Tab' key (and if necessary, press 'Tab' a second time).
    
    This works as well in jupyter qtconsole, but not in plain python REPL
    """
    
    return α * np.exp(-(x-x0)/τ) + y0

def alphaFunction(x, parameters):
    """
    The Alpha function: a single exponential rise and decay, both with the same 
    time-constant (τ):
    
    y = a + b⋅(x-x₀)⋅exp(-(x-x₀)/τ)/τ if x-x₀ >= 0 and a elsewhere
    
    where:
        a  is the offset;
    
        b  is the scale;
    
        x₀ is the delay ("onset");
    
        τ  is the time constant
    
    
    Parameters:
    ===========
    x: predictor (independent variable) - 1D numpy ndarray
    
    parameters: 1D numeric sequence (tuple, list, numpy array) of four elements:
    
                a, b, x₀, τ
    
    Returns:
    ========
    1D numpy array (vector)
    
    Example: (run in Scipyen's console)
    ========
    
    from core import models
    
    x = np.linspace(0.0,1.0, 1000);
    
    parameters = [0, -1, 0.05, 0.01];
    
    y = alphaFunction(x, parameters)
    
    plt.plot(x,y)
    
    """
    
    # make sure x is a 1D array (vector)
    x = x.flatten()
    
    # unpack parameters
    a, b, x0, tau = parameters
    
    xt = (x-x0)/tau
    
    y = np.full_like(x, a)
    
    y[xt>=0] = a + b * xt[xt>=0] * np.exp(-xt[xt>=0])
    
    return y


def nsfa(x, parameters):
    """
        y = x * i - x²/N + b
    
    Parameters: i, N, b: unitary current (pA), number of channels, background current variance (pA²))
    """
    if isinstance(x, pq.Quantity):
        x = x.magnitude
        
    x = x.flatten()
    
    i, N, b = parameters
    
    y = x*i - x**2 / N + b
    
    return y
   

def Clements_Bekkers_97(x, parameters, unit_amplitude:bool=False):
    """
    Clements & Bekkers 1997 mEPSC waveform.

    This approximates a single exponential rise and decay each with their own 
    time constant:
    
    y = α + β * (1 - exp(-(x-x₀)/τ₁)) ⋅ exp(-(x-x₀)/τ₂) for x-x₀ >= 0, or α elsewhere
    
    where:
        α  = offset (usually, 0.);
    
        β  = scale;
    
        x₀ = delay ("onset") (ms);
    
        τ₁, τ₂ = time constants, respectively, for rise and decay
    
    
    Parameters:
    ============
    x: predictor (independent variable e.g., time) - 1D numpy ndarray

    parameters: 1D sequence (tuple, list, numpy array) of five float scalars:
                α, β, x₀, τ₁ and τ₂
    
                where:
                    α is considered in pA,
                    β is dimensionless,
                    x₀, τ₁ and τ₂ are considered in s
    
                and τ₁ > 0 τ₂ > 0
    
    unit_amplitude: optional, default is False
        When True, return a waveform with baseline 0 and peak value +1 , using 
        the given time constants τ₁ and τ₂
    
    Returns:
    ========
    1D numpy array (vector)
    
    
    """
    if isinstance(x, pq.Quantity):
        x = x.magnitude
        
    x = x.flatten()
    
    α, β, x0, τ1, τ2 = parameters
    
    xx = x-x0
    
    efunc       = lambda x, τ: np.exp(-x/τ)
    risefunc    = lambda x, τ: 1-efunc(x,τ)
    decayfunc   = efunc
    
    y = np.full_like(xx, 0.)
    
    
    if any(v == 0 for v in (τ2, τ2)):
        y += α
        y[xx>=0] = np.nan
    else:
        rise = risefunc(xx[xx>=0], τ1)
        decay = decayfunc(xx[xx>=0], τ2)
        
        if unit_amplitude:
            # xₘ = -τ1*np.log(τ1/(τ1+τ2))# + x0 # do NOT add x0 here because we only work on xx>=0
            # yₘ = risefunc(xₘ, τ1) * decayfunc(xₘ, τ2)
            # peak = -1. if β < 0 else 1.
            # β = peak/yₘ
            β = get_CB_scale_for_unit_amplitude(β, τ1, τ2)# + x0 # do NOT add x0 here because we only work on xx>=0
            # print(f"yₘ {yₘ}, β {β}")
            
        y[xx>=0] = β * rise * decay
        y += α
        # y[xx>=0] = α + β * (1 - np.exp(-xx[xx>=0]/τ₁)) * np.exp(-xx[xx>=0]/τ₂)
    
    return y

def get_CB_scale_for_unit_amplitude(β, τ_rise, τ_decay, x0=0.):
    efunc       = lambda x, τ: np.exp(-x/τ)
    risefunc    = lambda x, τ: 1-efunc(x,τ)
    decayfunc   = efunc
    
    xₘ = -τ_rise * np.log(τ_rise/(τ_rise + τ_decay)) + x0
    
    yₘ = risefunc(xₘ, τ_rise) * decayfunc(xₘ, τ_decay)
    peak = -1. if β < 0 else 1.
    
    return peak/yₘ
    

def exp_rise_multi_decay(x, parameters, returnDecays = False):
    """ Realization of a transient signal with a single exponential rise (r) and
        n exponential decays (d1..dn), at an onset (delay) x0 and a given 
        "DC" component (offset) o: 

        y = (1 - exp( -(x-x₀)/r ) * ( a₀     * exp( -(x-x₀)/d₀)     + 
                                      a₁     * exp( -(x-x₀)/d₁)     +
                                      .                             +
                                      .                             +
                                      aₙ₋₁   * exp( -(x-x₀)/dₙ₋₁ )) + o               (1)


        where:

            x₀          = onset (delay) of the transient; only makes sense when x0 >= 0
            r           = rising phase time constant; 
            a₀...aₙ₋₁   = scale for each of the n decay components;
            d₀...dₙ₋₁   = time constant for each of the decay components;
            o           = offset (`DC' component)
            
            
    Arguments:
            
    x   =   the independent (predictor) data (represents the definition domain for 
            the model function e.g., a time vector)
            This is NOT a pyton quantity, just a 1D numpy array.
            
    parameters = 1D numeric sequence (tuple, list, numpy array) with minimum five elements 
            such that len(parameters) satisfies 2 * n + 3 where n >=1 is the number of decays
            in the model.
            
            ATTENTION: ORDER OF MODEL PARAMETERS:
            
            Model parameter values are interpreted to be given in the following order:
            
            a₀, d₀, <a₁, d₁, ...aₙ, dₙ>, o, r, x₀
            
            For each decay component there are two parameters: 
            a (scale) and d (time constant).
            
            Decay components are given in order (scale₀, decay₀, scale₁, decay₁, etc)
            and are followed by offset (o), rise time constant (r) and delay (x₀).
            
            For example, [a₀, d₀, a₁, d₁, o, r, x₀] specifies a transient signal 
            with two decay components, (a₀, d₀, a₁, d₁)
            
            The time constants (r, d₀, d₁, ...) and the delay x₀ are considered to
            be given in the same time units as x. The offset and scale parameters
            are considered to be given in the units of the signal.
            For code simplicity I do NOT use python quantities here, so appropriate scaling
            must be applied to the parameters before passing them to this function.
            
    
    Returns:
    
    y = the model curve
    
    yd = a list of model curves for each scaled decay component; it has as many curves
        as there are 'a' and 'd' elements in parameters
        
        
    NOTE: Python 3 only supports a subset of the unicode character set for 
    identifiers (or variable names). 
    
    For example, the following are invalid variable names: 'a₀' or 'α₀', although
    they MAY be used in documetation; on the other hand the following ARE valid:
    'a0', 'a_0', 'α0', or 'α_0'

    To insert unicode characters in variable names in Scipyen's console, use
    '\'followed by 'Tab' key (and if necessary, press 'Tab' a second time).
    
    This works as well in jupyter qtconsole, but not in plain python terminal
    
    """
    
    # NOTE: call np.squeeze on the argument BEFORE passing it to this function !!!
    
    nDecays = check_rise_decay_params(parameters)
    
    if isinstance(x, numbers.Real):
        # for using this function with scipy.integrate.quad, which evaluates the
        # model function at a single point
        #x = x - parameters[-1]
        
        if x < 0:
            return 0
        
        y = 1 - np.exp(-x/parameters[-2])
        
        yd = list()
        
        for k in range(nDecays):
            yd.append(parameters[2*k] * np.exp(1-x/parameters[2*k+1]))
            
        y += sum(yd)
        
        return y
            
        #if returnDecays:
            #return y, yd
            
        #else:
            #return y
        
    else:
        if x.ndim > 1:
            raise ValueError("Vector x must have exactly one dimension (i.e., a column vector)")
        
        x = x - parameters[-1] # apply the delay to the time domain
        
        y = np.zeros(x.shape)
        
        #print(y.shape)
        
        yd = np.tile(y[:,np.newaxis], (1,nDecays))
        
        
        y[x>=0] = 1 - np.exp(-x[x>=0]/parameters[-2])
        
        for k in range(nDecays):
            yd[x>=0, k] = parameters[2*k] * np.exp(1-x[x>=0]/parameters[2*k+1])
            
        y *= np.sum(yd,axis=1) 
        y += parameters[-3]
        
        if returnDecays:
            return y, yd
        else:
            return y

def compound_exp_rise_multi_decay(x, parameters, returnDecays = False):
    """Compound transient signal -- linear sum of delayed single transient signals
    Arguments:
        x = 1D predictor vector
        
        parameters = a list of parameter sequences where each sequence is as 
                    defined for the parameters argument of exp_rise_multi_decay
        
    Returns:
        y   = realization of the compound signal model curve
        yc  = list of individual transient models within the compound signal
        ycd = list of individual decay components
        
        NOTE: for a single-component EPSCaT, y and yc contain the same data
        
    """
    #print("parameters", parameters)
    
    # NOTE: 2017-12-26 00:06:38
    # this is so that the function can be used with scipy.integrate.quad
    if isinstance(x, numbers.Real):
        y = 0
        #print("parameters: ", parameters)
        #print("x: ", x)
        for p in parameters:
            #print("p: ", p)
            y += exp_rise_multi_decay(x, p)
        
        return y # NOTE: returns one scalar !!!
    
    else:
        if x.ndim > 1:
            raise ValueError("Vector x must have exactly one dimension (i.e., a column vector)")
        
        y = np.zeros(x.shape)
        
        yc = list()
        
        ycd = list()
        
        for p in parameters:
            #print("p", p)
            
            (yc_, ycd_) = exp_rise_multi_decay(x, p, True)

            y += yc_
            
            yc.append(yc_)
            
            ycd.append(ycd_)

        if returnDecays:
            return y, yc, ycd
        
        else:
            return y, yc
    
def Markwardt_Nilius(x, g, e, h, s):
    """Markwardt & Nilius model for voltage-gated Ca2+ channels I-V relationship
    See Markwardt & Nilius (1988), J Physiol (London)
    
    Parameters:
    ========== 
    x   = column vector (np.array) with membrane voltage (Vm) data
    
    The model parameters are (real scalars, corresponding to units in parentheses):
    
    g  = slope conductance (nS)
    
    e  = extrapolated reversal potential (mV) of the current (from slope conductance)
        i.e. same as Thevenin equivalent e.m.f.
        
    v  = Vm at half-maximal current activation (mV) (i.e. taken on the rising 
        region of the I(V) curve)
    
    s  = slope parameter of Ca2+ channel activation (mV)
    
    Returns:
    ======== 
    
    A column vector Im = f(Vm) were f is the Markwardt & Nilius model
    
    """
    y = g * (x - e) / (1 + np.exp(-(x-h)/s))
    
    return y

# def Xu_Lipscombe():
#     #Vm = membrane potential
#     #V0_5 = activation midpoint
#     #Erev = reversal potential
#     
#     #p1 = Ca2+ permability * [Ca2+]i * RT
#     #p2 = zF/RT with z = 2 valency
#     #F = Faraday constant
#     #R = gas constant
#     #T temperature in degK
#     #k = Boltzmann constant
#     
#     #I = p1 * p2**2 * Vm * (1 - exp(-(Vm-Erev * p2))/(1- exp(-(Vm * p2)))) / (1 + exp(-(Vm-V0_5)/k))
#     
#     pass

def Talbot_Sayer(x, a, b, c, x0, **kwargs):# t = 33 * pq.degC, o = 2.5 * pq.mM):
    """
    Talbot & Sayer model for voltage-gated Ca2+ channels I-V relationship.
    
    Boltzman squared, multiplied by Goldman-Hogdkin-Katz, 
    see Talbot & Sayer 1996, J. Neurophysiol. 76(3):2120-2124
    
    Positional parameters:
    =====================
    
    x   = 1D numpy array (vector): definition domain (e.g. membrane voltage)
    
    a   = real: initial value for Boltzman slope factor
    
    b   = real: initial scale value
    
    c   = real: initial value for internal Ca2+ concentration (in mM)
    
    x0  = real: initial value of onset ("shift")
    
    Var-keyword parameters 
    ======================
    
    t   = python quantity: temperature in degrees Celsius (degC); default: 33 degC
    
    o   = python quantity: external Ca2+ concentration in mM; default: 2.5 mM
    
    Returns:
    =======
    A realization of the I-V model function in 
    Talbot & Sayer 1996, J. Neurophysiol. 76(3):2120-2124
    as a numpy vector
    
    
    NOTE:
    Do not use directly in curve fitting, as it expects more arguments
    that the model parameters. The extra arguments are given as keyword
    arguments. If used directly in fitting, then expected keyword arguments WILL
    get their default values.
    
    """
    from scipy import constants
    
    # default values
    t_ = 33
    o = 2.5 * pq.mM
    
    if len(kwargs) > 0:
        if "t" in kwargs:
            t = kwargs["t"]
        
            if isinstance(t, pq.Quantity) and t.dimensionality == (1*pq.degC).dimensionality:
                t_ = t.magnitude
                
            elif isinstance(t, numbers.Real):
                t_ = t
                
            else:
                raise TypeError("Was expecting 't' (temperature) as a real scalar or a python quantity in degC. got %s instead" % type(t).__name__)
        
        if "o" in kwargs:
            o = kwargs["o"]
            
            if isinstance(o, numbers.Real):
                o *= pq.mM
                
            else:
                if not isinstance(o, pq.Quantity) or o.dimensionality != (1*pq.mM).dimensionality:
                    raise TypeError("Was expecting 'o' (external Ca2+ concentration) as a real scalar or a python quantity in mM; got %s instead" % type(o).__name__)
            
            
    
    T = constants.convert_temperature(t_, "Celsius", "Kelvin") * pq.degK
    
    F = constants.physical_constants["Faraday constant"][0] * pq.C/pq.mol
    
    R = constants.physical_constants["molar gas constant"][0] * pq.J/(pq.mol * pq.degK)
    
    k = F/(R*T) # NOTE: this is in C/J i.e. 1/V, because 1V  = 1J/C
    
    k = k.rescale(1/pq.mV) #  because x is in mV
    
    #print(k)
    
    #k = 0.0379
    
    # see Kay & Wong (1987) J. Physiol, 392:603-616 ↦ Boltzmann eqn squared
    boltzmann = 1 / (1 + np.exp(-a * k.magnitude * (x-x0)))**2
    
    ghkexp = np.exp(-2 * x * k.magnitude)
    
    # Goldman-Hogkin-Katz
    ghk = x * b * (c - o.magnitude * ghkexp) / (1-ghkexp)

    return boltzmann * ghk

def gaussianSum1D(x, *args, **kwargs):
    """ Sum of shifted Gaussians in 1D.
    
    Implements:
    
        y = a0*exp(-((x-b0)/c0)^2) + a1*exp(-((x-b1)/c1)^2) + ...
            ak*exp(-((x-bk)/ck)^2) + ...
            an*exp(-((x-bn)/cn)^2) + d
            
        for a sum of shifted n+1 1D Gaussians on top of a common offset d
    
    Parameters:
    ==========
    
    x = 1D numpy array: the domain of definition
    
    Var-positional parameters:
    ==========================
    
    EXACTLY n * 3 + 1 elements: a0, b0, c0, ..., ak, bk, bk, ... an-1, bn-1, cn-1, d
    
    for n 1D Gaussian curves
    
    If packed in a sequence, it can be unpacked by assing it as a starred expression
    in the function call.
    
    keyword parameters:
    ===================
    
    components: bool, default False: 
    
                when False, the function returns the compound Gaussian only, as 
                            a numpy array ("column vector")
            
                when True, the function returns a tuple containing the compound 
                            Gaussian as above, and a matrix with each individual 
                            Gaussian component in its columns
    
    """
    #print("gaussianSum1D args: ", args)
    
    components = False
    
    if len(kwargs) and "components" in kwargs:
        components = kwargs["components"]
    
    # NOTE: 2018-09-14 09:42:08
    # find out how many gaussians are specified by the parameters
    ngauss, rem = divmod(len(args), 3)
    
    if ngauss < 1 or rem != 1:
        raise RuntimeError("There must be exactly n * 3 + 1; got %d instead" % len(args))
    
    #print(x.shape[0])
    
    #ygauss = np.full([x.shape[0], ngauss], 0)
    ygauss = np.full([x.shape[0], ngauss], np.nan)
    
    #print("ygauss shape: ", ygauss.shape)
    
    for k in range(ngauss):
        a, b, c = args[slice(k*3, k*3+3)]
        ygauss[:,k] = a * np.exp(-((x-b)/c)**2)
        
    ret = np.nansum(ygauss, axis=1) + args[-1]
    
    #print("return shape: ", ret.shape)
    
    if components:
        return ret, ygauss + args[-1]
    
    return ret
    
    
def Frank_Fuortes(x, tau, x0):
    """ Frank & Fuortes 1956 expression Irh/I = 1 - exp(-(t-t0)/tau)
    
    In the Frank & Fuortes 1956 paper, Irheo is a constant experimentally measured.
    Use this to get the membrane time constant only.
    
    The original equation (1) is used for the determination of the 
    membrane time-constant from strength-latency relationship.
    
    Irh/I = 1 - exp(-t/tau)                                         (1)
    
        where Irh (rheobase curent) is measured experimentally as the 
        smallest I value where AP are fired.
        
    In practice, the following equation is used:
    
    Irh/I = 1 - exp(-(t-t0)/tau)                                    (2)
        
        where t0 is a small "delay" i.e., the smallest latency used in the 
        experiment.
        
        This helps the fit as latency approaches 0.
            
    References:
    
    Frank & Fuortes (1956) Stimulation of spinal motoneurones with 
    intracellular electrodes. J.Physiol. 134, 451-470
    """
    return 1-np.exp(-(x-x0)/tau)
    #return 1-np.exp(-x/tau)

def Frank_Fuortes2(x, irh, tau, x0):
    """ Implements 1/I = (1-exp(-t/tau)) / Irh 
    
    By rearranging the Frank & Fuortes 1956 equation
    one can also get a fitted value for Irheobase 
    
    1/I = (1-exp(-t/tau)) / Irh                                     (2)
    References:
    
    Frank & Fuortes (1956) Stimulation of spinal motoneurones with 
    intracellular electrodes. J.Physiol. 134, 451-470
    """
    return (1-np.exp(-(x-x0)/tau)) / irh
    #return (1-np.exp(-x/tau)) / irh

    
def Boltzmann(x, p, pos:bool=True):
    """ Realises y = 1/(1+exp(±(x₀ - x)/κ))

    Function parameters:
    ====================
    x: float scalar (e.g., membrane voltage)
    
    p: array-like, float, with two elements: x₀ and κ (in THIS order)
    
    pos: bool, optional (default is True)
        When True, the function uses a positive exponential argument (e.g. useful
        to fit an activation curve)
    
        When False, the exponential argument is negative (e.g., useful to fit an 
        inactivation curve)
    
    Returns:
    ========
    A scalar (e.g., membrane current)
    
    Notes:
    ======
    
    Boltzmann's equation is commonly used to describe the voltage-dependent gating
    of voltage-gated ion channels:
    
        Activation:
    
        Iₘ = 1/(1+exp((V½ - Vₘ)/κ))                                 (1)

        Inactivation:
    
        Iₘ = 1/(1+exp(-(V½ - Vₘ)/κ))                                (2)
    
    where:
    
    Iₘ can be:
        ∘ the recorded membrane current at a range of Vₘ values, normalized to 
            the maximal recorded current value
    
        ∘ fractional open time (for recordings from a small number of channels, 
            see e.g., Magee & Johnston, JPhysiol, 1995) - by definition 
            normalized.
    
        ∘ chord or slope conductance normalized to maximal value, e.g., see
            Magee & Johnston 1995
    
        When all other channels are blocked, Iₘ is specific to the studied
        channels.
    
    Vₘ is the membrane voltage
    
    V½ is the "half-maximum" voltage - the voltage where ensemble channel 
    current is half the maximum, or where half of the channels are active
    
    κ is a "slope" factor; when fitting I-V (or G-V) relationships, κ usually is
    𝒛𝑹𝑻/𝑭 (e.g., see Cui et al, 1997, J Gen Physiol), where:
    
    𝒛  apparent gating charge [C]
    𝑻  temperature [K]
    𝑹  molar gas constant 8.31446261815324 [J K⁻¹ mol⁻¹]
    𝑭  Faraday constant 96485.33212331001 [C mol⁻¹]

    NOTE V½ and κ are often different for activation and inactivation
    
    Let ξ = (V½ - Vₘ)/κ
    
    
    Then:
    
    (Vₘ-V½)/κ = -ξ
    
    and:
    
    1/(1+exp(-ξ)) = 1/(1+1/exp(ξ)) = exp(ξ)/(1+exp(ξ)) = exp(ξ) × 1/(1+exp(ξ))
    |___________|                                                 |__________|
    inactivation                                                   activation
    
    (NOTE the change in sign of the exponential argument!)
    
    When fitting experimental data, the fitted parameters are x₀ and κ.
    
    The equation is also an empyrical model of the "gating" mechanism for 
    voltage dependent channels Naᵥ and Kᵥ in the Hodgkin-Huxley formalism.
     
    """
    
    x0, κ = p
    
    # sign of ξ
    ξ = x0 - x if pos else x - x0
    ξ /= κ
    # ξ = (x0 - x) / κ if pos else (x - x0)/κ
    return 1/(1+np.exp(ξ))
    
    # α = 1 if pos == True else -1
    # return 1/(1+np.exp(α * (x0 - x) / κ))

def Heaviside(x:typing.Union[pq.Quantity, np.ndarray], 
              x0:typing.Union[float, pq.Quantity], 
              α:bool=True) -> np.ndarray:
    """Heaviside (step) function
    
    Parameters:
    ===========
    x: domain vector
    x0: coordinate of the step change (in domain space)
    α: bool, default is True.
        Flag for the direction of step change:
        True (default) → 0 → 1 transition
        False ⇒ transition 1 → 0
        
"""
    if not is_vector(x):
        raise TypeError(f"Domain (x) is not a vector")
    
    if isinstance(x0, np.ndarray):
        if x0.size != 1:
            raise TypeError(f"x0 expected an array of size 1; got {x0.size} instead")
        
    elif not isinstance(x0, float):
        raise TypeError(f"x0 must be a scalar float or an array with size 1")
        
    # if all(isinstance(v, pq.Quantity) for v in (x, x0)):
    if isinstance(x, pq.Quantity):
        if isinstance(x0, pq.Quantity):
            if not scq.units_convertible(x,x0):
                raise TypeError(f"x and x0 have incompatible units")
            
            if x.units != x0.units:
                x0 = x0.rescale(x.units)
                
            x0 = x0.magnitude.flatten()[0]

        x = x.magnitude
                
    else:
        if isinstance(x0, pq.Quantity):
            warnings.warn(f"x0 is a quantity but the domain is not; will strip the units from x0")
            x0 = x0.magnitude.flatten()[0]
            
    x = x.flatten()
    
    xx = x - x0
    
    ν = 0. if α else 1.
    λ = 1. if α else 0.
    
    y = np.full_like(x, fill_value = ν)
    y[xx >= 0] = λ
    
    return y
    
    
def Heaviside2(x:typing.Union[pq.Quantity, np.ndarray], 
              x0:typing.Union[float, pq.Quantity], 
              level0:float=0., level1:float=1.) -> np.ndarray:
    """Heaviside (step) function
    
    Parameters:
    ===========
    x: domain vector
    x0: coordinate of the step change (in domain space)
    level0, level1:float; optional, defaults are 0 anbd 1, respectively
        The initial and the final level of the step function.
        
"""
    if not is_vector(x):
        raise TypeError(f"Domain (x) is not a vector")
    
    if isinstance(x0, np.ndarray):
        if x0.size != 1:
            raise TypeError(f"x0 expected an array of size 1; got {x0.size} instead")
        
    elif not isinstance(x0, float):
        raise TypeError(f"x0 must be a scalar float or an array with size 1")
        
    # if all(isinstance(v, pq.Quantity) for v in (x, x0)):
    if isinstance(x, pq.Quantity):
        if isinstance(x0, pq.Quantity):
            if not scq.units_convertible(x,x0):
                raise TypeError(f"x and x0 have incompatible units")
            
            if x.units != x0.units:
                x0 = x0.rescale(x.units)
                
            x0 = x0.magnitude.flatten()[0]

        x = x.magnitude
                
    else:
        if isinstance(x0, pq.Quantity):
            warnings.warn(f"x0 is a quantity but the domain is not; will strip the units from x0")
            x0 = x0.magnitude.flatten()[0]
            
    x = x.flatten()
    
    xx = x - x0
    
    y = np.full_like(x, fill_value = level0)
    y[xx >= 0] = level1
    
    return y
    
    
def boxcar(x, p, up_first:bool=True):
    x0, x1 = p
    
    ud = [True, False] if up_first else [False, True]
    
    if x0 < x1:
        print(f"x0 < x1 {x0 < x1}; up_first: {up_first}")
        #       up then down                                                        down then up
        return Heaviside(x, x0, ud[0]) * Heaviside(x, x1, ud[1])# if up_first else Heaviside(x, x0, False) + Heaviside(x, x1, True)
        
    else:
        print(f"x0 >= x1 {x0 >= x1}; up_first: {up_first}")
        return Heaviside(x, x0, ud[0]) * Heaviside(x, x1, ud[1])# if up_first else Heaviside(x, x1, False) + Heaviside(x, x0, True)
        # return Heaviside(x, x0, False) + Heaviside(x, x1, True) if up_first else Heaviside(x, x1, False) + Heaviside(x, x0, True)
        # return Heaviside(x, x0,False) * Heaviside(x, x1, True) if up_first else Heaviside(x, x1, False) + Heaviside(x, x0, True)
        # return Heaviside(x, x1, True) * Heaviside(x, x0, False) if up_first else Heaviside(x, x1, False) + Heaviside(x, x0, True)
        #      up follows down                                                  down follows up
        # return Heaviside(x, x0, False) + Heaviside(x, x1, True) if up_first else Heaviside(x, x0, False) + Heaviside(x, x1, False)
        

def boxcar2(x, p, level0=0., level1=1.):
    """"""
    x0, x1 = p
    
    return Heaviside2(x, x0, level0, level1) + Heaviside2(x, x1, level1, level0)



def ramp(x, p = (0., 0., 1., 1.)):
    x0, y0, x1, y1 = p
    
    if isinstance(x, pq.Quantity):
        if isinstance(x0, pq.Quantity):
            if not scq.units_convertible(x,x0):
                raise TypeError(f"x and x0 have incompatible units")
            
            if x.units != x0.units:
                x0 = x0.rescale(x.units)
                
            x0 = x0.magnitude.flatten()[0]

        if isinstance(x1, pq.Quantity):
            if not scq.units_convertible(x,x1):
                raise TypeError(f"x and x1 have incompatible units")
            
            if x.units != x1.units:
                x1 = x1.rescale(x.units)
                
            x1 = x1.magnitude.flatten()[0]

        x = x.magnitude
                
    else:
        if isinstance(x0, pq.Quantity):
            warnings.warn(f"x0 is a quantity but the domain is not; will strip the units from x0")
            x0 = x0.magnitude.flatten()[0]
            
        if isinstance(x1, pq.Quantity):
            warnings.warn(f"x1 is a quantity but the domain is not; will strip the units from x0")
            x1 = x1.magnitude.flatten()[0]
            
    x = x.flatten()
    y = np.full_like(x, fill_value = y0)
    
    xx0 = x-x0
    xx1 = x-x1
    
    α = (y1-y0)/(x1-x0)
    
    y[xx1 >= 0] = y1
    y[xx0 < 0] = y0
    ndx = (xx0 >= 0) & (xx1 < 0)
    y[ndx] = α * xx0[ndx]
    
    return y
    
    
    

    
