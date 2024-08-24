# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import (safeWrapper, deprecation, iter_attribute,
                       filter_type, filterfalse_type, 
                       filter_attribute, filterfalse_attribute,
                       filter_attr, filterfalse_attr)
from core.sysutils import adapt_ui_path
from core.vigra_patches import vigra
from gui import pictgui as pgui
from gui.pyqtgraph_patch import pyqtgraph as pgraph
from gui import painting_shared
from collections import ChainMap, namedtuple, defaultdict

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_GraphicsImageViewerWidget, QWidget = __loadUiType__(adapt_ui_path(__module_path__,'graphicsimageviewer.ui'))

class GraphicsImageViewerScene(QtWidgets.QGraphicsScene):
    signalMouseAt = Signal(int,int,name="signalMouseAt")
    
    signalMouseLeave = Signal()
    
    def __init__(self, gpix=None, rect = None, **args):
        if rect is not None:
            super(GraphicsImageViewerScene, self).__init__(rect = rect, **args)
            
        else:
            super(GraphicsImageViewerScene, self).__init__(**args)
            
        self.__gpixitem__ = None
        
        self.graphicsItemDragMode=False

    ####
    # public methods
    ####
    
    @property
    def rootImage(self):
        return self.__gpixitem__
    
    @rootImage.setter
    def rootImage(self, gpix):
        if gpix is None:
            return
        
        if self.__gpixitem__ is not None:
            super().removeItem(self.__gpixitem__)
            
        nItems = len(self.items())
        
        super().addItem(gpix)
        
        if nItems > 0:
            gpix.setZValue(-nItems-1)
            
        self.setSceneRect(gpix.boundingRect())
        gpix.setVisible(True)
        self.__gpixitem__ = gpix
        #self.__gpixitem__.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        
    def clear(self):
        super(GraphicsImageViewerScene, self).clear()
        self.__gpixitem__ = None
        
    def setRootImage(self, gpix):
        #print("scene setRootImage: %s" % gpix)
        self.rootImage=gpix
        
    def addItem(self, item, picAsRoot=True):
        #print("scene addItem %s" % item)
        if isinstance(item, QtWidgets.QGraphicsPixmapItem) and picAsRoot:
            self.rootImage = item
        else:
            super().addItem(item)
            item.setVisible(True)
            
    def mouseMoveEvent(self, evt):
        """Emits signalMouseAt(x,y) if event position is inside the scene.
        """
        
        if self.__gpixitem__ is None:
            return
        
        if self.sceneRect().contains(evt.scenePos().x(), evt.scenePos().y()):
            self.signalMouseAt.emit(int(evt.scenePos().x()), int(evt.scenePos().y()))
            
        else:
            self.signalMouseLeave.emit()
            
        super().mouseMoveEvent(evt)
        evt.accept()
        
    def mousePressEvent(self, evt):
        super().mousePressEvent(evt)
        evt.accept()
        
        
    def mouseReleaseEvent(self, evt):
        super().mouseReleaseEvent(evt)
        evt.accept()
        
    def hoverMoveEvent(self, evt):
        if self.__gpixitem__ is None:
            return
        
        super().event(evt)
        
        if self.sceneRect().contains(evt.pos().x(), evt.pos().y()):
            self.signalMouseAt.emit(int(evt.pos().x()), int(evt.pos().y()))
            
    def wheelEvent(self, evt):
        evt.ignore()
        
class GraphicsImageViewerWidget(QWidget, Ui_GraphicsImageViewerWidget):
    """
    A simple image view widget based on Qt5 graphics view framework
    
    The widget does not own the data but a pixmap copy of it; therefore data values 
    under the cursors must be received via signal/slot mechanism from the parent window.
    Signals from the underlying scene are exposed as public APIand shoul be connected
    to appropriate slots in the container window
    """
    
    # NOTE: 2017-03-23 13:55:36
    # While in C++ I had subclassed the QGraphicsView to a custom derived class
    # in python/PyQt5 I cannot "promote" the QGraphicsView widget in the
    # UI class to this derived class
    # TODO Therefore the functionality of said derived class must be somehow 
    # implemented here
    
    # TODO add functionality from ExtendedImageViewer class
    
    
    ####
    # signals
    ####
    signalMouseAt             = Signal(int, int, name="signalMouseAt")
    signalCursorAt            = Signal(str, list, name="signalCursorAt")
    signalZoomChanged         = Signal(float, name="signalZoomChanged")
    signalCursorPosChanged    = Signal(str, "QPointF", name="signalCursorPosChanged")
    signalCursorLinkRequest   = Signal(pgui.GraphicsObject, name="signalCursorLinkRequest")
    signalCursorUnlinkRequest = Signal(pgui.GraphicsObject, name="signalCursorUnlinkRequest")
    signalCursorAdded         = Signal(object, name="signalCursorAdded")
    signalCursorChanged       = Signal(object, name="signalCursorChanged")
    signalCursorRemoved       = Signal(object, name="signalCursorRemoved")
    signalGraphicsObjectSelected      = Signal(object, name="signalGraphicsObjectSelected")
    signalRoiAdded            = Signal(object, name="signalRoiAdded")
    signalRoiChanged          = Signal(object, name="signalRoiChanged")
    signalRoiRemoved          = Signal(object, name="signalRoiRemoved")
    signalRoiSelected         = Signal(object, name="signalRoiSelected")
    signalGraphicsDeselected  = Signal()
    
    ####
    # constructor
    ####
    
    def __init__(self, img=None, parent=None, imageViewer=None):
        super(GraphicsImageViewerWidget, self).__init__(parent=parent)
        
        # NOTE: 2021-05-08 10:46:01 NEW API
        self._planargraphics_ = list()
        
        self.__zoomVal__ = 1.0
        self._minZoom__ = 0.1
        self.__maxZoom__ = 100
        
        self.__escape_pressed___ = False
        self.__mouse_pressed___ = False
        
        self.__last_mouse_click_lmb__ = None
        
        self.__interactiveZoom__ = False
        
        self.__defaultCursorWindow__ = 10.0
        self.__defaultCursorRadius__ = 0.5

        self.__cursorWindow__ = self.__defaultCursorWindow__
        self.__cursorRadius__ = self.__defaultCursorRadius__

        
        # NOTE: 2017-08-10 13:45:17
        # make separate dictionaries for each roi type -- NOT a chainmap!
        self._graphicsObjects_ = dict([(k.value, dict()) for k in pgui.PlanarGraphicsType])
        
        # grab dictionaries for cursor types in a chain map
        cursorTypeInts = [t.value for t in pgui.PlanarGraphicsType if \
            t.value < pgui.PlanarGraphicsType.allCursorTypes]
        
        self.__cursors__ = ChainMap() # almost empty ChainMap
        self.__cursors__.maps.clear() # make sure it is empty
        
        for k in cursorTypeInts:    # now chain up the cursor dictionaries
            self.__cursors__.maps.append(self._graphicsObjects_[k])
        
        # do the same for roi types
        roiTypeInts = [t.value for t in pgui.PlanarGraphicsType if \
            t.value > pgui.PlanarGraphicsType.allCursorTypes]
        
        self.__rois__ = ChainMap()
        self.__rois__.maps.clear()
        
        # NOTE: 2017-11-28 22:25:33
        # maps attribute is a list !!!
        # would ChainMap.new_child() be more appropriate, below?
        for k in roiTypeInts:
            self.__rois__.maps.append(self._graphicsObjects_[k])

        
        self.selectedCursor = None
        
        self.selectedRoi = None
        
        # NOTE: 2017-06-27 23:10:05
        # hack to get context menu working for non-selected cursors
        self._cursorContextMenuSourceId = None 
        
        
        self.__scene__ = GraphicsImageViewerScene(parent=self)
        self.__scene__.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        
        self._configureUI_()
        
        self._imageGraphicsView.setScene(self.__scene__)
        
        if img is not None:
            if isinstance(img, QtGui.QImage):
                self.__scene__.rootImage = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(img))
                
            elif isinstance(img, QtGui.QPixmap):
                self.__scene__.rootImage = QtWidgets.QGraphicsPixmapItem(img)

        self.__image_viewer__ = imageViewer
        
    ####
    # private methods
    ####
    
    def _configureUI_(self):
        self.setupUi(self)
        self._imageGraphicsView.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self._imageGraphicsView.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self._imageGraphicsView.setBackgroundBrush(QtGui.QBrush(painting_shared.make_transparent_bg(size=24)))
        self._topLabel.clear()
        
    def _zoomView(self, val):
        self._imageGraphicsView.resetTransform()
        self._imageGraphicsView.scale(val, val)
        self.__zoomVal__ = val
        self.signalZoomChanged[float].emit(self.__zoomVal__)
        
    def _removeGraphicsObject(self, o):
        """Removes a GraphicsObject from the scene.
        A GraphicsObject is a frontend to a PlanarGraphics object.
        CAUTION: This function only removes the frontent (a Qt graphics item);
        the widget stil retains a reference to the PlanarGraphics backend of 
        the removed GraphicsObject! Furthermore, the PlanarGraphics itself
        still retains a reference to the GraphicsObject. Most likely you don't
        want this.
    
        For the most general case use _removePlanarGraphics method.
        """
        o.backend.frontends.clear()
        self.scene.removeItem(o)
        if isinstance(o.backend, pgui.Cursor):
            self.signalCursorRemoved.emit(o.backend)
            if self.selectedCursor is o:
                self.selectedCursor = None
        else:
            self.signalRoiRemoved.emit(o.backend)
            if self.selectedRoi is o:
                self.selectedRoi = None
        
    def _removeSelectedPlanarGraphics(self, cursors:bool=True):
        if cursors and self.selectedCursor:
            self._removeGraphicsObject(self.selectedCursor)
            
        elif self.selectedRoi:
            self._removeGraphicsObject(self.selectedRoi)
            
    def _removeAllPlanarGraphics(self, cursors:typing.Optional[bool] = None):
        predicate = lambda x: isinstance(x.backend, pgui.Cursor)
        
        if isinstance(cursors, bool):
            if cursors:
                objs = [o for o in filter(predicate, self.graphicsObjects)]
            else:
                objs = [o for o in itertools.filterfalse(predicate, self.graphicsObjects)]
                
        else:
            objs = self.graphicsObjects
            
        for o in objs:
            self._removeGraphicsObject(o)

    def _removePlanarGraphics(self, name:typing.Optional[str]=None,
                              cursors:typing.Optional[bool]=None):
        """Removes a PlanarGraphics object by its name.
        Optionally, the operation can be restricted to cursors or non-cursors
        (i.e., ROIs).
        """
        if cursors is None:
            objs = list(self.planarGraphics)
            
        elif isinstance(cursors, bool):
            if cursors:
                objs = list(self.graphicsCursors)

            else:
                objs = list(self.rois)

        else:
            raise TypeError(f"'cursors' flag expected to be None, or a bool; instead, got {type(cursors).__name__}")
        
        if len(objs) == 0:
            scipywarn("There are no planar graphics in this viewer")
            return
                
        objNames = [o.name for o in objs]
        
            
        if isinstance(name, (tuple, list)) and len(name) and all([isinstance(n, str) and len(n.strip())]):
            objIds = name
            
        elif isinstance(name, str) and len(name.strip()):
            objIds = [name]
            
        else:
            dlgTitle = "Remove %ss" % "cursor" if cursors else "ROI"
            
            selectionDialog = ItemsListDialog(self, objNames,
                                                title = dlgTitle,
                                                selectmode = QtWidgets.QAbstractItemView.MultiSelection)
            
            ans = selectionDialog.exec_()
            
            if ans != QtWidgets.QDialog.Accepted:
                return
            
            objIds = selectionDialog.selectedItemsText # this is a list of str
            
        if len(objIds) == 0:
            return
        
        # print(f"{self.__class__.__name__}._removePlanarGraphics:\n\tobjIds = {objIds}")
        oo = [o for o in filter(lambda x: x.backend.name in objIds, self.graphicsObjects)]
        
        # print(f"{self.__class__.__name__}._removePlanarGraphics:\n\too = {oo}")
        
        # if cursors:
        #     objs = [o for o in filter(lambda x: isinstance(x.backend, pgui.Cursor) and x.backend.name in objIds, self.graphicsObjects)]
        # else:
        #     objs = [o for o in filter(lambda x: not isinstance(x.backend, pgui.Cursor) and x.backend.name in objIds, self.graphicsObjects)]
        
        if self.selectedCursor in oo:
            self.selectedCursor = None
        if self.selectedRoi in oo:
            self.selectedRoi = None
            
        # if cursors:
        #     if self.selectedCursor in oo:
        #         self.selectedCursor = None
        # else:
        #     if self.selectedRoi in oo:
        #         self.selectedRoi = None
            
        for o in oo:
            self._removeGraphicsObject(o)
                
        
    def _cursorEditor(self, crsId:str=None):
        if len([o for o in self.graphicsCursors]) == 0:
            return
        
        if not isinstance(crsId, str) or len(crsId.strip()) == 0:
            selectionDialog = ItemsListDialog(self, sorted([c.name for c in self.graphicsCursors]), "Select cursor")
            
            a = selectionDialog.exec_()
            
            if a == QtWidgets.QDialog.Accepted:
                crsId = selectionDialog.selectedItemsText
            else:
                return

            if len(crsId) == 0:
                return
        
            crsId = crsId[0]
        
        cursor = [o for o in filter(lambda x: isinstance(x.backend, pgui.Cursor) and x.backend.name == crsId, self.graphicsObjects)]
        
        if len(cursor) == 0:
            return
        
        cursor = cursor[0]
        
        d = quickdialog.QuickDialog(self, "Edit cursor %s" % cursor.name)

        d.promptWidgets = list()
        
        namePrompt = quickdialog.StringInput(d, "New label:")
        namePrompt.variable.setClearButtonEnabled(True)
        namePrompt.variable.redoAvailable=True
        namePrompt.variable.undoAvailable=True
        namePrompt.setText(crsId)
        
        d.promptWidgets.append(namePrompt)
        
        showsPositionCheckBox = quickdialog.CheckBox(d, "Label shows position")
        showsPositionCheckBox.setChecked(cursor.labelShowsPosition)
        
        
        d.promptWidgets.append(showsPositionCheckBox)
        
        showsOpaqueLabel = quickdialog.CheckBox(d, "Opaque label")
        showsOpaqueLabel.setChecked(not cursor.hasTransparentLabel)
        
        d.promptWidgets.append(showsOpaqueLabel)
        
        # NOTE: 2021-05-04 15:53:58
        # old style type checks based on PlanarGraphicsType kept for backward compatibility
        # NOTE: 2021-05-10 14:27:11 transition to complete removal or PlanarGraphicsType enum
        if isinstance(cursor.backend, pgui.VerticalCursor):
            promptX = quickdialog.FloatInput(d, "X coordinate (pixels):")
            promptX.variable.setClearButtonEnabled(True)
            promptX.variable.redoAvailable=True
            promptX.variable.undoAvailable=True
            promptX.setValue(cursor.x)
            d.promptWidgets.append(promptX)
        
            promptXWindow = quickdialog.FloatInput(d, "Horizontal window size (pixels):")
            promptXWindow.variable.setClearButtonEnabled(True)
            promptXWindow.variable.redoAvailable=True
            promptXWindow.variable.undoAvailable=True
            promptXWindow.setValue(cursor.xwindow)
            d.promptWidgets.append(promptXWindow)
            
        elif isinstance(cursor.backend, pgui.HorizontalCursor):
            promptY = quickdialog.FloatInput(d, "Y coordinate (pixels):")
            promptY.variable.setClearButtonEnabled(True)
            promptY.variable.redoAvailable=True
            promptY.variable.undoAvailable=True
            promptY.setValue(cursor.y)
            d.promptWidgets.append(promptY)
            
            promptYWindow = quickdialog.FloatInput(d, "Vertical window size (pixels):")
            promptYWindow.variable.setClearButtonEnabled(True)
            promptYWindow.variable.redoAvailable=True
            promptYWindow.variable.undoAvailable=True
            promptYWindow.setValue(cursor.ywindow)
            d.promptWidgets.append(promptYWindow)
            
        else: # crosshair / point cursors
            promptX = quickdialog.FloatInput(d, "X coordinate:")
            promptX.variable.setClearButtonEnabled(True)
            promptX.variable.redoAvailable=True
            promptX.variable.undoAvailable=True
            promptX.setValue(cursor.x)
            d.promptWidgets.append(promptX)
            
            promptXWindow = quickdialog.FloatInput(d, "Horizontal window size:")
            promptXWindow.variable.setClearButtonEnabled(True)
            promptXWindow.variable.redoAvailable=True
            promptXWindow.variable.undoAvailable=True
            promptXWindow.setValue(cursor.xwindow)
            d.promptWidgets.append(promptXWindow)
            
            promptY = quickdialog.FloatInput(d, "Y coordinate:")
            promptY.variable.setClearButtonEnabled(True)
            promptY.variable.redoAvailable=True
            promptY.variable.undoAvailable=True
            promptY.setValue(cursor.y)
            d.promptWidgets.append(promptY)
            
            promptYWindow = quickdialog.FloatInput(d, "Vertical window size:")
            promptYWindow.variable.setClearButtonEnabled(True)
            promptYWindow.variable.redoAvailable=True
            promptYWindow.variable.undoAvailable=True
            promptYWindow.setValue(cursor.ywindow)
            d.promptWidgets.append(promptYWindow)
                
        framesWhereVisible = quickdialog.StringInput(d, "Visible frames:")
        framesWhereVisible.setToolTip("Enter comma-separated list of visible frames, the keyword 'all', or 'range(start,[stop,[step]]')")
        framesWhereVisible.setWhatsThis("Enter comma-separated list of visible frames, the keyword 'all', or 'range(start,[stop,[step]]')")
        
        if len(cursor.frameVisibility)==0:
            framesWhereVisible.setText("all")
            
        else:
            b = ""
            if len(cursor.frameVisibility):
                for f in cursor.frameVisibility[:-1]:
                    if f is None:
                        continue
                    
                    b += "%d, " % f
                    
                f = cursor.frameVisibility[-1]
                
                if f is not None:
                    b += "%d" % cursor.frameVisibility[-1]
                    
            if len(b.strip()) == 0:
                b = "all"
                
            framesWhereVisible.setText(b)

        d.promptWidgets.append(framesWhereVisible)
        
        linkToFramesCheckBox = quickdialog.CheckBox(d, "Link position to frame number")
        linkToFramesCheckBox.setChecked( len(cursor.backend.states) > 1)
        
        d.promptWidgets.append(linkToFramesCheckBox)
        
        for w in d.promptWidgets:
            if not isinstance(w, quickdialog.CheckBox):
                w.variable.setClearButtonEnabled(True)
                w.variable.redoAvailable=True
                w.variable.undoAvailable=True

        if d.exec() == QtWidgets.QDialog.Accepted:
            old_name = cursor.name
            
            newName = namePrompt.text()
            
            if newName is not None and len(newName.strip()) > 0:
                if newName != old_name:
                    if newName in [o.name for o in self.graphicsCursors]:
                        QtWidgets.QMessageBox.critical(self, "Cursor name clash", "A cursor named %s already exists" % newName)
                        return
                    
            if isinstance(cursor.backend, pgui.VerticalCursor) or cursor.backend.type & pgui.PlanarGraphicsType.vertical_cursor:
                cursor.backend.x = promptX.value()
                cursor.backend.xwindow = promptXWindow.value()
                
            elif isinstance(cursor.backend, pgui.HorizontalCursor) or cursor.backend.type & pgui.PlanarGraphicsType.horizontal_cursor:
                cursor.backend.y = promptY.value()
                cursor.backend.ywindow = promptYWindow.value()

            else:
                cursor.backend.x = promptX.value()
                cursor.backend.y = promptY.value()
                cursor.backend.xwindow = promptXWindow.value()
                cursor.backend.ywindow = promptYWindow.value()
        
            cursor.labelShowsPosition = showsPositionCheckBox.selection()
            
            cursor.setTransparentLabel(not showsOpaqueLabel.selection())
            
            
            newFrames = []
            
            txt = framesWhereVisible.text()
            
            if len(txt.strip()) == 0:
                newFrames = []
                
            elif txt.strip().lower() == "all":
                if self.__image_viewer__ is not None:
                    newFrames = [f for f in range(self.__image_viewer__.nFrames)]
                else:
                    newFrames = []
                
            elif txt.find("range") == 0:
                val = eval(txt)
                
                newFrames = [f for f in val]
                
            elif any(c in txt for c in (":", ",")):
                try:
                    c_parts = txt.split(",")
                    new_frames = list()
                    for c in c_parts:
                        if ":" in c:
                            new_frames.extend(i for i in strutils.str2range(c))
                        else:
                            new_frames.append(int(c))
                except:
                    traceback_print_exc()
                
            #elif txt.find(":") > 0:
                #try:
                    #newFrames = [int(f_) for f_ in txt.split(":")]
                    #if len(newFrames) > 3:
                        #newFrames = []
                        
                    #else:
                        #newFrames = range(*newFrames)
                        
                #except Exception as e:
                    #traceback_print_exc()
                    
            #else:
                #try:
                    #newFrames = [int(f_) for f_ in txt.split(",")]
                    
                #except Exception as e:
                    #traceback.print_exc()
                    
            linkToFrames = linkToFramesCheckBox.selection()
            
            if linkToFrames:
                cursor.frameVisibility = newFrames
                
                cursor.backend.linkFrames(newFrames)
                
            else:
                cursor.frameVisibility = []
            
            cursor.backend.name = newName
            
            self.signalCursorChanged.emit(cursor.backend)

        self._cursorContextMenuSourceId = None
        
    @Slot()
    def buildROI(self):
        """Interactively builds a new ROI (i.e. using the GUI).
        """
        # NOTE: triggered by ImageViewer.newROIAction
        # once the ROI is build, the ROI is set to emit signalROIConstructed
        # which is connected to slot_newROIConstructed, which in turn emits
        # signalRoiAdded (so that "sister" windows can be notified)
        #print("buildROI")
        params = None
        pos = QtCore.QPointF(0,0)
        
        p = self.parent()

        while p is not None and not isinstance(p, ImageViewer):
            p = p.parent()
            
        if p is not None and isinstance(p, ImageViewer):
            frame = p.currentFrame
            
        else:
            frame = 0

        newROI = pgui.GraphicsObject(params, 
                                pos=pos,
                                objectType=pgui.PlanarGraphicsType.allShapeTypes,
                                visibleFrames=[],
                                label=None,
                                currentFrame=frame,
                                parentWidget=self)
        
        self.__scene__.addItem(newROI)
        
        newROI.signalROIConstructed.connect(self.slot_newROIConstructed)
        
        return newROI

    def createNewRoi(self, params=None, roiType=None, label=None,
                     frame=None, pos=None, movable=True, 
                     editable=True, frameVisibility=[], 
                     showLabel=True, labelShowsPosition=True,
                     autoSelect=False, parentWidget=None):
        """Creates a ROI programmatically, or interactively
        """
        if self.__scene__.rootImage is None:
            return
        
        if parentWidget is None:
            if isinstance(self.__image_viewer__, ImageViewer):
                parentWidget = self.__image_viewer__
            else:
                parentWidget = self
                
        if all([v is None for v in (params, roiType, )]):
            self.buildROI()
            
        rTypeStr = ""
        
        # NOTE: 2021-05-04 16:16:24
        # old style type check for backward compatibility
        if isinstance(params, pgui.PlanarGraphics):
            if params.type & pgui.PlanarGraphicsType.allShapeTypes:
                roiType = params.type
                
            else:
                raise TypeError("Cannot build a ROI with this PlanarGraphics type: %s" % params.type)

        if roiType & pgui.PlanarGraphicsType.point:
            rTypeStr = "p"
        elif roiType & pgui.PlanarGraphicsType.line:
            rTypeStr = "l"
        elif roiType & pgui.PlanarGraphicsType.rectangle:
            rTypeStr = "r"
        elif roiType & pgui.PlanarGraphicsType.ellipse:
            rTypeStr = "e"
        elif roiType & pgui.PlanarGraphicsType.polygon:
            rTypeStr = "pg"
        elif roiType & (pgui.PlanarGraphicsType.path | pgui.PlanarGraphicsType.polyline):
            rTypeStr = "pt"
        else:
            return
        
        if frame is None:
            if type(parentWidget).__name__ == "ImageViewer":
                frame = parentWidget.currentFrame
            else:
                frame = 0
                
        nFrames = 1
                
        if type(parentWidget).__name__ == "ImageViewer":
            nFrames = parentWidget.nFrames
            
            if frame < 0 :
                frame = nFrames
                
            if frame >= nFrames:
                frame = nFrames-1
                
        if frameVisibility is None:
            if isinstance(params, pgui.PlanarGraphics) and params.type & pgui.PlanarGraphicsType.allShapeTypes:
                if not isinstance(params, pgui.Path):
                    frameVisibility = params.frameIndices
                    
                else:
                    frameVisibility = []
                
                if len(frameVisibility) == 1 and frameVisibility[0] is None:
                    frameVisibility.clear()
                    
            else:
                frameVisibility = [f for f in range(nFrames)]
            
        else:
            if not isinstance(params, pgui.Path):
                if not isinstance(frameVisibility, (tuple, list)) or not all([isinstance(f, int) for f in frameVisibility]):
                    raise TypeError("frame visibility must be specified as a list of ints or an empty list, or None; got %s instead" % frameVisibility)
                
                elif len(frameVisibility) == 0:
                    frameVisibility = [0]
            
        if isinstance(roiType, int):
            rDict = self._graphicsObjects_[roiType]
            
        else:
            rDict = self._graphicsObjects_[roiType.value]
            
        if label is None or (isinstance(label, str) and len(label) == 0):
            if isinstance(params, pgui.PlanarGraphics) and (isinstance(params.name, str) and len(params.name) > 0):
                tryName = params.name
                if tryName in rDict.keys():
                    tryName = utilities.counter_suffix(tryName, [s for s in rDict.keys()])
                    
                roiId = tryName
                
            else:
                roiId = "%s%d" % (rTypeStr, len(rDict))
            
        elif isinstance(label, str) and len(label):
            roiId = "%s%d" % (label, len(rDict))
                
        if roiId in rDict.keys():
            roiId += "%d" % len(rDict)
        
        if pos is not None and not isinstance(pos, (QtCore.QPoint, QtCore.QPointF)):
            raise TypeError("pos must be a QPoint or QPointF; got %s instead" % (type(pos).__name__))
        
        if pos is None:
            pos = QtCore.QPointF(0,0)
            
        if parentWidget is None:
            parentWidget = self
            
        #print("GraphicsImageViewerWidget.createNewRoi params %s" % params)
        #print("GraphicsImageViewerWidget.createNewRoi frameVisibility %s" % frameVisibility)
        
        roi = pgui.GraphicsObject(obj                 = params,
                                  showLabel           = showLabel,
                                  labelShowsPosition  = labelShowsPosition,
                                  parentWidget        = parentWidget)
        
        roi.canMove = movable
        roi.canEdit = editable
        
        # NOTE: 2021-04-18 12:13:21 FIXME
        # do I reallly need guiClient, here? rois and cursors should always be 
        # notified of frame change, right?
        if type(parentWidget).__name__ == "ImageViewer":
            parentWidget.frameChanged[int].connect(roi.slotFrameChanged)
            
        if autoSelect:
            for r in self.__rois__.values():
                r.setSelected(False)
                
            roi.setSelected(True)

        self.__scene__.addItem(roi)

        roi.signalPosition.connect(self.slot_reportCursorPos)
        roi.selectMe[str, bool].connect(self.slot_setSelectedRoi)
        roi.requestContextMenu.connect(self.slot_graphicsObjectMenuRequested)
        #roi.signalBackendChanged[object].connect(self.slot_roiChanged)
        
        rDict[roiId] = roi
        
        self.scene.update(self.scene.sceneRect().x(), 
                          self.scene.sceneRect().y(), 
                          self.scene.sceneRect().width(), 
                          self.scene.sceneRect().height())
        
        #self.signalRoiAdded.emit(roi.backend)
        
        return roi
    
    def newGraphicsObject(self, item:typing.Optional[typing.Union[pgui.PlanarGraphics, type]], 
                          movable=True, editable=True, showLabel=True, 
                          labelShowsPosition=True, autoSelect=False) -> typing.Optional[pgui.GraphicsObject]:
        """Creates a GraphicsObject that represents a PlanarGraphics for display.
        
        The object is created by either:
        1) passing a PlanarGraphics (e.g. constructed in separate code then 
           passed to this function call as the 'item' parameter).
           
           NOTE: This is the way to parametrically create a GraphicsObject:
           create the PlanarGraphics 'backend' first, then use it to construct
           the GraphicsObject 'frontend' which will be added to the scene.
           
        2) using GUI interaction (mouse events with key modifiers): here, a
            GraphicsObject is constructed in "buildMode", which will create its
            own 'backend'; the management of mouse events (and associated key 
            modifiers) is taken care of by the GraphicsObject :class:.
            
            In this case, the type of the PlanarGraphics 'backend' is specified
            by passing its :class: as the 'item' parameter.
            
            To keep things simple, all GraphicsObject/PlanarGraphics constructed
            via GUI will get a default name as specified by the concrete 'backend'
            type, will be visible in all available frames, and their 'currentFrame'
            attribute will be set to the current frame of the viewer, or 0 (zero).
            
        Parameters:
        ===========
        
        item: a pgui.PlanarGraphics object, or a :class: object that is a
            concrete subclass of pgui.PlanarGraphics.
            
        movable:bool, optional (default is True)
            When True, the user can move the object in the scene using the mouse
            
        editable:bool, optional (default is True)
            When True, the user can edit the object (and indirectly its 'backend' 
            shape) using mouse actions and associated key modifiers
            
        labelShowsPosition:bool optional (default is True)
            When True, the displayed label also shows the object's position.
            
            This is mostly useful for cursors, where is displays:
            the 'x' coordinate for Vertical cursors
            the 'y' coordinate for Horizontal cursors
            the 'x,y' coordinates pair for Crosshair and Point cursors
            
            NOTE: The coordinate values are NOT calibrated (i.e. they are in pixels)
            
            ATTENTION: To avoid clutter, this parameter should be set to False
                for non-cursor PlanarGraphics.
                
        autoSelect:bool, optional (default is True)
            When True, the GraphicsObject will be selected after adding to the
            scene.
            
        """
        if self.__scene__.rootImage is None:
            return
        
        qobj = None
        
        if type(self.__image_viewer__).__name__ == "ImageViewer":
            parentWidget = self.__image_viewer__
        else:
            parentWidget = self
            
        if isinstance(item, pgui.PlanarGraphics):
            maxWidth  = self.__scene__.rootImage.boundingRect().width()
            maxHeight = self.__scene__.rootImage.boundingRect().height()
            
            if isinstance(item, pgui.Cursor):
                # FIXME 2021-08-18 10:31:43 in planargraphics
                # cursor width & height should NEVER be none!
                if item.width is None: 
                    item.width = maxWidth
                    
                if item.width <= 0 or item.width > maxWidth:
                    item.width = maxWidth
                    
                if item.height is None:
                    item.height = maxHeight
                    
                if item.height <= 0 or item.height > maxHeight:
                    item.height = maxHeight
                    
                if item.x < 0:
                    item.x = 0
                    
                if item.x > maxWidth:
                    item.x  = maxWidth
                    
            qobj = pgui.GraphicsObject(obj=item, showLabel=showLabel, 
                                       labelShowsPosition = labelShowsPosition,
                                       parentWidget = parentWidget)
            
        elif isinstance(item, type) and pgui.PlanarGraphics in item.__mro__:
            # NOTE: 2021-05-10 11:47:48 
            # The user creates a new object by GUI interaction:
            # * for cursors, we only need a single mouse click in the scene, to
            #   indicate where the initial cursor position
            # * for non-cursors, we need a more elaborate set of actions to "draw"
            #   the PlanarGraphics backend, which can be:
            #   a) a primitive (Move, Line, Ellipse, Retangle)
            #   b) a Path constructed from any number of the above primitives
            #      plus Arc, ArcMove, Cubic and Quad, and other Path objects
            
            default_x = np.floor(self.__scene__.rootImage.boundingRect().center().x())
            default_y = np.floor(self.__scene__.rootImage.boundingRect().center().y())
            
            name = "%s%d" % (item._default_label_, len([o for o in filter_type(self.planarGraphics, item)]))
            
            if type(parentWidget).__name__ == "ImageViewer":
                frame = parentWidget.currentFrame
            else:
                frame = 0
                
            if pgui.Cursor in item.__mro__:
                # Construct a concrete Cursor type by clicking in the scene
                # requires that the scene has a rootImage.
                if item not in (pgui.CrosshairCursor, pgui.HorizontalCursor, pgui.PointCursor, pgui.VerticalCursor):
                    raise TypeError("Expecting a CrosshairCursor, HorizontalCursor, PointCursor, or VerticalCursor")
                
                currentTopLabelText = self._topLabel.text()
                
                self._topLabel.setText(currentTopLabelText + " Double-click left mouse button for cursor position")
                
                currentGUICursor = self._imageGraphicsView.viewport().cursor()
                
                self._imageGraphicsView.viewport().setCursor(QtCore.Qt.CrossCursor)
                
                eventSinks = [pgui.MouseEventSink() for o in self.graphicsObjects]
                
                [_ for _ in itertools.starmap(lambda x,y: x.installEventFilter(y),
                                              zip(self.graphicsObjects, eventSinks))]
                
                # NOTE: 2021-05-10 10:41:19 
                # wait for mouse press or Esc key press
                while not self.__escape_pressed___ and not self.__mouse_pressed___:
                    # NOTE: 2021-05-10 10:39:47
                    # see self.mousePressEvent(), self.mouseReleaseEvent() and
                    # self.keyPressEvent()
                    # the self.mouse...Event() set up __last_mouse_click_lmb__
                    # the self.keyPressEvent() captures Esc key press
                    QtCore.QCoreApplication.processEvents() 
                    
                self.__escape_pressed___ = False
                self.__mouse_pressed___  = False
                
                [_ for _ in itertools.starmap(lambda x,y: x.removeEventFilter(y),
                                              zip(self.graphicsObjects, eventSinks))]
                
                self._imageGraphicsView.viewport().setCursor(currentGUICursor)
                
                self._topLabel.setText(currentTopLabelText)
                
                # NOTE: 2021-05-10 10:38:15 
                # self.__last_mouse_click_lmb__ is set by self.mousePressEvent
                
                if isinstance(self.__last_mouse_click_lmb__, (QtCore.QPoint, QtCore.QPointF)):
                    # the loop at NOTE: 2021-05-10 10:41:19 was interrupted by
                    # mouse press, therefore we land here
                    point = QtCore.QPointF(self.__last_mouse_click_lmb__)
                    
                    if self.scene.sceneRect().contains(point):
                        # NOTE: 2021-05-10 10:49:38
                        # item is one of the concrete pgui cursor classes, so it
                        # works as a factory here:
                        pobj = item(point.x(), point.y(), 
                                    self.scene.sceneRect().width(),
                                    self.scene.sceneRect().height(),
                                    self.__cursorWindow__, 
                                    self.__cursorWindow__,
                                    self.__cursorRadius__,
                                    name=name,
                                    frameindex=[],
                                    currentFrame=frame)
                        
                        qobj = pgui.GraphicsObject(obj=pobj, showLabel=showLabel, 
                                       labelShowsPosition = labelShowsPosition,
                                       parentWidget = parentWidget)
                        
                    self.__last_mouse_click_lmb__ = None
                    
            else:
                pass # TODO start shape building process
        
        qobj.canMove = movable
        qobj.canEdit = editable
            
        # NOTE: 2021-04-18 12:13:21 FIXME
        # do I reallly need guiClient, here? rois and cursors should always be 
        # notified of frame change, right?
        if type(parentWidget).__name__ == "ImageViewer":
            parentWidget.frameChanged[int].connect(qobj.slotFrameChanged)
            
        self.scene.addItem(qobj)
        
        if autoSelect:
            for c in self.graphicsObjects:
                c.setSelected(False)
                
            qobj.setSelected(True)
            
        if isinstance(qobj.backend, pgui.Cursor):
            qobj.signalPosition.connect(self.slot_reportCursorPos)
            
        qobj.selectMe[str, bool].connect(self.slot_setSelectedCursor)
        qobj.requestContextMenu.connect(self.slot_graphicsObjectMenuRequested)
        
        if qobj.backend.hasStateForFrame():
            qobj.show()
            
        return qobj
        
    def clear(self):
        """Clears the contents of the viewer.
        
        Removes all cursors, rois and image data and clears the 
        underlying scene.
        
        """
        for d in self._graphicsObjects_.values():
            d.clear()
            
        for d in self.__cursors__.values():
            d.clear()
            
        self.selectedCursor = None
        self.selectedRoi = None
        self._cursorContextMenuSourceId = None 
        
        self.__scene__.clear()
    
    ####
    # slots
    ####
    
    @Slot(int, str)
    @safeWrapper
    def slot_newROIConstructed(self, roiType, roiName):
        sender = self.sender()
        
        # see NOTE: 2018-09-25 23:06:55
        #sigBlock = QtCore.QSignalBlocker(sender)
        
        if roiType & pgui.PlanarGraphicsType.point:
            rTypeStr = "p"
            
        elif roiType & pgui.PlanarGraphicsType.line:
            rTypeStr = "l"
            
        elif roiType & pgui.PlanarGraphicsType.rectangle:
            rTypeStr = "r"
            
        elif roiType & pgui.PlanarGraphicsType.ellipse:
            rTypeStr = "e"
            
        elif roiType & pgui.PlanarGraphicsType.polygon:
            rTypeStr = "pg"
            
        elif roiType & pgui.PlanarGraphicsType.path:
            rTypeStr = "pt"
            
        elif roiType == 0:
            sender.signalROIConstructed.disconnect()
            self.__scene__.removeItem(sender)
            return
        else:
            return
        
        sender.signalPosition.connect(self.slot_reportCursorPos)
        sender.selectMe.connect(self.slot_setSelectedRoi)
        sender.requestContextMenu.connect(self.slot_graphicsObjectMenuRequested)
        
        rDict = self._graphicsObjects_[roiType]
        
        roiId = "%s%d" % (rTypeStr, len(rDict))
        sender.name=roiId
        
        rDict[roiId] = sender
        
        self.selectedRoi = sender
        
        self.signalRoiAdded.emit(sender.backend)
            
    @Slot(object)
    @safeWrapper
    def slot_cursorChanged(self, obj):
        self.signalCursorChanged.emit(obj)
        
    @Slot(object)
    @safeWrapper
    def slot_roiChanged(self, obj):
        self.signalRoiChanged.emit(obj)
        
    @Slot(float)
    @safeWrapper
    def slot_zoom(self, val):
        self._zoomView(val)
        
    @Slot(float)
    @safeWrapper
    def slot_relativeZoom(self, val):
        newZoom = self.__zoomVal__ + val
        
        if newZoom < self._minZoom__:
            newZoom = self._minZoom__
        elif newZoom > self.__maxZoom__:
            newZoom = self.__maxZoom__
                
        self._zoomView(newZoom)
        
    @Slot()
    @safeWrapper
    def slot_editAnyCursor(self):
        self._cursorEditor()

    @Slot()
    @safeWrapper
    def slot_editSelectedCursor(self):
        if self.selectedCursor is not None:
            self._cursorEditor(self.selectedCursor.ID)
            
    @Slot()
    @safeWrapper
    def slot_editCursor(self):
        if self._cursorContextMenuSourceId is not None and self._cursorContextMenuSourceId in iter_attribute(self.graphicsCursors, "name"):
            self._cursorEditor(self._cursorContextMenuSourceId)
            
    def propagateCursorState(self):
        if self._cursorContextMenuSourceId is not None and self._cursorContextMenuSourceId in iter_attribute(self.graphicsCursors, "name"):
            cursor = [o for o in filter(lambda x: isinstance(x.backend, pgui.Cursor) and x.backend.name == self._cursorContextMenuSourceId, self.graphicsObjects)]
            if len(cursor) == 0:
                return
            
            cursor = cursor[0]

            if cursor.backend.hasHardFrameAssociations and cursor.backend.hasStateForCurrentFrame:
                cursor.backend.propagateFrameState(cursor.backend.currentFrame, cursor.backend.frameIndices)
                cursor.backend.updateFrontends()
    
    @Slot()
    @safeWrapper
    def slot_editRoi(self):
        # TODO: select a roi fromt the list then bring up a ROI edit dialog
        pass
    
    @Slot()
    @safeWrapper
    def slot_editRoiProperties(self): # to always work on selected ROI
        # TODO bring up a ROI edit dialog
        # this MUST have a checkbox to allow shape editing when OK-ed
        pass

    @Slot()
    @safeWrapper
    def slot_editRoiShape(self): # to always work on selected ROI!
        if self.selectedRoi is not None:
            self.selectedRoi.editMode = True
            # press RETURN in editMode to turn editMode OFF
        

    @Slot(str, QtCore.QPoint)
    @safeWrapper
    def slot_graphicsObjectMenuRequested(self, objId, pos):
        if objId in iter_attribute(self.graphicsCursors,"name"):
            self._cursorContextMenuSourceId = objId
            
            cm = QtWidgets.QMenu("Cursor Menu", self)
            crsEditAction = cm.addAction("Edit properties for %s cursor" % objId)
            crsEditAction.triggered.connect(self.slot_editCursor)
            
            crsPropagateStateToAllFrames = cm.addAction("Propagate current state to all frames")
            crsPropagateStateToAllFrames.triggered.connect(self.propagateCursorState)
            
            crsLinkCursorAction = cm.addAction("Link...")
            crsUnlinkCursorAction = cm.addAction("Unlink...")
            crsRemoveAction = cm.addAction("Remove %s cursor" % objId)
            crsRemoveAction.triggered.connect(self.slot_removeCursor)
            cm.exec(pos)
            
        elif objId in [o.name for o in self.rois]:
            self._roiContextMenuSourceId = objId
            
            cm = QtWidgets.QMenu("ROI Menu", self)
            crsEditAction = cm.addAction("Edit properties for %s ROI" % objId)
            crsEditAction.triggered.connect(self.slot_editRoi)
            
            pathEditAction = cm.addAction("Edit path for %s" % objId)
            pathEditAction.triggered.connect(self.slot_editRoiShape)
            
            crsLinkCursorAction = cm.addAction("Link...")
            crsUnlinkCursorAction = cm.addAction("Unlink...")
            crsRemoveAction = cm.addAction("Remove %s ROI" % objId)
            crsRemoveAction.triggered.connect(self.slot_removeRoi)
            cm.exec(pos)
            
    @Slot(str, bool)
    @safeWrapper
    def slot_setSelectedGraphicsObject(self, objId:str, sel:bool):
        # TODO 2021-05-10 13:31:27
        # do we want to have an unique selection among ALL the graphics items, 
        # or a unique selection PER GROUP of graphics object type (i.e. cursors
        # vs rois)?
        # I'm partial to the second option...'
        if objId in iter_attribute(self.graphicsCursors, "name"):
            obj = [o for o in self.graphicsObjects if isinstance(o.backend, pgui.Cursor) and o.backend.name == objId]
            if len(obj):
                self.selectedCursor = obj[0]
                self.signalGraphicsObjectSelected.emit(self.selectedCursor.backend)
            else:
                self.selectedCursor = None
                self.signalGraphicsDeselected.emit()
                
        elif objId in iter_attribute(self.rois, "name"):
            obj = [o for o in self.graphicsObjects if not isinstance(o.backend, pgui.Cursor) and o.backend.name == objId]
            if len(obj):
                self.selectedRoi = obj[0]
                self.signalGraphicsObjectSelected.emit(self.selectedRoi.backend)
            else:
                self.selectedRoi = None
                self.signalGraphicsDeselected.emit()
            
        #else:

    @Slot(str, bool)
    @safeWrapper
    def slot_setSelectedCursor(self, cId:str, sel:bool):
        """To keep track of what cursor is selected, 
        independently of the underlying graphics view fw.
        """
        if cId in iter_attribute(self.graphicsCursors, "name"):
            if sel:
                c = [o for o in self.graphicsObjects if o.backend.name == cId]
                if len(c):
                    self.selectedCursor = c[0]
                    self.signalGraphicsObjectSelected.emit(self.selectedCursor.backend)
                    return
                
        self.selectedCursor = None
        self.signalGraphicsDeselected.emit()
            
    @Slot(str, bool)
    @safeWrapper
    def slot_setSelectedRoi(self, rId:str, sel:bool):
        if rId in iter_attribute(self.rois, "name"):
            if sel:
                r = [o for o in self.graphicsObjects if o.backend.name == rId]
                if len(r):
                    self.selectedRoi = r[0]
                    self.signalGraphicsObjectSelected.emit(self.selectedRoi.backend)
                    return
            
        self.selectedRoi = None
        self.signalGraphicsDeselected.emit()
            
    @Slot()
    @safeWrapper
    def slot_newHorizontalCursor(self):
        obj = self.newGraphicsObject(pgui.HorizontalCursor)
        if obj is not None:
            self.signalCursorAdded.emit(obj.backend)

    @Slot()
    @safeWrapper
    def slot_newPointCursor(self):
        obj = self.newGraphicsObject(pgui.PointCursor)
        if obj is not None:
            self.signalCursorAdded.emit(obj.backend)
    
    @Slot()
    @safeWrapper
    def slot_newVerticalCursor(self):
        obj = self.newGraphicsObject(pgui.VerticalCursor)
        if obj is not None:
            self.signalCursorAdded.emit(obj.backend)
    
    @Slot()
    @safeWrapper
    def slot_newCrosshairCursor(self):
        obj = self.newGraphicsObject(pgui.CrosshairCursor)
        if obj is not None:
            self.signalCursorAdded.emit(obj.backend)
    
    @Slot(str)
    @safeWrapper
    def slot_selectCursor(self, crsId):
        if crsId in iter_attribute(self.graphicsCursors, "name"):
            self.slot_setSelectedCursor(crsId, True)
      
    @Slot(str)
    @safeWrapper
    def slot_selectGraphicsObject(self, objId):
        self.slot_setSelectedGraphicsObject(objId)
      
    @Slot()
    @safeWrapper
    def slot_receiveCursorUnlinkRequest(self):
        pass
    
    @Slot()
    @safeWrapper
    def slot_receiveCursorLinkRequest(self):
        pass
    
    @Slot(str, "QPointF")
    @safeWrapper
    def slot_reportCursorPos(self, crsId, pos):
        if crsId in iter_attribute(self.graphicsCursors, "name"):
            obj = [o for o in self.imageCursor(crsId)]
            
            if len(obj) == 0:
                return
            
            obj = obj[0]
            
            if isinstance(obj, pgui.VerticalCursor):
                self.signalCursorAt[str, list].emit(crsId, 
                                                    [np.floor(pos.x()), None, obj.xwindow])
                
            elif isinstance(obj, pgui.HorizontalCursor):
                self.signalCursorAt[str, list].emit(crsId, 
                                                    [None, np.floor(pos.y()), obj.ywindow])
                
            else:
                self.signalCursorAt[str, list].emit(crsId,
                                                    [np.floor(pos.x()), np.floor(pos.y()), obj.xwindow, obj.ywindow])
                
    @Slot()
    @safeWrapper
    def slot_removeCursors(self):
        self._removePlanarGraphics(cursors=True)
        
    @Slot()
    @safeWrapper
    def slot_removeAllCursors(self):
        self._removeAllPlanarGraphics(cursors=True)
        for crs in filter(lambda x: isinstance(x.backend, pgui.Cursor), self.graphicsObjects):
            crs.backend.frontends.clear()
            self.scene.removeItem(crs)
            
        self.selectedCursor = None
        
    @Slot()
    @safeWrapper
    def slot_removeSelectedCursor(self):
        self._removeSelectedPlanarGraphics(cursors=True)
        
    @Slot()
    @safeWrapper
    def slot_removeCursor(self):
        if len([o for o in self.graphicsCursors]) == 0:
            return
        
        if self._cursorContextMenuSourceId is not None and self._cursorContextMenuSourceId in iter_attribute(self.graphicsCursors, "name"):
            self.slot_removeCursorByName(self._cursorContextMenuSourceId)
        
    @Slot(str)
    @safeWrapper
    def slot_removeCursorByName(self, crsId):
        self._removePlanarGraphics(crsId, True)
            
    @Slot()
    @safeWrapper
    def slot_removeRois(self):
        self._removePlanarGraphics(cursors=False)
        
    @Slot()
    @safeWrapper
    def slot_removeAllRois(self):
        self._removeAllPlanarGraphics(cursors=False)
        
    @Slot()
    @safeWrapper
    def slot_removeAllGraphics(self):
        self._removeAllPlanarGraphics()
        
    @Slot()
    @safeWrapper
    def slot_removeSelectedRoi(self):
        self._removeSelectedPlanarGraphics(cursors=False)
        
    @Slot(str)
    @safeWrapper
    def slot_removeRoiByName(self, roiId):
        self._removePlanarGraphics(roiId, False)

    @Slot()
    @safeWrapper
    def slot_removeRoi(self):
        if len(self.__rois__) == 0:
            return
        
        if self._roiContextMenuSourceId is not None and self._roiContextMenuSourceId in self.__rois__.keys():
            self.slot_removeRoiByName(self._roiContextMenuSourceId)
        

   #### BEGIN properties
    
    @property
    def minZoom(self):
        return self._minZoom__
    
    @minZoom.setter
    def minZoom(self, val):
        self._minZoom__ = val
        
    #@Property(float)
    @property
    def maxZoom(self):
        return self.__maxZoom__
    
    @maxZoom.setter
    def maxZoom(self, val):
        self.__maxZoom__ = val
        
    @property
    def scene(self):
        return self.__scene__
    
    @property
    def graphicsview(self):
        return self._imageGraphicsView
    
    @property
    def imageViewer(self):
        return self.__image_viewer__
    
    @property
    def graphicsObjects(self) -> typing.Iterator:
        """Iterator for existing pictgui.GraphicsObjects.
        """

        #NOTE ATTENTION: 2021-05-08 21:27:31 New API:
        
        #To simplify the code, GraphicsImageViewerWidget does not store references
        #to either the scene's GraphicsObject objects, or to their PlanarGraphics
        #backends.
        
        #The GraphicsObject instances are already owned by the viewer widget's 
        #scene, and their PlanarGraphics backends can be accessed through the
        #'backend' attribute of the GraphicsObject instance.
        
        #This property allows access to the GraphicsObject instances that are
        #owned by the scene, and thus indirectly to their PlanarGraphics 'backend'.

        return filter_type(self.scene.items(), pgui.GraphicsObject)
        
    @property
    def planarGraphics(self) -> typing.Generator:
        """Iterator for the backends of all the GraphicsObjects in the scene.
        These include cursors and rois.
        """
        return iter_attribute(self.graphicsObjects, "backend")
    
    @property
    def rois(self) -> typing.Iterator:
        """All ROIs (PlanarGraphics) with frontends in the scene.
        """
        return filterfalse_type(self.planarGraphics, pgui.Cursor)
    
    @property
    def graphicsCursors(self) -> typing.Iterator:
        """All PlanarGraphics Cursors with frontends in the scene.
        """
        return filter_type(self.planarGraphics, pgui.Cursor)
        
    #### END properties

    #### BEGIN public methods
    
    @safeWrapper
    def roi(self, value:typing.Optional[typing.Any]=None, attribute:str="name", 
            predicate:typing.Optional[typing.Callable[...,bool]]=lambda x,y: x == y, 
            **kwargs):
        """Iterates through ROIs with specific attributes.
        
        ROIs are selected by comparing the value of a specific ROI attribute
        (named in 'attribute') against the value specified in 'value'.
        
        The two values are compared using the predicate specified in 'predicate'.
        By default, the predicate tests for equality.
        
        Parameters:
        ==========
        value: any type; optional, default is None
            The value against which the value of the named attribute is compared.
            
            When None, returns self.rois property directly
            
        Named Parameters:
        =================
        attribute: str, default is "name" - the name of the attribute for which
            the value will be compared against 'value'
        
        predicate: a callable that takes two parameters and returns a bool.
            Performs the actual comparison between 'value' and the named attribute
            value.
            
            The first parameter of the predicate is a place holder for the value
            of the attribute given in 'attribute'
            
            The second parameter is the placeholder for 'value'
            
            In short, the predicate compares the vlue of the named attribute to
            that given in 'value'
            
            Optional: default is the identity (lambda x,y: x==y)
            
        Var-keyword parameters:
        =======================
        Mapping of attribute name to function
        attribute_name:str -> function object (unary predicate)
            This is an alternative syntax that supplements the 'value' and
            'attribute' parameters described above.
            
            e.g.:
            roi(name=lambda x: x=="some_name")
            
        Returns:
        ========
        An iterator for non-Cursor PlanarGraphics objects, optionally having the 
        named attribute with values that satisfy the predicate, and possibly
        further attributes with values as specified in kwargs.
        
        By default, the function returns an iterator of ROIs selected by their 
        name.
        
        """
        
        if len(kwargs):
            ret = list()
            for n,f in kwargs.items():
                if isinstance(f, function):
                    ret.append(filter_attribute(self.rois, n, f))
                    
        else:
            ret = self.rois
            
        
        return filter_attribute(ret, attribute, value, predicate)
        
    @safeWrapper
    def imageCursor(self, value:typing.Optional[typing.Any] = None, 
                     attribute:str="name",
                     predicate:typing.Optional[typing.Callable[...,bool]]=lambda x,y: x == y, 
                     **kwargs):
        """Iterates through Cursors with specific attributes.
        
        Data cursors are selected by comparing the value of a specific cursor 
        attribute (named in 'attribute') against the value specified in 'value'.
        
        The two values are compared using the predicate specified in 'predicate'.
        By default, the predicate tests for equality.
        
        Parameters:
        ==========
        value: any type; optional, default is None
            The value against which the value of the named attribute is compared.
            
            When None, returns self.graphicsCursors property directly.
            
        Named Parameters:
        =================
        attribute: str, default is "name" - the name of the attribute for which
            the value will be compared against 'value'
        
        predicate: a callable that takes two parameters and returns a bool.
            Performs the actual comparison between 'value' and the named attribute
            value.
            
            The first parameter of the predicate is a place holder for the value
            of the attribute given in 'attribute'
            
            The second parameter is the placeholder for 'value'
            
            In short, the predicate compares the vlue of the named attribute to
            that given in 'value'
            
            Optional: default is the identity (lambda x,y: x==y)
            
        Var-keyword parameters:
        =======================
        Mapping of attribute name to function
        attribute_name:str -> function object (unary predicate)
            This is an alternative syntax that supplements the 'value' and
            'attribute' parameters described above.
            
            e.g.:
            imageCursor(name=lambda x: x=="some_name")
            
        Returns:
        ========
        An iterator for Cursor PlanarGraphics objects, optionally having the 
        named attribute with values that satisfy the predicate, and possibly
        further attributes with values as specified in kwargs.
        
        By default, the function returns an iterator of Cursor selected by their
        name.
        
        """
        if len(kwargs):
            ret = list()
            for n, f in kwargs.items():
                ret.append(filter_attribute(self.graphicsCursors, n, f))
        else:
            ret = self.graphicsCursors
            
        return filter_attribute(ret, attribute, value, predicate)
    
    def verticalCursor(self, value:typing.Any=None, attribute:str="name", predicate:typing.Optional[typing.Callable[...,bool]]=lambda x,y: x == y):
        return filter_attribute(filter_type(self.planarGraphics, pgui.VerticalCursor), 
                                attribute, value, predicate)
        
    def horizontalCursor(self, value:typing.Any=None, attribute:str="name", predicate:typing.Optional[typing.Callable[...,bool]]=lambda x,y: x == y):
        return filter_attribute(filter_type(self.planarGraphics, pgui.HorizontalCursor), 
                                attribute, value, predicate)
        
    def crosshairCursor(self, value:typing.Any=None, attribute:str="name", predicate:typing.Optional[typing.Callable[...,bool]]=lambda x,y: x == y):
        return filter_attribute(filter_type(self.planarGraphics, pgui.CrosshairCursor), 
                                attribute, value, predicate)
        
    def pointCursor(self, value:typing.Any=None, attribute:str="name", predicate:typing.Optional[typing.Callable[...,bool]]=lambda x,y: x == y):
        return filter_attribute(filter_type(self.planarGraphics, pgui.PointCursor), 
                                attribute, value, predicate)
        
    @safeWrapper
    def hasCursor(self, crsid):
        """Tests for existence of a GraphicsObject cursor with given id or label.
        
        Parameters:
        ===========
        roiId: str: the roi Id or roi Name (label)
        """
        
        if not isinstance(crsid, str):
            raise TypeError("Expecting a str; got %s instead" % type(crsid).__name__)
        
        if len(self.__cursors__) == 0:
            return False
        
        if not crsid in self.__cursors__.keys():
            cid_label = [(cid, c.label) for (cid, c) in self.__cursors__.items() if c.label == crsid]
            
            return len(cid_label) > 0
        
        else:
            return True
    
    def setMessage(self, s):
        pass
    
    def wheelEvent(self, evt):
        if evt.modifiers() and QtCore.Qt.ShiftModifier:
            step = 1
                
            nDegrees = evt.angleDelta().y()*step/8
            
            nSteps = nDegrees / 15
            
            zoomChange = nSteps * 0.1
            
            self.slot_relativeZoom(zoomChange)
        evt.accept()

    def timerEvent(self, evt):
        evt.ignore()
        
    def keyPressEvent(self, evt):
        if evt.key() == QtCore.Qt.Key_Escape:
            self.__escape_pressed___ = True
            
        evt.accept()
        
    @safeWrapper
    def mousePressEvent(self, evt):
        self.__mouse_pressed___ = True
        
        if evt.button() == QtCore.Qt.LeftButton:
            self.__last_mouse_click_lmb__ = evt.pos()
            
        elif evt.button() == QtCore.Qt.RightButton:
            self.__last_mouse_click_lmb__ = None
        
        evt.accept()
    
    @safeWrapper
    def mouseReleaseEvent(self, evt):
        self.__mouse_pressed___ = True
        
        if evt.button() == QtCore.Qt.LeftButton:
            self.__last_mouse_click_lmb__ = evt.pos()
            
        elif evt.button() == QtCore.Qt.RightButton:
            self.__last_mouse_click_lmb__ = None
        
        evt.accept()
    
    def setImage(self, img):
        self.view(img)
        
    def view(self, a):
        if isinstance(a, QtGui.QPixmap):
            self.__scene__.rootImage = QtWidgets.QGraphicsPixmapItem(a)
            
        elif isinstance(a, QtGui.QImage):
            self.__scene__.rootImage = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(a))
        
    def interactiveZoom(self):
        self.__interactiveZoom__ = not self.__interactiveZoom__
    
    def setBackground(self, brush):
        self.__scene__.setBackground(brush)
        
    def setTopLabelText(self, value):
        self._topLabel.setText(value)
        
    def clearTopLabel(self):
        self._topLabel.clear()
        
    def clearLabels(self):
        self.clearTopLabel()
        
    #### END public methods
    
        
