# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'chemicalsynapsewidget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QHBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QTabWidget, QWidget)

from gui.widgets.dataclasswidgets.cellcompartmentwidget import CellCompartmentWidget
from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget

class Ui_ChemicalSynapseWidget(object):
    def setupUi(self, ChemicalSynapseWidget):
        if not ChemicalSynapseWidget.objectName():
            ChemicalSynapseWidget.setObjectName(u"ChemicalSynapseWidget")
        ChemicalSynapseWidget.resize(342, 177)
        self.gridLayout_3 = QGridLayout(ChemicalSynapseWidget)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.nameDescriptionWidget = NameDescriptionWidget(ChemicalSynapseWidget)
        self.nameDescriptionWidget.setObjectName(u"nameDescriptionWidget")

        self.gridLayout_3.addWidget(self.nameDescriptionWidget, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(ChemicalSynapseWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.synapseMorhpologicalTypeComboBox = QComboBox(ChemicalSynapseWidget)
        self.synapseMorhpologicalTypeComboBox.setObjectName(u"synapseMorhpologicalTypeComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.synapseMorhpologicalTypeComboBox.sizePolicy().hasHeightForWidth())
        self.synapseMorhpologicalTypeComboBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.synapseMorhpologicalTypeComboBox)

        self.label_2 = QLabel(ChemicalSynapseWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.synapseFunctionalTypeComboBox = QComboBox(ChemicalSynapseWidget)
        self.synapseFunctionalTypeComboBox.setObjectName(u"synapseFunctionalTypeComboBox")
        sizePolicy.setHeightForWidth(self.synapseFunctionalTypeComboBox.sizePolicy().hasHeightForWidth())
        self.synapseFunctionalTypeComboBox.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.synapseFunctionalTypeComboBox)


        self.gridLayout_3.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_3 = QLabel(ChemicalSynapseWidget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_3.addWidget(self.label_3)

        self.neurotransmitterComboBox = QComboBox(ChemicalSynapseWidget)
        self.neurotransmitterComboBox.setObjectName(u"neurotransmitterComboBox")
        sizePolicy.setHeightForWidth(self.neurotransmitterComboBox.sizePolicy().hasHeightForWidth())
        self.neurotransmitterComboBox.setSizePolicy(sizePolicy)

        self.horizontalLayout_3.addWidget(self.neurotransmitterComboBox)

        self.retrogradeCheckBox = QCheckBox(ChemicalSynapseWidget)
        self.retrogradeCheckBox.setObjectName(u"retrogradeCheckBox")

        self.horizontalLayout_3.addWidget(self.retrogradeCheckBox)


        self.gridLayout_3.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)

        self.chemicalSynapseComponentsTabWidget = QTabWidget(ChemicalSynapseWidget)
        self.chemicalSynapseComponentsTabWidget.setObjectName(u"chemicalSynapseComponentsTabWidget")
        self.presynapticTab = QWidget()
        self.presynapticTab.setObjectName(u"presynapticTab")
        self.gridLayout = QGridLayout(self.presynapticTab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.presynapticCompartmentWidget = CellCompartmentWidget(self.presynapticTab)
        self.presynapticCompartmentWidget.setObjectName(u"presynapticCompartmentWidget")

        self.gridLayout.addWidget(self.presynapticCompartmentWidget, 0, 0, 1, 1)

        self.chemicalSynapseComponentsTabWidget.addTab(self.presynapticTab, "")
        self.postsynapticTab = QWidget()
        self.postsynapticTab.setObjectName(u"postsynapticTab")
        self.gridLayout_2 = QGridLayout(self.postsynapticTab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.postsynapticCompartmentWidget = CellCompartmentWidget(self.postsynapticTab)
        self.postsynapticCompartmentWidget.setObjectName(u"postsynapticCompartmentWidget")

        self.gridLayout_2.addWidget(self.postsynapticCompartmentWidget, 0, 0, 1, 1)

        self.chemicalSynapseComponentsTabWidget.addTab(self.postsynapticTab, "")

        self.gridLayout_3.addWidget(self.chemicalSynapseComponentsTabWidget, 3, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 2, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_3.addItem(self.verticalSpacer, 4, 0, 1, 1)

#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.synapseMorhpologicalTypeComboBox)
        self.label_2.setBuddy(self.synapseFunctionalTypeComboBox)
        self.label_3.setBuddy(self.neurotransmitterComboBox)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(ChemicalSynapseWidget)

        self.chemicalSynapseComponentsTabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(ChemicalSynapseWidget)
    # setupUi

    def retranslateUi(self, ChemicalSynapseWidget):
        ChemicalSynapseWidget.setWindowTitle(QCoreApplication.translate("ChemicalSynapseWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("ChemicalSynapseWidget", u"Morphology:", None))
        self.label_2.setText(QCoreApplication.translate("ChemicalSynapseWidget", u"Function:", None))
        self.label_3.setText(QCoreApplication.translate("ChemicalSynapseWidget", u"Transmitter:", None))
        self.retrogradeCheckBox.setText(QCoreApplication.translate("ChemicalSynapseWidget", u"Retrograde", None))
        self.chemicalSynapseComponentsTabWidget.setTabText(self.chemicalSynapseComponentsTabWidget.indexOf(self.presynapticTab), QCoreApplication.translate("ChemicalSynapseWidget", u"Presynaptic", None))
        self.chemicalSynapseComponentsTabWidget.setTabText(self.chemicalSynapseComponentsTabWidget.indexOf(self.postsynapticTab), QCoreApplication.translate("ChemicalSynapseWidget", u"Postsynaptic", None))
    # retranslateUi

