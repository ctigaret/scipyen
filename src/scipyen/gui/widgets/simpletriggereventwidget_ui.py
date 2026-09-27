# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'simpletriggereventwidget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QWidget)

from gui.widgets.small_widgets import LineEdit

class Ui_SimpleTriggerEventWidget(object):
    def setupUi(self, SimpleTriggerEventWidget):
        if not SimpleTriggerEventWidget.objectName():
            SimpleTriggerEventWidget.setObjectName(u"SimpleTriggerEventWidget")
        SimpleTriggerEventWidget.resize(254, 29)
        self.gridLayout = QGridLayout(SimpleTriggerEventWidget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.timesLineEdit = LineEdit(SimpleTriggerEventWidget)
        self.timesLineEdit.setObjectName(u"timesLineEdit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.timesLineEdit.sizePolicy().hasHeightForWidth())
        self.timesLineEdit.setSizePolicy(sizePolicy)
        self.timesLineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.timesLineEdit, 0, 0, 1, 1)


        self.retranslateUi(SimpleTriggerEventWidget)

        QMetaObject.connectSlotsByName(SimpleTriggerEventWidget)
    # setupUi

    def retranslateUi(self, SimpleTriggerEventWidget):
        SimpleTriggerEventWidget.setWindowTitle(QCoreApplication.translate("SimpleTriggerEventWidget", u"SimpleTriggerEventWidget", None))
    # retranslateUi

