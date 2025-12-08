# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" Collection of 1D and nD functions and helper functions, for use in model fitting.

WARNING: This module is on its way to deprecation, and it wil be superseded by
modelfitting.py in the (hopefully not too distant) future.

For now, stick with THIS module.

NOTE: 2025-05-08 10:39:04

Parametric models are defined by functions taking one independent variable, ``𝑥`` 
(the predictor) and a set of coefficients, and implement the mathematical expression
to generate a waveform (dependent variable ``𝑦``). The mathematical expression
describes the dependency of 𝑦 on 𝑥 and on the model coefficients.

There functions are named in a way suggestive of the parametric model they implement.

For example, an exponential decay is defined by:

    ``y = exp(-(x)/τ)``                                         (1)
    
    thus requiring a single coefficient: τ
    
A biased and scaled version of (1) is:
    
    ``y = α + β × exp(-(x)/τ)``                                 (2)
    
    thus requiring three coefficients: α (the additive bias), β (the multiplicative
    bias, or 'scale'), and τ
    
A biased, scaled and shifted version of (1) is:

    ``y = α + β × exp(-(x-x₀)/τ)``                                 (3)
    
    and requires an additional coefficient: x₀ (the shift)
    
    Here, the shift is useful when the exponential process begins at some point
    AFTER the start of the predictor 𝑥
    
    
ATTENTION: Please decorate all model functions with the modelfunction decorator.
This will help locating/accessing these functions easily from other Scipyen
components.
"""
import typing
import numpy as np
import quantities as pq
import pandas as pd
import numbers
import dataclasses
from core import scipyen_quantities as scq
from core.prog import (scipywarn, signature_as_dict, decorator, timefunc)

@decorator
def modelfunction(f:typing.Callable, nvars:int=1, 
                  parameter_names:typing.Optional[typing.Sequence[str]]=None,
                  n_parameters:typing.Optional[int] = None,
                  parameter_units:typing.Optional[dict]=None,
                  **kwargs):
    r"""Decorator to tag a function as a mathematical model function.
A mathematical model function realizes a function of one or more independent 
variables based on a mathematical expression and a set of independent parameters.

The function returns an nD array where 1 <= n <= nvars (see below)

By using this decorator, model functions can be identified as such, regardless 
of the module (in Scipyen's tree) where they are defined.

This decorator sets the attributes listed below, to a model function. 

'nvars': number of independent variables (e.g. 1D or nD function)

'parameter_names': sequence of parameter symbols as they appear in the mathematical
    model; these parameters are "fixed" for a given model instance and are 
    responsible for generating a "family" of models from the same independent 
    variable, such that the models in the family have one thing in common: the 
    mathematical relation between the independent variable(s) and the parameter.

    These parameters are also the ones that are determined in curve fitting (i.e.
    when fitting a model to some real data thought to follow the mathematical
    relation that defines the model).

'parameter_units' (see below)

NOTE: these attributes are NOT directly accessible from within the function's
scope (i.e. excuted code). 

Parameters:
f: the decorated function
nvars: number of independent variables; this determines the general syntax of the 
    model function, e.g.:
    one independent variable (i.e., 1D model):  f(x,   /, *params)
    two independent variables (2D model):       f(x,y, /, *params)
    ⋮
    and so on...

    Optional; default is 1. WARNING: do NOT confuse with the number of model 
    parameters

parameter_names: typing.Sequence[str] — names (symbols) for the parameters.
    These can usually be inferred from the function's signature via the 
    'inspect' module, which is what the function 'model_parameters(…)' in this
    module does. However, this can be tedious for model functions with a more 
    complex syntax; hence this attribute comes in handy.

    Optional, default is tuple() (empty tuple)

    When the model defines a variadic number of parameters (see e.g., exponential_decays_product_biased_shifted)
    these are indicated by a * suffix

parameter_units: optional mapping
    parameter symbol:str ↦ physical unit: Quantity, UnitQuantity, or sequence of such

    Default is None
    When given, this flags that some model parameters actually have physical units;
    the keys are the names of the model parameters (as in parameter_names).

    When the model defines a variadic number of parameters (see e.g., 
    exponential_decays_product_biased_shifted) their keys are suffixed by a '*' (as above) 
    and their associated units are the same.

    Since not all parameters necessarily associate physical units, those that do not
    may be omitted from this mapping. However, ATTENTION: the full sequence of
    parameter names SHOULD be given in 'parameter_names', as above. Parameters
    that are omitted from parameter_units will by default get pq.dimensionless as
    physical unit.

    The safest practice is to associate these unitless parameters with pq.dimensionless
    which will flag them as such.

    Some models may accept parameters with physical units that depend on the physical
    dimensionality of the dependent variable. For example, alphaSynapse — which 
    models a time-varying function of ANY dependent physical variable, whether it
    is current, voltage, fluorescence intensity, etc — takes an "offset" parameter 
    (α) which by definition has the same units as the dependent variable.

    In such cases you have the option to specify None or dataclasses.MISSING in lieu
    of units. Since the actual physical dimensionality of the dependent variable 
    is often unknown before calling the model function, using MISSING or None as
    dimensionality tag flags that the parameter should receive the units of the
    dependent variable at runtime.


    WARNING: This does not mean that the decorated model function expects Quantities
    as values for the parameter; it is up to the function what to do with its
    own call arguments

n_parameters: int: number of model parameters; again, this can be inferred from the 
    length of the paraneter names sequence, or indirectly by inspecting the 
    function's signature; however, this provides a direct access, useful for
    model functions with a more complex signature

    Optional default is 0, or -1 for variadic parameters

    NOTE: this will be updated automatically wher 'parameternames' above is set 
    to a non-empty sequence of str

    NOTE: the wrapper also gives access to these

Var-positional parameters:
additional attributes to be set to the wrapped function WARNING under development

NOTE for developers: this function defines a function decorator with optional
arguments; this is made possible by decorating this function with the prog.decorator
taken from PythonDecoratorLibrary, see
https://wiki.python.org/moin/PythonDecoratorLibrary#Creating_decorator_with_optional_arguments

"""
    def wrapper(f):
        setattr(f, "model_function", True)
        setattr(f, "nvars", nvars)
        if isinstance(parameter_names, typing.Sequence) and len(parameter_names) and all(isinstance(p, str) for p in parameter_names):
            setattr(f, "parameter_names", parameter_names)
        else:
            setattr(f, "parameter_names", tuple())
            
        
        if isinstance(parameter_units, dict):
            check_value_type = lambda v: (isinstance(v, pq.Quantity) and v.size==1) or isinstance(v, (type(None), type(dataclasses.MISSING)))
            if len(parameter_units) and all(isinstance(k, str) for k in parameter_units.keys()):
                pnames = getattr(f, "parameter_names", None)
                if pnames is None or isinstance(pnames, typing.Sequence) and len(pnames) == 0:
                    setattr(f, "parameter_names", tuple(parameter_units.keys()))
                    
                punits = dict(map(lambda p: (p, pq.dimensionless), pnames))
                
                for key, value in parameter_units.items():
                    if key not in f.parameter_names:
                        continue
                    if (check_value_type(value)) or (isinstance(value, typing.Sequence) and all(check_value_type(v) for v in value)):
                        punits[key] = value
                        
                setattr(f, "parameter_units", punits)
                
            else:
                pnames = getattr(f, "parameter_names", None)
                if isinstance(pnames, typing.Sequence) and len(pnames) and all(isinstance(p, str) for p in pnames):
                    punits = dict(map(lambda p: (p, pq.dimensionless), pnames))
                    setattr(f, "parameter_units", punits)
                    
        else:
            pnames = getattr(f, "parameter_names", None)
            if isinstance(pnames, typing.Sequence) and len(pnames) and all(isinstance(p, str) for p in pnames):
                punits = dict(map(lambda p: (p, pq.dimensionless), pnames))
                setattr(f, "parameter_units", punits)
                
            
        if isinstance(n_parameters, int) and len(f.parameter_names) == 0:
            # use 'nparameters' only when parameternames is not given
            if n_parameters < -1:
                raise ValueError("Number of parameters must be >= -1")
            
            setattr(f, "n_parameters", n_parameters)
        else:
            if any("*" in p for p in f.parameter_names):
                setattr(f, "n_parameters", -1)
            else:
                setattr(f, "n_parameters", len(f.parameter_names))
        
        for key, value in kwargs.items():
            setattr(f, key, value)
        return f
    
    return wrapper(f)
    # wf = wrapper(f)
    # setattr(wf, "self", f)
    # return wf

def check_unpack_model_params_seq(params:typing.Sequence | np.ndarray, n:int):
    r"""Verifies and unpacks model parameters, when supplied as a Sequence or vector"""
    if isinstance(params, typing.Sequence) and len(params) == n and all (isinstance(v, float) for v in params):
        return tuple(params)
    
    elif isinstance(params, np.ndarray) and params.size == n:
        return tuple(map(lambda v: float(v), params))
    
    else:
        raise TypeError(f"Expecting a sequence or a numpy array with {n} elements")

def check_rise_decay_params(x:typing.Sequence[float]):
    r"""Returns the number of decay components for a exp-rise-multi-decay transient.
    x = iterable with model parameters (see exponential_rise_decays_product_biased_shifted())
    """
    if np.remainder(len(x)-3, 2) != 0:
        raise ValueError("Unexpected number of elements in the parameters vector; must be 2n + 3 where n is the number of decay components; instead got %d elements" % len(parameters))
    
    return (len(x)-3) // 2

@modelfunction(parameter_names = ("β0", "β1", "λ0", "λ1"))
def biexponential(x:typing.Union[np.ndarray, float], 
                  β0:float|typing.Sequence[float]|np.ndarray, /,
                  β1:typing.Optional[float] = None, 
                  λ0:typing.Optional[float] = None, 
                  λ1:typing.Optional[float] = None) -> np.ndarray | float:
    r"""Sum of two exponentials:
    β0 × exp(λ0 × x) + β1 × exp(λ1 × x)
"""
    if isinstance(β0, (typing.Sequence, np.ndarray)):
        β0, β1, λ0, λ1 = check_unpack_model_params_seq(β0, 4)
        
    if not all(isinstance(v, float) for v in (β0, β1, λ0, λ1)):
        raise TypeError("Expecting four comma-separated floats or a sequence of four floats")
    
    return β0 * np.exp(λ0 * x) + β1 * np.exp(λ1 * x)

@modelfunction(parameter_names = ("β0", "β1", "τ0", "τ1"))
def biexponential_decay(x:typing.Union[np.ndarray, float], 
                        β0:float|typing.Sequence[float]|np.ndarray, /,
                        β1:typing.Optional[float] = None, 
                        τ0:typing.Optional[float] = None, 
                        τ1:typing.Optional[float] = None) -> np.ndarray | float:
    r"""Sum of two exponential decays ('bi-exponential decay')"""
    if isinstance(β0, (typing.Sequence, np.ndarray)):
        β0, β1, τ0, τ1 = check_unpack_model_params_seq(β0, 4)
        
    if not all(isinstance(v, float) for v in (β0, β1, τ0, τ1)):
        raise TypeError("Expecting four comma-separated float scalars or a sequence of four float scalars")
    
    return β0 * np.exp(-x / τ0) + β1 * np.exp(-x / τ1)

@modelfunction(parameter_names = ("α", "β0", "β1", "τ0", "τ1"))
def biexponential_decay_biased(x:np.ndarray | float, α:typing.Union[float,typing.Sequence[float], np.ndarray],/, 
                               β0:typing.Optional[float]=None, β1:typing.Optional[float]=None, 
                               τ0:typing.Optional[float]=None, τ1:typing.Optional[float]=None) -> np.ndarray | float:
    r"""Sum of two exponential decays ('bi-exponential decay') with bias
     ('offset'):
    
    α + β0 × exp(-x / τ0) + β1 × exp(-x / τ1)
"""
    if isinstance(α, (typing.Sequence, np.ndarray)):
        α, β0, β1, τ0, τ1 = check_unpack_model_params_seq(α, 5)
        
    if not all(isinstance(v, float) for v in (α, β0, β1, τ0, τ1)):
        raise TypeError("Expecting a comma-separated list of 5 parameters or a sequence of 5 parameters (α, β0, β1, τ0, τ1)")

    return α + β0 * np.exp(-x / τ0) + β1 * np.exp(-x / τ1)

@modelfunction(parameter_names = ("α", "β0", "β1", "x0", "τ0", "τ1"))
def biexponential_decay_biased_shifted(x: np.ndarray | float, 
                                α:typing.Union[float, typing.Sequence[float], np.ndarray], /, 
                                β0:typing.Optional[float], 
                                β1:typing.Optional[float], 
                                x0:typing.Optional[float], 
                                τ0:typing.Optional[float], 
                                τ1:typing.Optional[float]) -> np.ndarray | float:
    r"""Sum of two exponential decays (a.k.a 'bi-exponential decay') with bias
    ('offset') AND a shift ('onset'):
    
    α + β0 × exp(-(x-x0) / τ0) + β1 × exp(-(x-x0) / τ1)
"""
    if isinstance(α, (typing.Sequence, np.ndarray)):
        α, β0, β1, x0, τ0, τ1 = check_unpack_model_params_seq(α, 6)
        
    if not all(isinstance(v, float) for v in (α, β0, β1, x0, τ0, τ1)):
        raise TypeError("Expecting a comma-separated list of 6 parameters or a sequence of 6 parameters (α, β0, β1, τ0, τ1)")

    return α + β0 * np.exp(-(x-x0) / τ0) + β1 * np.exp(-(x-x0) / τ1)

@modelfunction(parameter_names = ("α", "β", "x0", "τ*"))
def exponential_decays_product_biased_shifted(x: np.ndarray | float, 
                                   α:typing.Sequence[float] | float | np.ndarray, /,
                                   β:typing.Optional[float] = None, 
                                   x0:typing.Optional[float] = None, *τ) -> np.ndarray | float:
    r"""Product of several exponential decays, biased and shifted

    Realizes:
                ₙ₋₁
    y = α + β × Π  exp(-(x-x₀)/τₖ) = α + β × exp(-(x-x₀)/τᵪ)    , where:
                ᵏ⁼⁰

    • τ is a sequence of floats with the individual time constants, one for
    each decay component
    • τᵪ is the "combined" decay time constant
    • 𝑛 is the number of exponentials in the product above and the length of the
        τ sequence - currently, a maximum of two exponential is supported

    For two exponentials, this is (using python 0-based indexing):
    
    τᵪ = (τ₀ × τ₁)/(τ₀ + τ₁), where τ₀ = τ[0] and τ₁ = τ[1] 
    
    Let:
    λ₀ = 1/τ₀, λ₁ = 1/τ₁, λᵪ = λ₀ + λ₁ = 1/τ₀ + 1/τ₁ = (τ₀ + τ₁) / (τ₀ × τ₁)
    
    ⟹ τᵪ = 1/λᵪ = (τ₀ × τ₁ / (τ₀ + τ₁))
    
    Then:
    exp(x / τ₀) × exp(x / τ₁) = exp(x × λ₀) × exp(x × λ₁) = 
    exp(x × (λ₀ + λ₁))        = exp(x × λᵪ) = exp(x/τᵪ)
    
    Although it can be extended to a product of more than two exponentials, this 
    is likely to introduce more errors/instability, and to make it harder for the
    solver to converge on a solution.
    
    The function core.curvefitting.guess_init_two_exp_prod can be used to generate
    initial coefficient values for a product of two exponentials, but be aware 
    that the last two values in the result of that function have to be inverted 
    (1/x) to be used as time constants (see documentation for guess_init_two_exp_prod()).
    
The other parameters are as for exponential_decay_biased_shifted.
    
NOTE: For calling purposes, α can be supplied as a sequence of (α, β, x0), and any
    arguments folowing it will be included in τ
    
"""
    if isinstance(α, (typing.Sequence, np.ndarray)):
        τ = (β, x0) + τ
        α, β, x0 = check_unpack_model_params_seq(α, 3)
        
    if not all(isinstance(v, float) for v in (α, β0, β1, x0)) and not all(isinstance(v, float) for v in τ):
        raise TypeError("Expecting a comma-separated list of parameters or a sequence of three parameters (α, β0, β1) followed by individual τ values")

    if len(τ) == 0:
        raise ValueError(f"τ must be supplied")
    elif len(τ) == 1:
        return exponential_decay_biased_shifted(x, α, β, x0, τ[0])
    else:
        # λ = np.sum(list(map(lambda v: 1/v, τ)))
        τc = np.prod(τ)/np.sum(τ)
        
    return α + β * np.exp(-(x-x0) / τc)

@modelfunction(parameter_names = ("α", "β", "x0", "τ"))
def exponential_decay_biased_shifted(x:np.ndarray | float, 
                                     α:typing.Sequence[float] | np.ndarray | float, /,
                                     β:typing.Optional[float] = None, 
                                     x0:typing.Optional[float] = None, 
                                     τ:typing.Optional[float] = None) -> np.ndarray | float:
    r"""Single exponential decay, with bias and shift

    y = α + β × exp(-(x-x₀)/τ)
    
Parameters:
===========
x: independent variable (e.g., time): 1D numpy array

coefficients are given as floats in the following order:

α (offset), β (scale), x₀ (onset), τ (time constant)
    
"""

#     NOTE: Python 3 only supports a subset of the unicode character set for 
#     identifiers (or variable names). 
#     
#     For example, the following are invalid variable names: 'a₀' or 'α₀', although
#     they MAY be used in documetation; on the other hand the following ARE valid:
#     'a0', 'a_0', 'α0', or 'α_0'
# 
#     To insert unicode characters in variable names in Scipyen's console, use
#     '\'followed by 'Tab' key (and if necessary, press 'Tab' a second time).
#     
#     This works as well in jupyter qtconsole, but not in plain python REPL
    # y0, α, x0, τ = parameters
    
    if isinstance(α, (typing.Sequence, np.ndarray)):
        α, β, x0, τ = check_unpack_model_params_seq(α, 4)
        
    if not all(isinstance(v, float) for v in (α, β, x0, τ )):
        raise TypeError("Expecting a sequence of floats or a comma-separated list of floats")
    
    λ = 1/τ
    return α + β * np.exp(-(x-x0)*λ)

@modelfunction(parameter_names = ("α", "β", "x0", "τ"))
def exponential_rise_biased_shifted(x:np.ndarray | float, 
                                    α:typing.Sequence[float]|np.ndarray, 
                                    β:typing.Optional[float] = None, 
                                    x0:typing.Optional[float] = None, 
                                    τ:typing.Optional[float] = None) -> np.ndarray | float:
    r"""Single exponential rise, with bias and shift.

    Realizes α + β × [1 - exp(-(x-x₀)/τ)]

    Parameters:
    ===========
    x: independent variable (e.g., time): 1D numpy array

    coefficients are given as floats in the following order:

    α (bias), β (scale), x₀ (shift), τ (time constant)
"""
    if isinstance(α, (typing.Sequence, np.ndarray)):
        α, β, x0, τ = check_unpack_model_params_seq(α, 4)
        
    if not all(isinstance(v, float) for v in (α, β, x0, τ)):
        raise TypeError("Expecting four comma-separated float scalars or a sequence of four float scalars")
    
    return α + β * (1 - np.exp(-(x-x0)/τ))

# @timefunc # uncomment this for testing 😄
@modelfunction(parameter_names = ("α", "β", "x0", "τ"),
               parameter_units={"α": dataclasses.MISSING,"β":pq.dimensionless,"x0":pq.s, "τ":pq.s},
               title="AlphaSynapse")
def alphaSynapse(x:np.ndarray | float, α:typing.Union[typing.Sequence[float],np.ndarray,float], /,
                  β:typing.Optional[float] = None, x0:typing.Optional[float] = None,
                  τ:typing.Optional[float] = None) -> np.ndarray | float:
    r"""
NEURON AlphaSynapse function.

A single exponential rise and decay, both with the same constant (τ):

        /    
    y = | α + β × (x-x₀)/τ × exp(-(x-x₀-τ)/τ)         where x-x₀ >= 0 
        | α                                           elsewhere
        \
where:
    α  is the additive bias (offset);

    β  is the multiplicative bias (scale);

    x₀ is the shift (delay, or onset);

    τ  is the synaptic time constant

Introduced by NEURON simulation software (https://nrn.readthedocs.io/en/9.0.1/index.html)
to describe the time course of the membrane current at an ideal synapse, evoked
by a transmitter release event.
The description below is taken from the nrnoc/syn.moc file in NEURON's source
tree:

"a synaptic current with alpha function conductance defined by
        i = g * (v - e)      i(nanoamps), g(microsiemens);
        where
         g = 0 for t < onset and
         g = gmax * (t - onset)/tau * exp(-(t - onset - tau)/tau)
          for t > onset
          
this has the property that the maximum value is gmax and occurs at
 t = delay + tau."

also used by NEST
https://www.nest-simulator.org/ 

Parameters:
===========
x: predictor (independent variable) - 1D numpy ndarray
α, β, x0, τ: see above 
When α is a sequence of scalars (1D array-like), it is interpreted as containing 
the individual α, β, x0, τ coefficients 'packed' in this sequence (some optimization
 functions expect this)
    
parameters: 1D array-like: numeric sequence (tuple, list, numpy array) with four
    elements in the following order (see above for their meaning):

The original alpha synapse in NEURON syn.mod does NOT include an additive bias;
this is because it models an ideal system, whereas here I'm giving the possibility
to use this function for fitting recorded data as well (where there exists a 
DC component, equivalent to the 'offset' α). To obtain the same thing as in 
NEURON just set α to 0.

The β parameter here corresponds to the 𝑔ₘₐₓ in NEURON's code (see above).
HOWEVER, whether β is a conductance (𝑔) or not depends on what exactly you use 
THIS function for 😄. NEURON's syn.mod calculates 𝑔 THEN converts it to a 
synaptic current 𝑖 (see above); if you use this function to model a current,
you might want to adjust β accordingly (i.e. set it to YOUR 𝑔ₘₐₓ times the 
electromotive force 𝑣 - 𝑒).

The x0 parameter here corresponds to the 'onset' in NEURON's code (see above).

Finally, 'x' here corresponds to 𝑡 in NEURON's code. If follows that x0 and τ
have the same physical units as 'x'.
    

Returns:
========
1D numpy array (vector)

Example: (run in Scipyen's console)
========

from core import models

x = np.linspace(0.0,1.0, 1000);

parameters = [0, -1, 0.05, 0.01];

y = alphaSynapse(x, *parameters)

OR: 

y = alphaSynapse_model(x, parameters)

plt.plot(x,y)

CHANGELOG:
==========
Renamed from alphaFunction to alphaSynapse to avoid confusion, especially with
the mathematical Alpha Function (https://mathworld.wolfram.com/AlphaFunction.html)
    
"""
    # NOTE: Python currently does not support unicode
    # characters such as sub- or super-scripts, so please use 'x0', not 'x₀'
    # in the code
    
    # unpack parameters
    if isinstance(α, (typing.Sequence, np.ndarray)):
        α, β, x0, τ = check_unpack_model_params_seq(α, 4)
        
    if not all(isinstance(v, float) for v in (α, β, x0, τ)):
        raise TypeError("Expecting four comma-separated float scalars or a sequence of four float scalars")
    
    assert(τ > 0.), "Time constant MUST be strictly positive"
    
    # NOTE: 2025-12-08 00:24:16
    # the original "alpha" function in NEURON's syn.mod is 
    # v * exp(1-v) with v being (x-onset)/tau
    # (pretty similar to an exponential integral?)
    #
    # Here, I also include the multiplicative bias (β here is gₘₐₓ in syn.mod) 
    # and the additive bias ("offset") α
    def alpha(v):
        # NOTE: 2025-12-08 00:28:34 
        # using numpy builtin ufuncs here; 
        # they're OK with scalar floats too, but they return a np.float64
        # therefore I need to cast back to float, see NOTE: 2025-12-08 00:29:32 
        return np.add(α, np.multiply(β, np.multiply(v, np.exp(1. - v))))
    
    # NOTE: 2025-12-08 00:48:54 
    # DISCARD this option as is unefficient (frompyfunc returns PyObject and is
    # MUCH slower, check '->' timings below and NOTE: 2025-12-08 00:50:00)
    # # NOTE: 2025-12-08 00:23:08
    # # vectorized version used when x is a numpy array
    # valpha = np.frompyfunc(alpha, 1, 1) 
    
    # make sure x is a numpy array or a scalar
    if not isinstance(x, (float, np.ndarray)):
        raise TypeError(f"Independent variable 'x' has unexpected type: {type(x).__name__}")
    
    xt = (x-x0)/τ
    
    # NOTE: 2025-12-07 23:29:18
    # in NEURON's syn.mod there is an additional condition for returning 0., when v > 10. - 
    # probably to make sure that extremely small values from v × exp(1-v) truly vanish
    # I don't use that here
    #
    if isinstance(x, float):
        # x is a scalar, all simple!
        # NOTE: 2025-12-08 00:29:32
        # casting to plain float, see NOTE: 2025-12-08 00:28:34 
        return float(alpha(xt)) if xt >=0 else 0.
    
    else:
        if x.size == 1:
            # no point in vectorizing on array with one element
            return alpha(xt) if xt >=0 else np.array([α])
    
        y = np.full_like(x, α)
        
        # using built-in ufuncs (a LOT more efficient !!!)
        # y[xt>=0] = α + β * xt[xt>=0] * np.exp(1.-xt[xt>=0]) # -> core.models.alphaSynapse : 0.0044766569990315475
        y[xt>=0] = alpha(xt[xt>=0]) # -> core.models.alphaSynapse : 0.0031144210006459616
        
        # NOTE: 2025-12-08 00:50:00 -> TOO SLOW !!!
        # valpha(xt, y, where = xt>=0, casting="unsafe") # outputs directly into y -> core.models.alphaSynapse : 0.6116345360023843
        
        return y

@modelfunction(parameter_names = ("i", "n", "b"))
def nsfa(x:np.ndarray | float, i:float|pq.Quantity|typing.Sequence[typing.Union[float, pq.Quantity]], /, 
         n:typing.Optional[typing.Union[float, pq.Quantity]] = None, 
         b:typing.Optional[typing.Union[float, pq.Quantity]] = None) -> np.ndarray | float:
    r"""
        y = x * i - x²/N + b
    
    Parameters: i, N, b: unitary current (pA), number of channels, background current variance (pA²))
    
WARNING: do not pass quantities for the parameters, yet; just use floats
"""
    if isinstance(i, typing.Sequence) and len(i) == 3 and all(isinstance(v, (float, pq.Quantity)) for v in i):
        i, n, b = check_unpack_model_params_seq(i, 3)
        # i, n, b = i
        
    if not all(isinstance(v, (float, pq.Quantity)) for v in (i, n, b)):
        raise TypeError("Expecting three comma-separated float scalars or a sequence of three float scalars")
        
    if isinstance(x, pq.Quantity):
        x = x.magnitude
        
    x = x.flatten()
    
    return x*i - x**2 / n + b
    
@modelfunction(parameter_names = ("α", "β", "x0", "τ1", "τ2"),
               parameter_units = {"α"})
def Clements_Bekkers_97(x:np.ndarray | float,
                        α:typing.Union[float, typing.Sequence[float]], /, 
                        β:typing.Optional[float] = None, 
                        x0:typing.Optional[float] = None, 
                        τ1:typing.Optional[float] = None, 
                        τ2:typing.Optional[float] = None,
                        **kwargs) -> np.ndarray | float:
    r"""
    Clements & Bekkers 1997 mEPSC waveform (alphafunction-like).

    This approximates a single exponential rise and decay each with their own 
    time constant:
    
        /
        | α + β × (1 - exp(-(x-x₀)/τ₁)) × exp(-(x-x₀)/τ₂) for x-x₀ >= 0, 
    y = |
        | α elsewhere
        \
            
    where:
        α  = offset (usually, 0.);
    
        β  = scale;
    
        x₀ = delay ("onset") (ms);
    
        τ₁, τ₂ = time constants, respectively, for rise and decay
    
    Parameters:
    ============
    x: predictor (independent variable e.g., time) - 1D numpy ndarray

    α, β, x₀, τ₁ and τ₂: float scalars, where:
        α is considered in pA,
        β is dimensionless,
        x₀, τ₁ and τ₂ are considered to be given in s

        and τ₁ > 0 τ₂ > 0
    
    Var-keyword parameters:
    =======================
    unit_amplitude: optional, default is False
        When True, return a waveform with baseline 0 and peak value +1 , using 
        the given time constants τ₁ and τ₂
    
    Returns:
    ========
    1D numpy array (vector)
    
    NOTE: the DURATION of the waveform is determined by the independent variable
    'x'
    
    """
    unit_amplitude = kwargs.pop("unit_amplitude", False)
    if isinstance(x, pq.Quantity):
        x = x.magnitude
        
    x = x.flatten()
    
    # print(f"Clements_Bekkers_97: α = {α}")
    
    # NOTE: 2025-11-05 21:31:27
    # allow passing all parameters packed in a sequence, so as to do away with 
    # the *_model version of this function
    if isinstance(α, (typing.Sequence, np.ndarray)):
        α,  β, x0, τ1, τ2 = check_unpack_model_params_seq(α, 5)
        
    if not all(isinstance(v, float) for v in (α,  β, x0, τ1, τ2)):
        scipywarn(f"Clements_Bekkers_97 got α = {α} ({type(α).__name__}),  β = {β}, x0 = {x0}, τ1 = {τ1}, τ2 = {τ2}")
        raise TypeError("Expecting a sequence of 'α,  β, x₀, τ₁ τ₂' scalar floats or a comma-separated list of scalar floats for 'α,  β, x₀, τ₁ τ₂'")
        
    # α, β, x0, τ1, τ2 = parameters
    
    xx = x-x0
    
    efunc       = lambda x, τ: np.exp(-x/τ)
    risefunc    = lambda x, τ: 1-efunc(x,τ)
    decayfunc   = efunc
    
    y = np.full_like(xx, 0.)
    
    
    if any(v == 0 for v in (τ1, τ2)):
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
    
    return y

def get_CB_scale_for_unit_amplitude(β:float,τ_rise:float, τ_decay:float, x0:float = 0.):
    efunc       = lambda x, τ: np.exp(-x/τ)
    risefunc    = lambda x, τ: 1-efunc(x,τ)
    decayfunc   = efunc
    
    xₘ = -τ_rise * np.log(τ_rise/(τ_rise + τ_decay)) + x0
    
    yₘ = risefunc(xₘ, τ_rise) * decayfunc(xₘ, τ_decay)
    peak = -1. if β < 0 else 1.
    
    return peak/yₘ

@modelfunction(parameter_names = ("α", "β0", "x0_0", "τ0_0", "τ0_1", "β1", "x0_1", "τ1_0", "τ1_1"))
def CBsum(x:np.ndarray | float, α:float | typing.Sequence[float], /, 
          β0:typing.Optional[float]=None, x0_0:typing.Optional[float]=None,
          τ0_0:typing.Optional[float]=None, τ0_1:typing.Optional[float]=None, 
          β1:typing.Optional[float]=None, x0_1:typing.Optional[float]=None, 
          τ1_0:typing.Optional[float]=None, τ1_1:typing.Optional[float]=None) -> np.ndarray | float:
    r"""Realizes a sum of two Clements_Bekkers_97 functions, on x.
    
    Let 𝒙 a 1D domain vector:
    
        𝒚₀ = α + β₀ * (1 - exp(-(x-x₀₀)/τ₀₀)) ⋅ exp(-(x-x₀₀)/τ₁₀)
        𝒚₁ = 0 + β₁ * (1 - exp(-(x-x₀₀)/τ₀₁)) ⋅ exp(-(x-x₀₁)/τ₁₁)
    
    Then:
    
        𝒚 = 𝒚₀ + 𝒚₁
        
    Empyrical model that can be used for fitting a compound AHP/ADP waveform as 
    a sum of two "alphafunctions".

    Parameters:
    ===========
    
    x: 1D domain vector (typically, time)
    
    parameters: a sequence (tuple, list) of model parameters in the following
        order:
    
        α, β₀, x₀₀, τ₀₀, τ₁₀, β₁, x₀₁, τ₀₁, τ₁₁

    """
    # NOTE: 2025-11-05 21:31:42
    # allow passing all parameters packed in a sequence, so as to do away with 
    # the *_model version of this function
    if isinstance(α, typing.Sequence) and len(α) == 9 and all(isinstance(v, float) for v in α):
        α, β0, x0_0, t0_0, t0_1, β1, x0_1, t1_0, t1_1 = α
        
    if not all(isinstance(v, float) for v in (α, β0, x0_0, τ0_0, τ0_1, β1, x0_1, τ1_0, τ1_1 )):
        raise TypeError("Expecting a sequence of 'α, β0, x0_0, τ0_0, τ0_1, β1, x0_1, τ1_0, τ1_1' scalar floats or a coma-separated list of scalar floats for 'α, β0, x0_0, τ0_0, τ0_1, β1, x0_1, τ1_0, τ1_1'")
        
    y0 = Clements_Bekkers_97(x, α, β0, x0_0, τ0_0, τ0_1)
    
    y1 = Clements_Bekkers_97(x, 0., β1, x0_1, τ1_0, τ1_1)
    
    return y0 + y1
    
@modelfunction(parameter_names = ("x0", "ρ", "β*", "τ*", "α"))
def exponential_rise_decays_product_biased_shifted(x:np.ndarray|float, *parameters:float,
                         **kwargs) -> np.ndarray|float:
    r"""Realization of a transient signal as a biased (α) product of one 
        exponential rise with constant ρ and a sum of 𝑛 exponential 
        decays with constants τ₀ … τₙ₋₁.
        All exponential terms are shifted by x₀; all exponential decay terms 
        are individually scaled (β):

        y = (1 - exp( -(x-x₀)/ρ ) × ( β₀     × exp( -(x-x₀)/τ₀)     + 
                                      β₁     × exp( -(x-x₀)/τ₁)     +
                                      .                             +
                                      .                             +
                                      βₙ₋₁   × exp( -(x-x₀)/τₙ₋₁ )) + α               (1)


        where:

            x₀          = shift ('onset', 'delay') of the transient; only makes 
                          sense when x0 >= 0
            ρ           = rising phase time constant; 
            β₀...βₙ₋₁   = scale for each of the n decay components;
            τ₀...τₙ₋₁   = time constant for each of the decay components;
            α           = bias, or offset (`DC' component)
            
        Typically used to model compound Ca²⁺ transient waveforms generated by a 
        sequence of events (e.g., pre- and post-synaptic spikes, etc, see 
        Tigaret et al, Nature Comms, 2016)
    
    Positional parameters:
    =====================
    
    x   =   the independent (predictor) data; represents the definition domain 
            for the model function e.g., a time vector, if modelling a time-
            varying process
            
            
    parameters = 1D numeric sequence (tuple, list, numpy array) with minimum five elements 
            such that len(parameters) satisfies 2 * n + 3 where n >=1 is the number of decays
            in the model.
            
            ATTENTION: ORDER OF MODEL PARAMETERS:
            
            For each decay component there are two parameters: 
            β (scale) and τ (decay constant).
            
            Model parameter values are interpreted to be given in the following order:
            
            β₀, τ₀, <β₁, τ₁, ...βₙ₋₁, τₙ₋₁>, α, ρ, x₀
            
            i.e., decay components are given in order (scale₀, decay₀, scale₁, decay₁, etc)
            followed by offset (o), rise time constant (r) and delay (x₀).
            
            For example, [β₀, τ₀, β₁, τ₁, α, ρ, x₀] specifies a transient signal 
            with two decay components, (β₀, τ₀, β₁, τ₁)
            
            The exponential constants (ρ, τ₀, τ₁, ...) and the shift x₀ are taken
            as having same physical units as x. The bias α is considered to have
            the same units as the result, and the scale parameters β are unitless.
    
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
    
    if isinstance(x, np.ndarray):
        x = np.squeeze(x)
    
    returnDecays = kwargs.pop("returnDecays", False)
    if len(parameters) == 1 and isinstance(parameters[0], typing.Sequence) and all(isinstance(v, float) for v in parameters[0]):
        parameters = parameters[0]
        
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

@modelfunction(parameter_names=("p*"))
def compound_exponential_rise_decays_product_biased_shifted(x:np.ndarray | float, *parameters, 
                                  returnDecays = False) -> np.ndarray | float:
    r"""Compound transient signal -- linear sum of delayed single transient signals
    Arguments:
        x = 1D predictor vector
        
        parameters = coefficient sequences where each sequence is as defined for
                    the `parameters` argument of exponential_rise_decays_product_biased_shifted
        
    Returns:
        y   = realization of the compound signal model curve
        yc  = list of individual transient models within the compound signal
        ycd = list of individual decay components
        
        NOTE: for a single-component EPSCaT, y and yc contain the same data
        
    """
    #print("parameters", parameters)
    
    if len(parameters) == 1 and isinstance(parameters[0], typing.Sequence):
        parameter = parameters[0]
    
    # NOTE: 2017-12-26 00:06:38
    # this is so that the function can be used with scipy.integrate.quad
    if isinstance(x, numbers.Real):
        y = 0
        #print("parameters: ", parameters)
        #print("x: ", x)
        for p in parameters:
            #print("p: ", p)
            y += exponential_rise_decays_product_biased_shifted(x, p)
        
        return y # NOTE: returns one scalar !!!
    
    else:
        if x.ndim > 1:
            raise ValueError("Vector x must have exactly one dimension (i.e., a column vector)")
        
        y = np.zeros(x.shape)
        
        yc = list()
        
        ycd = list()
        
        for p in parameters:
            #print("p", p)
            
            (yc_, ycd_) = exponential_rise_decays_product_biased_shifted_model(x, p, True)

            y += yc_
            
            yc.append(yc_)
            
            ycd.append(ycd_)

        if returnDecays:
            return y, yc, ycd
        
        else:
            return y, yc
        
@modelfunction(parameter_names=("γ", "ϵ", "χ", "σ"))
def Markwardt_Nilius(x:np.ndarray|float, γ:typing.Sequence[float]|float, /,
                     ϵ:typing.Optional[float]=None, 
                     χ:typing.Optional[float]=None, 
                     σ:typing.Optional[float]=None) -> np.ndarray | float:
    r"""Markwardt & Nilius model for voltage-gated Ca2+ channels I-V relationship
    
    Implements:
    
            y = γ × (x - ϵ) / ( 1 + exp(-(x-χ)/σ))
    
    See Markwardt & Nilius (1988), J Physiol (London)
    
    Parameters:
    ========== 
    x   = column vector (np.array) with membrane voltage (Vm) data
    
    The model parameters are (real scalars, corresponding to units in parentheses):
    
    γ  = slope conductance (nS)
    
    ϵ  = extrapolated reversal potential (mV) of the current (from slope conductance)
        i.e. same as the Thevenin equivalent e.m.f.
        
    
    χ  = the "delay"
    
    σ  = slope parameter of Ca2+ channel activation (mV)
    
    Returns:
    ======== 
    
    A column vector Im = f(Vm) were f is the Markwardt & Nilius model
    
    """
    # v  = Vm at half-maximal current activation (mV) (i.e. taken on the rising 
    #     region of the I(V) curve)
    
    if isinstance(γ, typing.Sequence) and len(γ) == 4 and all(isinstance(v, float) for v in γ):
        γ, ϵ, χ, σ = check_unpack_model_params_seq(γ, 4)
        # γ, ϵ, χ, σ = γ
        
    if not all(isinstance(v, float) for v in (γ, ϵ, χ, σ)):
        raise TypeError("Expecting a comma-separated list of four float scalars or a sequence of four float scalars")
    
    y = γ * (x - ϵ) / (1 + np.exp(-(x-χ)/σ))
    
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

@modelfunction(parameter_names = ("a", "b", "c", "x0"))
def Talbot_Sayer(x:typing.Union[float, np.ndarray], a:typing.Union[float, typing.Sequence[float]], /,
                 b:typing.Optional[float]=None, c:typing.Optional[float]=None, 
                 x0:typing.Optional[float]=None, **kwargs) -> np.ndarray | float:
    r"""
    Talbot & Sayer model for voltage-gated Ca2+ channels I-V relationship.
    
    Boltzman squared, multiplied by Goldman-Hogdkin-Katz, 
    see Talbot & Sayer 1996, J. Neurophysiol. 76(3):2120-2124
    
    Positional parameters:
    =====================
    
    x   = 1D numpy array (vector): definition domain (e.g. membrane voltage) ↦ Voltage units
    
    a   = real: initial value for Boltzman slope factor ↦ pq.dimensionless
    
    b   = real: initial scale value ↦ mV × mM / pA  = kg × mol/(m × s³ × A²)
                                                    = kg × mol/(m × s³ × C² × s⁻²)
    
    c   = real: initial value for internal Ca2+ concentration ↦ concentration units (typically, mM)
    
    x0  = real: initial value of onset ("shift") ↦ units of 'x' (i.e., Voltage)
    
    Var-keyword parameters 
    ======================
    
    t   = python quantity: temperature in degrees Celsius (degC); default: 33 degC
    
    o   = python quantity: external Ca²⁺ concentration, in mM; default: 2.5 mM
    
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
    # t = 33 * pq.degC, o = 2.5 * pq.mM):
    from scipy import constants
    
    # default values
    t_ = 33
    o = 2.5 * pq.mM
    
    if isinstance(a, typing.Sequence) and len(i) == 4 and all(isinstance(v, (float, pq.Quantity)) for v in i):
        a, b, c, x0 = check_unpack_model_params_seq(a, 4)
    
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
    # NOTE: 2025-12-02 21:08:00
    # dimensional analysis:
    # k * (x-x0) = 1/V * V = dimensionless
    boltzmann = 1 / (1 + np.exp(-a * k.magnitude * (x-x0)))**2 # ↦ pq.dimensionless
    
    ghkexp = np.exp(-2 * x * k.magnitude) # ↦ pq.dimensionless (see NOTE: 2025-12-02 21:08:00)
    
    # Goldman-Hogkin-Katz current equation
    ghk = x * b * (c - o.magnitude * ghkexp) / (1-ghkexp)

    return boltzmann * ghk # ↦ Current units (typically, pA)

@modelfunction(parameter_names = ("α*", "β*", "σ*", "δ"))
def gaussianSum1D(x:np.ndarray | float, *args, **kwargs) -> np.ndarray | float:
    r""" Sum of shifted Gaussians in 1D.
    
    Implements:
    
        y = α₀   × exp(-((x-β₀)/σ₀)²) + 
            α₁   × exp(-((x-β₁)/σ₁)²) + 
            ⋮
            αₖ   × exp(-((x-βₖ)/σₖ)²) +
            ⋮
            αₙ₋₁ × exp(-((x-βₙ₋₁)/σₙ₋₁)²) + 
            δ
            
        for a sum of shifted n+1 1D Gaussians on top of a common offset δ
    
        Model parameters: 
        α₀ ⋯ αₙ₋₁ : scales for each Gaussian
        β₀ ⋯ βₙ₋₁ : shift of each Guassian on the 'x' axis
        σ₀ ⋯ σₙ₋₁ : "spread" of each Gaussian
        δ         : common offset in 'y' axis
        
    
    Parameters:
    ==========
    
    x = 1D numpy array: the domain of definition
    
    Var-positional parameters:
    ==========================
    
    EXACTLY n * 3 + 1 elements: α₀, β₀, σ₀, …, αₖ, βₖ, σₖ, ... αₙ₋₁, βₙ₋₁, σₙ₋₁, δ
    
    for n 1D Gaussian curves
    
    If packed in a sequence, it can be unpacked by passing it as a starred expression
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
        α, β, γ = args[slice(k*3, k*3+3)]
        ygauss[:,k] = α * np.exp(-((x-β)/γ)**2)
        
    ret = np.nansum(ygauss, axis=1) + args[-1]
    
    #print("return shape: ", ret.shape)
    
    if components:
        return ret, ygauss + args[-1]
    
    return ret
    
@modelfunction(parameter_names=("τ", "x0"))
def Frank_Fuortes(x:np.ndarray | float, 
                  τ:float | typing.Sequence[float], /,  
                  x0: typing.Optional[float] = None) -> np.ndarray | float:
    r""" Frank & Fuortes 1956 expression Irh/I = 1 - exp(-(t-t0)/tau)
    
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
    if isinstance(τ, typing.Sequence) and len(τ) == 2 and all(isinstance(v, float) for v in τ):
        τ, x0 = τ
        
    if not all(isinstance(v, float) for v in (τ, x0)):
        raise TypeError("Expecting a sequence of two float scalars or a comma-separated list of two scalars")

    return 1-np.exp(-(x-x0)/tau)

@modelfunction(parameter_names=("irh", "τ", "x0"))
def Frank_Fuortes2(x:np.ndarray | float, irh:typing.Sequence[float] | float, /,
                   τ:typing.Optional[float] = None, 
                   x0: typing.Optional[float] = None) -> np.ndarray | float:
    r""" Implements 1/I = (1-exp(-t/tau)) / Irh 
    
    By rearranging the Frank & Fuortes 1956 equation
    one can also get a fitted value for Irheobase 
    
    1/I = (1-exp(-t/τ)) / Irh                                     (2)
    
    where t = x - x0
    
    References:
    
    Frank & Fuortes (1956) Stimulation of spinal motoneurones with 
    intracellular electrodes. J.Physiol. 134, 451-470
    """
    if isinstance(irh, typing.Sequence) and len(irh) == 3 and all(isinstance(v, float) for v in irh):
        irh, τ, x0 = irh
        
    if not all(isinstance(v, float) for v in (irh, τ, x0)):
        raise TypeError("Expecting a sequence of three float scalars or a comma-separated list of three scalars")
    
    return (1-np.exp(-(x-x0)/τ)) / irh

@modelfunction(parameter_names=("x0", "κ"))
def Boltzmann(x:np.ndarray | float, x0:typing.Sequence[float] | float, /,
              κ:typing.Optional[float] = None,
              pos:bool=True) -> np.ndarray | float:
    r""" Boltzmann function:

Realises y = 1/(1+exp(±(x₀ - x)/κ))

Parameters:
==========
x: float scalar (e.g., membrane voltage)

p: array-like, with two float elements: x₀ and κ (in THIS order)

pos: bool, optional (default is True) — the sign of the exponent:
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
    if isinstance(x0, typing.Sequence) and len(x0)==2 and all(isinstance(v, float) for v in x0):
        x0, κ = z0
    
    # sign of ξ
    ξ = x0 - x if pos else x - x0
    ξ /= κ
    return 1/(1+np.exp(ξ))
    
@modelfunction(parameter_names=("x0", ))
def Heaviside(x:np.ndarray|float, 
              x0:typing.Union[float, pq.Quantity], /, 
              α:bool=True) -> np.ndarray | float:
    r"""Heaviside (step) function:
    
    Step transition between two levels (0 and 1)
    
    Parameters:
    ===========
    x: domain vector
    x0: coordinate of the step change (in domain space)
    α: bool, default is True.
        Flag for the direction of step change:
        True (default) → 0 → 1 transition
        False ⇒ transition 1 → 0
        
    """
    from core.datatypes import is_vector
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
            if not scq.unitsConvertible(x,x0):
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
    
@modelfunction(parameter_names=("x0",))
def Heaviside2(x:np.ndarray|float, 
              x0:typing.Union[float, pq.Quantity], 
              level0:float=0., level1:float=1.) -> np.ndarray | float:
    """Heaviside (step) function - general version
    
    Step transition from level0 to level1. by default the levels are
    0. and 1. (floats)
    
    Parameters:
    ===========
    x: domain vector
    x0: coordinate of the step change (in domain space)
    level0, level1:float; optional, defaults are 0 and 1, respectively
        The initial and the final level of the step function.
        
    """
    from core.datatypes import is_vector
    
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
            if not scq.unitsConvertible(x,x0):
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
    
@modelfunction(parameter_names = ("x0", "x1"))
def boxcar(x:np.ndarray | float, x0:typing.Union[typing.Sequence[float], float], /, 
           x1:typing.Optional[float]=None, up_first:bool=True) -> np.ndarray | float:
    r"""Boxcar function: 
Two successive Heaviside (step) functions of opposite directions"""
    # x0, x1 = p
    x0, x1 = check_unpack_model_params_seq(x0, 2)
    
    ud = [True, False] if up_first else [False, True]
    
    if x0 < x1:
        # print(f"x0 < x1 {x0 < x1}; up_first: {up_first}")
        #       up then down                                                        down then up
        return Heaviside(x, x0, ud[0]) * Heaviside(x, x1, ud[1])# if up_first else Heaviside(x, x0, False) + Heaviside(x, x1, True)
        
    else:
        print(f"x0 >= x1 {x0 >= x1}; up_first: {up_first}")
        return Heaviside(x, x0, ud[0]) * Heaviside(x, x1, ud[1])# if up_first else Heaviside(x, x1, False) + Heaviside(x, x0, True)

@modelfunction(parameter_names = ("x0", "x1"))
def boxcar2(x:np.ndarray | float, x0:typing.Union[typing.Sequence[float], float], /, 
            x1:typing.Optional[float]=None,
            level0:float=0., level1:float=1.) -> np.ndarray | float:
    r"""Boxcar function:
Two successive Heaviside2 (step) functions (general versions) in opposite directions"""
    x0, x1 = check_unpack_model_params_seq(x0, 2)
    
    return Heaviside2(x, x0, level0, level1) + Heaviside2(x, x1, level1, level0)

@modelfunction(parameter_names = ("x0", "y0", "x1", "y1"))
def ramp(x:typing.Union[float, np.ndarray], x0:typing.Union[float, np.ndarray], /, 
         y0=None, x1=None, y1=None) -> np.ndarray | float:
    r"""Linear ramp from (x₀, y₀) to (x₁, y₁)
    defaults are  = (0., 0., 1., 1.))

Parameters:
===========

x: the domain vector (e.g. time vector) - numpy array
p: the parameters in the specific order: (x₀, y₀, x₁, y₁)

"""
    if isinstance(x0, typing.Sequence) and len(x0) == 4:
        x0, y0, x1, y1 = check_unpack_model_params_seq(x0, 4)
    
    if isinstance(x, pq.Quantity):
        if isinstance(x0, pq.Quantity):
            if not scq.unitsConvertible(x,x0):
                raise TypeError(f"x and x0 have incompatible units")
            
            if x.units != x0.units:
                x0 = x0.rescale(x.units)
                
            x0 = x0.magnitude.flatten()[0]

        if isinstance(x1, pq.Quantity):
            if not scq.unitsConvertible(x,x1):
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
    
def model_parameter_names(func) -> list[str]:
    r"""WARNING: on its way to become DEPRECATED 
    Model functions should be defined using the @modelfunction decorator
    (see function modelfunction(…) in this module)
    """
    sig_dict = signature_as_dict(func)
    names = list()
    if len(sig_dict["positional"]) > 1:
        names.extend(list(sig_dict["positional"].keys())[1:])
        
    if len(sig_dict["named"]):
        names.extend(list(sig_dict["named"]))
        
    return names
        

def is_modelfunction(func:typing.Callable):
    if not isinstance(func, typing.Callable):
        return False
    
    return isinstance(getattr(func, "model_function", None), bool) and isinstance(getattr(func, "nvars", None), int)

def get_default_parameter_values(func:typing.Callable) -> pd.DataFrame | None:
    if not is_modelfunction(func):
        raise TypeError(f"{func} is not a model function")
    
    if len(func.parameter_names) <= 0:
        pass
