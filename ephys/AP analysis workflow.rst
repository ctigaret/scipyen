AP analysis workflow
====================

#. Record abf files: one current injection step per sweep.
#. Load abf files in scipyen: each block contains a series of current injection steps (as above)

#. call

>>> ephys.membrane.analyse_AP_step_injection_series()
