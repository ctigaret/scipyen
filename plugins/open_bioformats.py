from __future__ import print_function


import os, collections, bioformats as bf

import pictio as pio # this works, because by the time this module is loaded pictiio is already in sys modules

from PyQt5 import QtGui, QtCore, QtWidgets

def open_with_bioformats(fileName=None):
    ret = None
    if fileName is None:
        bf_extensions = bf.READABLE_FORMATS
        
        fileFilt = 'BioFormats Image Types (' + ' '.join([''.join(i) for i in zip('*' * len(bf.READABLE_FORMATS), '.'*len(bf.READABLE_FORMATS), bf.READABLE_FORMATS)]) +');;' +\
                    ';;'.join('{I} (*.{i});;'.format(I=i.upper(), i=i) for i in bf.READABLE_FORMATS)
        
        fileName = str(QtWidgets.QFileDialog.getOpenFileName(None, caption=u'Open Image File Using BioFormats', filter=fileFilt))
        
    if len(fileName) > 0:
        imgBaseName = os.path.splitext(os.path.basename(fileName))[0]
        ret = pio.openImageFile(fileName, useBioFormats=True)
                
    return ret

open_with_bioformats.__setattr__('__annotations__', {'return':'ret', 'fileName':str})

def init_pict_plugin():
    return {'File|Open|Image Using BioFormats': open_with_bioformats}

