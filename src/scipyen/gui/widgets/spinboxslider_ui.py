# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'spinboxslider.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QSizePolicy,
    QSlider, QSpinBox, QWidget)

class Ui_SpinBoxSlider(object):
    def setupUi(self, SpinBoxSlider):
        if not SpinBoxSlider.objectName():
            SpinBoxSlider.setObjectName(u"SpinBoxSlider")
        SpinBoxSlider.resize(477, 42)
        self.horizontalLayout = QHBoxLayout(SpinBoxSlider)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.descriptionLabel = QLabel(SpinBoxSlider)
        self.descriptionLabel.setObjectName(u"descriptionLabel")

        self.horizontalLayout.addWidget(self.descriptionLabel)

        self.framesQSpinBox = QSpinBox(SpinBoxSlider)
        self.framesQSpinBox.setObjectName(u"framesQSpinBox")

        self.horizontalLayout.addWidget(self.framesQSpinBox)

        self.totalFramesCountLabel = QLabel(SpinBoxSlider)
        self.totalFramesCountLabel.setObjectName(u"totalFramesCountLabel")

        self.horizontalLayout.addWidget(self.totalFramesCountLabel)

        self.framesQSlider = QSlider(SpinBoxSlider)
        self.framesQSlider.setObjectName(u"framesQSlider")
        self.framesQSlider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout.addWidget(self.framesQSlider)

#if QT_CONFIG(shortcut)
        self.descriptionLabel.setBuddy(self.framesQSpinBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(SpinBoxSlider)

        QMetaObject.connectSlotsByName(SpinBoxSlider)
    # setupUi

    def retranslateUi(self, SpinBoxSlider):
        SpinBoxSlider.setWindowTitle(QCoreApplication.translate("SpinBoxSlider", u"Form", None))
        self.descriptionLabel.setText(QCoreApplication.translate("SpinBoxSlider", u"Frame:", None))
        self.totalFramesCountLabel.setText(QCoreApplication.translate("SpinBoxSlider", u"of: 0", None))
    # retranslateUi

