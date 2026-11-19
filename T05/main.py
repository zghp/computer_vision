"""Replace the background of an image; only keep the main object inside a user-selected ROI."""
import sys

import cv2
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QColor, QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QColorDialog, QFileDialog, QMainWindow, QRubberBand


def fill_holes(binary):
    """Flood the background from every black border pixel, then add the unreached holes to the object."""
    flooded = binary.copy()
    h, w = binary.shape
    fill_mask = np.zeros((h + 2, w + 2), np.uint8)
    border = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
    border += [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    for x, y in border:
        if flooded[y, x] == 0:
            cv2.floodFill(flooded, fill_mask, (x, y), 255)
    return binary | cv2.bitwise_not(flooded)


def compute_mask(image, threshold):
    """Return a binary mask (255 = main object): inverted threshold on gray levels, then hole filling."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    return fill_holes(binary)


def solid_background(size, red, green, blue):
    """Create a (width, height) background filled with a single color."""
    width, height = size
    background = np.zeros((height, width, 3), np.uint8)
    background[:] = (blue, green, red)
    return background


def combine(image, background, mask):
    """Keep the image where the mask is set and the background everywhere else."""
    foreground = cv2.bitwise_and(image, image, mask=mask)
    behind = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(mask))
    return foreground | behind


def mat_to_qimage(image):
    """Convert a grayscale or BGR OpenCV image to a QImage."""
    if image.ndim == 2:
        h, w = image.shape
        return QImage(image.data, w, h, image.strides[0], QImage.Format_Grayscale8).copy()
    rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    h, w, _ = rgb.shape
    return QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()


class MainWindow(QMainWindow):
    """Main window: load a photo, select the ROI with the mouse, choose the background color."""

    def __init__(self):
        """Load the Designer UI, initialise the state and connect signals."""
        super().__init__()
        uic.loadUi("mainwindow.ui", self)
        self.photo = None                  # original image (BGR)
        self.roi = None                    # (x, y, w, h) in image coordinates
        self.color = QColor(160, 32, 240)  # default background: purple
        self.origin = None                 # mouse press position on the original label
        self.band = QRubberBand(QRubberBand.Rectangle, self.labelOriginal)
        self.show_color()

        self.btnLoad.clicked.connect(self.on_btn_load)
        self.btnColor.clicked.connect(self.on_btn_color)
        self.sliderThreshold.valueChanged.connect(self.on_slider_threshold)
        self.labelOriginal.mousePressEvent = self.on_mouse_press
        self.labelOriginal.mouseMoveEvent = self.on_mouse_move
        self.labelOriginal.mouseReleaseEvent = self.on_mouse_release

    def show_color(self):
        """Display the current background color in the small color label."""
        self.labelColor.setStyleSheet(f"background-color: {self.color.name()}; border: 1px solid black;")

    @staticmethod
    def show_image(image, label):
        """Display an OpenCV image in a label, keeping the aspect ratio."""
        pixmap = QPixmap.fromImage(mat_to_qimage(image))
        label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_result(self):
        """Recompute the mask and both result images (ROI only and full photo)."""
        if self.photo is None:
            return
        self.show_image(self.photo, self.labelOriginal)
        if self.roi is None:
            return
        x, y, w, h = self.roi
        roi = self.photo[y:y + h, x:x + w]
        mask = compute_mask(roi, self.sliderThreshold.value())
        c = self.color
        full = solid_background((self.photo.shape[1], self.photo.shape[0]), c.red(), c.green(), c.blue())
        full[y:y + h, x:x + w] = combine(roi, full[y:y + h, x:x + w], mask)
        self.show_image(mask, self.labelMask)
        self.show_image(full[y:y + h, x:x + w], self.labelRoiResult)
        self.show_image(full, self.labelFullResult)

    def to_image_coords(self, pos):
        """Convert a point on the original label to image coordinates (clamped to the image)."""
        pix = self.labelOriginal.pixmap()
        offset_x = (self.labelOriginal.width() - pix.width()) // 2
        offset_y = (self.labelOriginal.height() - pix.height()) // 2
        scale = self.photo.shape[1] / pix.width()
        x = int((pos.x() - offset_x) * scale)
        y = int((pos.y() - offset_y) * scale)
        return min(max(x, 0), self.photo.shape[1] - 1), min(max(y, 0), self.photo.shape[0] - 1)

    def on_mouse_press(self, event):
        """Start the ROI selection."""
        if self.photo is None:
            return
        self.origin = event.pos()
        self.band.setGeometry(QRect(self.origin, self.origin))
        self.band.show()

    def on_mouse_move(self, event):
        """Update the rubber band while dragging."""
        if self.origin is not None:
            self.band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def on_mouse_release(self, event):
        """Finish the selection, store the ROI in image coordinates and update the results."""
        if self.origin is None:
            return
        x1, y1 = self.to_image_coords(self.origin)
        x2, y2 = self.to_image_coords(event.pos())
        self.origin = None
        if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
            self.roi = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            self.update_result()

    def on_btn_load(self):
        """Ask for an image file and load it."""
        path, _ = QFileDialog.getOpenFileName(self, "Load image", "", "Images (*.jpg *.jpeg *.png)")
        if not path:
            return
        image = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return
        self.photo, self.roi = image, None
        self.band.hide()
        self.update_result()

    def on_btn_color(self):
        """Let the user choose the background color."""
        chosen = QColorDialog.getColor(self.color, self, "Choose background color")
        if chosen.isValid():
            self.color = chosen
            self.show_color()
            self.update_result()

    def on_slider_threshold(self, value):
        """Update the threshold label and the results."""
        self.labelThreshold.setText(str(value))
        self.update_result()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())