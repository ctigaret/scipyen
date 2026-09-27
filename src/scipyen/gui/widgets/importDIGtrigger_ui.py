# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'importDIGtrigger.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QHeaderView,
    QPushButton, QSizePolicy, QSpacerItem, QTableView,
    QWidget)

class Ui_ImportDIGTriggerWidget(object):
    def setupUi(self, ImportDIGTriggerWidget):
        if not ImportDIGTriggerWidget.objectName():
            ImportDIGTriggerWidget.setObjectName(u"ImportDIGTriggerWidget")
        ImportDIGTriggerWidget.resize(501, 229)
        self.gridLayout = QGridLayout(ImportDIGTriggerWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.tableView = QTableView(ImportDIGTriggerWidget)
        self.tableView.setObjectName(u"tableView")

        self.gridLayout.addWidget(self.tableView, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.importPushButton = QPushButton(ImportDIGTriggerWidget)
        self.importPushButton.setObjectName(u"importPushButton")
        icon = QIcon(QIcon.fromTheme(u"document-import"))
        self.importPushButton.setIcon(icon)
        self.importPushButton.setFlat(True)

        self.horizontalLayout.addWidget(self.importPushButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)


        self.retranslateUi(ImportDIGTriggerWidget)

        QMetaObject.connectSlotsByName(ImportDIGTriggerWidget)
    # setupUi

    def retranslateUi(self, ImportDIGTriggerWidget):
        ImportDIGTriggerWidget.setWindowTitle(QCoreApplication.translate("ImportDIGTriggerWidget", u"ImportDIGTriggerWidget", None))
#if QT_CONFIG(tooltip)
        ImportDIGTriggerWidget.setToolTip(QCoreApplication.translate("ImportDIGTriggerWidget", u"ImportDIGTriggerWidget", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        ImportDIGTriggerWidget.setStatusTip(QCoreApplication.translate("ImportDIGTriggerWidget", u"ImportDIGTriggerWidget", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        ImportDIGTriggerWidget.setWhatsThis(QCoreApplication.translate("ImportDIGTriggerWidget", u"ImportDIGTriggerWidget", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.tableView.setToolTip(QCoreApplication.translate("ImportDIGTriggerWidget", u"DIG Triggers defined in the acqusition protocol", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.tableView.setStatusTip(QCoreApplication.translate("ImportDIGTriggerWidget", u"DIG Triggers defined in the acqusition protocol", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.tableView.setWhatsThis(QCoreApplication.translate("ImportDIGTriggerWidget", u"DIG Triggers defined in the acqusition protocol", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(tooltip)
        self.importPushButton.setToolTip(QCoreApplication.translate("ImportDIGTriggerWidget", u"Import from recording protocol", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.importPushButton.setStatusTip(QCoreApplication.translate("ImportDIGTriggerWidget", u"Import from recording protocol", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.importPushButton.setWhatsThis(QCoreApplication.translate("ImportDIGTriggerWidget", u"Import from recording protocol", None))
#endif // QT_CONFIG(whatsthis)
        self.importPushButton.setText(QCoreApplication.translate("ImportDIGTriggerWidget", u"Import", None))
    # retranslateUi

