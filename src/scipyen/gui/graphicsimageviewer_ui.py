# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'graphicsimageviewer.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QGraphicsView, QGridLayout,
    QLabel, QSizePolicy, QVBoxLayout, QWidget)

class Ui_GraphicsImageViewerWidget(object):
    def setupUi(self, GraphicsImageViewerWidget):
        if not GraphicsImageViewerWidget.objectName():
            GraphicsImageViewerWidget.setObjectName(u"GraphicsImageViewerWidget")
        GraphicsImageViewerWidget.resize(492, 531)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(GraphicsImageViewerWidget.sizePolicy().hasHeightForWidth())
        GraphicsImageViewerWidget.setSizePolicy(sizePolicy)
        GraphicsImageViewerWidget.setMinimumSize(QSize(0, 0))
        GraphicsImageViewerWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.gridLayout = QGridLayout(GraphicsImageViewerWidget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self._topLabel = QLabel(GraphicsImageViewerWidget)
        self._topLabel.setObjectName(u"_topLabel")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self._topLabel.sizePolicy().hasHeightForWidth())
        self._topLabel.setSizePolicy(sizePolicy1)
        self._topLabel.setLineWidth(0)
        self._topLabel.setMidLineWidth(0)
        self._topLabel.setScaledContents(True)
        self._topLabel.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self._topLabel.setWordWrap(True)
        self._topLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalLayout.addWidget(self._topLabel)

        self._imageGraphicsView = QGraphicsView(GraphicsImageViewerWidget)
        self._imageGraphicsView.setObjectName(u"_imageGraphicsView")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(1)
        sizePolicy2.setVerticalStretch(1)
        sizePolicy2.setHeightForWidth(self._imageGraphicsView.sizePolicy().hasHeightForWidth())
        self._imageGraphicsView.setSizePolicy(sizePolicy2)
        self._imageGraphicsView.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        brush = QBrush(QColor(128, 128, 128, 255))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        self._imageGraphicsView.setBackgroundBrush(brush)
        self._imageGraphicsView.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self._imageGraphicsView.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._imageGraphicsView.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
        self._imageGraphicsView.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._imageGraphicsView.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._imageGraphicsView.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)

        self.verticalLayout.addWidget(self._imageGraphicsView)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)


        self.retranslateUi(GraphicsImageViewerWidget)

        QMetaObject.connectSlotsByName(GraphicsImageViewerWidget)
    # setupUi

    def retranslateUi(self, GraphicsImageViewerWidget):
        GraphicsImageViewerWidget.setWindowTitle(QCoreApplication.translate("GraphicsImageViewerWidget", u"ImageViewerWidget", None))
#if QT_CONFIG(tooltip)
        self._topLabel.setToolTip(QCoreApplication.translate("GraphicsImageViewerWidget", u"Image size", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self._topLabel.setWhatsThis(QCoreApplication.translate("GraphicsImageViewerWidget", u"Displays image size", None))
#endif // QT_CONFIG(whatsthis)
        self._topLabel.setText("")
    # retranslateUi

