# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'cancellableqprogressbar.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QProgressBar, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget)

class Ui_CancellableQProgressBar(object):
    def setupUi(self, CancellableQProgressBar):
        if not CancellableQProgressBar.objectName():
            CancellableQProgressBar.setObjectName(u"CancellableQProgressBar")
        CancellableQProgressBar.resize(309, 46)
        self.verticalLayout = QVBoxLayout(CancellableQProgressBar)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.progressBar = QProgressBar(CancellableQProgressBar)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setMaximum(98)
        self.progressBar.setValue(24)

        self.horizontalLayout.addWidget(self.progressBar)

        self.cancelButton = QToolButton(CancellableQProgressBar)
        self.cancelButton.setObjectName(u"cancelButton")
        icon = QIcon(QIcon.fromTheme(u"dialog-cancel"))
        self.cancelButton.setIcon(icon)

        self.horizontalLayout.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(CancellableQProgressBar)

        QMetaObject.connectSlotsByName(CancellableQProgressBar)
    # setupUi

    def retranslateUi(self, CancellableQProgressBar):
        CancellableQProgressBar.setWindowTitle(QCoreApplication.translate("CancellableQProgressBar", u"Form", None))
#if QT_CONFIG(tooltip)
        self.cancelButton.setToolTip(QCoreApplication.translate("CancellableQProgressBar", u"Cancel", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.cancelButton.setStatusTip(QCoreApplication.translate("CancellableQProgressBar", u"Cancels the process", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.cancelButton.setWhatsThis(QCoreApplication.translate("CancellableQProgressBar", u"Cancels the process", None))
#endif // QT_CONFIG(whatsthis)
        self.cancelButton.setText(QCoreApplication.translate("CancellableQProgressBar", u"Cancel", None))
    # retranslateUi

