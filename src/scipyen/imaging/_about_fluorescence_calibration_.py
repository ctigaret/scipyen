# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
    Extract from Helmchen (2011) CSH Protocols RE: Ca²⁺ indicators
    
    F = Φ⋅Q_D⋅Q_F⋅α⋅𝐼₀⋅n = S⋅n, where:
    
    F: fluorescence intensity from an observation volume V
    n: molar amount of dye molecules in V (i.e., number of moles in V - might as well be the dye concentration)
    𝐼₀: illumination intensity
    α: dye absorption
    Q_F: quantum yield of the dye
    Φ: photon collection efficiency of the optical setup
    Q_D: quantum efficiency of the detector
    
    S: proportionality constant resulted from the multiplicaton of factors that 
        depend on dye properties or the experimental setup:
        
        S = Φ⋅Q_D⋅Q_F⋅α⋅𝐼₀
        
    For Ca²⁺ indicators:
        𝒏f: molar amount of free indicator 
        𝒏b: molar amount of Ca²⁺-bound indicator
        𝒏ₜ: total molar amount of indicator = 𝒏f + 𝒏b
        
        It follows that:
            at 0 Ca²⁺ concentration: 𝒏f = 𝒏ₜ
            at saturating Ca²⁺ concentration: 𝒏b = 𝒏ₜ
        
        These have different quantum yields => different "S" factors: 
        
        F   = Sf ⋅ 𝒏f + Sb ⋅ 𝒏b
            = Fmin + (Sb - Sf)/𝒏b
            = Fmax - (Sb - Sf)/𝒏f, 
            
            where:
            
            Fmin = Sf ⋅ 𝒏ₜ: fluorescence at 0 Ca²⁺ concentration, and
            Fmax = Sb ⋅ 𝒏ₜ: fluorescence at saturating Ca²⁺ concentration,
            
            assuming a fluorescence increase upon Ca²⁺ binding (i.e., bound 
            indicator has a higher quantum yield).
            
    Assuming 1:1 complexation of Ca²⁺ with the dye, the law of mass action is:
    
        Kd = 𝒏f ⋅ [Ca²⁺]ᵢ / 𝒏b: the dissociation constant of the indicator
        
    
    Dye concentration
    
    Assuming all dye molecules sense the same illumination intensity (no inner 
    filtering condition):
    
    The intensity of light that is absorbed by a layer of fluorescent dye 
    of thickness 𝒍:
    
        𝑰abs =  𝑰₀(1-10ᵋˡᶜ) ≈ 𝑰₀ ln(10)ε𝒍𝒄
        
            ε: molar extinction coefficient, ranging betwen 20,000-100,000 M⁻¹cm⁻¹
            c: dye concentration
            
            This linear approximation of 𝑰abs and 𝒄 is valid for 𝒄 << [ln(10)ε𝒍]⁻¹
            
            thus setting an upper limit of the useful dye concentration (!):
            
            • for cells with ⌀ 10 μm the concentration shoud be well below 5-20 mM
            
            • for thick cuvettes is ∼ 1 cm path length the dye should bemore diluted,
            typically 1 μM
            
    Background subtraction:
    
    Any background fluorescence 𝑭bkg must be subtracted from the observed fluorescence:
    
    𝑭 = 𝑭obs - 𝑭bkg
    
    before applying any conversion to [Ca²⁺]ᵢ
    
    𝑭bkg must be measured throughout the experiment in a slice region nearby the
    cell of interest, directly before and after the recording experiment.
    
    Se ealso Chen et al 2006 In Situ Background Estimation in Quantitative Fluorescence Imaging
        
        
        
        
    
    
    
    
    
    
    

"""
