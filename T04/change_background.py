"""
Background replacement using thresholding (PyQt5 + Qt Designer).
"""
import io
import os
import re
import sys
import cv2
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QImage, QPixmap
from PyQt5.QtWidgets import (QApplication, QColorDialog, QFileDialog,
                             QMainWindow, QMessageBox)

UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "change_background.ui")
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;All files (*)"


def load_ui_compat(path, baseinstance):
    """Load a .ui file saved by newer Qt Designer (Qt 6).
    Rewrite scoped enums in memory so PyQt5 can parse them successfully.
    """
    with open(path, encoding="utf-8") as f:
        xml = f.read()

    def fix(match):
        text = re.sub(r"(\w+)::\w+::(\w+)", r"\1::\2", match.group(2))
        return match.group(1) + text + match.group(3)

    xml = re.sub(r"(<(?:enum|set)>)([^<]*)(</(?:enum|set)>)", fix, xml)
    return uic.loadUi(io.StringIO(xml), baseinstance)


def read_image(path):
    """Read any common image type and return an 8-bit, 3-channel BGR array."""
    try:
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except OSError:
        return None


def create_mask(img_bgr, threshold, inverse):
    """Return a binary mask where 255 = foreground and 0 = background."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    thresh_type = cv2.THRESH_BINARY_INV if inverse else cv2.THRESH_BINARY
    _, binary = cv2.threshold(gray, threshold, 255, thresh_type)

    if binary[0, 0] == 0:
        flooded = binary.copy()
        h, w = binary.shape[:2]
        ff_mask = np.zeros((h + 2, w + 2), np.uint8)
        cv2.floodFill(flooded, ff_mask, (0, 0), 255)
        mask = cv2.bitwise_or(binary, cv2.bitwise_not(flooded))
    else:
        mask = binary

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    return cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel), cv2.MORPH_CLOSE, kernel)


def replace_background(img_bgr, mask, background_bgr):
    """Smoothly merge foreground and background using alpha blending."""
    h, w = img_bgr.shape[:2]
    if background_bgr.shape[:2] != (h, w):
        background_bgr = cv2.resize(background_bgr, (w, h), interpolation=cv2.INTER_AREA)

    alpha = cv2.GaussianBlur(mask, (5, 5), 0).astype(np.float32) / 255.0
    result = img_bgr.astype(np.float32) * alpha[..., None] + background_bgr.astype(np.float32) * (1.0 - alpha[..., None])
    return result.astype(np.uint8)


def bgr_to_pixmap(img_bgr):
    """Convert an OpenCV image to a QPixmap."""
    if img_bgr.ndim == 2:
        img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w, c = rgb.shape
    return QPixmap.fromImage(QImage(rgb.data, w, h, c * w, QImage.Format_RGB888).copy())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load UI using the compatibility wrapper to fix Qt 6 -> PyQt5 enum mismatches
        load_ui_compat(UI_FILE, self)

        self.img = None
        self.texture = None
        self.color = (0, 200, 0)
        self.mask = None
        self.result = None

        # Signals
        self.openButton.clicked.connect(self.open_photo)
        self.colorButton.clicked.connect(self.choose_color)
        self.textureButton.clicked.connect(self.choose_texture)
        self.saveButton.clicked.connect(self.save_result)
        self.radioColor.toggled.connect(self.update_result)
        self.thresholdSlider.valueChanged.connect(self.update_result)
        self.checkInverse.stateChanged.connect(self.update_result)

        self.update_color_preview()

    def open_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose photo", "", IMAGE_FILTER)
        if path and (img := read_image(path)) is not None:
            self.img = img
            self.update_result()
        elif path:
            QMessageBox.warning(self, "Error", "Could not read the photo.")

    def choose_color(self):
        b, g, r = self.color
        c = QColorDialog.getColor(QColor(r, g, b), self, "Choose color")
        if c.isValid():
            self.color = (c.blue(), c.green(), c.red())
            self.update_color_preview()
            self.radioColor.setChecked(True)
            self.update_result()

    def update_color_preview(self):
        b, g, r = self.color
        self.labelColorPreview.setStyleSheet(f"background: rgb({r},{g},{b}); border:1px solid #444;")

    def choose_texture(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose background picture", "", IMAGE_FILTER)
        if path and (tex := read_image(path)) is not None:
            self.texture = tex
            self.radioPicture.setChecked(True)
            self.update_result()
        elif path:
            QMessageBox.warning(self, "Error", "Could not read the picture.")

    def update_result(self, *_):
        val = self.thresholdSlider.value()
        self.labelThreshold.setText(f"Threshold: {val}")
        if self.img is None:
            return

        self.mask = create_mask(self.img, val, self.checkInverse.isChecked())
        h, w = self.img.shape[:2]
        
        background = np.full((h, w, 3), self.color, np.uint8) if (self.radioColor.isChecked() or self.texture is None) else self.texture
        self.result = replace_background(self.img, self.mask, background)
        self.refresh_display()

    def refresh_display(self):
        for label, image in ((self.labelOriginal, self.img), (self.labelMask, self.mask), (self.labelResult, self.result)):
            if image is not None:
                label.setPixmap(bgr_to_pixmap(image).scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_display()

    def save_result(self):
        if self.result is not None and (path := QFileDialog.getSaveFileName(self, "Save", "result.png", "PNG (*.png);;JPG (*.jpg)")[0]):
            ext = os.path.splitext(path)[1] or ".png"
            ok, buf = cv2.imencode(ext, self.result)
            if ok:
                buf.tofile(path)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())