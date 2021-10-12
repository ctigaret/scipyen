"""Collection of functions to read/write to HDF5 files
To avoid circular module dependencies, this module should be imported
independently from pictio.

    NOTE: 2021-10-12 09:29:38

    ==============
    Design notes:
    ==============

    An object is the HDF5 File root (/)
    
    Instance attributes & properties (but NEITHER methods, NOR :class: attributes)
    correspond to the following HDF5 structures:
    
    Python types:               HDF5 Structure:          Attribute:
    ============================================================================
    bool and numeric scalars    dataset                 "type": type's name
    sequences (list, tuple)     
    str                         
    
    
    
    
    
"""

import numpy as np
import quantities as pq
import neo
import pandas as pd
import vigra
import h5py
from core.prog import safeWrapper
from core.traitcontainers import DataBag
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datatypes import (TypeEnum,UnitTypes, Genotypes, arbitrary_unit, pixel_unit, 
                            channel_unit,
                            space_frequency_unit,
                            angle_frequency_unit,
                            custom_unit_symbols,
                            unit_quantity_from_name_or_symbol,
                            day_in_vitro,
                            week_in_vitro, postnatal_day, postnatal_month,
                            embryonic_day, embryonic_week, embryonic_month,
                            )
from core.modelfitting import (FitModel, ModelExpression,)
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.triggerprotocols import TriggerProtocol
from imaging.axiscalibration import AxisCalibration
from imaging.indicator import IndicatorCalibration
from imaging.scandata import (AnalysisUnit, ScanData,)
from gui.pictgui import (Arc, ArcMove, CrosshairCursor, Cubic, Ellipse, 
                         HorizontalCursor, Line, Move, Quad, Path, 
                         PlanarGraphics, Rect, Text, VerticalCursor,)

