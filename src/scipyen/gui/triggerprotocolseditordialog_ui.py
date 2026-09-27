# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'triggerprotocolseditordialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QGridLayout, QHBoxLayout, QHeaderView, QSizePolicy,
    QTableView, QToolButton, QWidget)

class Ui_TriggerProtocolsEditorDialog(object):
    def setupUi(self, TriggerProtocolsEditorDialog):
        if not TriggerProtocolsEditorDialog.objectName():
            TriggerProtocolsEditorDialog.setObjectName(u"TriggerProtocolsEditorDialog")
        TriggerProtocolsEditorDialog.resize(466, 283)
        self.gridLayout = QGridLayout(TriggerProtocolsEditorDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.addProtocolToolButton = QToolButton(TriggerProtocolsEditorDialog)
        self.addProtocolToolButton.setObjectName(u"addProtocolToolButton")
        icon = QIcon(QIcon.fromTheme(u"list-add"))
        self.addProtocolToolButton.setIcon(icon)

        self.horizontalLayout.addWidget(self.addProtocolToolButton)

        self.removeProtocolToolButton = QToolButton(TriggerProtocolsEditorDialog)
        self.removeProtocolToolButton.setObjectName(u"removeProtocolToolButton")
        icon1 = QIcon(QIcon.fromTheme(u"list-remove"))
        self.removeProtocolToolButton.setIcon(icon1)

        self.horizontalLayout.addWidget(self.removeProtocolToolButton)

        self.detectProtocolsToolButton = QToolButton(TriggerProtocolsEditorDialog)
        self.detectProtocolsToolButton.setObjectName(u"detectProtocolsToolButton")
        icon2 = QIcon(QIcon.fromTheme(u"tools-wizard"))
        self.detectProtocolsToolButton.setIcon(icon2)

        self.horizontalLayout.addWidget(self.detectProtocolsToolButton)

        self.triggerProtocolFileChooserToolButton = QToolButton(TriggerProtocolsEditorDialog)
        self.triggerProtocolFileChooserToolButton.setObjectName(u"triggerProtocolFileChooserToolButton")
        icon3 = QIcon()
        iconThemeName = u"document-open"
        if QIcon.hasThemeIcon(iconThemeName):
            icon3 = QIcon.fromTheme(iconThemeName)
        else:
            icon3.addFile(u"../systems", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        self.triggerProtocolFileChooserToolButton.setIcon(icon3)

        self.horizontalLayout.addWidget(self.triggerProtocolFileChooserToolButton)

        self.importProtocolsToolButton = QToolButton(TriggerProtocolsEditorDialog)
        self.importProtocolsToolButton.setObjectName(u"importProtocolsToolButton")
        icon4 = QIcon(QIcon.fromTheme(u"document-import"))
        self.importProtocolsToolButton.setIcon(icon4)

        self.horizontalLayout.addWidget(self.importProtocolsToolButton)

        self.clearProtocolsToolButton = QToolButton(TriggerProtocolsEditorDialog)
        self.clearProtocolsToolButton.setObjectName(u"clearProtocolsToolButton")
        icon5 = QIcon(QIcon.fromTheme(u"edit-clear-all"))
        self.clearProtocolsToolButton.setIcon(icon5)

        self.horizontalLayout.addWidget(self.clearProtocolsToolButton)

        self.buttonBox = QDialogButtonBox(TriggerProtocolsEditorDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.horizontalLayout.addWidget(self.buttonBox)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.protocolTableView = QTableView(TriggerProtocolsEditorDialog)
        self.protocolTableView.setObjectName(u"protocolTableView")
        self.protocolTableView.setAlternatingRowColors(True)
        self.protocolTableView.setGridStyle(Qt.PenStyle.NoPen)

        self.gridLayout.addWidget(self.protocolTableView, 0, 0, 1, 1)


        self.retranslateUi(TriggerProtocolsEditorDialog)
        self.buttonBox.accepted.connect(TriggerProtocolsEditorDialog.accept)
        self.buttonBox.rejected.connect(TriggerProtocolsEditorDialog.reject)

        QMetaObject.connectSlotsByName(TriggerProtocolsEditorDialog)
    # setupUi

    def retranslateUi(self, TriggerProtocolsEditorDialog):
        TriggerProtocolsEditorDialog.setWindowTitle(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Dialog", None))
        self.addProtocolToolButton.setText(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Add Protocol", None))
        self.removeProtocolToolButton.setText(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Remove Selected Protocol", None))
#if QT_CONFIG(tooltip)
        self.detectProtocolsToolButton.setToolTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Detect Trigger Events", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.detectProtocolsToolButton.setStatusTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Detect Trigger Events", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.detectProtocolsToolButton.setWhatsThis(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"<html><head/><body><p>Detect triggers from TTL-like signals embedded in the electrophysiology data</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.detectProtocolsToolButton.setText(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Detect Triggers", None))
#if QT_CONFIG(tooltip)
        self.triggerProtocolFileChooserToolButton.setToolTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Open protocols file", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.triggerProtocolFileChooserToolButton.setStatusTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Open protocols file", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.triggerProtocolFileChooserToolButton.setWhatsThis(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Open protocols file", None))
#endif // QT_CONFIG(whatsthis)
        self.triggerProtocolFileChooserToolButton.setText(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"...", None))
#if QT_CONFIG(tooltip)
        self.importProtocolsToolButton.setToolTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Import Protocols", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.importProtocolsToolButton.setStatusTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Import Protocols", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.importProtocolsToolButton.setWhatsThis(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"<html><head/><body><p>Import protocols from another ScanData object or a protocols object in workspace</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.importProtocolsToolButton.setText(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Import Protocols", None))
#if QT_CONFIG(tooltip)
        self.clearProtocolsToolButton.setToolTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Clear Protocols", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.clearProtocolsToolButton.setStatusTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Clear Protocols", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.clearProtocolsToolButton.setWhatsThis(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"<html><head/><body><p>Removes all trigger protocols and events embedded in the data</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.clearProtocolsToolButton.setText(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Clear", None))
#if QT_CONFIG(tooltip)
        self.protocolTableView.setToolTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Trigger protocols", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.protocolTableView.setStatusTip(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Trigger protocols", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.protocolTableView.setWhatsThis(QCoreApplication.translate("TriggerProtocolsEditorDialog", u"Trigger protocols", None))
#endif // QT_CONFIG(whatsthis)
    # retranslateUi

