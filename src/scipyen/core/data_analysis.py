# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

'''
Frequently used data analysis functions
TODO Bring here generic versions of frequently used data analysis routines
from CaTanalysis and ephys
'''

import pandas as pd

def normalizeDataFrameVariables(data, parameter, 
                                normalising_level, 
                                normalising_reference_category,
                                normlaised_target_categories,
                                return_columns,inplace=True):
    """
    TODO
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas Data Frame; got %s instead" % type(data).__name__)
    
    if isinstance(parameter, str):
        if parameter not in data.columns:
            raise KeyError("parameter %s not found in data columns" % parameter)
        
        params = [parameter]
        
    elif isinstance(parameter, (tuple, list)) and all([isinstance(p, str) for p in parameter]):
        if any([p not in data.columns for p in parameter]):
            raise ValueError("some parameters in %s not found in data columns" % repr(parameter))
        
        params = [p for p in parameter]
        
    norm_series_names = ["%s_norm_to_%s" % (p, normalising_reference_category) for p in params]
    
    norm_series = [pd.Series(np.nan, index = data.index, name=n) for n in norm_series_names]
    
    
def anova_table(aov):
    """Auguments ANOVA table produced by statsmodels.stats.anova_lm.
    
    Includes meas squares and effect sizes (eta squared and omega squared)
    """
    aov['mean_sq'] = aov[:]['sum_sq']/aov[:]['df']

    aov['eta_sq'] = aov[:-1]['sum_sq']/sum(aov['sum_sq'])

    aov['omega_sq'] = (aov[:-1]['sum_sq']-(aov[:-1]['df']*aov['mean_sq'][-1]))/(sum(aov['sum_sq'])+aov['mean_sq'][-1])

    cols = ['sum_sq', 'df', 'mean_sq', 'F', 'PR(>F)', 'eta_sq', 'omega_sq']
    aov = aov[cols]
    return aov

