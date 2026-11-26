"""
Blur the background of a live webcam stream (PyQt5 + Qt Designer).

The perssn in the foreground is turned into a mask (white = person, black = background).
A strong filter is applied ONLY to the background.

Two ways to find the person:
  * GrabCut in ROI: drag a box around yourself; GrabCut separates you from the background inside the box.
  * Background difference: capture the empty background first; every pixel that differs from it is considered the person.
"""
import os
import sys

import cv2
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import QRect, Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QRubberBand

UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background_blur.ui")
WIDTH, HEIGHT = 640, 480 # working frame size

# "How to use" instructions under the camera image
HELP_GRABCUT = ("HOW TO USE:<br><br>"
                "&bull; drag a box around yourself on the camera<br>"
                "&bull; everything outside the box is background<br>"
                "&bull; Grab Cut separates everything inside from the backgorund")
HELP_DIFFERENCE = ("HOW TO USE:<br><br>"
                   "&bull; step out of the frame<br>"
                   "&bull; click 'Capture empty background'<br>"
                   "&bull; step back in<br>"
                   "&bull; only the pixels that differ from the saved background are kept sharp<br><br>"
                   "Difference threshold:<br><br>"
                   "&bull; lower = more sensitive; catches more noise<br>"
                   "&bull; higher = less sensitive; may miss parts of preson in frame")


# ------------------------------- masks ---------------------------------
def fill_holes(binary):
    """flood the bg from every black border pixel, then add the unreached holes to the object (from prev T05 hw)"""
    flooded = binary.copy()
    h, w = binary.shape
    fill_mask = np.zeros((h + 2, w + 2), np.uint8)
    border = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
    border += [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    for x, y in border:
        if flooded[y, x] == 0:
            cv2.floodFill(flooded, fill_mask, (x, y), 255)
    return binary | cv2.bitwise_not(flooded)


def clean_mask(mask):
    """remove small dots, close small gaps and fill the holes inside the person"""
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)    # remove dots
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)   # close gaps
    return fill_holes(mask)


def mask_grabcut(frame, roi):
    """find the person inside the ROI box with GrabCut; returns 255 = person, 0 = background."""
    # GrabCut runs on a 4x smaller copy of the frame cos its slow (160 x 120)
    small = cv2.resize(frame, (WIDTH // 4, HEIGHT // 4), interpolation=cv2.INTER_AREA)
    x, y, w, h = (v // 4 for v in roi) # the box, scaled down the same way

    # GrabCut writes its answer for every pixel into this mask
    gc_mask = np.zeros(small.shape[:2], np.uint8)
    # internal colour models GrabCut learns (background / foreground); must be 1 x 65 arrays
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    # GC_INIT_WITH_RECT: everything outside the box is surely background,
    # inside the box GrabCut decides; 2 = number of iterations (more = better but slower)
    cv2.grabCut(small, gc_mask, (x, y, w, h), bgd_model, fgd_model, 2, cv2.GC_INIT_WITH_RECT)

    # pixel labels: 0 = sure background, 1 = sure foreground,
    #               2 = probable background, 3 = probable foreground
    person = np.where((gc_mask == 1) | (gc_mask == 3), 255, 0).astype(np.uint8)
    return cv2.resize(person, (WIDTH, HEIGHT)) # back to the full frame size


def mask_difference(frame, background, threshold):
    """pixels that differ from the empty background by more than the threshold = person."""
    diff = cv2.absdiff(cv2.GaussianBlur(frame, (5, 5), 0), cv2.GaussianBlur(background, (5, 5), 0))
    diff = diff.max(axis=2) # biggest change of the 3 colour channels (B, G, R)
    _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    return mask


# ------------------------------- filtering ---------------------------------
def apply_filter(frame, name, k):
    """filter the whole frame with the chosen method; k = odd kernel size"""
    if name == "Gaussian":
        return cv2.GaussianBlur(frame, (k, k), 0)
    if name == "Blur (box)":
        return cv2.blur(frame, (k, k))
    if name == "Median":
        return cv2.medianBlur(frame, k)
    return cv2.bilateralFilter(frame, 15, 150, 150)


def blur_background(frame, filtered, mask):
    """person from the original frame + background from the filtered frame"""
    person = cv2.bitwise_and(frame, frame, mask=mask)
    background = cv2.bitwise_and(filtered, filtered, mask=cv2.bitwise_not(mask))
    return cv2.add(person, background)


def to_pixmap(image):
    """convert an OpenCV image (gray or BGR) to a QPixmap."""
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w, _ = rgb.shape
    return QPixmap.fromImage(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy())


# ------------------------------- window ---------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(UI_FILE, self)
        self.camera = None
        self.frame = None
        self.background = None
        self.result = None
        self.roi = (128, 24, 384, 450)
        self.origin = None
        self.band = QRubberBand(QRubberBand.Rectangle, self.labelCamera)

        self.btnCapture.clicked.connect(self.on_btn_capture)
        self.btnSave.clicked.connect(self.on_btn_save)
        self.comboMethod.currentIndexChanged.connect(self.on_method_changed)
        self.sliderThreshold.valueChanged.connect(self.on_slider_threshold)
        self.sliderKernel.valueChanged.connect(self.on_slider_kernel)
        self.labelCamera.mousePressEvent = self.on_mouse_press
        self.labelCamera.mouseMoveEvent = self.on_mouse_move
        self.labelCamera.mouseReleaseEvent = self.on_mouse_release
        self.labelStatus.setText(HELP_GRABCUT)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        QTimer.singleShot(100, self.start_camera)     # show the window first, then open the camera

    def start_camera(self):
        # on Windows DirectShow opens the webcam much faster than the default
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        self.camera = cv2.VideoCapture(0, backend)
        if not self.camera.isOpened():
            self.labelStatus.setText("No camera found (is it used by another app?)")
            return
        self.timer.start(30) # abt 30 frames per second

    def next_frame(self):
        ok, frame = self.camera.read()
        if not ok:
            return
        self.frame = cv2.resize(cv2.flip(frame, 1), (WIDTH, HEIGHT))   # mirror image
        use_difference = self.comboMethod.currentIndex() == 1

        # 1. mask of the person
        if use_difference and self.background is not None:
            mask = mask_difference(self.frame, self.background, self.sliderThreshold.value())
        elif use_difference:
            mask = np.zeros((HEIGHT, WIDTH), np.uint8) # no background yet -> blur everything
        else:
            mask = mask_grabcut(self.frame, self.roi)
        mask = clean_mask(mask)

        # 2. filter the background only
        k = self.odd_kernel_size()
        filtered = apply_filter(self.frame, self.comboFilter.currentText(), k)
        self.result = blur_background(self.frame, filtered, mask)

        # 3. display (the green box only used by GrabCut)
        preview = self.frame.copy()
        if not use_difference:
            x, y, w, h = self.roi
            cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
        self.show_image(preview, self.labelCamera)
        self.show_image(mask, self.labelMask)
        self.show_image(self.result, self.labelResult)

    @staticmethod
    def show_image(image, label):
        label.setPixmap(to_pixmap(image).scaled(label.size(), Qt.KeepAspectRatio))

    def on_method_changed(self, index):
        self.labelStatus.setText(HELP_DIFFERENCE if index == 1 else HELP_GRABCUT)

    # ------------------------------- drawing the ROI box with the mouse ---------------------------------
    def to_image_coords(self, pos):
        x = int(pos.x() * WIDTH / self.labelCamera.width())
        y = int(pos.y() * HEIGHT / self.labelCamera.height())
        # keep a small margin: GrabCut needs some background pixels outside the box
        return min(max(x, 4), WIDTH - 5), min(max(y, 4), HEIGHT - 5)

    def on_mouse_press(self, event):
        if self.comboMethod.currentIndex() == 1: # no box in background difference mode
            return
        self.origin = event.pos()
        self.band.setGeometry(QRect(self.origin, self.origin))
        self.band.show()

    def on_mouse_move(self, event):
        if self.origin is not None:
            self.band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def on_mouse_release(self, event):
        if self.origin is None:
            return
        x1, y1 = self.to_image_coords(self.origin)
        x2, y2 = self.to_image_coords(event.pos())
        self.origin = None
        self.band.hide()
        # ignore tiny accidental clicks
        # if you just click on the camera image, or drag only a few pixels
        # then the old box is kept instead of being replaced by a tiny one
        if abs(x2 - x1) > 20 and abs(y2 - y1) > 20: 
            self.roi = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    # ------------------------------- sliders ---------------------------------
    def odd_kernel_size(self):
        """The kernel size must be odd (3, 5, 7, ...), so even values are increased by 1."""
        # An odd kernel has an exact centre pixel, and that centre is the pixel being changed
        # The reason is that a filter works by placing the kernel (a small k × k square) over each pixel and replacing that pixel with
        # a combination of the pixels under the square. The pixel being changed sits in the middle of the square:
        # 3 x 3 (odd)            4 x 4 (even)
        # [ . . . ]              [ . . . . ]
        # [ . X . ]              [ . . . . ]   <- no middle cell
        # [ . . . ]              [ . . . . ]      
        #                       [ . . . . ]
        k = self.sliderKernel.value()
        if k % 2 == 0:
            k = k + 1
        return k

    def on_slider_threshold(self, value):
        self.labelThreshold.setText(str(value))

    def on_slider_kernel(self, value):
        self.labelKernel.setText(str(self.odd_kernel_size()))

    # ------------------------------- buttons ---------------------------------
    def on_btn_capture(self):
        if self.frame is not None:
            self.background = self.frame.copy()
            self.comboMethod.setCurrentIndex(1)

    def on_btn_save(self):
        if self.result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save", "result.png", "PNG (*.png);;JPG (*.jpg)")
        if path:
            cv2.imwrite(path, self.result)

    def closeEvent(self, event):
        self.timer.stop()
        if self.camera is not None:
            self.camera.release()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
