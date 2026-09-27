# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dataexchangewidget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLayout, QSizePolicy, QSpacerItem, QToolButton,
    QVBoxLayout, QWidget)

class Ui_DataExchangeWidget(object):
    def setupUi(self, DataExchangeWidget):
        if not DataExchangeWidget.objectName():
            DataExchangeWidget.setObjectName(u"DataExchangeWidget")
        DataExchangeWidget.resize(281, 76)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(DataExchangeWidget.sizePolicy().hasHeightForWidth())
        DataExchangeWidget.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(DataExchangeWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.objectSymbolLayout = QHBoxLayout()
        self.objectSymbolLayout.setObjectName(u"objectSymbolLayout")
        self.objectSymbolLabel = QLabel(DataExchangeWidget)
        self.objectSymbolLabel.setObjectName(u"objectSymbolLabel")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.objectSymbolLabel.sizePolicy().hasHeightForWidth())
        self.objectSymbolLabel.setSizePolicy(sizePolicy1)

        self.objectSymbolLayout.addWidget(self.objectSymbolLabel)

        self.objectSymbolSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.objectSymbolLayout.addItem(self.objectSymbolSpacer)


        self.verticalLayout.addLayout(self.objectSymbolLayout)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.newObjectToolButton = QToolButton(DataExchangeWidget)
        self.newObjectToolButton.setObjectName(u"newObjectToolButton")
        icon = QIcon(QIcon.fromTheme(u"document-new"))
        self.newObjectToolButton.setIcon(icon)
        self.newObjectToolButton.setAutoRaise(True)

        self.horizontalLayout_3.addWidget(self.newObjectToolButton)

        self.loadToolButton = QToolButton(DataExchangeWidget)
        self.loadToolButton.setObjectName(u"loadToolButton")
        self.loadToolButton.setMinimumSize(QSize(16, 16))
        icon1 = QIcon(QIcon.fromTheme(u"document-open"))
        self.loadToolButton.setIcon(icon1)
        self.loadToolButton.setAutoRaise(True)

        self.horizontalLayout_3.addWidget(self.loadToolButton)

        self.saveToolButton = QToolButton(DataExchangeWidget)
        self.saveToolButton.setObjectName(u"saveToolButton")
        self.saveToolButton.setMinimumSize(QSize(16, 16))
        icon2 = QIcon(QIcon.fromTheme(u"document-save"))
        self.saveToolButton.setIcon(icon2)
        self.saveToolButton.setAutoRaise(True)

        self.horizontalLayout_3.addWidget(self.saveToolButton)

        self.importToolButton = QToolButton(DataExchangeWidget)
        self.importToolButton.setObjectName(u"importToolButton")
        self.importToolButton.setMinimumSize(QSize(16, 16))
        icon3 = QIcon(QIcon.fromTheme(u"document-import"))
        self.importToolButton.setIcon(icon3)
        self.importToolButton.setAutoRaise(True)

        self.horizontalLayout_3.addWidget(self.importToolButton)

        self.exportToolButton = QToolButton(DataExchangeWidget)
        self.exportToolButton.setObjectName(u"exportToolButton")
        self.exportToolButton.setMinimumSize(QSize(16, 16))
        icon4 = QIcon(QIcon.fromTheme(u"document-export"))
        self.exportToolButton.setIcon(icon4)
        self.exportToolButton.setAutoRaise(True)

        self.horizontalLayout_3.addWidget(self.exportToolButton)

        self.copyToolButton = QToolButton(DataExchangeWidget)
        self.copyToolButton.setObjectName(u"copyToolButton")
        icon5 = QIcon(QIcon.fromTheme(u"edit-copy"))
        self.copyToolButton.setIcon(icon5)
        self.copyToolButton.setAutoRaise(True)

        self.horizontalLayout_3.addWidget(self.copyToolButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_2)


        self.verticalLayout.addLayout(self.horizontalLayout_3)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)


        self.retranslateUi(DataExchangeWidget)

        QMetaObject.connectSlotsByName(DataExchangeWidget)
    # setupUi

    def retranslateUi(self, DataExchangeWidget):
        DataExchangeWidget.setWindowTitle(QCoreApplication.translate("DataExchangeWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.objectSymbolLabel.setToolTip(QCoreApplication.translate("DataExchangeWidget", u"Namespace symbol bound to this object", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.objectSymbolLabel.setStatusTip(QCoreApplication.translate("DataExchangeWidget", u"Namespace symbol bound to this object", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.objectSymbolLabel.setWhatsThis(QCoreApplication.translate("DataExchangeWidget", u"Namespace symbol bound to this object", None))
#endif // QT_CONFIG(whatsthis)
        self.objectSymbolLabel.setText("")
#if QT_CONFIG(tooltip)
        self.newObjectToolButton.setToolTip(QCoreApplication.translate("DataExchangeWidget", u"Create new object with default values", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.newObjectToolButton.setStatusTip(QCoreApplication.translate("DataExchangeWidget", u"Create new object with default values", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.newObjectToolButton.setWhatsThis(QCoreApplication.translate("DataExchangeWidget", u"Create new object with default values", None))
#endif // QT_CONFIG(whatsthis)
        self.newObjectToolButton.setText(QCoreApplication.translate("DataExchangeWidget", u"New", None))
#if QT_CONFIG(tooltip)
        self.loadToolButton.setToolTip(QCoreApplication.translate("DataExchangeWidget", u"Load data from file", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.loadToolButton.setStatusTip(QCoreApplication.translate("DataExchangeWidget", u"Load data from file", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.loadToolButton.setWhatsThis(QCoreApplication.translate("DataExchangeWidget", u"Load data from file", None))
#endif // QT_CONFIG(whatsthis)
        self.loadToolButton.setText(QCoreApplication.translate("DataExchangeWidget", u"Load from file", None))
#if QT_CONFIG(tooltip)
        self.saveToolButton.setToolTip(QCoreApplication.translate("DataExchangeWidget", u"Save as pickle", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.saveToolButton.setStatusTip(QCoreApplication.translate("DataExchangeWidget", u"Save as pickle", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.saveToolButton.setWhatsThis(QCoreApplication.translate("DataExchangeWidget", u"Save as pickle", None))
#endif // QT_CONFIG(whatsthis)
        self.saveToolButton.setText(QCoreApplication.translate("DataExchangeWidget", u"Save", None))
#if QT_CONFIG(tooltip)
        self.importToolButton.setToolTip(QCoreApplication.translate("DataExchangeWidget", u"Import from workspace", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.importToolButton.setStatusTip(QCoreApplication.translate("DataExchangeWidget", u"Import from workspace", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.importToolButton.setWhatsThis(QCoreApplication.translate("DataExchangeWidget", u"Import from workspace", None))
#endif // QT_CONFIG(whatsthis)
        self.importToolButton.setText(QCoreApplication.translate("DataExchangeWidget", u"Import", None))
#if QT_CONFIG(tooltip)
        self.exportToolButton.setToolTip(QCoreApplication.translate("DataExchangeWidget", u"Export to workspace.\n"
"This will bind the object to a new symbol in the workspace. \n"
"If the object is already bound to another symbol, both symbols will point to the same object.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.exportToolButton.setStatusTip(QCoreApplication.translate("DataExchangeWidget", u"Export to workspace.", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.exportToolButton.setWhatsThis(QCoreApplication.translate("DataExchangeWidget", u"Export to workspace.\n"
"This will bind the object to a new symbol in the workspace. \n"
"If the object is already bound to another symbol, both symbols will point to the same object.", None))
#endif // QT_CONFIG(whatsthis)
        self.exportToolButton.setText(QCoreApplication.translate("DataExchangeWidget", u"Export", None))
#if QT_CONFIG(tooltip)
        self.copyToolButton.setToolTip(QCoreApplication.translate("DataExchangeWidget", u"Export a deep copy to the workspace.\n"
"You will still work on the original object.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.copyToolButton.setStatusTip(QCoreApplication.translate("DataExchangeWidget", u"Export a deep copy to the workspace. You will still work on the original object.", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.copyToolButton.setWhatsThis(QCoreApplication.translate("DataExchangeWidget", u"Export a deep copy to the workspace.\n"
"You will still work on the original object.", None))
#endif // QT_CONFIG(whatsthis)
        self.copyToolButton.setText(QCoreApplication.translate("DataExchangeWidget", u"Copy", None))
    # retranslateUi

