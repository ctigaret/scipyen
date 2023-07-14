import os, sys

import matplotlib as mpl

from .scipyenviewer import (ScipyenViewer, ScipyenFrameViewer,)
from .dictviewer import DataViewer
from .matrixviewer import MatrixViewer
from .imageviewer import ImageViewer
from .signalviewer import SignalViewer
from .tableeditor import TableEditor
from .textviewer import TextViewer
from .xmlviewer import XMLViewer
# from .widgets.breadcrumb_nav import Navigator


# NOTE: 2022-12-25 23:19:16
# plugins framework takes care of this
# gui_viewers = {DataViewer, MatrixViewer, ImageViewer, SignalViewer, 
#                TableEditor, TextViewer, XMLViewer}
#gui_viewers = [ScipyenViewer, ScipyenFrameViewer, DataViewer, MatrixViewer, ImageViewer, SignalViewer, 
               #TableEditor, TextViewer, XMLViewer]
