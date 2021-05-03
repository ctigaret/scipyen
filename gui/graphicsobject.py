from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.datatypes import TypeEnum
from core.prog import (safeWrapper, deprecated,
                       timefunc, processtimefunc,)

class GraphicsObjectType(TypeEnum):
    """Enumeration of all supported graphical object types.
    FIXME Complete the doc string
    Type name             type value  QGraphicsItem               Planar Descriptors
    ===============================================================================
    vertical_cursor     = 1                                     x, y, width, height, xWin, yWin, radius
    horizontal_cursor   = 2                                     x, y, width, height, xWin, yWin, radius
    crosshair_cursor    = 4                                     x, y, width, height, xWin, yWin, radius
    point_cursor        = 8                                     x, y, width, height, xWin, yWin, radius
    point               = 16    
    line                = 32    
    polyline            = 64
    rectangle           = 128   
    polygon             = 256   
    ellipse             = 512   
    quad                = 1024
    cubic               = 2048
    arc                 = 4096
    arcmove             = 8192
    path                = 16384 
    text                = 32768 
    
    lineCursorTypes     = vertical_cursor       | horizontal_cursor
    shapedCursorTypes   = lineCursorTypes       | crosshair_cursor
    allCursorTypes      = shapedCursorTypes     | point_cursor
    
    lineTypes           = line                  | polyline
    linearTypes         = point                 | lineTypes
    polygonTypes        = rectangle             | polygon 
    linearShapeTypes    = polygonTypes          | linearTypes
    arcTypes            = arc                   | arcmove
    closedArcTypes      = ellipse               | arcTypes
    curveTypes          = quad                  | cubic
    basicShapeTypes     = linearShapeTypes      | closedArcTypes | curveTypes
    commonShapeTypes    = basicShapeTypes                                       # alias
    geometricShapeTypes = commonShapeTypes      | path
    allShapeTypes       = geometricShapeTypes   | text                          # all non-cursor types
    
    allObjectTypes      = allCursorTypes        | allShapeTypes
    allGraphicsTypes    = allObjectTypes
 
    move                = point                                                 # alias
  
    """
    vertical_cursor     = 1     # 5 parameters (W, H, xWin, yWin, radius)
    horizontal_cursor   = 2     # 5 parameters (W, H, xWin, yWin, radius)
    crosshair_cursor    = 4     # 5 parameters (W, H, xWin, yWin, radius)
    point_cursor        = 8     # 5 parameters (W, H, xWin, yWin, radius)
    point               = 16    # QPainterPath              QPointF     <=> 2 coordinates (X,Y)
    line                = 32    # QGraphicsLineItem         QLineF      <=> 4 coordinates (X0, Y0, X1, Y1)
    polyline            = 64
    rectangle           = 128   # QGraphicsRectItem         QRectF      <=> 4 coordinates (X, Y, W, H) = closed
    polygon             = 256   # QGraphicsPolygonItem      QPolygonF   <=> sequence of QPointF <=> sequence of (X, Y) pairs
    ellipse             = 512   # QGraphicsEllipseItem      QRectF      <=> 4 coordinates (X, Y, W, H) = closed
    quad                = 1024
    cubic               = 2048
    arc                 = 4096
    arcmove             = 8192
    path                = 16384 # Path
    qtpath              = 32768 # QPainterPath
    text                = 65536 # QGraphicsSimpleTextItem               <=> str
    
    lineCursorTypes     = vertical_cursor       | horizontal_cursor
    shapedCursorTypes   = lineCursorTypes       | crosshair_cursor
    allCursorTypes      = shapedCursorTypes     | point_cursor
    
    lineTypes           = line                  | polyline
    linearTypes         = point                 | lineTypes
    polygonTypes        = rectangle             | polygon 
    linearShapeTypes    = polygonTypes          | linearTypes
    arcTypes            = arc                   | arcmove
    closedArcTypes      = ellipse               | arcTypes
    curveTypes          = quad                  | cubic
    basicShapeTypes     = linearShapeTypes      | closedArcTypes | curveTypes
    commonShapeTypes    = basicShapeTypes                                       # alias
    geometricShapeTypes = commonShapeTypes      | path
    allShapeTypes       = geometricShapeTypes   | text                          # all non-cursor types
    
    allObjectTypes      = allCursorTypes        | allShapeTypes
    allGraphicsTypes    = allObjectTypes
 
    move                = point                                                 # alias
  
class GraphicsObject(QtWidgets.QGraphicsObject):
    """Qt Graphics Framework object frontend for PlanarGraphics objects
    TODO 2021-04-25 11:59:29
    Move this to imageviewer module, as they only apply to GraphicsImageViewerWidget
    FIXME
    TODO Logic for building/editing ROIs is broken for ellipse -- why?
    TODO check cachedPath logic
    
    NOTE: 2019-03-09 10:05:30
    the correspondence between the display object and the PlanarGraphics object
    is to be managed by an instance of Planar2QGraphicsManager
        
    NOTE: 2018-01-17 21:56:23
    currentframe and framesVisibility __init__() parameters cached to be 
    available when exiting build mode (i.e., from within __finalizeShape__)
         
         
    TODO: when building a shape, by default the resulting backend has no frame-state
    association; we must then give the option to associate states with certain frame
        
        
    NOTE: 2018-01-19 09:49:04 DONE
    x and y properties correctly update self.backend x and y
    
    NOTE: 2018-01-19 17:04:36
    TODO: curent frame might have to be managed independently, to allow more flexibility
    on linked cursors:
    
        now, several GUI cursors (frontends) can be referenced by a common backend
        however, image viewer windows are not necessarily "linked" i.e., one may
        be able to view a different image frames in different windows.
        
        The issue is whaty happens when a window shows a frame for which backend 
        has descriptor state, but another window shows a frame where the (same)
        backend does NOT have a descriptor state. Clearly, in the latter, the cursor
        is NOT visible -- DONE. However, when changing frames in a window this also 
        sets the backend's currentFrame to that value
    
    NOTE: All the action in build mode happens in the mouse event handlers
    
    Encapsulates the GUI conterpart ("frontend") of the PlanarGraphics objects
    defined in this module. In turn the PlanarGraphics objects are the "backend" 
    of the GraphicsObject.
    
    The PlanarGraphics objects are in a one-to-many relationship with GraphicsObject
    objects: several GraphicsObject objects may subserve (i.e. graphically display)
    the same PlanarGraphics object. It follows that the same PlanarGraphics object
    may be displayed by several GraphicsObject objects, each in its own graphics 
    scene.
    
    The PlanarGraphics -- GraphicsObject entity can be constructed from both 
    directions:
    
    a) constructing a GraphicsObject parametrically (i.e. from planar descriptors 
    as per the __init__() signature of the GraphicsObject) generates a PlanarGraphics
    backend automatically
    
    b) constructing a PlanarGraphics object then displaying it in a scene (by 
    calling the appropriate addGraphicsObject method in ImageViewer) will generate
    a GraphicsObject frontend in that image viewer's scene.
    
    From the GUI, the user can manipulate the frontend directly (mouse and key
    strokes) whereas the backends can only be are manipulated indirectly (via their 
    frontends).
    
    
    
    The following graphical types are supported (see the GraphicsObjectType enumeration):

    vertical_cursor     = 1     
    horizontal_cursor   = 2     
    crosshair_cursor    = 4     
    point_cursor        = 8     
    point               = 16    
    line                = 32    
    polyline            = 64
    rectangle           = 128   
    polygon             = 256   
    ellipse             = 512   
    quad                = 1024
    cubic               = 2048
    arc                 = 4096
    arcmove             = 8192
    path                = 16384 
    text                = 32768 
    
    lineCursorTypes     = vertical_cursor       | horizontal_cursor
    shapedCursorTypes   = lineCursorTypes       | crosshair_cursor
    allCursorTypes      = shapedCursorTypes     | point_cursor
    
    lineTypes         = line                  | polyline
    polygonTypes        = rectangle             | polygon 
    linearShapeTypes    = polygonTypes          | lineTypes
    arcTypes            = arc                   | arcmove
    curveTypes          = ellipse               | arcTypes
    basicShapeTypes     = linearShapeTypes      | curveTypes
    commonShapeTypes    = basicShapeTypes       | point
    geometricShapeTypes = commonShapeTypes      | path
    allShapeTypes       = geometricShapeTypes   | text
    
    allObjectTypes      = allCursorTypes        | allShapeTypes
  
    Any combination of these flags can be used to determine the type of the
    GraphicsObject instance or its inclusion in the subsets above, using 
    logical AND (&).
    
    e.g. self.objectType & allCursorTypes returns > 0 if the object is a cursor type
    
    Non-cursor types are rendered by means of QAbstractGraphicsShapeItem. This means
    that except for text, path, point and line, the generated shaped are always closed
    (in particular the polygons).
    
    To generate open polygons use the "path" type with QPainterPaths to draw 
    an open polygon (in Qt a polygon is considered "open" if the two extreme 
    points have different coordinates).
        
    """
    
    nonCursorTypes      = GraphicsObjectType.allShapeTypes
    
    #allObjectTypes      = allCursorTypes                        | allShapeTypes
    
    #undefinedType       = 0
    
        
    # this is for Qt Graphics View Framework RTTI logic
    Type = QtWidgets.QGraphicsItem.UserType + GraphicsObjectType.allObjectTypes
    
    signalPosition = pyqtSignal(int, str, "QPointF", name="signalPosition")
    
    # used to notify the cursor manager (a graphics viewer widget) that this cursor has been selected
    selectMe = pyqtSignal(str, bool, name="selectMe") 
    
    signalGraphicsObjectPositionChange = pyqtSignal("QPointF", name="signalGraphicsObjectPositionChange")
    
    # it is up to the cursor manager (a graphics viewer widget) to decide what 
    # to do with this (i.e., what menu & actions to generate)
    requestContextMenu = pyqtSignal(str,QtCore.QPoint, name="requestContextMenu")
    
    signalROIConstructed = pyqtSignal(int, str, name="signalROIConstructed")
    
    signalBackendChanged = pyqtSignal(object, name="signalBackendChanged")
    
    signalIDChanged = pyqtSignal(str, name="signalIDChanged")
    

    # NOTE: 2017-08-08 22:57:15 TODO:
    # API change to allow various graphic object types
    # NOTE: regular shape items as in QAbstractGraphicsShapeItem derivatives:
    # QGraphicsLineItem - straight lines, or points (a <<VERY>> short line)
    # QGraphicsEllipseItem - ellipse, circle and arcs of ellipse or circle, or point (a <<VERY>> small circle)
    # QGraphicsRectItem - rectangle, square, point (a <<VERY>> small square)
    # QGraphicsPolygonItem -- polygons
    # QGraphicsPathItem --  any path
    #
    # Requirements for construction:
    # (these are for pre-defined cursors and ROIs, for 
    #  interactively defining a ROI, see notes for buildMode)
    #
    # for cursors (of any type) -- 6-tuple (width, height, radius, winX, winY, cursor_type)
    # for ellipse (including circles), rectangles (including squares): 5-tuple (x, y, width, height, shape_type)
    # for arcs: 6-tuple (x, y, width, height, startAngle, spanAngle) => pies
    # for lines: 5-tuple (x1, y1, x2, y2, shape_type)
    # for generic path: I could fallback to the datatypes.ScanROI contructor rules to generate a QPainterPath
    #
    # Drawing mechanisms:
    # TODO: __drawObject__ to delegate
    # for cursors -- TODO: __drawCursor__ should only contain code for cursor drawing
    # for other QAbstractGraphicsShapeItem objects:
    #                TODO: construct a member QAbstractGraphicsShapeItem object
    #                       use its path(), shape(), boundingRect() functions
    
    # NOTE: 2018-01-15 22:38:58
    # To align GraphicsObject API with PlanarGraphics API the following parameters
    # have been removed from the GraphicsObject c'tor, as being redundant: 
    # visibleInAllFrames
    # linkedToFrame
    #
    # When frameVisibility is an empty list, the GraphicsObject becomes visible 
    # in all available frames and its backend (a PlanarGraphics object) has a 
    # common status. Furthermore, in this case various planar descriptors have 
    # the same value in _ALL_ frames (as if linkedToFrame was False)
    #
    # Conversely, when frameVisibility is not empty, the GraphicsObject frontend
    # is visible ONLY in the frame indices listed there, and its PlanarGraphics
    # backend has frame-state associations. Implicitly, changing the value of 
    # planar graphic descriptors in one frame are reflected in that frame only
    # (as if linkedToFrame was True).
    #
    # To be able to modify planar descriptor values in a frame-specific manner,
    # then set frameVisibility to the list of _ALL_ frame indices in the data.
    
    def __setup_default_appearance__(self):
        self.defaultTextBackgroundBrush = QtGui.QBrush(QtCore.Qt.white, QtCore.Qt.SolidPattern)
        self.defaultBrush = QtGui.QBrush(QtCore.Qt.white, QtCore.Qt.SolidPattern)
        
        self.defaultTextPenWidth = 1
        
        self.defaultPenWidth = 1
        
        self.defaultPenStyle = QtCore.Qt.DashLine
        self.defaultSelectedPenStyle = QtCore.Qt.SolidLine
        
        self.defaultColor = QtCore.Qt.magenta
        self.defaultCBCursorColor = QtCore.Qt.red
        self.defaultLinkedCursorColor = QtCore.Qt.darkMagenta
        
        self.defaultTextPen   = QtGui.QPen(self.defaultColor, self.defaultTextPenWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        self.defaultTextBrush = QtGui.QBrush(self.defaultColor, QtCore.Qt.SolidPattern)

        self.defaultLinkedTextPen   = QtGui.QPen(self.defaultLinkedCursorColor, self.defaultTextPenWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        #self.defaultLinkedTextPen   = QtGui.QPen(QtCore.Qt.black, self.defaultTextPenWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        self.defaultLinkedTextBrush = QtGui.QBrush(self.defaultLinkedCursorColor, QtCore.Qt.SolidPattern)
        
        # NOTE: 2018-06-23 17:21:06
        # "CB stands for "CommonBackend"
        self.defaultCBTextPen = QtGui.QPen(self.defaultCBCursorColor, self.defaultTextPenWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        self.defaultCBTextBrush = QtGui.QBrush(self.defaultCBCursorColor, QtCore.Qt.SolidPattern)
        
        self.defaultTextFont = QtGui.QFont("sans-serif")
        
        self.defaultPen = QtGui.QPen(self.defaultColor)
        self.defaultPen.setStyle(self.defaultPenStyle)
        self.defaultPen.setWidth(self.defaultPenWidth)
        self.defaultPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultSelectedPen = QtGui.QPen(self.defaultColor)
        self.defaultSelectedPen.setStyle(self.defaultSelectedPenStyle)
        self.defaultSelectedPen.setWidth(self.defaultPenWidth)
        self.defaultSelectedPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultSelectedPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultLinkedPen = QtGui.QPen(self.defaultLinkedCursorColor)
        self.defaultLinkedPen.setStyle(self.defaultPenStyle)
        self.defaultLinkedPen.setWidth(self.defaultPenWidth)
        self.defaultLinkedPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultLinkedPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultLinkedSelectedPen = QtGui.QPen(self.defaultLinkedCursorColor)
        self.defaultLinkedSelectedPen.setStyle(self.defaultSelectedPenStyle)
        self.defaultLinkedSelectedPen.setWidth(self.defaultPenWidth)
        self.defaultLinkedSelectedPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultLinkedSelectedPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultCBPen  = QtGui.QPen(self.defaultCBCursorColor)
        self.defaultCBPen.setStyle(self.defaultPenStyle)
        self.defaultCBPen.setWidth(self.defaultPenWidth)
        self.defaultCBPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultCBPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultCBSelectedPen = QtGui.QPen(self.defaultCBCursorColor)
        self.defaultCBSelectedPen.setStyle(self.defaultSelectedPenStyle)
        self.defaultCBSelectedPen.setWidth(self.defaultPenWidth)
        self.defaultCBSelectedPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultCBSelectedPen.setJoinStyle(QtCore.Qt.RoundJoin)
    
    def __init__(self, 
                 parameters=None, 
                 pos=None, 
                 objectType=GraphicsObjectType.allShapeTypes,
                 currentFrame=0, 
                 visibleFrames = [], 
                 label=None, 
                 labelShowsPosition=True, 
                 showLabel=True,
                 parentWidget=None):
                 
        """
        Named parameters:
        =================
        parameters: (optional, default is None) a PlanarGraphics object, or a 
            sequence of numeric values for the construction of a PlanarGraphics
            object as described in the table below.
                    
            When 'parameters' is None or an empty sequence, the 'objectType'
            parameter determines the behaviour as follows:
            (1) if objectType is NOT a cursor type, this triggers the 
                interactive drawing logic (to build the PlanarGraphics shape 
                using the GUI).
                
            (2) if objectType is a cursor type, raises an error (cursors cannot
            be built interactively)
            
            Otherwise, the length of the sequence must match the number of the 
            numeric values expected by the to-be-constructed PlanarGraphics with
            the type specified by 'objectType' parameter (see table).
        
        "objectType":     Value:    Type of "parameters" argument:
        ========================================================================
        vertical_cursor   1         numeric 5-tuple (W, H, xWin, yWin, radius)
        horizontal_cursor 2         numeric 5-tuple (W, H, xWin, yWin, radius)
        crosshair_cursor  4         numeric 5-tuple (W, H, xWin, yWin, radius)
        point_cursor      8         numeric 5-tuple (W, H, xWin, yWin, radius)
        point             16        numeric triple  (X, Y, radius)
        line              32        numeric 4-tuple (X0, Y0, X1, Y1) or QLineF
        rectangle         64        numeric 4-tuple (X,  Y,  W,  H)  or QRectF
        ellipse           128       numeric 4-tuple (X,  Y,  W,  H)  or QRectF
        polygon           256       sequence of numeric pairs (X, Y) or sequence of QPointF
        path              512       QPainterPath or a sequence of two-element tuples, where:
                                    element 0 is a str one of: "move", "start", 
                                    "line", "curve", or "control"
                                    element 1 is a tuple of coordinates (x,y);
                                    Each "curve" element MUST be followed by two 
                                    "control" elements.
                                            
        text              1024        str
        ========================================================================
        (See GraphicsObjectType enum for details)
        
        pos:    QtCore.QPoint or QtCore.QPointF, or None; default is None, which
                places the object at the scene's (0,0) coordinate
        
        objectType : one of the GraphicsObjectType enum values default is 
                    GraphicsObject.allShapeTypes (see GraphicsObjectType enum 
                    for details)
                    
        currentFrame, visibleFrames -- used only for parametric c'tor (which 
                    also builds a backend)
            
                    
        label: str or None (default) : this is what may be shown as cursor label 
            (the default is to show its own ID, if given)
        
        labelShowsPosition : bool (default is True)
        
        showLabel : bool (default is True)
        
        parentWidget : QtWidget (GraphicsImageViewerWidget) or None (default)
        
        roiId: str or None (default is None): this sets a default ID for the object
                
                NOTE: when None, the object will get its ID from the type
                
                NOTE: this is NOT the variable name under which this object is
                bound in the caller's namespace
                
        """
        #NOTE: 2017-11-20 22:57:21
        # backend for non-cursor types is self._graphicsShapedItem
        # whereas in cursor self._graphicsShapedItem is None !!!
        
        super(QtWidgets.QGraphicsObject, self).__init__()
        print("GraphicsObject__init__")
        print("\t")
        
        if not isinstance(parentWidget, QtWidgets.QWidget) and type(parentWidget).__name__ != "GraphicsImageViewerWidget":
            raise TypeError("'parentWidget' expected to be a GraphicsImageViewerWidget; got %s instead" % (type(self._parentWidget).__name__))
        
        self._parentWidget = parentWidget
        
        if isinstance(objectType, int):
            if not objectType & GraphicsObjectType.allObjectTypes:
                raise ValueError("objectType specifies an unknown GraphicsObjectType")
            
        elif not isinstance(objectType, GraphicsObjectType):
            raise TypeError("Second parameter must be an int or a GraphicsObjectType; got %s instead" % (type(objectType).__name__))
        
        self.__setup_default_appearance__()
        # NOT: 2017-11-24 22:30:00
        # assign this early
        # this MAY be overridden in __parse_parameters__
        #self._objectType = objectType # an int or enum !!!
        
        # NOTE: this is the actual string used for label display; 
        # it may be suffixed with the position if labelShowsPosition is True
        self._displayStr= "" 
        self._ID_ = ""
            
        # check for frameVisibility parameter
        # execute this in the __parse_parameters__ function so that we can 
        # distinguish between the case where we construct a GraphicsObject from 
        # a PlanarGraphics backend (and therefore frame visibility is given by 
        # the backend's frame-state associations) and the case where we construct
        # a GraphicsObject parametrically (thus constructing a new backend from 
        # scratch, hence we need frameVisibility parameter to set up the backend's
        # frame-state associations)

        # see qt5 examples/widgets/painting/pathstroke/

        self._pointSize = 5
        self._c_penWidth = 1
        self._c_penStyle = QtCore.Qt.SolidLine
        
        # NOTE: 2018-01-17 15:33:58
        # used in buildMode or editMode; applies to non-cursor objects only
        #self._c_shape_point         = -1
        self._c_activePoint         = -1 # shape point editing - used in edit & build modes
        self._c_activeControlPoint  = -1 # path control point editing; valid values are 0 and 1
        self._control_points        = [None, None]  # used in curve (cubic, quad) segment building for path ROIs
        self._constrainedPoint      = None
        self._hover_point           = None    # because a null QPointF is still valid:
        self._movePoint             = False
        
        # CAUTION make sure this is empty after exit from build or edit modes
        # ATTENTION NO subpaths allowed in cached path (for the moment) = use only
        # non-path ("primitive") PlanarGraphics objects as elements
        # CAUTION this ALWAYS  has a commonState (i.e. we cache it for the currently
        # displayed frame)

        # exists throughtout the lifetime of self.
        # must not be empty
        # generated in the following circumstances:
        # 1) __finalizeShape__ after exit from build mode
        # 2) __parse_parameters__ when _objectType is not a cursor
        #   either when object is build parametrically, or when it is derived from
        #   a backend. 
        #   depending on _objectType, _cachedPath may contain a copy of the backend
        #   itself, or a "control" path (containing control points & lines)
        #   
        # WARNING the cached path can contain only Move, Line, Cubic and Quad objects !!!
        #   e.g., for a rectangle or ellipse, the control line (used in building & editing)
        #   is in fact the diagonal or one of the diameters, respectively
        
        self._cachedPath_ = Path()
        
        self._shapeIsEditable       = False # control point editing
        self._movable               = True # moveable by mouse or keyboard
        self._editable              = True # switching to edit mode allowed
        self._transformable         = False # rotation & skewing
        self._buildMode             = False
        self._showlabel             = showLabel
        self._opaqueLabel = True
        self._curveBuild = False
        
        # NOTE: 2017-06-29 08:32:11
        # flags when a new position change sequence has begun (the previous 
        # sequence, if any, ended with a mouse release event)
        self._positionChangeHasBegun = False
        
        
        # NOTE: 2017-11-23 00:08:04
        # unlike non-cursor types, cursors are NOT back-ended by a QGraphicsItem
        # but rather directly painted by self.paint() method
        # the flag below toggles the cursor painting ON / OFF
        # TODO sync me with current frame cf self._frameindex
        self.__objectVisible__ = True
        
        self._labelShowsCoordinates = labelShowsPosition
        
        self._wbarPos = QtCore.QPointF() # planar descriptor for cursor width bar; NOT stored in the backend
        
        # NOTE: 2017-06-28 17:19:20
        # used as a flag to know when itemChange has been called the first time
        # when object is a cursor type
        self._deltaPos = QtCore.QPointF()# NOT stored in the baskend

        # NOTE: 2017-06-30 13:52:03
        # used for linked cursors logic, when object if a cursor type
        self._oldPos = QtCore.QPointF() # NOT stored in the backend
        
        # elements of cursor types - do NOT use _graphicsShapedItem here
        # because the Qt GraphicsView system will be decorate its bounding rect 
        # when selected
        self._vline     = QtCore.QLineF() # vertical cursor line
        self._hline     = QtCore.QLineF() # horizontal cursor line
        self._hwbar     = QtCore.QLineF() # vertical cursor window line
        self._vwbar     = QtCore.QLineF() # horizontal cursor window line
        self._crect     = QtCore.QRectF() # point cursor central rect
        self._wrect     = QtCore.QRectF() # point and crosshair cursor window rect

        self._labelRect = QtCore.QRectF() # a Null rectangle!!!
        self._labelPos  = QtCore.QPointF()
        
        self._backend_ = None

        self.__parse_parameters__(parameters, pos, objectType, visibleFrames, currentFrame)
        
        # ###
        # BEGIN ID and label management
        # ###
        
        # NOTE: bring names under a common value and KISS!
        # use same string for ID, label (the prefix of the display string) and backend name
        
        # if ID is given in the constructor, use it for self._ID_; else, generate it from object type
        #
        # if label is given in the constructor, use it for label, and for the ID !!!;
        #
        # else, if there is a backend and the backend has a name, use this as a label
        #
        # otherwise, use the ID for both label and backend name
        
        
        if isinstance(label, str) and len(label.strip()) > 0: 
            # label passed as __init__ parameter overrides => set name for backend too
            self._ID_ = label
            if self._backend_ is not None:
                self._backend_.name = self._ID_
                self._backend_.updateLinkedObjects()
            
        else:
            # no label passed at __init__; 
            if self._backend_ is not None and isinstance(self._backend_.name, str) and len(self._backend_.name.strip()):
                # if backend exists, use its name as ID
                self._ID_ = self._backend_.name
                
            else:
                if isinstance(self._objectType, int):
                    try:
                        self._ID_ = GraphicsObjectType(self._objectType).name
                        
                    except:
                        self._ID_ = "graphics_object"
                        
                else:
                    self._ID_ = self._objectType.name
                    
        # ###
        # END ID and label manageent
        # ###

        # NOTE: 2018-01-26 10:07:28
        # use a list of backends !!!
        self._linkedGraphicsObjects = list()
                
        self._isLinked = len(self._linkedGraphicsObjects)>0
        
        self._textPen               = self.defaultTextPen
        self._textBrush             = self.defaultTextBrush
        self._textBackgroundBrush   = self.defaultTextBackgroundBrush
        self._textCBPen             = self.defaultCBTextPen
        self._textCBBrush           = self.defaultCBTextBrush
        
        self._textFont              = self.defaultTextFont
        
        self._linkedTextPen         = self.defaultLinkedTextPen
        self._linkedTextBrush       = self.defaultLinkedTextBrush
        
        self._cursorPen             = self.defaultPen
        self._selectedCursorPen     = self.defaultSelectedPen
        
        self._linkedPen             = self.defaultLinkedPen
        self._linkedSelectedPen     = self.defaultLinkedSelectedPen
        
        self._cBPen                 = self.defaultCBPen
        self._cBSelectedPen         = self.defaultCBSelectedPen
        
        self._controlPointPen       = QtGui.QPen(QtGui.QColor(50, 100, 120, 200))
        self._controlPointBrush     = QtGui.QBrush(QtGui.QColor(200, 200, 210, 120))
        self._testBrush             = QtGui.QBrush(QtGui.QColor(100,100,105, 120))
        
        self._controlLinePen        = QtGui.QPen(QtGui.QBrush(QtCore.Qt.lightGray), 
                                                 1, QtCore.Qt.SolidLine)
        

        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable                 | \
                      QtWidgets.QGraphicsItem.ItemIsFocusable               | \
                      QtWidgets.QGraphicsItem.ItemIsSelectable              | \
                      QtWidgets.QGraphicsItem.ItemSendsGeometryChanges      | \
                      QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges)

        self.setAcceptHoverEvents(True)
        
        #self.setBoundingRegionGranularity(0.5)
        
        if self._objectType == GraphicsObjectType.crosshair_cursor:
            self.setBoundingRegionGranularity(0.5)
            
        if self._backend_ is not None:
            self.setVisible(len(self._backend_.frameIndices)==0 or self._backend_.hasStateForFrame(self._backend_.currentFrame))
            if self not in self._backend_.frontends:
                self._backend_.frontends.append(self)
            
            for f in self._backend_.frontends:
                if f != self:
                    self.signalGraphicsObjectPositionChange.connect(f.slotLinkedGraphicsObjectPositionChange)
                    f.signalGraphicsObjectPositionChange.connect(self.slotLinkedGraphicsObjectPositionChange)
                    
        self.__drawObject__() 
                    
        self.update()
        
    def __make_backend__(self, parameters, pos, gtype, frameindex=None, currentframe=0):
        """Constructs a PlanarGraphics backend from geometric coordinates.
        
        This also generates a PlanarGraphics backend from the 'parameters' argument
        
        Parameters:
        ===========
        
        parameters : numeric sequence, a str, or one of the following QtCore
            types: QLineF, QRectF, QPolygonF
                NOTE: QRectF is used as abounding rectangle for Rect and Ellipse
        
        """
        # NOTE 2021-04-25 13:37:19
        # TODO FIXME I think the frame index paradigm must be revisited...
        # check frameindex and currentframe
        if isinstance(frameindex, (tuple, list)):
            # this can be an empty sequence!!!
            if len(frameindex)> 0:
                if len(frameindex) == 1 and frameindex[0] is None:
                    frameindex.clear()
                    
                elif not all([isinstance(a, numbers.Integral) and a >= 0 for a in frameindex]):
                    raise TypeError("visible frame indices must be non-negative integers")
        
        elif isinstance(frameindex, numbers.Integral):
            if frameindex < 0:
                raise ValueError("visible frame index cannot be negative")
            
            frameindex = [frameindex]
            
        elif frameindex is None:
            frameindex = []
            
        else:
            raise TypeError("Index of visible frames (frameindex) expected to be an int or a sequence of int, or None; got %s instead" % type(frameindex).__name__)
        
        self._frameindex = frameindex

        if not isinstance(currentframe, numbers.Integral):
            raise TypeError("currentframe expected to be an int got %s instead" % type(currentFrame).__name__)
        
        self._currentframe_ = currentframe
        
        if gtype & GraphicsObjectType.allCursorTypes: # parametric c'tor for cursors
            if len(parameters) == 5 and all([isinstance(c, numbers.Number) for c in parameters]):
                if pos is None:
                    pos = QtCore.QPointF(0.,0.)
                
                self._backend_ = Cursor(pos.x(),  
                                        pos.y(),
                                        float(parameters[0]),
                                        float(parameters[1]),
                                        float(parameters[2]), 
                                        float(parameters[3]), 
                                        float(parameters[4]), 
                                        frameindex=frameindex,
                                        name=self._objectType.name,
                                        currentframe=self._currentframe_,
                                        graphicstype=gtype)
                
                super().setPos(pos)
                
            else:
                raise ValueError("For parametric cursor construction, 'parameters' must be a sequence of five 5 numbers; instead got %d elements" % (len(parameters)))
                
        else: # parametric c'tor for non-cursor graphic objects
            # NOTE: 2021-04-25 13:41:06
            # Enter build mode when one of the following is True:
            # * parameters is an empty sequence
            # * parameters is an empty Path
            # 
            if any([parameters is None, (isinstance(parameters, (tuple, list, Path)) and len(parameters) == 0)]):
                self._buildMode = True # self._backend_ will be built in __finalizeShape__() after exit from build mode
            #if parameters is None or (isinstance(parameters, (tuple, list)) and len(parameters) == 0) \
                #or (isinstance(parameters, Path) and len(parameters) == 0) or \
                #self._objectType == GraphicsObjectType.allShapeTypes:
                ## enters build mode
                #self._buildMode = True # self._backend_ will be built in __finalizeShape__() after exit from build mode

            elif isinstance(parameters, QtCore.QLineF):
                # NOTE: 2021-04-25 13:47:18
                # FIXME: this should be set appropriately by Path.__init__
                #self._objectType = GraphicsObjectType.line
                self._backend_ = Path(Move(parameters.p1().x(), parameters.p1().y()),
                            Line(parameters.p2().x(), parameters.p2().y()),
                            frameindex = self._frameindex,
                            currentframe = self._currentframe_)
    
                if self._backend_.name is None or len(self._backend_.name) == 0:
                    self._backend_.name = self._backend_.type.name
                
                self._cachedPath_ = self._backend_.asPath()
                
            elif isinstance(parameters, QtCore.QRectF):
                # parametric construction from a QRectF -- bounding rectangle
                # for Ellipse and Rect
                if gtype & GraphicsObjectType.rectangle:
                    self._backend_ = Rect(parameters.topLeft().x(), 
                                            parameters.topLeft().y(), 
                                            parameters.width(), 
                                            parameters.height(), 
                                            name = self._objectType.name, 
                                            frameindex = self._frameindex, 
                                            currentframe=self._currentframe_)
                    
                elif gtype & GraphicsObjectType.ellipse:
                    self._backend_ = Ellipse(parameters.topLeft().x(), 
                                            parameters.topLeft().y(), 
                                            parameters.width(), 
                                            parameters.height(), 
                                            name = self._objectType.name, 
                                            frameindex = self._frameindex, 
                                            currentframe=self._currentframe_)
                    
                else:
                    raise ValueError("mismatch between the graphics object type (%s) and parameter type (%s)" % (gtype, type(parameters).__name__))
                
                if self._backend_.name is None or len(self._backend_.name) == 0:
                    self._backend_.name = self._backend_.type.name
                
                self._cachedPath_ = self._backend_.asPath()
                        
            elif isinstance(parameters, QtGui.QPolygonF):
                # parametric c'tor from a QPolygonF
                # NOTE: QPolygonF if a :typedef: for QPointF list (I think?)
                # this HAS to be done this way, becase QPolygonF is NOT a python iterable
                self._objectType = GraphicsObjectType.polygon
                self._backend_ = Path()
                
                for k, p in enumerate(parameters):
                    if k == 0:
                        self._backend_.append(Move(p.x(), p.y()))
                        
                    else:
                        self._backend_.append(Line(p.x(), p.y()))
                        
                if self._frameindex is not None and len(self._frameindex):
                    self._backend_.frameIndices = self._frameindex
                    self._backend_.currentFrame = self._currentframe_
                
                if self._backend_.name is None or len(self._backend_.name) == 0:
                    self._backend_.name = self._objectType.name
                
                self._cachedPath_ = self._backend_.asPath()
                
            elif isinstance(parameters, QtGui.QPainterPath):
                self._objectType = GraphicsObjectType.path
                
                self._backend_ = Path()
                
                self._backend_.adoptPainterPath(parameters)
                
                #if self._frameindex is not None and len(self._frameindex):
                self._backend_.frameIndices = self._frameindex
                self._backend_.currentFrame = self._currentframe_
                    
                if self._backend_.name is None or len(self._backend_.name) == 0:
                    self._backend_.name = self._objectType.name
                
                self._cachedPath_ = self._backend_.asPath()
                
            elif isinstance(parameters, (tuple, list)):
                if all([isinstance(p, (QtCore.QPointF, QtCore.QPoint)) for p in parameters]):
                    # parametric c'tor from sequence of Qt points
                    self._objectType = GraphicsObjectType.polygon
                    
                    self._backend_ = Path()
                    self._backend_.append(Move(parameters[0].x(), parameters[0].y()))
                    
                    for c in parameters[1:]:
                        self._backend_.append(Line(c.x(), c.y()))
                        
                    #if self._frameindex is not None and len(self._frameindex):
                    self._backend_.frameIndices = self._frameindex
                    self._backend_.currentFrame = self._currentframe_
                        
                    if self._backend_.name is None or len(self._backend_.name) == 0:
                        self._backend_.name = self._objectType.name
                    
                    self._cachedPath_ = self._backend_.asPath()

                elif all([isinstance(p, (Start, Move, Line, Cubic, Quad, Arc, ArcMove)) for p in parameters]):
                    self._backend_ = Path(parameters) # a copy c'tor
                    self._objectType = self._backend_.type

                    if self._frameindex is not None and len(self._frameindex):
                        self._backend_.frameIndices = self._frameindex
                        self._backend_.currentFrame = self._currentframe_
                    
                    if self._backend_.name is None or len(self._backend_.name) == 0:
                        self._backend_.name = self._objectType.name
                    
                    self._cachedPath_ = self._backend_.asPath()
                    
                elif all([isinstance(p, numbers.Number) for p in parameters]):
                    if self._objectType & (GraphicsObjectType.line | GraphicsObjectType.rectangle | GraphicsObjectType.ellipse):
                        if len(parameters) == 4:
                            # x0, y0, x1, y1; either a line, 
                            # or the line of a rectangle's diagonal
                            # or one of the diameters of an ellipse
                            # the above is determined by the passed object type argument
                            # to __init__
                            
                            # cachedPath stores the control line (a diagonal)
                            if self._objectType == GraphicsObjectType.line:
                                
                                self._backend_ = Path(Move(parameters[0], parameters[1]), 
                                                        Line(parameters[2], parameters[3]))
                                
                            elif self._objectType == GraphicsObjectType.rectangle:
                                self._backend_ = Rect(parameters[0], parameters[1], 
                                                    parameters[2] - parameters[0],
                                                    parameters[3] - parameters[1])
                                
                            else:
                                self._backend_ = Ellipse(parameters[0], 
                                                        parameters[1], 
                                                        parameters[2] - parameters[0],
                                                        parameters[3] - parameters[1])

                            # override backend's frame-state associations & currentframe 
                            # ONLY if self._frameindex was set by __init__ parameter
                            #if self._frameindex is not None and len(self._frameindex):
                            self._backend_.frameIndices = self._frameindex
                            self._backend_.currentFrame = self._currentframe_
                            
                            if self._backend_.name is None or len(self._backend_.name) == 0:
                                self._backend_.name = self._objectType.name
                    
                            self._cachedPath_ = self._backend_.asPath()
                            
                        else:
                            raise TypeError("For line, ellipse or rectangle, a sequence of four scalars were expected")
                            
                    elif self._objectType & GraphicsObjectType.point:
                        # parametric construction of a Point
                        # TODO 2017-11-25 00:16:35
                        # make it accept a pictgui.Point - TODO define this :class: !
                        if len(parameters) in (2,3):
                            x = parameters[0]
                            y = parameters[1]
                            
                            if len(parameters) == 3:
                                self._pointSize = parameters[2]

                            self._backend_ = Move(parameters[0], parameters[1],
                                                frameindex = self._frameindex,
                                                currentframe=self._currentframe_)
                                
                            if self._backend_.name is None or len(self._backend_.name) == 0:
                                self._backend_.name = self._objectType.name
                            
                            self._cachedPath_ = self._backend_.asPath()
                            
                        else:
                            raise TypeError("For a point, 'parameters' is expected to be a sequence of two (x,y) or three (x, y, radius) numbers; got %s instead" % (type(parameters).__name__))
                    
                    elif self._objectType & (GraphicsObjectType.polygon | GraphicsObjectType.polyline):
                        if len(parameters)%2:
                            raise TypeError("For polygons or polyline, the numeric parameters must be a sequence with an even number of elements (x0,y0,x1,y1,... etc)")
                            
                        self._backend_ = Path()
                        
                        for k in range(0, len(parameters),2):
                            if k == 0:
                                self._backend_.append(Move(parameters[k], parameters[k+1]))
                                
                            else:
                                self._backend_.append(Line(parameters[k], parameters[k+1]))
                                
                        self._backend_.frameIndices = self._frameindex
                        
                        self._backend_.currentFrame = self._currentframe_
                            
                        if self._backend_.name is None or len(self._backend_.name) == 0:
                            self._backend_.name = self._objectType.name
                        
                        self._cachedPath_ = self._backend_.asPath()
                            
                elif all([isinstance(p, (tuple, list)) and len(p) == 2 and all([isinstance(cc, numbers.Number) for cc in p]) for p in parameters]):
                    # parametric c'tor from (X,Y) pairs of scalar coordinates
                    # force polyline type -- if you want to build a rectangle se above
                    
                    self._backend_ = Path()
                    self._backend_.append(Move(parameters[0][0], parameters[0][1]))

                    for p in parameters[1:]:
                        self._backend_.append(Line(p[0], p[1]))
                        
                    if self._objectType == GraphicsObjectType.polygon:
                        self._backend_.closed = True
                        
                    else:
                        self._objectType = GraphicsObjectType.polyline
                    
                    #if self._frameindex is not None and len(self._frameindex):
                    self._backend_.frameIndices = self._frameindex
                    self._backend_.currentFrame = self._currentframe_
                    
                    if self._backend_.name is None or len(self._backend_.name) == 0:
                        self._backend_.name = self._objectType.name
                    
                    self._cachedPath_ = self._backend_.asPath()
                        

    def __parse_parameters__(self, parameters, pos, gtype, frameindex = None, currentframe = 0):
        """Determines whether the constructor is supposed to build, or was given a backend
        
        The process follows some rules:
        
        1) For parametric constructors:
        1.1) for cursors, build the backend (Cursor) from the supplied parameters
        1.2) for shaped objects, build the cached path then generate a backend from it
        
        2) When this object is initialized from a planar graphic object:
        2.1) for cursors, use the planar graphics as backend
        2.2) for shaped objects (i.e. antything but Cursor), use the planar 
            graphics passed in 'parameters' as backend then generate a cached
            path from the state descriptor associated with the current frame
        (or from the common state descriptor)
        
        3) When function returns there shoud ALWAYS be a backend and, in the case
        of shaped objects, a cached path.
        
        3.1) The ONLY EXCEPTION this rule is for shaped objects construction with
        no parameters whatsoever: buildMode is invoked to generate a backend and 
        a cached path.
        
        frameindex and current frame are used ONLY when the graphics object is contructed
        parametrically (which also generates its own new backend);
        
        when the graphics object is contructed on an existing backend, frameindex 
        and currentframe parameters passed to the function call here are ignored
        
        """
        # ###
        # BEGIN parse parameters
        # ###
        
        # NOTE: 2021-04-24 22:02:33 FIXME
        # this should not be needed: the GraphicsObject must ALWAYS have a PlanarGraphics
        # backend and the the graphics type must be the one of the backend!
        #if isinstance(parameters, PlanarGraphics): 
            ## parameters are the backend, so override self._objectType set in __init__
            #self._objectType = parameters.type
            
        if not isinstance(pos, (QtCore.QPoint, QtCore.QPointF, type(None))):
            raise TypeError("When given, pos must be a QPoint or QPointF")
        
        # TODO 2017-11-25 00:15:21
        # set up backends when parameter is a pictgui primitive
        # link coordinate changes to the attributes of the backend
        #
        # FIXME: a str argument should be treated by parametric c'tor for Text
        # PlanarGraphics
        if isinstance(parameters, (Cursor, Ellipse, Rect, Path, Text, str)):
            if isinstance(parameters, (Cursor, Ellipse, Rect, Path)):
                if isinstance(parameters, Path) and len(parameters) == 0:
                    self.__make_backend__(parameters, pos, frameindex, currentframe)
                else:
                    # NOTE: 2021-04-25 11:19:19
                    # All Path objects should begin with a Move point, and this 
                    # rule should be enforced by Path constructors (and copy
                    # constructors. etc) - NOT HERE (it is NOT the job of GraphicsObject
                    # to do this)
                    self._backend_    = parameters # so that we reference this directly from this object
                    #self._objectType = self._backend_.type
                
                # cursors do not have a cached path
                if not isinstance(parameters, Cursor):
                    self._cachedPath_ = self._backend_.asPath()
                
            elif isinstance(parameters, str): # TODO: move this to __make_backend__
                    painter.drawText(parameters)
                    self._backend_ = Text(parameters)
                    
                    self._objectType = GraphicsObjectType.text
                    
            else:
                raise TypeError("Inavlid 'parameters' type for backend-based construction: %s" % type(parameters).__name__)

            self._buildMode = False
                    
            self._frameindex = self._backend_.frameIndices
            self._currentframe_ = self._backend_.currentFrame
                
            if self._backend_.name is None or len(self._backend_.name) == 0:
                self._backend_.name = self._objectType.name
                self._backend_.updateLinkedObjects()
            
            if pos is None or (isinstance(pos, (QtCore.QPoint, QtCore.QPointF)) and pos.isNull()):
                if self._backend_ is not None and self._backend_.hasStateForFrame(self._currentframe_):
                    pos = self._backend_.pos
                else:
                    pos = QtCore.QPointF(0,0)
                
            super().setPos(pos)
            
        else:
            self.__make_backend__(parameters, pos, frameindex, currentframe)
        
            
        # ###
        # END parse parameters
        # ###
        
    def __str__(self):
        return "%s, type %s, ID %s, backend %s" \
            % (self.__repr__(), self._objectType.name, self._ID_, self.backend.__repr__())
            
    def __setDisplayStr__(self, value=None):
        """Constructs the label string
        """
        nameStr = ""
        
        if value is None:
            if self._backend_ is None:
                nameStr = self._ID_
                
            else:
                nameStr = self._backend_.name

        elif isinstance(value, str):
            nameStr = value
            
        else:
            raise TypeError("Expecting a string argument, or None; got %s instead" % (type(value).__name__))
        
        if self._backend_ is not None and self._backend_.hasStateForFrame(self._currentframe_):
            if not isinstance(self._backend_, Path):
                stateDescriptor = self._backend_.getState(self._currentframe_)

                if isinstance(stateDescriptor, list) and len(stateDescriptor):
                    stateDescriptor = stateDescriptor[0]
                    
                if stateDescriptor is not None and len(stateDescriptor):
                    if self._parentWidget is not None: # why this condition here?
                        if self._labelShowsCoordinates:
                            if self.objectType & GraphicsObjectType.allCursorTypes:
                                if self._objectType & GraphicsObjectType.vertical_cursor:
                                    nameStr += ": %g" % stateDescriptor.x
                                    
                                elif self._objectType == GraphicsObjectType.horizontal_cursor:
                                    nameStr += ": %g" % stateDescriptor.y
                                    
                                else:
                                    nameStr += ": %g, %g" % (stateDescriptor.x, stateDescriptor.y)
                            
        self._displayStr = nameStr
        
    @safeWrapper
    def __calculate_shape__(self):
        if self._backend_ is not None:
            # non-cursor
            if self._buildMode or self.editMode:
                if self._cachedPath_ is not None and len(self._cachedPath_)> 0:
                    path.addPath(self._cachedPath_())
                    
                    if len(self._cachedPath_) > 1:
                        for k, element in enumerate(self._cachedPath_):
                            path.addEllipse(element.x, element.y,
                                            self._pointSize * 2.,
                                            self._pointSize * 2.)
                            
                path.addRect(sc.sceneRect())
                
            path.addPath(self._backend_())
                
            self.__setDisplayStr__()
                
            self.__updateLabelRect__()
            
            path.addRect(self._labelRect)
            
            if self.isSelected():
                if self._isLinked: # linked to other GraphicsObjects !!!
                    pen  = self._linkedSelectedPen
                    
                else:
                    pen = self._selectedCursorPen
                    
            else:
                if self._isLinked:# linked to other GraphicsObjects !!!
                    pen = self._linkedPen
                    #self._graphicsShapedItem.setPen(self._linkedPen)
                    
                else:
                    pen = self._cursorPen
                    
            pathStroker = QtGui.QPainterPathStroker(pen)
            
            return pathStroker.createStroke(path)
            
        else: 
            # no backend = this is in buildMode
            if self._cachedPath_ is not None and len(self._cachedPath_)> 0:
                pathStroker = QtGui.QPainterPathStroker(self._selectedCursorPen)
                
                path.addPath(pathStroker.createStroke(self._cachedPath_()))

            path.addRect(sc.sceneRect())
            
            
        return path
    
            
    @safeWrapper
    def __updateLabelRect__(self):
        """Calculates label bounding rectangle
        """
        if len(self._displayStr) > 0:
            fRect = self._parentWidget.fontMetrics().boundingRect(self._displayStr)
            self._labelRect.setRect(fRect.x(), fRect.y(), fRect.width(), fRect.height())

        else:
            self._labelRect  = QtCore.QRectF() # a null rect
        
    def __finalizeShape__(self):
        """Creates the _graphicsShapedItem, an instance of QGraphicsItem.
        Used only by non-cursor types, after exit from build mode.
        Relies on self._cachedPath_ which is a PlanarGraphics Path object. Therefore
        if makes inferences from self._objectType and the number of elements in
        self._cachedPath_
        """
        if self._objectType & GraphicsObjectType.allCursorTypes:
            # NOTE: do NOT use _graphicsShapedItem for cursors !!!
            return
            
        else:#FIXME in build mode there is no _backend_; we create it here from the cached path
            #NOTE: for non-cursors, cachedPath is generated in build mode, or in
            #NOTE:  __parse_parameters__()
            if len(self._cachedPath_):
                if self._backend_ is None:
                    # NOTE: 2018-01-23 20:20:38
                    # needs to create particular backends for Rect and Ellipse
                    # because self._cachedPath_ is a generic Path object
                    # (see __parse_parameters__)
                    if self._objectType == GraphicsObjectType.rectangle:
                        self._backend_ = Rect(self._cachedPath_[0].x,
                                             self._cachedPath_[0].y,
                                             self._cachedPath_[1].x-self._cachedPath_[0].x,
                                             self._cachedPath_[1].y-self._cachedPath_[0].y)
                        
                    elif self._objectType == GraphicsObjectType.ellipse:
                        self._backend_ = Ellipse(self._cachedPath_[0].x,
                                                self._cachedPath_[0].y,
                                                self._cachedPath_[1].x-self._cachedPath_[0].x,
                                                self._cachedPath_[1].y-self._cachedPath_[0].y)
                        
                        
                    else:
                        self._backend_ = self._cachedPath_.copy()
                        
                super().setPos(self._backend_.pos)
                
                self._buildMode = False
                self._control_points = [None, None]
                
                self._hover_point = None
            
                self.signalROIConstructed.emit(self.objectType, self.name)
                
                if self._backend_ is not None:
                    self._backend_.frontends.append(self)
            
            else:
                # no cached path exists
                self.signalROIConstructed.emit(0, "")
        
        self.update()

    def __drawObject__(self):
        if self._backend_ is None:
            return

        #if self._backend_.currentFrame != self._currentframe_:
            #self._backend_.currentFrame = self._currentframe_
        
        if len(self._displayStr) > 0:
            self.__setDisplayStr__(self._displayStr)
            
        else:
            self.__setDisplayStr__()
            
        if self.isCursor:
            self.__drawCursor__()
            
        else:
            self.__drawROI__()
            
    def __drawROI__(self):
        if self._buildMode:
            return
        
        self.__updateCachedPathFromBackend__() # to make sure control points stay within scene's rectangle

        self.update()
        
    def __drawCursor__(self):
        """Draws cursor
        """
        # NOTE: 2017-11-27 21:08:06
        # QPointF movedBy only used for crosshair cursors !!!
        #if not self.hasStateDescriptor:
            #return
        
        #state = self._backend_.getState(self._backend_.currentFrame)
        state = self._backend_.currentState
        
        if state is None or len(state) == 0:
            return
        
        self.prepareGeometryChange() # inherited from QGraphicsObject
        
        try:
            #NOTE: 2018-01-16 22:20:38 API change:
            # do NOT store our own graphics descriptors any more; use backend properties
            # getters for the planar descriptors; 
            # ATTENTION backend descriptors are in scene coordinates; therefore they 
            # need to be mapped back on this item's coordinates
            # CAUTION: the reverse is NOT true in itemChange where "value" is already given
            # in scene coordinates, and therefore self._deltaPos is also in scene coordinates
            
            # the access to the backend's planar descriptors always reads values 
            # from the current descriptor state of the backend, that is, either the
            # common state, or the state associated with the current image frame 
            # (for a data "volume") is the backend has frame-state associations
            
            # NOTE: 2018-01-18 15:16:55
            # THAT'S THE CORRECT WAY !!!
            # main cursor lines:
            self._vline = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x, 0)), 
                                        self.mapFromScene(QtCore.QPointF(state.x, state.height)))
            
            self._hline = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(0, state.y)), 
                                        self.mapFromScene(QtCore.QPointF(state.width, state.y)))
            
            # for vertical cursor ONLY
            if self._positionChangeHasBegun:
                newY = self._wbarPos.y() + self._deltaPos.y()
                
                if newY < 0:
                    newY = 0
                    
                elif newY > state.height-1:
                    newY = state.height-1
                    
                self._hwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x - state.xwindow/2,
                                                                            newY)),
                                            self.mapFromScene(QtCore.QPointF(state.x + state.xwindow/2,
                                                                            newY)))
                
            else:
                self._hwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x - state.xwindow/2,
                                                                            self._wbarPos.y())), 
                                            self.mapFromScene(QtCore.QPointF(state.x + state.xwindow/2,
                                                                            self._wbarPos.y())))
            
            # for horizontal cursor ONLY
            if self._positionChangeHasBegun:
                newX = self._wbarPos.x() + self._deltaPos.x()
                
                if newX < 0:
                    newX = 0
                    
                elif newX > state.width-1:
                    newX = state.width-1
                    
                self._vwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(newX, 
                                                                            state.y - state.ywindow/2)),
                                            self.mapFromScene(QtCore.QPointF(newX, 
                                                                            state.y + state.ywindow/2)))
                
            else:
                self._vwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(self._wbarPos.x(), 
                                                                            state.y - state.ywindow/2)),
                                            self.mapFromScene(QtCore.QPointF(self._wbarPos.x(), 
                                                                            state.y + state.ywindow/2)))
            
            # component of the point cursor (central rect)
            self._crect = QtCore.QRectF(self.mapFromScene(QtCore.QPointF(state.x - state.radius,
                                                                        state.y - state.radius)),
                                        self.mapFromScene(QtCore.QPointF(state.x + state.radius,
                                                                        state.y + state.radius)))
            
            # component of the point cursor and of the crosshair cursor (window rect)
            self._wrect = QtCore.QRectF(self.mapFromScene(QtCore.QPointF(state.x - state.xwindow/2,
                                                                        state.y - state.ywindow/2)),
                                        self.mapFromScene(QtCore.QPointF(state.x + state.xwindow/2,
                                                                        state.y + state.ywindow/2)))


            super().update()
            
        except Exception as exc:
            traceback.print_exc()
            #print("in %s %s" % (self.objectType, self.name))
        
        
    @property
    def isLinked(self):
        self._isLinked = len(self._linkedGraphicsObjects) > 0
        return self._isLinked
    
    def isLinkedWith(self, other):
        return other.ID in self._linkedGraphicsObjects
        
    # NOTE: 2017-06-30 12:04:24
    # TODO: functions/event handlers to implement/overload:
    # TODO OPTIONAL: collidesWithItem()
    # TODO OPTIONAL: contains() -- relies on shape()
    # TODO OPTIONAL: focusInEvent, focusOutEvent hoverEnterEvent hoverLeaveEvent 
    # TODO OPTIONAL: keyReleaseEvent (to move it by keyboard)
    # TODO OPTIONAL: hoverMoveEvent -- optional
    
    def type(self):
        return GraphicsObject.Type
    
    @safeWrapper
    def getShapePathElements(self):
        if not self.hasStateDescriptor:
            return
        
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return
        
        path = self.graphicsItem.shape() #  a QPainterPath with subpaths!
        
        elements = [path.elementAt(k) for k in range(path.elementCount())]
        
        # find subpaths: subpaths always begin with a moveTo element
        
        pathBreaks = [k for (k,e) in enumerate(elements) if e.type == QtGui.QPainterPath.MoveToElement]
        pathBreaks.append(len(elements))
        
        paths = [[e for e in elements[slice(pathBreaks[k], pathBreaks[k+1])]] for k in range(len(pathBreaks)-1)]
            
        return paths
    
        # NOTE: 2017-08-10 15:20:50

    @safeWrapper
    def __updateCachedPathFromBackend__(self):
        """No mapping transformations here, as the cached path is a copy of the
        _backend_'s state associated with the current frame.
        """
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return
        
        sc = self.scene()
            
        if self.scene() is None:
            try:
                sc = self._parentWidget.scene
            except:
                return
        
        if sc is None:
            return
            
        pad = self._pointSize
        left = pad
        right = sc.width() - pad
        top = pad
        bottom =sc.height() - pad
        
        if self._backend_ is None:
            return
        
        if isinstance(self._backend_, (Ellipse, Rect)):
            self._cachedPath_ = Path(Move(self._backend_.x, 
                                            self._backend_.y),
                                       Line(self._backend_.x + self._backend_.w,
                                            self._backend_.y + self._backend_.h))
                                    
        elif isinstance(self._backend_, Path):
            if self._backend_.hasStateForFrame(self._currentframe_):
                self._cachedPath_ = self._backend_.asPath(self._currentframe_)
                
            else:
                self._cachedPath_ = Path()
                
        else:
            self._cachedPath_ = self._backend_.asPath()
            
    def show(self):
        self.setVisible(True)
        
    def hide(self):
        self.setvibisle(False)
    
    #@safeWrapper
    def boundingRect(self):
        """Mandatory to get the bounding rectangle of this item
        """
        bRect = QtCore.QRectF()
        sc = self.scene()
        #if self.scene() is None:
            #sc = self.scene
        if sc is None:
            if self._parentWidget is not None:
                sc = self._parentWidget.scene
                
        if sc is None:
            return bRect #  return a null QRect!
            
        self.__setDisplayStr__(self._ID_)
            
        self.__updateLabelRect__()
        
        try:
            if self.objectType & GraphicsObjectType.allCursorTypes:
                # NOTE: 2018-01-25 22:06:25
                # this is required: what if this cursor is linked with one in another
                # window that shows a different frame, for which the backend has no
                # state descriptor?
                # seame check is done for non-cursor types, below
                state = self._backend_.getState(self._currentframe_) 
                
                if isinstance(state, DataBag) and len(state):
                    if self.isVerticalCursor:
                        # QRectF(x,y,w,h)
                        bRect = self.mapRectFromScene(QtCore.QRectF(state.x - state.xwindow/2,
                                                                    0, 
                                                                    state.xwindow, 
                                                                    state.height))
                        
                    elif self.isHorizontalCursor:
                        bRect = self.mapRectFromScene(QtCore.QRectF(0, 
                                                                    state.y - state.ywindow/2,  
                                                                    state.width, 
                                                                    state.ywindow))
                        
                    elif self.isCrosshairCursor:
                        bRect =  self.mapRectFromScene(QtCore.QRectF(-state.width//2, 
                                                                    -state.height//2, 
                                                                    state.width, 
                                                                    state.height))
                        
                    else: # point cursor
                        bRect = self.mapRectFromScene(QtCore.QRectF(state.x - state.xwindow/2, 
                                                                    state.y - state.ywindow/2, 
                                                                    state.xwindow, 
                                                                    state.ywindow))

                    if not self._labelRect.isNull():
                        bRect |= self._labelRect # union
                        
                else:
                    bRect = QtCore.QRectF()
                        
            else:
                # not a cursor
                if self._backend_ is not None and self._backend_.hasStateForFrame(self._currentframe_) and self._backend_() is not None:
                    #bRect = self.mapRectFromScene(self._backend_().controlPointRect()) # relies on planar graphics's shape !!!!
                    bRect = self.mapRectFromScene(self._backend_().boundingRect()) # relies on planar graphics's shape !!!!
                    
                    if self.editMode:
                        bRect |= self.mapRectFromScene(self._cachedPath_().boundingRect())
                        
                else:
                    # no backend, or backend has no state
                    if self._buildMode:
                        # we need this to pick up mouse events from anywhere in the scene
                        bRect = sc.sceneRect()
                        
                    else:
                        bRect = QtCore.QRectF()
                        
                if not self._labelRect.isNull():
                    lrect = QtCore.QRectF(self._labelRect.topLeft(),
                                        self._labelRect.bottomRight())
                    
                    lrect.moveBottomLeft(bRect.center())
                    
                    bRect |= lrect # union
        except Exception as exc:
            traceback.print_exc()
            #print("in %s %s frame %d" % (self.type, self.name, self.currentFrame))
        
                
        return bRect
    
    def toScenePath(self):
        """Returns a new pictgui.Path object or None if isCursor is True.
        
        This constructs a new pictgui.Path object. 
        
        To reflect the changes in this object's values in an existing
        pictgui.Path object, use direct access to the attributes of the latter.
        
        Coordinates are mapped to scene's coordinate system
        
        NOTE: This is not a reference to the backend Path object
        """
        #if not self.hasStateDescriptor:
            #return
        
        if not self.isCursor:
            if self.isText:
                # TODO FIXME ???
                raise NotImplementedError("Scene coordinates from text objects not yet implemented")
            
            if len(self._cachedPath_ > 0):
                return Path([self.mapToScene(p) for p in self._cachedPath_.qPoints()])
            
    def toSceneCursor(self):
        """Returns a new pictgui.Cursor object or None if isCursor is False.
        
        This constructs a new pictgui.Cursor object. 
        
        To reflect the changes in this object's values in an existing 
        pictgui.Cursor object use direct acces to the attributes of the latter.
        
        Coordinates are mapped to scene's coordinate system.
        
        NOTE: This does NOT return the reference to the backend Cursor object (which may exist)
        """
        #if not self.hasStateDescriptor:
            #return
        
        if self.isCursor:
            stateDescriptor = self._backend_.getState(self._currentframe_)
            if stateDescriptor and len(stateDescriptor):
                p = self.mapToScene(QtCore.QPointF(self._backend_.x, self._backend_.y))
                return Cursor(self.name, p.x(), p.y(), self._backend_.width, self._backend_.height, self._backend_.xwindow, self._backend_.ywindow, self._backend_.radius)
            
                #p = self.mapToScene(QtCore.QPointF(stateDescriptor.x, stateDescriptor.y))
                #return Cursor(self.name, p.x(), p.y(), stateDescriptor.width, stateDescriptor.height, stateDescriptor.xwindow, stateDescriptor.ywindow, stateDescriptor.radius)
            
    def getScenePosition(self):
        """Returns the position in the scene as x, y sequence
        FIXME
        """
        p = self.mapToScene(self._backend_.pos)
            
        return p.x(), p.y()
            
            
    def getSceneCoordinates(self):
        """Returns the coordinates that define this shape in the scene.
        FIXME
        Coordinates are mapped to scene's coordinate system
        """
        # NOTE: 2017-11-21 23:07:07
        # DO NOT not rely on QPainterPath - pictgui.Path conversions here, 
        # because QPainterPath inserts all sorts of points & segments (something
        # to do with how they compute the rendering of the actual path)
        # 
        stateDescriptor = self._backend_.getState(self._currentframe_)
        
        if len(stateDescriptor):
            if self.isCursor:
                p = self.mapToScene(QtCore.QPointF(self._backend_.x, self._backend_.y))
                ret = [p.x(), p.y(), self._backend_.width, self._backend_.height, self._backend_.xwindow, self._backend_.ywindow, self._backend_.radius]

            else: #FIXME
                if isinstance(stateDescriptor, list):
                    pp = list()
                    for s in stateDescriptor:
                        if s:
                            pp.append([])
                        else:
                            pp.append(None)
                            
                pp = [self.mapToScene(p) for p in stateDescriptor.qPoints()]
                
                if self.isPoint:
                    ret = [pp[0].x(), pp[0].y()]
                    
                elif self.isLine:
                    ret = [pp[0].x(), pp[0].y(), pp[1].x(), pp[1].y()]
                
                elif self.isRectangle or self.isEllipse:
                    # the cached path is the diagonal/primary diameter line!
                    # return the x, y, width, height
                    ret = [pp[0].x(), pp[0].y(), pp1.x() - pp0.x(), pp1.y() - pp0.y()]
                    
                elif self.isPolygon:
                    ret = [[p.x(), p.y()] for p in pp]
                    
                elif self.isPath:
                    # TODO FIXME
                    raise NotImplementedError("Scene coordinates from path objects not yet implemented")
                
                elif self.isText:
                    # TODO FIXME ???
                    raise NotImplementedError("Scene coordinates from text objects not yet implemented")
                
        return ret
    
    @safeWrapper
    def shape(self):
        """ Used in collision detection, etc.
        Currently return a path made of this item's bounding rectangle.
        """
        path = QtGui.QPainterPath()
        
        sc = self.scene()
        
        if sc is None:
            if self._parentWidget is not None:
                sc = self._parentWidget.scene
                
        if sc is None:
            #path.addRect(QtCore.QRectF()) #  return a null QRect!
            return path
        
        if self.objectType & GraphicsObjectType.allCursorTypes:
            state = self._backend_.getState(self._currentframe_)
            if state is not None and len(state):
                if self.isCrosshairCursor:
                    path.moveTo(state.x, -state.height//2 - self._deltaPos.y()) # BEGIN vertical line
                    path.lineTo(state.x, state.height//2 - self._deltaPos.y())  # END vertical line
                    path.moveTo(-state.width//2 - self._deltaPos.x(), state.y)  # BEGIN horizontal line
                    path.lineTo(state.width//2 - self._deltaPos.x(), state.y)   # END horizontal line
                    
                    self.__setDisplayStr__()
                        
                    self.__updateLabelRect__()
                    
                    path.addRect(self._labelRect)
                    
                else:
                    path.addRect(self.boundingRect()) # for cursors this is safe: it DOES NOT recurse infinitely
                
            return path
        
        else:
            if self._backend_ is not None and self._backend_.hasStateForFrame(self._currentframe_) and self._backend_() is not None:
                path.addPath(self.mapFromScene(self._backend_()))
                
                if self._objectType == GraphicsObjectType.line:
                    p0 = self.mapFromScene(QtCore.QPointF(self._backend_[0].x, 
                                                          self._backend_[0].y))
                    
                    p1 = self.mapFromScene(QtCore.QPointF(self._backend_[1].x, 
                                                          self._backend_[1].y))
                    
                    path.addRect(QtCore.QRectF(p0,p1))
                    
                elif self._objectType == GraphicsObjectType.path:
                    path.addRect(self.mapRectFromScene(self._backend_().boundingRect()))
                
                if self.editMode:
                    if self._cachedPath_ is not None and len(self._cachedPath_)> 0:
                        path.addPath(self.mapFromScene(self._cachedPath_()))
                        
                    if len(self._cachedPath_) > 1:
                        for k, element in enumerate(self._cachedPath_):
                            pt = self.mapFromScene(QtCore.QPointF(element.x, 
                                                                  element.y))
                            
                            path.addEllipse(pt, self._pointSize, self._pointSize)

                self.__setDisplayStr__()
                    
                self.__updateLabelRect__()
                
                lrect = QtCore.QRectF(self._labelRect.topLeft(),
                                      self._labelRect.bottomRight())
                
                lrect.moveBottomLeft(self.boundingRect().center())
                path.addRect(lrect)
                path.addRect(self.boundingRect())
                
                path.setFillRule(QtCore.Qt.WindingFill)
                
                return path
            
    
            else: 
                # either no backend (in build mode), or no state for current frame
                if self._buildMode:
                    if self._cachedPath_ is not None and len(self._cachedPath_)> 0:
                        path.addPath(self._cachedPath_())
                    
                    path.addRect(sc.sceneRect()) # needed to find collisions with mouse
                
        return path
    
    def setPos(self, x, y=None):
        """Overloads QGraphicsItem.setPos()
        Parameters:
        ==========
        x: float or QtCore.QPointF when y is None
        y: float or None
        """
        # NOTE changes to backend ar done by itemChange()
        if self.objectType & GraphicsObjectType.allCursorTypes:
            if all([isinstance(v, numbers.Real) for v in (x,y)]):
                super().setPos(x,y)
                
            elif isinstance(x, QtCore.QPointF):
                super().setPos(x)
                
            elif isinstance(x, QtCore.QPoint):
                super().setPos(QtCore.QPointF(x))
                
            else:
                raise TypeError("Either x and y must be supplied as floats, or x must be a QPointF or QPoint")
            
        else:
            if all([isinstance(v, numbers.Real) for v in (x,y)]):
                super().setPos(x,y)
                
            elif isinstance(x, QtCore.QPointF):
                super().setPos(x)
                
            elif isinstance(x, QtCore.QPoint):
                super().setPos(QtCore.QPointF(x))
                
            else:
                raise TypeError("Either x and y must be supplied as floats, or x must be a QPointF or QPoint")
            
        self.redraw()
        
    def update(self):
        if self.scene(): # because it may by Null at construction
            self.scene().update(self.boundingRect())
            #self.scene().update(self.scene().sceneRect().x(), \
                                #self.scene().sceneRect().y(), \
                                #self.scene().sceneRect().width(), \
                                #self.scene().sceneRect().height())
            
            #for v in self.scene().views():
                #v.repaint(v.childrenRect())
            
        else:
            super().update()
        
    def redraw(self):
        self.__drawObject__()

        #if self._labelShowsCoordinates:
        self.__setDisplayStr__()
        self.__updateLabelRect__()

        self.update()
        
    def paint(self, painter, styleOption, widget):
        # NOTE: 2021-03-07 18:30:02
        # to time the painter, uncomment "self.timed_paint(...)" below and comment
        # out the line after it ("self.do_paint(...)")
        # When times, the duration of one executino of do_paint is printed on
        # stdout - CAUTION generates large output
        #self.timed_paint(painter, styleOption, widget)
        self.do_paint(painter, styleOption, widget)
        
    @timefunc
    def timed_paint(self, painter, styleOption, widget):
        # NOTE: 2021-03-07 18:32:00
        # timed version of the painter; to time the painter, call this function
        # instead of "do_paint" in self.paint(...) - see NOTE: 2021-03-07 18:30:02
        self.do_paint(painter, styleOption, widget)
        
    #@safeWrapper
    def do_paint(self, painter, styleOption, widget):
        """Does the actual painting of the item.
        Also called by super().update() & scene.update()
        """
        # NOTE: 2021-03-07 18:33:05
        # both paint and timed_paint call this function; use timed_paint to
        # time the painter - i.e., to output the duration of the paint execution
        # on the stdout - CAUTION generates large outputs
        
        try:
            if not self.__objectVisible__:
                return
            
            if not self._buildMode:
                if self._backend_ is None:
                    return
                
                if not self._backend_.hasStateForFrame(self._backend_.currentFrame):
                    return
                
            self.__updateLabelRect__()
            
            if self._buildMode:
                painter.setPen(self._selectedCursorPen)
                textPen = self._textPen
                
            else:
                if self.isSelected(): # inherited from QGraphicsItem via QGraphicsObject
                    if self._isLinked:
                        painter.setPen(self._linkedSelectedPen)
                        textPen = self._linkedTextPen
                        
                    elif len(self._backend_.frontends) > 0:
                        painter.setPen(self._cBSelectedPen)
                        textPen = self._textCBPen
                        
                    else:
                        painter.setPen(self._selectedCursorPen)
                        textPen = self._textPen
                        
                else:
                    if self._isLinked:
                        painter.setPen(self._linkedPen)
                        textPen = self._linkedTextPen
                        
                    elif len(self._backend_.frontends) > 0:
                        painter.setPen(self._cBPen)
                        textPen = self._textCBPen
                        
                    else:
                        painter.setPen(self._cursorPen)
                        textPen = self._textPen

            labelPos = None         # NOTE: 2017-06-23 09:41:24
                                    # below I calculate a default label position
                                    # based on cursor type
                                    # this position will be then changed dynamically
                                    # according to the font metrics
                                    # when the painter becomes active
                                    
            painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
            
            if self.objectType & GraphicsObjectType.allCursorTypes:
                # NOTE: 2018-01-18 14:47:49
                # WARNING: DO NOT use _graphicsShapedItem to represent cursors,
                # because the Qt GraphicsView system renders its shape's bounding 
                # rect with a dotted line when item is selected.
                ### self._graphicsShapedItem.paint(painter, styleOption, widget)

                lines = None
                rects = None
                
                state = self._backend_.getState(self._backend_.currentFrame)
                
                if state is None or len(state) == 0:
                    return
                
                if self._objectType == GraphicsObjectType.vertical_cursor:
                    lines = [self._vline, self._hwbar]
                    
                    labelPos = self.mapFromScene(QtCore.QPointF(self._backend_.x - self._labelRect.width()/2, 
                                                                self._labelRect.height()))

                elif self._objectType == GraphicsObjectType.horizontal_cursor:
                    lines = [self._hline, self._vwbar]
                    labelPos = self.mapFromScene(QtCore.QPointF(0, self._backend_.height/2 - self._labelRect.height()/2))

                elif self._objectType == GraphicsObjectType.crosshair_cursor:
                    lines = [self._vline, self._hline]
                    labelPos = self.mapFromScene(QtCore.QPointF(self._backend_.x  - self._labelRect.width()/2,
                                                                self._labelRect.height()))
                    
                    rects = [self._wrect]
                        
                else: # point cursor
                    rects = [self._crect]
                    labelPos = self.mapFromScene(QtCore.QPointF(self._backend_.x - self._labelRect.width()/2,
                                                                self._backend_.y - self._labelRect.height()))

                if lines is not None:
                    painter.drawLines(lines)
                    
                if rects is not None:
                    painter.drawRects(rects)
                    
            else:
                # non-cursor types
                # NOTE: FIXME be aware of undefined behaviours !!! (check flags and types)
                if self._buildMode: # this only makes sense for ROIs
                    if len(self._cachedPath_) == 0: # nothing to paint !
                        return
                    
                    # NOTE: 2018-01-24 15:57:16 
                    # THE SHAPE IN BUILD MODE = cached path
                    # first draw the shape
                    painter.setPen(self._selectedCursorPen)
                    
                    if self.objectType & GraphicsObjectType.path:
                        painter.drawPath(self._cachedPath_)
                        #painter.drawPath(self._cachedPath_())
                        
                        if self._curveBuild and self._hover_point is not None:
                            if self._control_points[0] is not None:
                                path = QtGui.QPainterPath(self._cachedPath_[-1].point())
                                
                                if self._control_points[1] is not None:
                                    path.cubicTo(self._control_points[0], 
                                                self._control_points[1], 
                                                self._hover_point)
                                    
                                else:
                                    path.quadTo(self._control_points[0], 
                                                self._hover_point)
                                    
                                painter.drawPath(path)
                                
                    if len(self._cachedPath_) > 1:
                        if self.objectType & GraphicsObjectType.line:
                            painter.drawLine(self._cachedPath_[-2].point(), 
                                            self._cachedPath_[-1].point())
                            
                        elif self.objectType & GraphicsObjectType.rectangle:
                            painter.drawRect(QtCore.QRectF(self._cachedPath_[-2].point(), 
                                                        self._cachedPath_[-1].point()))
                            
                        elif self.objectType & GraphicsObjectType.ellipse:
                            painter.drawEllipse(QtCore.QRectF(self._cachedPath_[-2].point(), 
                                                            self._cachedPath_[-1].point()))
                            
                        elif self.objectType & GraphicsObjectType.polygon:
                            for k, element in enumerate(self._cachedPath_):
                                if k > 0:
                                    painter.drawLine(self._cachedPath_[k-1].point(), 
                                                    self._cachedPath_[k].point())
                        

                    # NOTE: 2018-01-24 15:56:51 
                    # CONTROL POINTS AND LINES IN BUILD MODE
                    # now draw control points and lines
                    # draw control points
                    painter.setPen(self._controlPointPen) 
                    painter.setBrush(self._controlPointBrush)
                    
                    for k, element in enumerate(self._cachedPath_):
                        painter.drawEllipse(element.x - self._pointSize,
                                            elementy - self._pointSize,
                                            self._pointSize * 2., 
                                            self._pointSize * 2.)
                        
                        if k > 0:
                            painter.drawLine(self._cachedPath_[k-1].point(), 
                                            element.point())
                            
                    # NOTE: 2018-01-24 15:58:33 
                    # EXTRA CONTROL POINTS AND HOVER POINT IN BUILD MODE WHERE THEY EXIST
                    if self.objectType & GraphicsObjectType.path:
                        if self._control_points[0] is not None:
                            painter.drawEllipse(self._control_points[0].x() - self._pointSize,
                                                self._control_points[0].y() - self._pointSize,
                                                self._pointSize * 2., 
                                                self._pointSize * 2.)
                            
                            painter.drawLine(self._cachedPath_[-1].point(), 
                                            self._control_points[0])
                            
                            if self._control_points[1] is not None:
                                painter.drawEllipse(self._control_points[1].x() - self._pointSize,
                                                    self._control_points[1].y() - self._pointSize,
                                                    self._pointSize * 2., 
                                                    self._pointSize * 2.)
                                
                                painter.drawLine(self._control_points[0], 
                                                self._control_points[1])
                                
                                if self._hover_point is not None:
                                    painter.drawEllipse(self._hover_point.x() - self._pointSize, 
                                                        self._hover_point.y() - self._pointSize, 
                                                        self._pointSize * 2., 
                                                        self._pointSize *2.)
                                    
                                    painter.drawLine(self._control_points[1], 
                                                    self._hover_point)
                                    
                                
                            else:
                                if self._hover_point is not None:
                                    painter.drawEllipse(self._hover_point.x() - self._pointSize, 
                                                        self._hover_point.y() - self._pointSize, 
                                                        self._pointSize * 2., 
                                                        self._pointSize *2.)
                                    
                                    painter.drawLine(self._control_points[0], 
                                                    self._hover_point)
                                    
                        elif self._hover_point is not None:
                            painter.drawEllipse(self._hover_point.x() - self._pointSize, 
                                                self._hover_point.y() - self._pointSize, 
                                                self._pointSize * 2., 
                                                self._pointSize *2.)
                            
                            painter.drawLine(self._cachedPath_[-1].point(), 
                                            self._hover_point)
                        
                    elif self._hover_point is not None:
                        painter.drawEllipse(self._hover_point.x() - self._pointSize, 
                                            self._hover_point.y() - self._pointSize, 
                                            self._pointSize * 2., 
                                            self._pointSize *2.)
                        
                        painter.drawLine(self._cachedPath_[-1].point(), 
                                        self._hover_point)

                        if self.objectType & GraphicsObjectType.line:
                            painter.drawLine(self._cachedPath_[-1].point(), 
                                            self._hover_point)
                        
                        elif self.objectType & GraphicsObjectType.rectangle:
                            painter.drawRect(QtCore.QRectF(self._cachedPath_[-1].point(), 
                                                        self._hover_point))
                            
                        elif self.objectType & GraphicsObjectType.ellipse:
                            painter.drawEllipse(QtCore.QRectF(self._cachedPath_[-1].point(), 
                                                            self._hover_point))
                            
                        elif self.objectType & GraphicsObjectType.polygon:
                            painter.drawLine(self._cachedPath_[-1].point(), 
                                            self._hover_point)

                    labelPos = self.boundingRect().center()
                    
                else:
                    # not in build mode
                    # NOTE: 2018-01-24 16:12:20
                    # DRAW SHAPE 
                    
                    # NOTE: 2018-01-24 16:12:43
                    # SELECT PEN & BRUSH FIRST
                    if self.isSelected():
                        if self._isLinked: # linked to other GraphicsObjects !!!
                            painter.setPen(self._linkedSelectedPen)
                            
                        elif self.sharesBackend:
                            painter.setPen(self._cBSelectedPen)
                            
                        else:
                            painter.setPen(self._selectedCursorPen)
                            
                    else:
                        if self._isLinked:# linked to other GraphicsObjects !!!
                            painter.setPen(self._linkedPen)
                            
                        elif self.sharesBackend:
                            painter.setPen(self._cBPen)
                            
                        else:
                            painter.setPen(self._cursorPen)
                            
                    if self.objectType & GraphicsObjectType.point:
                        if self._isLinked:# linked to other GraphicsObjects !!!
                            brush = QtGui.QBrush(self.defaultLinkedCursorColor)
                            
                        else:
                            brush = QtGui.QBrush(self.defaultColor)
                            
                        painter.setBrush(brush)
                            
                    # NOTE: 2018-01-24 16:13:03
                    # DRAW THE ACTUAL SHAPE
                    # NOTE: 2018-01-24 17:17:05
                    # WE SHOULD HAVE A _backend_ BY NOW
                    
                    #if self._cachedPath_ is not None and len(self._cachedPath_):
                    if self._backend_ is not None:
                        if self._objectType == GraphicsObjectType.ellipse:
                            r_ = self.mapRectFromScene(self._backend_.x,
                                                       self._backend_.y,
                                                       self._backend_.w,
                                                       self._backend_.h)
                            
                            painter.drawEllipse(r_)

                        elif self._objectType == GraphicsObjectType.rectangle:
                            r_ = self.mapRectFromScene(self._backend_.x,
                                                       self._backend_.y,
                                                       self._backend_.w,
                                                       self._backend_.h)
                            
                            painter.drawRect(r_)
                                                                            
                        elif self._objectType == GraphicsObjectType.point:
                            p_ = self.mapFromScene(self._backend_.x,
                                                   self._backend_.y)
                            
                            r_ = self.mapRectFromScene(self._backend_.x,
                                                       self._backend_.y,
                                                       self._backend_.w,
                                                       self._backend_.h)
                            
                            painter.drawPoint(p_)

                            painter.drawEllipse(r_)
                            
                        else: # general Path backend, including polyline, polygon
                            path = self._backend_.asPath(frame=self._currentframe_)
                            
                            qpath = self.mapFromScene(path())
                            
                            painter.drawPath(qpath)
                            
                    labelPos = self.boundingRect().center()
                    
                    if self.editMode:
                        # NOTE: 2018-01-24 16:14:15
                        # CONTROL AND HOVER POINTS AND CONTROL LINES IN EDIT MODE
                        
                        painter.setPen(self._controlPointPen)
                        painter.setBrush(self._controlPointBrush)
                        
                        # ATTENTION for paths, curves have extra control points!
                        
                        if self._cachedPath_ is not None and len(self._cachedPath_) > 0:
                            if self.objectType & GraphicsObjectType.path:
                                for k, element in enumerate(self._cachedPath_):
                                    if isinstance(element, Quad):
                                        pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        cp = self.mapFromScene(QtCore.QPointF(element.cx, element.cy))
                                        
                                        painter.drawEllipse(cp.x() - self._pointSize, \
                                                            cp.y() - self._pointSize, \
                                                            self._pointSize * 2., self._pointSize * 2.)
                                        
                                        painter.drawEllipse(pt.x() - self._pointSize, \
                                                            pt.y() - self._pointSize, \
                                                            self._pointSize * 2., self._pointSize * 2.)
                                        
                                        painter.drawLine(self.mapFromScene(self._cachedPath_[k-1].point()), cp)
                                        painter.drawLine(cp, pt)
                                        
                                    elif isinstance(element, Cubic):
                                        pt  = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        cp1 = self.mapFromScene(QtCore.QPointF(element.c1x, element.c1y))
                                        cp2 = self.mapFromScene(QtCore.QPointF(element.c2x, element.c2y))
                                        
                                        painter.drawEllipse(cp1, self._pointSize, self._pointSize)
                                        
                                        painter.drawEllipse(cp2, self._pointSize, self._pointSize)
                                        
                                        painter.drawEllipse(pt,  self._pointSize, self._pointSize)
                                        
                                        painter.drawLine(self.mapFromScene(self._cachedPath_[k-1].point()), cp1)
                                        
                                        painter.drawLine(cp1, cp2)
                                        painter.drawLine(cp2, pt)
                                        
                                    else:
                                        
                                        pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        
                                        painter.drawEllipse(pt, self._pointSize, self._pointSize)
                                        
                            elif self._objectType & (GraphicsObjectType.rectangle | GraphicsObjectType.ellipse):
                                p0 = self.mapFromScene(QtCore.QPointF(self._cachedPath_[0].x, 
                                                                      self._cachedPath_[0].y))
                                
                                p1 = self.mapFromScene(QtCore.QPointF(self._cachedPath_[1].x,
                                                                      self._cachedPath_[1].y))
                                    
                                painter.drawEllipse(p0, self._pointSize, self._pointSize)
                                painter.drawLine(p0,p1)
                                painter.drawEllipse(p1, self._pointSize, self._pointSize)
                                    
                            else:
                                for k, element in enumerate(self._cachedPath_):
                                    pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                    
                                    painter.drawEllipse(pt, self._pointSize, self._pointSize)
                                    
                                    if k > 0:
                                        painter.drawLine(self.mapFromScene(self._cachedPath_[k-1].point()), 
                                                        self.mapFromScene(element.point()))

            # CAUTION: DO NOT DELETE when commented-out 
            # this paints the boundingRect() and shape() of the thing when
            # debugging
            #### BEGIN DEBUGGING
            #painter.fillRect(self.boundingRect(), self._controlPointBrush)
            #painter.fillPath(self.shape(), self._testBrush)
            #painter.setPen(QtCore.Qt.darkRed)
            #painter.drawPath(self.shape())
            #### END DEBUGGING

            if self._showlabel:
                if len(self._displayStr) > 0 and labelPos is not None:
                    pen = painter.pen()
                    bgMode = painter.backgroundMode()
                    bg = painter.background()
                    
                    if self._opaqueLabel:
                        painter.setBackgroundMode(QtCore.Qt.OpaqueMode)
                        self._textBackgroundBrush.setStyle(QtCore.Qt.SolidPattern)
                        
                    else:
                        self._textBackgroundBrush.setStyle(QtCore.Qt.NoBrush)
                        
                    painter.setPen(textPen)
                        
                    painter.setBackground(self._textBackgroundBrush)
                        
                    painter.drawText(labelPos, self._displayStr)
                    
                    painter.setBackground(bg)
                    painter.setBackgroundMode(bgMode)
                    painter.setPen(pen)
            
        except Exception as exc:
            traceback.print_exc()
            #print("in %s %s" % (self.objectType, self.name))
            
            
    @safeWrapper
    def itemChange(self, change, value):
        """Customizes the cursor movement by mouse or keyboard.
        
        1. For vertical/horizontal cursors: 
            1.1 restricts the movement of the _MAIN_ cursor line (the long line) 
                and label to the perpendicular direction; 
            1.2 allows the movement of the window bar along the direction of the
                _MAIN_ cursor line (basically, the window bar moves unrestricted)
            
        2. For crosshair cursors: 
            2.1 moves the center of the cursor but readjust the geometry of the 
                cursor lines such that they always span the entire image
            2.2 the label movement is restricted horizontally (label is attached
                to the vertical cursor line)
        
         1 & 2 achieved by partially restricting the new position and/or repainting.
         
        3. For non-cursors:
            just pudates the backen'd x and y coordinates (the effects of which
            depend on what the backend is) for the current frame
        """
        # TODO because this changes the backend, we must ensure the backend
        # in turn updates all OTHER frontends it may have !!!
        
        # NOTE: 2017-08-11 13:12:24
        #
        # trap here position changes for cursors (ONLY) so that we can constrain
        # the movement of their components:
        #
        # 1) for vertical cursors, the main line and label are only allowed to
        # move horizontally
        #
        # 2) for horizontal cursors, the main line and label are only allowed to 
        # move vertically;
        #
        # 3) for crosshair cursors, the main lines must be trimmed/grown at the 
        # opposite ends according the thir direction of move (such that the main
        # cursor lines always span the scene rectangle)
        #
        # 4) in addition, the window bars (small whiskers perpendicular to the 
        # main cursor line) are allowed to move in both orthogonal directions
        # i.e. allow vertical movement for the whiskers of a vertical cursor, 
        # and horizontal movement for the whiskers of a horizontal cursor
        
        #print("itemChange value: %s" % self.name, value)
        
        
        #NOTE: 2018-01-23 18:01:36
        # ATTENTION only check for backend when position changed
        # in buildmode there is neither _backend_ nor _graphicsShapedItem
        # if you return early without calling super().itemChange
        # the item wont be added to the scene when value is scene change!
        
        #print("self._deltaPos: ", self._deltaPos)
        
        if change == QtWidgets.QGraphicsItem.ItemPositionChange and self.scene():
            if self._backend_ is None:
                return QtCore.QPoint()
            
            if not self._backend_.hasStateForFrame(self._currentframe_) or\
                    not self.__objectVisible__:
                value = QtCore.QPointF()
                return value
            
            if self.objectType & GraphicsObjectType.allCursorTypes:
                # cursor types
                stateDescriptor = self._backend_.getState(self._backend_.currentFrame)
                
                if stateDescriptor is None or len(stateDescriptor) == 0:
                    return value
                
                # NOTE 2018-01-18 16:57:28
                # ATTENTION This is also called by self.setPos() (inherited)
                self._positionChangeHasBegun = True # flag used in __drawCursor__()
                
                newPos = value
                
                # vertical cursors
                if self._objectType == GraphicsObjectType.vertical_cursor:
                    if not self.pos().isNull():
                        self._deltaPos = (newPos - self.pos())

                    newPos.setY(self.pos().y()) # restrict movement to horizontal axis only
                    
                    if newPos.x() < 0:
                        newPos.setX(0.0)
                        
                    elif newPos.x() > self._backend_.width:
                        newPos.setX(self._backend_.width)

                # horizontal cursors
                elif self._objectType == GraphicsObjectType.horizontal_cursor:
                    if not self.pos().isNull():
                        self._deltaPos = (newPos - self.pos())

                    newPos.setX(self.pos().x()) # restrict movement to vertical axis only

                    if newPos.y() < 0:
                        newPos.setY(0.0)
                        
                    elif newPos.y() > self._backend_.height:
                        newPos.setY(self._backend_.height)

                # crosshair cursors
                elif self._objectType == GraphicsObjectType.crosshair_cursor:
                    if newPos.x() <= 0.0:
                        newPos.setX(0.0)
                        
                    if newPos.x() > self._backend_.width:
                        newPos.setX(self._backend_.width)

                    if newPos.y() <= 0.0:
                        newPos.setY(0.0)
                        
                    if newPos.y() > self._backend_.height:
                        newPos.setY(self._backend_.height)
                        
                    self._deltaPos = (newPos - QtCore.QPointF(self._backend_.x, 
                                                              self._backend_.y))
                    
                else: # point cursors
                    if newPos.x() <= 0.0:
                        newPos.setX(0.0)
                        
                    if newPos.x() > self._backend_.width:
                        newPos.setX(self._backend_.width)

                    if newPos.y() <= 0.0:
                        newPos.setY(0.0)
                        
                    if newPos.y() > self._backend_.height:
                        newPos.setY(self._backend_.height)
                        
                    self._deltaPos = (newPos - QtCore.QPointF(self._backend_.x,
                                                              self._backend_.y))
                    
                # NOTE: 2018-01-18 15:44:28
                # CAUTION value is already in scene coordinates, so no mapping needed
                # here; 
                self._backend_.x = newPos.x()
                self._backend_.y = newPos.y()
                
            elif self._objectType & GraphicsObjectType.allShapeTypes:
                #non-cursor types
                if isinstance(self._backend_, Path): # use the x and y property setters
                    self._backend_.x = value.x()
                    self._backend_.y = value.y()
                    
                else:
                    self._backend_.x = value.x()
                    self._backend_.y = value.y()
                
            self._backend_.updateLinkedObjects()

            #self.__drawObject__()
            
            if self._labelShowsCoordinates:
                self.__setDisplayStr__()
                
                self.__updateLabelRect__()
                
            self.update()
            
            self.signalBackendChanged.emit(self._backend_)
        
            self.signalGraphicsObjectPositionChange.emit(self.mapToScene(value - self._oldPos))
            
            self._oldPos = self.pos()
                
        # NOTE: 2017-08-11 13:19:28
        #
        # selection change is applied to all GraphicsObject types, not just cursors
        #
        elif change == QtWidgets.QGraphicsItem.ItemSelectedChange and self.scene() is not None:
            # NOTE: ZValue refers to the stack ordering of the graphics items in the scene
            # and it has nothing to do with frame visibility.
            if value:
                nItems = len(self.scene().items())
                self.setZValue(nItems+1)
                
            else:
                self.setZValue(0)
                
            self.selectMe.emit(self._ID_, value)
            
        elif change == QtWidgets.QGraphicsItem.ItemScenePositionHasChanged and self.scene() is not None:
            # NOTE: NOT used for now...
            pass

        elif change == QtWidgets.QGraphicsItem.ItemSceneHasChanged: # now self.scene() is the NEW scene
            self.__drawObject__()

        self._oldPos = self.pos()
            
        return super(GraphicsObject, self).itemChange(change, value)

    @safeWrapper
    def mousePressEvent(self, evt):
        """Mouse press event handler.
        
        In build mode, entered when the ROI type has not beed pre-determined at 
        __init__(), keyboard modifiers determine what type of ROI is being created
        when the first point is generated with a mouse press:
        
            SHIFT             => rectangle
            CTRL              => ellipse
            ALT               => path
            CTRL SHIFT        => polygon
            ALT CTRL SHIFT    => point
            anything else     => line   (default)
        
        When ROI type is path, CTRL + ALT modifier creates a subpath.
        
        When ROI type is path and we are in _curveBuild mode, CTRL + ALT modifiers
        create a second control point, to create a cubic Bezier curve.
        
        
        """
        self.setCursor(QtCore.Qt.ClosedHandCursor)
        
        if self._buildMode: # this is ALWAYS False for cursors
            self.setCursor(QtCore.Qt.CrossCursor)
            # NOTE: 2017-08-21 22:21:58
            # to avoid confusions, determine ONCE AND FOR ALL the object type 
            # according to key modifiers, at FIRST PRESS (i.e. when _cachedPath
            # is empty) as follows:
            #
            # SHIFT             => rectangle
            # CTRL              => ellipse
            # ALT               => path
            # CTRL SHIFT        => polygon
            # ALT CTRL SHIFT    => point
            # anything else     => line
            #
            #
            # When ROI type is not determined by the call to __init__(), we build
            # a line ROI by default; keyboard modifiers can change the type of ROI
            # being built.
            #
            
            #print("scenepos: ", evt.scenePos())
            #pressPos = evt.pos()
            
            if self.objectType == GraphicsObjectType.allShapeTypes and \
                len(self._cachedPath_) == 0:
                # before adding first point, cheeck key modifiers and set
                # self._objectType accordingly
                
                # NOTE: 2018-01-23 22:41:05
                # ATTENTION: do not delete commented-out "mods" code -- for debugging
                
                mods = ""
                
                if evt.modifiers() == QtCore.Qt.ShiftModifier: 
                    ###SHIFT => rectangle
                    self._objectType = GraphicsObjectType.rectangle
                    mods = "shift"
                    
                elif evt.modifiers() == QtCore.Qt.ControlModifier: 
                    ###CTRL => ellipse
                    self._objectType = GraphicsObjectType.ellipse
                    mods = "ctrl"
                    
                elif evt.modifiers() ==  QtCore.Qt.AltModifier: 
                    ###ALT => path
                    self._objectType = GraphicsObjectType.path
                    mods = "alt"
                
                elif evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                    ###CTRL+SHIFT => polygon
                    self._objectType = GraphicsObjectType.polygon
                    mods = "ctrl+shift"
                    
                elif evt.modifiers() == (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                    ###ALt+CTRL+SHIFT => point
                    mods = "alt+=ctrl+shift"
                    self._objectType = GraphicsObjectType.point
                    
                else: 
                    if evt.modifiers() == QtCore.Qt.NoModifier:
                        mods = "none"
                        
                    ###anything else, or no modifiers => line
                    self._objectType = GraphicsObjectType.line
            
                #print("press at: ", evt.pos(), " mods: ", mods)
                
            if len(self._cachedPath_) == 0:
                # add first point
                self._cachedPath_.append(Move(evt.pos().x(), evt.pos().y()))
                
                if self.objectType & GraphicsObjectType.point:
                    # stop here if building just a point
                    self.__finalizeShape__()
                    
                #return
                
            else:
                #print("last press: ", evt.pos(), " hover point: ", self._hover_point)
                
                # there are previous points in the _cachedPath
                # check if evt.pos() is "over" the last point in the _cachedPath
                #d = QtCore.QLineF(evt.pos(), self._cachedPath_[-1].point()).length()
                d = QtCore.QLineF(self._hover_point, self._cachedPath_[-1].point()).length()
                
                # NOTE: self._constrainedPoint is set by mouse hover event handler
                # we set it to None after using it, here
                if d > 2 * self._pointSize: # press event fired far away from last point
                    if self.objectType & (GraphicsObjectType.line | GraphicsObjectType.rectangle | GraphicsObjectType.ellipse):
                        # does nothing is self._cachedPath_ already has more than one point
                        if len(self._cachedPath_) == 1:
                            # there is only one point prior to this one
                            
                            if self._constrainedPoint is not None and not self._constrainedPoint.isNull():
                                # append a constrained point is any
                                self._cachedPath_.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                self._constrainedPoint = None
                                
                            else:
                                # else append this point
                                if self._hover_point is not None and not self._hover_point.isNull():
                                    
                                    self._cachedPath_.append(Line(self._hover_point.x(), self._hover_point.y()))
                                    
                                else:
                                    self._cachedPath_.append(Line(evt.pos().x(), evt.pos().y()))
                                
                            #print("to finalize: ", self._cachedPath_)
                            
                            self.__finalizeShape__()
                            
                            #return
                        
                    elif self.objectType & GraphicsObjectType.polygon:
                        if self._constrainedPoint is not None:
                                self._cachedPath_.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                self._constrainedPoint = None
                                
                        else:
                            self._cachedPath_.append(Line(evt.pos().x(), evt.pos().y()))
                            
                        #self.update()
                        
                        #return
                    
                    elif self.objectType & GraphicsObjectType.path:
                        if self._curveBuild:
                            # self._curveBuild is set in mouse move event handler
                            if evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
                                self._control_points[1] = evt.pos()

                            else:
                                if self._control_points[0] is not None:
                                    if self._control_points[1] is not None:
                                        self._cachedPath_.append(Cubic(evt.pos().x(),
                                                                      evt.pos().y(),
                                                                      self._control_points[0].x(),
                                                                      self._control_points[0].y(),
                                                                      self._control_points[1].x(),
                                                                      self._control_points[1].y()))
                                        
                                        self._control_points[1] = None # cp has been used
                                        
                                    else:
                                        self._cachedPath_.append(Quad(evt.pos().x(),
                                                                     evt.pos().y(),
                                                                     self._control_points[0].x(),
                                                                     self._control_points[0].y()))
                                        
                                    self._control_points[0] = None # cp has been used
                                    
                                    self._curveBuild = False
                                    
                        else:
                            if evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier): # allow the creation of a subpath
                                self._cachedPath_.append(Move(evt.pos().x(), evt.pos().y()))
                                
                            else:
                                if self._constrainedPoint is not None:
                                    self._cachedPath_.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                    self._constrainedPoint = None
                                else:
                                    self._cachedPath_.append(Line(evt.pos().x(), evt.pos().y()))

                else: # select the last point, possibly move it, if followed by mouse move
                    self._movePoint = True
            
            self.update() # force repaint, do not propagate event to superclass
            
            self.selectMe.emit(self._ID_, True)

        if self.editMode: # this is ALWAYS False for cursors
            # select a control point according to mouse event position
            # see qt5 examples/widgets/painting/pathstroke/pathstroke.cpp
            distance = -1
            
            if self._cachedPath_ is None or len(self._cachedPath_) == 0:
                self._cachedPath_ = self._backend_.asPath(self._currentframe_) 
                self._cachedPath_.frameIndices = [] # force current state into a common state

            for k, p in enumerate(self._cachedPath_):
                if isinstance(p, Quad):
                    d = QtCore.QLineF(evt.pos(), self.mapFromScene(p.point())).length() # d = length of line between event pos and point pos
                    dc1 = QtCore.QLineF(evt.pos(), self.mapFromScene(QtCore.QPointF(p.cx, p.cy))).length()

                    self._c_shape_point = -1
                    
                    if dc1 < d:
                        if (distance <= 0 and dc1 <= 2 * self._pointSize) or dc1 < distance:
                            distance = dc1
                            self._c_activePoint = k
                            self._c_activeControlPoint = 0

                    else:
                        if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                            distance = d
                            self._c_activePoint = k
                            self._c_activeControlPoint = -1

                elif isinstance(p, Cubic):
                    d = QtCore.QLineF(evt.pos(), self.mapFromScene(p.point())).length() # d = length of line between event pos and point pos
                    dc1 = QtCore.QLineF(evt.pos(), self.mapFromScene(QtCore.QPointF(p.c1x, p.c1y))).length()
                    dc2 = QtCore.QLineF(evt.pos(), self.mapFromScene(QtCore.QPointF(p.c2x, p.c2y))).length()
                    #print("Cubic")
                    
                    self._c_shape_point = -1
                    
                    if dc1 < min(d, dc2):
                        if (distance <= 0 and dc1 <= 2 * self._pointSize) or dc1 < distance:
                            distance = dc1
                            self._c_activePoint = k
                            self._c_activeControlPoint = 0
                            
                    elif dc2 < min(d, dc1):
                        if (distance <= 0 and dc2 <= 2 * self._pointSize) or dc2 < distance:
                            distance = dc2
                            self._c_activePoint = k
                            self._c_activeControlPoint = 1
                            
                    elif d < min(dc1, dc2):
                        if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                            distance = d
                            self._c_activePoint = k
                            self._c_activeControlPoint = -1
                            
                    else:
                        if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                            distance = d
                            self._c_activePoint = k
                            self._c_activeControlPoint = -1

                else:
                    #print("Move or Line")
                    self._c_shape_point = -1
                    
                    d = QtCore.QLineF(evt.pos(), self.mapFromScene(p.point())).length() # d = length of line between event pos and point pos
                    if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                        distance = d
                        self._c_activePoint = k
                        self._c_activeControlPoint = -1
                        
            
            self.selectMe.emit(self._ID_, True)

            return

        super(GraphicsObject, self).mousePressEvent(evt)
        
        evt.accept()

    @safeWrapper
    def mouseMoveEvent(self, evt):
        """Mouse move event handler.
        
        In buildMode the type of ROI must have already been determined by the time
        this event is issued, either at __init__ or at the time of first mouse press event.
        
        Keyboard modifiers have the following effects (NOTE: they must be present
        throughout the sequence of mouse move events):
        
        CTRL:  => move in multiples of 45 degrees angles (snapping)
        
        SHIFT: => move on diagonal (e.g., for rectangles & ellipse, force them 
                  to be square and circle, respectively)
                  
        ALT:   => for path ROIs only, initiates the creation of a curved segment
                    (quadratic curve)

        """
        #print("mouse MOVE event position x: %g, y: %g"   % (evt.pos().x(), evt.pos().y()))
        #print("mouse MOVE event scene position x: %g, y: %g"   % (evt.scenePos().x(), evt.scenePos().y()))
        #print("mouse MOVE event from scene position x: %g, y: %g"   % (self.mapFromScene(evt.pos()).x(), self.mapFromScene(evt.pos()).y()))
        #print("mouse MOVE event to scene position x: %g, y: %g"   % (self.mapToScene(evt.pos()).x(), self.mapToScene(evt.pos()).y()))
        #print("MOVE")
        
        #print(self._backend_.x)
        
        
        if self._buildMode: 
            #mods = "none" 
            # build mode exists only for non-cursors
            # if objectType is a path then generate a curve (mouse is pressed) otherwise behave as for hoverMoveEvent
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
            currentPoint = evt.pos()
            
            if evt.modifiers() == QtCore.Qt.ControlModifier:
                mods = "ctrl"
                
                if len(self._cachedPath_) > 0:
                    lastPoint = self._cachedPath_[-1].point()
                    currentPoint = __constrain_0_45_90__(lastPoint, evt.pos())
                    
            elif evt.modifiers() == QtCore.Qt.ShiftModifier:
                mods = "shift"
                
                if len(self._cachedPath_) > 0:
                    lastPoint = self._cachedPath_[-1].point()
                    currentPoint = __constrain_square__(lastPoint, evt.pos())
                    
            elif evt.modifiers() == QtCore.Qt.AltModifier and self.objectType == GraphicsObjectType.path:
                mods ="alt"
                
                self._curveBuild = True # stays True until next mouse release or mouse press
                    
            #print("move at: ", evt.pos())
            #print("mods: ", mods)
            
            if self._movePoint:
                if len(self._cachedPath_) > 0:
                    if isinstance(self._cachedPath_[-1], Move):
                        self._cachedPath_[-1] = Move(evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self._cachedPath_[-1], Line):
                        self._cachedPath_[-1] = Line(evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self._cachedPath_[-1], Quad):
                        q = self._cachedPath_[-1]
                        self._cachedPath_[-1] = Quad(q.x1, q.y1, 
                                                       evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self._cachedPath_[-1], Cubic): # because the path may have been "normalized"
                        c = self._cachedPath_[-1]
                        self._cachedPath_[-1] = Quad(c.x, c.y, c.x1, c.y1, 
                                                       evt.pos().x(), evt.pos().y())
                    
                
            else:
                self._hover_point = currentPoint
                self._control_points[0] = None # avoid confusion in paint()
                
            self.update()
            
            self.selectMe.emit(self._ID_, True)

            
            return

        else: #  NOT in build mode
            #if not self.hasStateDescriptor:
                #return
        
            self.setCursor(QtCore.Qt.ClosedHandCursor) # this is the windowing system mouse pointer !!!

            # NOTE: 2018-09-26 14:47:05
            # by design, editMode can only be True for non-cursors
            if self.editMode and self._cachedPath_ is not None and len(self._cachedPath_) \
                and self._c_activePoint >= 0 and self._c_activePoint < len(self._cachedPath_):
                #self.prepareGeometryChange()
                element = self._cachedPath_[self._c_activePoint]
                
                epos = self.mapToScene(evt.pos())
                
                if isinstance(element, Move):
                    self._cachedPath_[self._c_activePoint] = Move(epos.x(), epos.y())
                    
                elif isinstance(element, Line):
                    self._cachedPath_[self._c_activePoint] = Line(epos.x(), epos.y())
                    
                elif isinstance(element, Quad):
                    if self._c_activeControlPoint == 0:
                        self._cachedPath_[self._c_activePoint] = Quad(cx=epos.x(), cy=epos.y(),
                                                                        x=element.x, y=element.y,)
                        
                    else:
                        self._cachedPath_[self._c_activePoint] = Quad(cx=element.cx, cy=element.cy,
                                                                        x=epos.x(), y=epos.y())
                    
                elif isinstance(element, Cubic):
                    if self._c_activeControlPoint == 0:
                        self._cachedPath_[self._c_activePoint] = Cubic(c1x=epos.x(), c1y=epos.y(),
                                                                         c2x=element.c2x, c2y=element.c2y,
                                                                         x=element.x, y=element.y,)
                        
                    elif self._c_activeControlPoint == 1:
                        self._cachedPath_[self._c_activePoint] = Cubic(c1x=element.c1x, c1y=element.c1y,
                                                                         c2x=epos.x(), c2y=epos.y(),
                                                                         x=element.x, y=element.y)
                        
                    else:
                        self._cachedPath_[self._c_activePoint] = Cubic(c1x=element.c1x, c1y=element.c1y,
                                                                         c2x=element.c2x, c2y=element.c2y,
                                                                         x=epos.x(), y=epos.y())
                        
                if self._backend_ is not None:
                    self.__updateBackendFromCachedPath__()
                    self.signalBackendChanged.emit(self._backend_)
            
                self.update() # calls paint() -- force repainting, do or propgate event to the superclass
                
                # NOTE: 2017-08-11 16:43:12
                # do NOT EVER call this here !!!
                # leave commented-out code as a reminder
                # ### super(GraphicsObject, self).mouseMoveEvent(evt)
                # ###
                #return

            elif self.canMove: # this will also change the position of the control points!
                # NOTE: itemChange changes the backend directly!, then
                # we call update
                if self._backend_ is not None:
                    #self.__updateBackendFromCachedPath__() # just DON'T
                    self.signalBackendChanged.emit(self._backend_)
                    
                    for f in self._backend_.frontends:
                        if f != self:
                            f.redraw()
            
                self.signalPosition[int, str, "QPointF"].emit(self.objectType.value, self._ID_, self.pos())
                #self.__updateCachedPathFromBackend__()
                # NOTE 2017-08-12 13:22:26
                # this IS NEEDED for cursor movement by mouse !!!!
                # backend updating for cursors is dealt with in itemChange
                super(GraphicsObject, self).mouseMoveEvent(evt)

            
            self.selectMe.emit(self._ID_, True)

    @safeWrapper
    def mouseReleaseEvent(self, evt):
        """Mouse release event handler
        """
        #if not self.hasStateDescriptor:
            #return
            
        #print(self._backend_.x)
        self._c_activePoint = -1 # restore this anyway!
        
        self.unsetCursor()
        
        if self._buildMode: # this is ALWAYS False for cursors
            # do something here ONLY if release is at some distance from most recent mouse press
            # NOTE: 2018-01-23 22:39:55
            # ATTENTION do not delete  -- for debugging
            mods = "" 
            if evt.modifiers() == QtCore.Qt.ShiftModifier:
                mods = "shift"
                
            elif evt.modifiers() == QtCore.Qt.ControlModifier: 
                mods = "ctrl"
                
            elif evt.modifiers() == QtCore.Qt.AltModifier: 
                mods ="alt"
                
            elif evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                mods = "ctrl+shift"
                
            elif evt.modifiers() == (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                mods = "alt+ctrl+shift"
                
            elif evt.modifiers() == QtCore.Qt.NoModifier:
                mods = "none"
                
            #print("release at: ", evt.pos(), " mods: ", mods)
            #print("obj type: ", self._objectType)
            
            if self._curveBuild:
                if self._control_points[1] is None: # we allow mod of 1st cp when there is no 2nd cp
                    self._control_points[0] = evt.pos()
                    
            self._hover_point = evt.pos()
            
            #super(GraphicsObject, self).mouseReleaseEvent(evt)
            self.update()
            return
            
        if self.canMove:
            # together with itemChange, this implements special treatment
            # of the object shape in the case of cursors (see notes in itemChange code)
            if self.objectType & GraphicsObjectType.allCursorTypes:
                stateDescriptor = self._backend_.getState(self._currentframe_)
                
                if stateDescriptor is None or len(stateDescriptor) == 0:
                    return
                
                self._positionChangeHasBegun=False
                self._wbarPos += self._deltaPos
                    
                if self._wbarPos.x()< 0:
                    self._wbarPos.setX(0.0)
                    
                elif self._wbarPos.x() >= stateDescriptor.width:
                    self._wbarPos.setX(stateDescriptor.width-1)
                            
                if self._wbarPos.y()< 0:
                    self._wbarPos.setY(0.0)
                    
                elif self._wbarPos.y() >= stateDescriptor.height:
                    self._wbarPos.setY(stateDescriptor.height-1)
                
            self._oldPos = self.pos()
            self._deltaPos = QtCore.QPointF(0.0, 0.0)
            
        # NOTE: 2017-06-29 08:40:08# don't do this -- it disturbs the crosshair lines
        #self._deltaPos.setX(0)
        #self._deltaPos.setY(0)
        
            
        self.selectMe.emit(self._ID_, True)

        super(GraphicsObject, self).mouseReleaseEvent(evt)
        
        evt.accept()

    #@safeWrapper
    #"def" mouseDoubleClickEvent(self, evt):
        #"""Mouse double-click event handler - do I need this ???
        #"""
        ## TODO: bring up cursor properties dialog
        ## NOTE: if in buildMode, end ROI construction 
        #if self._buildMode:
            #self.__finalizeShape__()
            
        #self.selectMe.emit(self._ID_, True)

        #super(GraphicsObject, self).mouseDoubleClickEvent(evt)

    @safeWrapper
    def contextMenuEvent(self, evt):
        """
        #TODO: popup context menu => Edit, Link/Unlink, Remove
        """
        self.selectMe.emit(self._ID_, True)

        self.requestContextMenu.emit(self.ID, evt.screenPos())
        
        super(GraphicsObject, self).contextMenuEvent(evt)
        
        evt.accept()# so that this doesn't propagate to the underlying graphics items
        
    @safeWrapper
    def hoverEnterEvent(self, evt):
        if self._buildMode:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
        if self.editMode:
            d = [QtCore.QLineF(evt.pos(), self.mapFromScene(p)).length() for p in self._cachedPath_.qPoints()]
            #print(d)
            if min(d) <= 2 * self._pointSize:
                self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
                
            else:
                self.unsetCursor()

        self.update()
        
        super(GraphicsObject, self).hoverEnterEvent(evt)
        
    @safeWrapper
    def hoverMoveEvent(self, evt):
        """Hover move event handler.
        
        In buildMode the type of ROI must have already been determined by the time
        this event is issued, either at __init__ or at the time of first mouse press event.
        
        Keyboard modifiers here serve to constrain any moves (NOTE: they must be
        present throughout the sequence of hover move events):
        
        CTRL:  => move in multiples of 45 degrees angles (snapping)
        
        SHIFT: => move on diagonal (e.g., for rectangles & ellipse, force them 
                  to be square and circle, respectively)
                  
        """
        #print("HOVER MOVE position x %g, y %g" % (evt.pos().x(), evt.pos().y()))
        #print("HOVER")
        
        if self._buildMode:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
            currentPoint = evt.pos()
            
            #NOTE 2018-01-23 22:39:28
            # ATTENTION do not delete -- for debugging
            #mods = "" 
            #if evt.modifiers() == QtCore.Qt.ShiftModifier:
                #mods = "shift"
                
            #elif evt.modifiers() == QtCore.Qt.ControlModifier: 
                #mods = "ctrl"
                
            #elif evt.modifiers() == QtCore.Qt.AltModifier: 
                #mods ="alt"
                
            #elif evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                #mods = "ctrl+shift"
                
            #elif evt.modifiers() == (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                #mods = "alt+ctrl+shift"
                
            #elif evt.modifiers() == QtCore.Qt.NoModifier:
                #mods = "none"
                
            #if len(self._cachedPath_):
                #print("hovermove at :", evt.pos(), " mods ", mods)
            
            if evt.modifiers() == QtCore.Qt.ControlModifier:
                if len(self._cachedPath_) > 0:
                    lastPoint = self._cachedPath_[-1].point()
                    d = QtCore.QLineF(currentPoint, lastPoint).length()
                    
                    if d > 2 * self._pointSize:
                        currentPoint = __constrain_0_45_90__(lastPoint, evt.pos())
                        self._constrainedPoint = currentPoint
                    
            elif evt.modifiers() == QtCore.Qt.ShiftModifier:
                if len(self._cachedPath_) > 0:
                    lastPoint = self._cachedPath_[-1].point()
                    d = QtCore.QLineF(currentPoint, lastPoint).length()
                    
                    if d > 2 * self._pointSize:
                        currentPoint = __constrain_square__(lastPoint, evt.pos())
                        self._constrainedPoint = currentPoint
                    
            self._hover_point = currentPoint

            self.update()
            
            # NOTE do not call super().hoverMoveEvent here
            
            return
            
        if self.editMode and self._cachedPath_ is not None and len(self._cachedPath_):
            d = [QtCore.QLineF(evt.pos(), self.mapFromScene(p)).length() for p in self._cachedPath_.qPoints()]
            
            if min(d) <= 2 * self._pointSize:
                self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
                
            else:
                self.unsetCursor()

        self.update()
        
        super(GraphicsObject, self).hoverMoveEvent(evt)
        
    @safeWrapper
    def hoverLeaveEvent(self, evt):
        self.unsetCursor()
        self.update()
        #print("hover leave position x %g, y %g" % (evt.pos().x(), evt.pos().y()))
        super(GraphicsObject, self).hoverLeaveEvent(evt)
            
    @safeWrapper
    def keyPressEvent(self, evt):
        # NOTE: 2017-06-29 08:44:34
        # "up" means move down (coordinates origin are top-left !!!)
        #if not self.hasStateDescriptor:
            #return
        
        if evt.key() == QtCore.Qt.Key_Delete:
            self.signalROIConstructed.emit(0, self.name) # deregisters self with parent and removes it
            
        if self._buildMode:
            # exit build mode here
            if evt.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self.__finalizeShape__()

            elif evt.key() == QtCore.Qt.Key_Escape:
                self._buildMode = False
                #self._graphicsShapedItem = None
                self._constrainedPoint = None
                self._curveSegmentConstruction = False
                self._hover_point = None
                self._cachedPath_.clear()
                self.update()
                self.signalROIConstructed.emit(0, self.name) # in order to deregister self with the caller
                
            return
        
        if self.editMode:
            # exit edit mode here
            if evt.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Escape):
                self.editMode = False
                self._cachedPath_.clear()
        
        if not self.canMove:
            return
        
        if self.objectType & GraphicsObjectType.allCursorTypes:
            if not self.hasStateDescriptor:
                return
            stateDescriptor = self._backend_.getState(self._currentframe_)
            #if stateDescriptor is None or len(stateDescriptor) == 0:
                #return
            
            if self._objectType == GraphicsObjectType.vertical_cursor:
                if evt.key() == QtCore.Qt.Key_Right:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(10.0,0.0)
                        
                    else:
                        self.moveBy(1.0,0.0)
                        
                elif evt.key() == QtCore.Qt.Key_Left:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(-10.0, 0.0)
                        
                    else:
                        self.moveBy(-1.0, 0.0)
                        
                elif evt.key() == QtCore.Qt.Key_Up:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self._wbarPos += QtCore.QPointF(0.0,-10.0)
                        
                    else:
                        self._wbarPos += QtCore.QPointF(0.0,-1.0)
                        
                    if self._wbarPos.y()< 0:
                        self._wbarPos.setY(0.0)
                        
                    elif self._wbarPos.y() > stateDescriptor.height-1:
                        self._wbarPos.setY(stateDescriptor.height-1)
                        
                    self.__drawObject__()

                elif evt.key() == QtCore.Qt.Key_Down:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self._wbarPos += QtCore.QPointF(0.0,10.0)
                        
                    else:
                        self._wbarPos += QtCore.QPointF(0.0,1.0)
                        
                    if self._wbarPos.y()< 0:
                        self._wbarPos.setY(0.0)
                        
                    elif self._wbarPos.y() > stateDescriptor.height-1:
                        self._wbarPos.setY(stateDescriptor.height-1)
                        
                    self.__drawObject__()
                
            elif self._objectType == GraphicsObjectType.horizontal_cursor:
                if evt.key() == QtCore.Qt.Key_Right:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self._wbarPos += QtCore.QPointF(10.0, 0.0)
                        
                    else:
                        self._wbarPos += QtCore.QPointF(1.0, 0.0)
                        
                    if self._wbarPos.x()< 0:
                        self._wbarPos.setX(0.0)
                        
                    elif self._wbarPos.x() > stateDescriptor.width-1:
                        self._wbarPos.setX(stateDescriptor.width-1)
                        
                    self.__drawObject__()
                    
                elif evt.key() == QtCore.Qt.Key_Left:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self._wbarPos += QtCore.QPointF(-10.0, 0.0)
                        
                    else:
                        self._wbarPos += QtCore.QPointF(-1.0, 0.0)
                        
                    if self._wbarPos.x()< 0:
                        self._wbarPos.setX(0.0)
                        
                    elif self._wbarPos.x() > stateDescriptor.width-1:
                        self._wbarPos.setX(stateDescriptor.width-1)
                        
                    self.__drawObject__()
                    
                elif evt.key() == QtCore.Qt.Key_Up:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(0.0,-10.0)
                        
                    else:
                        self.moveBy(0.0,-1.0)
                        
                elif evt.key() == QtCore.Qt.Key_Down:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(0.0,10.0)
                        
                    else:
                        self.moveBy(0.0,1.0)
                        
            elif self._objectType == GraphicsObjectType.crosshair_cursor:
                if evt.key() == QtCore.Qt.Key_Right:
                    moveX = 1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveX = 10.0
                    
                    newX = self.pos().x() + moveX
                    
                    if newX > self._backend_.width-1:
                        moveX = self._backend_.width-1 - self.pos().x()
                    
                    self.moveBy(moveX, 0.0)
                        
                elif evt.key() == QtCore.Qt.Key_Left:
                    moveX = -1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveX = -10.0
                        
                    newX = self.pos().x() + moveX
                    
                    if newX < 0 :
                        moveX = 0 - self.pos().x()
                    
                    self.moveBy(moveX, 0.0)
                    
                elif evt.key() == QtCore.Qt.Key_Up:
                    moveY = -1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveY = -10.0
                        
                    newY = self.pos().y() + moveY
                    
                    if newY < 0:
                        moveY = 0 - self.pos().y()
                        
                    self.moveBy(0.0, moveY)

                elif evt.key() == QtCore.Qt.Key_Down:
                    moveY = 1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveY = 10.0
                        
                    newY = self.pos().y() + moveY
                    
                    if newY > self._backend_.height-1:
                        moveY = self._backend_.height-1 - self.pos().y
                        
                    self.moveBy(0.0, moveY)
                        
                if self.pos().x() < 0:
                    y = self.pos().y()
                    self.setPos(0, y)
                    
                elif self.pos().x() > self._backend_.width-1:
                    y = self.pos().y()
                    self.setPos(self._backend_.width-1, y)
                    
                if self.pos().y() < 0:
                    x = self.pos().x()
                    self.setPos(x, 0)
                    
                elif self.pos().y() > self._backend_.height-1:
                    x = self.pos().x()
                    self.setPos(x, self._backend_.height-1)
                    
            else:
                if evt.key() == QtCore.Qt.Key_Right:
                    moveX = 1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveX = 10.0
                    
                    self.moveBy(moveX, 0.0)
                                        
                elif evt.key() == QtCore.Qt.Key_Left:
                    moveX = -1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveX = -10.0
                        
                    self.moveBy(moveX, 0.0)
                        
                elif evt.key() == QtCore.Qt.Key_Up:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(0.0,-10.0)
                        
                    else:
                        self.moveBy(0.0,-1.0)
                        
                elif evt.key() == QtCore.Qt.Key_Down:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(0.0,10.0)
                        
                    else:
                        self.moveBy(0.0,1.0)
                        
                if self.pos().x() < 0:
                    y = self.pos().y()
                    self.setPos(0, y)
                    
                elif self.pos().x() > self._backend_.width-1:
                    y = self.pos().y()
                    self.setPos(self._backend_.width-1, y)
                    
                if self.pos().y() < 0:
                    x = self.pos().x()
                    self.setPos(x, 0)
                    
                elif self.pos().y() > self._backend_.height-1:
                    x = self.pos().x()
                    self.setPos(x, self._backend_.height-1)
                    
        else:
            # non-cursor types
            if evt.key() == QtCore.Qt.Key_Right:
                if evt.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveBy(10.0,0.0)
                    
                else:
                    self.moveBy(1.0,0.0)
                    
            elif evt.key() == QtCore.Qt.Key_Left:
                if evt.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveBy(-10.0,0.0)
                    
                else:
                    self.moveBy(-1.0, 0.0)
                    
            elif evt.key() == QtCore.Qt.Key_Up:
                if evt.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveBy(0.0, -10.0)
                    
                else:
                    self.moveBy(0.0,-1.0)

            elif evt.key() == QtCore.Qt.Key_Down:
                if evt.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveBy(0.0,10.0)
                    
                else:
                    self.moveBy(0.0,1.0)
                    
        self.__drawObject__()
        self.update()

        super(GraphicsObject, self).keyPressEvent(evt)
        
    def setDefaultAppearance(self):
        self._textPen                = self.defaultTextPen
        self._textBrush              = self.defaultTextBrush
        self._textBackgroundBrush    = self.defaultTextBackgroundBrush
        
        self._textFont           = self.defaultTextFont
        
        self._linkedTextPen      = self.defaultLinkedTextPen
        self._linkedTextBrush    = self.defaultLinkedTextBrush
        
        self._cursorPen          = self.defaultPen
        self._selectedCursorPen  = self.defaultSelectedPen
        
        self._linkedPen          = self.defaultLinkedPen
        self._linkedSelectedPen  = self.defaultLinkedSelectedPen
        
        self._cBPen              = self.defaultCBPen
        self._cBSelectedPen      = self.defaultCBSelectedPen
        
        self._opaqueLabel = True
        
        self._labelShowsCoordinates = False
        
        self.__drawObject__()
        
        self.update()
        
    def sharesBackendWith(self, other):
        return other in self._backend_.frontends and self._backend_ == other.backend
    
    @property
    def hasTransparentLabel(self):
        return not self._opaqueLabel
    
    def setTransparentLabel(self, value):
        self._opaqueLabel = not value
        
        self.redraw()
        #self.update()
        
    @property
    def sharesBackend(self):
        return len(self._backend_.frontends) > 0
        
    #@property
    #"def" linked(self):
        #"""Returns a dict of GraphicsObject instances to which this object is linked with
        #"""
        #return self._linkedGraphicsObjects
        
                
    @pyqtSlot(int)
    @safeWrapper
    def slotFrameChanged(self, val):
        #print("slotFrameChanged")
        self._currentframe_ = val
        if self._backend_ is not None:
            self._backend_.currentFrame = val
            
            self._backend_.updateLinkedObjects()
            
            self.setVisible(len(self._backend_.frameIndices) > 0 or self._backend_.hasStateForFrame(val))
            
            if self.__objectVisible__:
                self.redraw()
            
            if len(self._linkedGraphicsObjects):
                for c in self._linkedGraphicsObjects.values():
                    if c != self:
                        c._currentframe_ = val
                        c.setVisible(len(c._backend_.frameIndices) > 0 or c._backend_.hasStateForFrame(val))
                        if c.__objectVisible__:
                            c.redraw()

    @pyqtSlot("QPointF")
    @safeWrapper
    def slotLinkedGraphicsObjectPositionChange(self, deltapos):
        """Catched signals emitted by linked graphics objects
        """
        other = self.sender()
        if self._currentframe_ == other._currentframe_:
            if self.hasStateDescriptor and other.hasStateDescriptor:
                
                self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, False)
                self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges, False)
                
                self.setPos(self.pos() + self.mapFromScene(deltapos))
                                    
                if self._labelShowsCoordinates:
                    self.__setDisplayStr__()
                    self.__updateLabelRect__()
                    
                self.update()
                    
                self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
                self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges, True)
        
    @property
    def visible(self):
        ret =  self.__objectVisible__ and super(GraphicsObject, self).isVisible()
            
        return ret
        
    @visible.setter
    def visible(self, value):
        if not isinstance(value, bool):
            raise TypeError("Expecting a bool value; got %s instead" % type(value).__name__)
        
        self.__objectVisible__ = value
        super(GraphicsObject, self).setVisible(value)
            
        self.update()
            
    def isVisible(self):
        ret =  self.__objectVisible__ and super(GraphicsObject, self).isVisible()
            
        return ret
        
    def setVisible(self, value):
        #print("%s setVisible %s in frame %d" % (self.ID, value, self._currentframe_))
        self.__objectVisible__ = value
        super(GraphicsObject, self).setVisible(value)
            
        self.update()
            
    @safeWrapper
    def __updateBackendFromCachedPath__(self):
        """Updates the backend primitive from this object, it being a ROI
        TODO/FIXME for now only supports Ellipse, Rect, and Path backends
        TODO expand for line, etc.
        NOTE: do not use for cursors !
        ATTENTION: does not work when _backend_ is None
        """
        if self._cachedPath_ is None or len(self._cachedPath_) == 0:
            return
        
        if self._backend_ is None:
            self._backend_ = self._cachedPath_.copy()
        
        # this is a reference; modifying stateDescriptor attributes effectively
        # modified self._backend_ state for _currentframe_
        #stateDescriptor = self._backend_.getState(self._currentframe_)
        
        #if len(stateDescriptor):
        
        # NOTE: 2019-03-25 20:44:39
        # TODO code for all non-Cursor types!
        if isinstance(self._backend_, (Ellipse, Rect)) and len(self._cachedPath_) >= 2:
            if self.hasStateDescriptor:
                self._backend_.x = self._cachedPath_[0].x
                
                self._backend_.y = self._cachedPath_[0].y
                
                self._backend_.w = self._cachedPath_[1].x - self._cachedPath_[0].x
                
                self._backend_.h = self._cachedPath_[1].y - self._cachedPath_[0].y
                
                self._backend_.updateLinkedObjects()
                
        elif isinstance(self._backend_, Path):
            try:
                for k, element in enumerate(self._cachedPath_):
                    self._backend_[k].x = element.x
                    self._backend_[k].y = element.y
                    
                self._backend_.updateLinkedObjects()
                    
            except Exception as e:
                traceback.print_exc()
                    
    #@safeWrapper
    def removeFromWidget(self):
        """Call this to have the GraphicsObject remove itself from the GraphicsImageViewerWidget
        """
        if type(self.parentwidget).__name__ == "ImageViewer":
            #print("GraphicsObject.removeFromWidget %s from %s" % (self.name, self.parentwidget.windowTitle()))
            self.parentwidget.removeGraphicsObject(self.name)
            
        elif type(self.parentwidget).__name__ == "GraphicsImageViewerWidget":
            if isinstance(self._backend_, Cursor):
                self.parentwidget.removeCursorByName(self.name)
                
            else:
                self.parentwidget.removeRoiByName(self.name)
        
        
    # NOTE: 2017-06-26 22:38:06 properties
    #
    
    @property
    def parentwidget(self):
        return self._parentWidget
    
    @property
    def showLabel(self):
        return self._showlabel
    
    @showLabel.setter
    def showLabel(self, value):
        self._showlabel=value
        self.update()
    
    @property
    def backend(self):
        """Read-only!
        The backend is set up at __init__ and it may be None.
        """
        return self._backend_
    
    @property
    def cachedPath(self):
        """Read-only
        """
        return self._cachedPath_
    
    # NOTE: 2017-11-22 23:49:35
    # new property: a list of frame indices where this object is visible
    # if list is empty, this implies the object is visible in ALL frames
    # be careful: is the list contains only a frame index that is never reached
    # the object will never become visible
    @property
    def frameVisibility(self):
        return self._backend_.frameIndices
    
    @frameVisibility.setter
    def frameVisibility(self, value):
        """
        value: int, a list of int or a range
        
        Ignored for Path objects (this is determined by inidividual elements of the Path)
        
        see PlanarGraphics.frameIndices property documentation for details
        
        """
        #print("frameVisibility.setter %s" % value)
        if isinstance(value, numbers.Integral):
            value = [value]
            
        elif isinstance(value, range):
            value = [v for v in value]
        
        if not isinstance(value, list):
            return
        
        if not isinstance(self._backend_, Path):
            self._backend_.frameIndices = value
        
        self._backend_.updateLinkedObjects()
        
        self.update()
        
        for f in self._backend_.frontends:
            if f != self:
                f.redraw()
        
        if len(self._linkedGraphicsObjects):
            # NOTE: this is now a list of backends!
            for c in self._linkedGraphicsObjects:
                if c != self._backend_:
                    c.frameIndices = value
                    
                    for f in c.frontends:
                        if f != self:
                            f.redraw()

    @property
    def currentFrame(self):
        return self._currentframe_
        
    @currentFrame.setter
    def currentFrame(self, value):
        #print("currentFrame.setter ", value)
        self._currentframe_ = value
        
    @property
    def currentBackendFrame(self):
        return self._backend_.currentFrame
    
    @currentBackendFrame.setter
    def currentBackendFrame(self, value):
        #print("currentBackendFrame.setter ", value)
        self._backend_.currentFrame=float(value)
        self._backend_.updateLinkedObjects()
        
    @property
    def hasStateDescriptor(self):
        return self._backend_.hasStateForFrame(self._currentframe_)
        
    @property
    def name(self):
        """Alias to self.ID
        """
        return self.ID
    
    @name.setter
    def name(self, val):
        self.ID = val
    
    @property
    def ID(self):
        """Name of this GUI GraphicsObject.
        This is kept in sync with the backend.name property
        """
        return self._ID_
    
    @ID.setter
    def ID(self, value):
        if isinstance(value, str):
            if len(value.strip()):
                if self._ID_ != value: # check to avoid recurrence
                    self._ID_ = value
                    self.signalIDChanged.emit(self._ID_)
                    self.redraw()
                    
            else:
                raise ValueError("value expected to be a non-empty string")
            
        else:
            raise TypeError("value expected to be a non-empty string; got %s instead" % type(value).__name__)
        
    @property
    def linkedToFrame(self):
        """Read-only
        To change, one can only manipulate "framesVisibility" property
        """
        return len(self._frameindex)
    
    #"@linkedToFrame.setter"
    #"def" linkedToFrame(self, val):
        #if val:
            
        #self._linkToFrame = val

    @property
    def labelShowsPosition(self):
        """When True, the coordinates will be displayed next to its name, on the label
        """
        return self._labelShowsCoordinates
    
    @labelShowsPosition.setter
    def labelShowsPosition(self, value):
        self._labelShowsCoordinates = value
        self.redraw()
        #self.__drawObject__()
        #self.update()
        
        for f in self._backend_.frontends:
            if f != self:
                f._labelShowsCoordinates = value
                f.redraw()

    #@property
    #"def" shapedItem(self):
        #"""Returns the underlying QAbstractGraphicsShapeItem or None if this is a cursor.
         #Same as self.graphicsItem()
        #"""
        #return self._graphicsShapedItem

    @property
    def x(self):
        """The x coordinate
        """
        return self.pos().x()
    
    @x.setter
    def x(self, val):
        y = self.pos().y()
        self.setPos(val,y)
        
        for c in self._linkedGraphicsObjects:
            if c != self._backend_:
                c.x = val
                
                for f in c.frontends:
                    if f != self:
                        f.redraw()
                    
    @property
    def horizontalWindow(self):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self._backend_.getState(self._currentframe_)
            
            if stateDescriptor and len(stateDescriptor):
                return stateDescriptor.xwindow
    
    @horizontalWindow.setter
    def horizontalWindow(self, val):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self._backend_.getState(self._currentframe_)
            
            if stateDescriptor is not None and len(stateDescriptor):
                stateDescriptor.xwindow = val
                self._backend_.updateLinkedObjects()
                self.redraw()
            
                for f in self._backend_.frontends:
                    if f != self:
                        f.redraw()
        
                if len(self._linkedGraphicsObjects):
                    for c in self._linkedGraphicsObjects:
                        if c != self._backend_:
                            c.xwindow = val
                            
                            for f in c.frontends:
                                if f != self:
                                    f.redraw()
                                
    @property
    def xwindow(self):
        """Alias for the "horizontalWindow" property
        """
        return self.horizontalWindow
    
    @xwindow.setter
    def xwindow(self, val):
        self.horizontalWindow = val
    
    @property
    def y(self):
        """The y coordinate
        """
        return self.pos().y()
    
    @y.setter
    def y(self, val):
        x = self.pos().x()
        self.setPos(x,val)
        
        if len(self._linkedGraphicsObjects):
            for c in self._linkedGraphicsObjects:
                if c != self._backend_:
                    c.y = val
                    
                    for f in c.frontends:
                        if f != self:
                            f.redraw()
                    
    @property
    def verticalWindow(self):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self._backend_.getState(self._currentframe_)
            if stateDescriptor is not None and len(stateDescriptor):
                return stateDescriptor.ywindow
    
    @verticalWindow.setter
    def verticalWindow(self, val):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self._backend_.getState(self._currentframe_)
            
            if stateDescriptor is not None and len(stateDescriptor):
                stateDescriptor.ywindow = val
                self._backend_.updateLinkedObjects()
                self.redraw()
                
                for f in self._backend_.frontends:
                    if f != self:
                        f.redraw()
        
                if len(self._linkedGraphicsObjects):
                    for c in self._linkedGraphicsObjects:
                        if c != self._backend_:
                            c.ywindow = val
                            
                            for f in c.frontends:
                                if f != self:
                                    f.redraw()
                                
    @property
    def ywindow(self):
        """ Alias for the "verticalWindow" property
        """
        return self.verticalWindow
    
    @ywindow.setter
    def ywindow(self, val):
        self.verticalWindow = val
        
    @property
    def radius(self):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self._backend_.getState(self._currentframe_)
            if stateDescriptor is not None and len(stateDescriptor):
                return stateDescriptor.radius
    
    @radius.setter
    def radius(self, val):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self._backend_.getState(self._currentframe_)
            if stateDescriptor is not None and len(stateDescriptor):
                stateDescriptor.radius = val
                self.redraw()
                self._backend_.updateLinkedObjects()
                self._backend_.updateFrontends()
                
                for f in self._backend_.frontends:
                    if f != self:
                        f.redraw()
                
                if len(self._linkedGraphicsObjects):
                    for c in self._linkedGraphicsObjects:
                        if c != self._backend_:
                            c.radius = val
                            
                            for f in c.frontends:
                                if f != self:
                                    f.redraw()
                            
                        if c.objectType & GraphicsObjectType.allCursorTypes and c != self:
                            if c.currentFrame == self.currentFrame:
                                if c in self._backend_.frontends:
                                    c.redraw()
                                else:
                                    c.radius  = stateDescriptor.radius
                                    
    @property
    def color(self):
        return self.penColor
    
    @color.setter
    def color(self, qcolor):
        """Set both the pen and text color to the same value
        """
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._cursorPen.setColor(qcolor)
            self._selectedCursorPen.setColor(qcolor)
            self._textPen.setColor(qcolor)
            self.update()
    
    @property
    def linkedColor(self):
        return self.penColor
    
    @linkedColor.setter
    def linkedColor(self, qcolor):
        """Set both the pen and text color to the same value
        """
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linkedPen.setColor(qcolor)
            self._linkedTextPen.setColor(qcolor)
            self._linkedSelectedPen.setColor(qcolor)
            self.update()
    
    @property
    def penColor(self):
        return self._cursorPen.color()
    
    @penColor.setter
    def penColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._cursorPen.setColor(qcolor)
            self._selectedCursorPen.setColor(qcolor)
            self.update()
        
    @property
    def colorForSharedBackend(self):
        return self._cBPen.color()
    
    @colorForSharedBackend.setter
    def colorForSharedBackend(self, qcolor):
        #print("GraphicsObject.colorForSharedBackend", qcolor)
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            #print("GraphicsObject.colorForSharedBackend", qcolor.name())
            self._cBPen.setColor(qcolor)
            self._cBSelectedPen.setColor(qcolor)
            self._textCBPen.setColor(qcolor)
            #print("colorForSharedBackend %s" % self.name)
            self.update()
        
    @property
    def linkedPenColor(self):
        return self._linkedPen.color()
    
    @linkedPenColor.setter
    def linkedPenColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linkedPen.setColor(qcolor)
            self._linkedSelectedPen.setColor(qcolor)
            self._linkedTextPen.setColor(qcolor)
            self.update()
        
    @property
    def textColor(self):
        return self._textPen.color()
    
    @textColor.setter
    def textColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._textPen.setColor(qcolor)
            self.update()
        
    @property
    def linkedTextColor(self):
        return self._linkedTextPen.color()
    
    @linkedTextColor.setter
    def linkedTextColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linkedTextPen.setColor(qcolor)
            self.update()
        
    @property
    def textBackground(self):
        return self._textBackgroundBrush
    
    @textBackground.setter
    def textBackground(self, brush):
        self._textBackgroundBrush = brush
        self.__drawObject__
        self.update()
        
    @property
    def opaqueLabel(self):
        return self._opaqueLabel
    
    @opaqueLabel.setter
    def opaqueLabel(self, val):
        self._opaqueLabel = val
        self.__drawObject__
        self.update()
        
    @property
    def labelFont(self):
        return self._textFont
    
    @labelFont.setter
    def labelFont(self, font):
        self._textFont = font
        self.__drawObject__
        self.update()
        
    @property
    def buildMode(self):
        """Read-only
        """
        return self._buildMode
    
    @property
    def editMode(self):
        """When True, the shape of the object (non-cursor types) can be edited.
        Default if False.
        Editing is done via control points (GUI editing).
        
        """
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return False
        
        return self._shapeIsEditable
    
    @editMode.setter
    def editMode(self, value):
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return

        self._shapeIsEditable = value
        
        if self._shapeIsEditable:
            self.__updateCachedPathFromBackend__()
            
        self.update()
        
        
    @property
    def canMove(self):
        """Can this object be moved by mouse or keyboard.
        By default, all graphics object types can be moved.
        For ROI types, setting this to False also sets editMode to False.
        """
        return self._movable
    
    @canMove.setter
    def canMove(self, value):
        self._movable = value
        
        if not self._movable:
            self.editMode = False
        
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, value)
        
    @property
    def canEdit(self):
        return self._editable
    
    @canEdit.setter
    def canEdit(self, value):
        self._editable = value
        
        if not self._editable:
            self.editMode=False
        
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, value)
        
    @property
    def canTransform(self):
        """Can the object be transformed (rotated/scaled/skewed).
        By default, objects cannot be transformes, except for being moved
        around the scene (see "canMove").
        However, non-cursor objects can be rotated/scaled/skewed
        when this property is set to "True"
        """
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return False
        
        return self._transformable
    
    @canTransform.setter
    def canTransform(self, value):
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return
        
        self._transformable = value
        
    @property
    def autoLabel(self):
        return self._autoLabel
    
    @autoLabel.setter
    def autoLabel(self, value):
        if not isinstance(value, bool):
            raise TypeError("Boolean expected; got %s instead" % type(value).__name__)
        
        self._autoLabel = value
        self.__setDisplayStr__()

    # NOTE: 2017-06-26 22:48:53 
    # immutable properties
    # ###
    @property
    def objectType(self):
        return self.backend.type
        #return self._objectType
    
    @property
    def isCursor(self):
        return self.objectType & GraphicsObjectType.allCursorTypes
    
    @property
    def isLineCursor(self):
        return self.objectType & GraphicsObjectType.lineCursorTypes
    
    @property
    def isShapedCursor(self):
        return self.objectType & GraphicsObjectType.shapedCursorTypes
    
    @property
    def isVerticalCursor(self):
        return self.objectType == GraphicsObjectType.vertical_cursor
    
    @property
    def isHorizontalCursor(self):
        return self.objectType == GraphicsObjectType.horizontal_cursor
    
    @property
    def isCrosshairCursor(self):
        return self.objectType == GraphicsObjectType.crosshair_cursor
    
    @property
    def isPointCursor(self):
        return self.objectType == GraphicsObjectType.point_cursor
    
    @property
    def isShapeObject(self):
        """All non-cursor types
        """
        return self.objectType & GraphicsObjectType.allObjectTypes
    
    @property
    def isROI(self):
        return self.objectType & GraphicsObjectType.geometricShapeTypes
    
    @property
    def isPolygonal(self):
        return self.objectType & GraphicsObjectType.polygonTypes
    
    @property
    def isLinear(self):
        return self.objectType & GraphicsObjectType.linearShapeTypes
    
    @property
    def isBasicShape(self):
        return self.objectType & GraphicsObjectType.basicShapeTypes
    
    @property
    def isCommonShape(self):
        return self.objectType & GraphicsObjectType.commonShapeTypes
    
    @property
    def isGeometricShape(self):
        """Alias to self.isROI
        """
        return self.isROI

    @property
    def isPoint(self):
        return self.objectType == GraphicsObjectType.point
    
    @property
    def isPolygon(self):
        return self.objectType == GraphicsObjectType.polygon
    
    @property
    def isRectangle(self):
        return self.objectType == GraphicsObjectType.rectangle
    
    @property
    def isLine(self):
        return self.objectType == GraphicsObjectType.line
    
    @property
    def isEllipse(self):
        return self.objectType == GraphicsObjectType.ellipse
    
    @property
    def isPath(self):
        return self.objectType == GraphicsObjectType.path
    
    @property
    def isText(self):
        return self.objectType == GraphicsObjectType.text
    
def printQPainterPath(p):
    s = []
    for k in range(p.elementCount()):
        element = p.elementAt(k)
        if p.elementAt(k).type == QtGui.QPainterPath.MoveToElement:
            s.append("moveTo(x=%g, y=%g)" % (element.x, element.y))
            
        elif p.elementAt(k).type == QtGui.QPainterPath.LineToElement:
            s.append("lineTo(x=%g, y=%g)" %(element.x, element.y))
            
        elif p.elementAt(k).type == QtGui.QPainterPath.CurveToElement: # this is the FIRST control point!
            c1 = p.elementAt(k+1)                                      # this is the SECOND control point!
            c2 = p.elementAt(k+2)                                      # this is the DESTINATION point !
            s.append("cubicTo(c1x=%g, c1y=%g, c2x=%g, c2y=%g, x=%g, y=%g)" %\
                (element.x, element.y, c1.x, c1.y, c2.x, c2.y, ))
            #s.append("cubicTo(c1x=%g, c1y=%g, c2x=%g, c2y=%g, x=%g, y=%g)" %\
                #(c1.x, c1.y, c2.x, c2.y, element.x, element.y))
            #self.append(Cubic(c1.x, c1.y, c2.x, c2.y, element.x, element.y))
            #self.append(Cubic(element.x, element.y, e1.x, e1.y, e2.x, e2.y))
            
        else: # do not parse curve to data elements
            s.append("controlPoint(x=%g, y=%g)" % (element.x, element.y)) 
    
    #s.append("]")
    
    return "[" + ", ".join(s) + "]"

