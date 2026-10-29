"""
Loads an image from the computer, lets the user write a single line of text
on it at a position chosen with sliders, with adjustable size, thickness and
colour, shows the result in the main window and allows saving it.
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QColorDialog
from PyQt5.QtGui import QPixmap, QImage
import sys
import cv2

# the initial image and the one with the text
imageOpenCV = None
imageText = None


class Ui_mainWindow(QMainWindow):
    """Main window that builds the interface and handles all user actions."""

    def setupUi(self, mainWindow):
        """Create all widgets (buttons, text field, sliders, image label)
        and connect their signals to the handler methods."""
        mainWindow.setWindowTitle("Text on image")
        mainWindow.resize(1000, 650)
        self.centralwidget = QtWidgets.QWidget(mainWindow)

        #teh button taht opens the image
        self.openButton = QtWidgets.QPushButton("Open image", self.centralwidget)
        self.openButton.setGeometry(QtCore.QRect(20, 20, 200, 35))
        self.openButton.clicked.connect(self.getImage)

        #the text field
        self.labelText = QtWidgets.QLabel("Text:", self.centralwidget)
        self.labelText.setGeometry(QtCore.QRect(20, 70, 200, 20))
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(20, 90, 200, 25))
        self.lineEdit.textChanged.connect(self.drawText)

        #slider for position x
        self.labelX = QtWidgets.QLabel(self.centralwidget)
        self.labelX.setGeometry(QtCore.QRect(20, 130, 200, 20))
        self.sliderX = QtWidgets.QSlider(QtCore.Qt.Horizontal, self.centralwidget)
        self.sliderX.setGeometry(QtCore.QRect(20, 150, 200, 22))
        self.sliderX.valueChanged.connect(self.drawText)

        #slider for position y
        self.labelY = QtWidgets.QLabel(self.centralwidget)
        self.labelY.setGeometry(QtCore.QRect(20, 185, 200, 20))
        self.sliderY = QtWidgets.QSlider(QtCore.Qt.Horizontal, self.centralwidget)
        self.sliderY.setGeometry(QtCore.QRect(20, 205, 200, 22))
        self.sliderY.valueChanged.connect(self.drawText)

        #slider for the text size
        self.labelSize = QtWidgets.QLabel(self.centralwidget)
        self.labelSize.setGeometry(QtCore.QRect(20, 240, 200, 20))
        self.sliderSize = QtWidgets.QSlider(QtCore.Qt.Horizontal, self.centralwidget)
        self.sliderSize.setGeometry(QtCore.QRect(20, 260, 200, 22))
        self.sliderSize.setRange(1, 100)
        self.sliderSize.setValue(10)
        self.sliderSize.valueChanged.connect(self.drawText)

        #slider for the text thickness
        self.labelThickness = QtWidgets.QLabel(self.centralwidget)
        self.labelThickness.setGeometry(QtCore.QRect(20, 295, 200, 20))
        self.sliderThickness = QtWidgets.QSlider(QtCore.Qt.Horizontal, self.centralwidget)
        self.sliderThickness.setGeometry(QtCore.QRect(20, 315, 200, 22))
        self.sliderThickness.setRange(1, 20)
        self.sliderThickness.setValue(2)
        self.sliderThickness.valueChanged.connect(self.drawText)

        #button for choosing the text colour
        self.colorButton = QtWidgets.QPushButton("Select colour:", self.centralwidget)
        self.colorButton.setGeometry(QtCore.QRect(20, 360, 200, 35))
        self.colorButton.clicked.connect(self.selectColor)

        #save button
        self.saveButton = QtWidgets.QPushButton("Save:", self.centralwidget)
        self.saveButton.setGeometry(QtCore.QRect(20, 410, 200, 35))
        self.saveButton.clicked.connect(self.saveImage)
        self.saveButton.setEnabled(False)

        #area where the picture is displayed
        self.imageDisplayArea = QtWidgets.QLabel(self.centralwidget)
        self.imageDisplayArea.setGeometry(QtCore.QRect(250, 20, 720, 580))

        mainWindow.setCentralWidget(self.centralwidget)

        #initial text colour (blac by default)
        self.textColor = (0, 0, 0)

        self.drawText()

    def getImage(self):
        """Open a file dialog, read the chosen image with OpenCV and adjust
        the position sliders to the image size."""
        filePath = QFileDialog.getOpenFileName(self, 'Open file', 'D:\\',
                                               'Image files (*.jpg *.jpeg *.png *.bmp)')
        if filePath[0] == "":
            return

        #read the photo with cv2
        global imageOpenCV
        image = cv2.imread(filePath[0])
        if image is None:
            return
        imageOpenCV = image
        h, w, _ = imageOpenCV.shape

        #text position
        self.sliderX.setMaximum(w)
        self.sliderY.setMaximum(h)
        self.sliderX.setValue(w // 10)
        self.sliderY.setValue(h // 2)

        self.saveButton.setEnabled(True)
        self.drawText()

    def selectColor(self):
        """Open a colour dialog and store the chosen colour in BGR format
        (the order used by OpenCV)."""
        color = QColorDialog.getColor(QtCore.Qt.black, self)
        if color.isValid():
            self.textColor = (color.blue(), color.green(), color.red())
            self.drawText()

    def drawText(self):
        """Write the text on a copy of the original image using the current
        slider values and colour, then display the result in the window."""
        x = self.sliderX.value()
        y = self.sliderY.value()
        size = self.sliderSize.value() / 10
        thickness = self.sliderThickness.value()
        self.labelX.setText("Position X: " + str(x))
        self.labelY.setText("Position Y: " + str(y))
        self.labelSize.setText("Size: " + str(size))
        self.labelThickness.setText("Thickness: " + str(thickness))

        #do nothing if theres no photo
        if imageOpenCV is None:
            return

        #write the text on a copy of the initial photo
        global imageText
        imageText = imageOpenCV.copy()
        cv2.putText(imageText,
                    self.lineEdit.text(),
                    (x, y), #position
                    cv2.FONT_HERSHEY_COMPLEX,
                    size, self.textColor, thickness) #font size, colour & thickness

        #display the photo
        h, w, _ = imageText.shape
        imageReady = cv2.cvtColor(imageText, cv2.COLOR_BGR2RGB)
        qImg = QImage(imageReady.data, w, h, 3 * w, QImage.Format_RGB888)
        self.imageDisplayArea.setPixmap(QPixmap(qImg).scaled(self.imageDisplayArea.size(), QtCore.Qt.KeepAspectRatio))

    def saveImage(self):
        """Open a save dialog and write the image with text to disk."""
        filePath = QFileDialog.getSaveFileName(self, 'Save file', 'result.png',
                                               'Images (*.png *.jpg *.bmp)')
        if filePath[0] != "" and imageText is not None:
            cv2.imwrite(filePath[0], imageText)


if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if not app: # verifies if QApplication exists, creates it otherwise
        app = QtWidgets.QApplication(sys.argv)

    mainWindow = QtWidgets.QMainWindow()
    ui = Ui_mainWindow()
    ui.setupUi(mainWindow)
    mainWindow.show()

    app.exec_()
