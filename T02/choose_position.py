"""Helper program for choosing the position of the bubbles with trackbars.

It uses the same settings as animation.py (the image, the bubble and the
bubble size), so animation.py must be in the same folder. Move the bubbles
with the four trackbars until they sit nicely above the characters, then
press ESC. The program prints the two lines that should be copied into
animation.py, replacing the LEFT_POSITION and RIGHT_POSITION values.
"""

import cv2
import animation as a


def nothing(x):
    """Empty function required by createTrackbar, as in the course example."""
    pass


def add_bubble(image, bubble, x, y):
    """Blend the bubble into the region of interest that starts at (x, y)."""
    hb, wb, _ = bubble.shape
    roi = image[y:y + hb, x:x + wb]
    roi = cv2.addWeighted(roi, 1, bubble, 1, 0)
    image[y:y + hb, x:x + wb] = roi


def main():
    """Show the image with both bubbles and the trackbars for their positions."""
    image, bubble = a.load_images()
    small_bubble, mirrored_bubble = a.prepare_bubbles(bubble)
    h, w, _ = image.shape

    max_x = w - a.BUBBLE_WIDTH
    max_y = h - a.BUBBLE_HEIGHT
    if max_x < 0 or max_y < 0:
        raise SystemExit('The bubble is larger than the image. '
                         'Reduce BUBBLE_WIDTH / BUBBLE_HEIGHT.')

    window_name = 'Choose the bubble positions - ESC to finish'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    xl, yl = a.LEFT_POSITION
    xr, yr = a.RIGHT_POSITION
    cv2.createTrackbar('x left', window_name, min(xl, max_x), max_x, nothing)
    cv2.createTrackbar('y left', window_name, min(yl, max_y), max_y, nothing)
    cv2.createTrackbar('x right', window_name, min(xr, max_x), max_x, nothing)
    cv2.createTrackbar('y right', window_name, min(yr, max_y), max_y, nothing)

    while True:
        xl = cv2.getTrackbarPos('x left', window_name)
        yl = cv2.getTrackbarPos('y left', window_name)
        xr = cv2.getTrackbarPos('x right', window_name)
        yr = cv2.getTrackbarPos('y right', window_name)

        preview = image.copy()
        add_bubble(preview, small_bubble, xl, yl)
        add_bubble(preview, mirrored_bubble, xr, yr)
        cv2.imshow(window_name, preview)

        if cv2.waitKey(1) == 27:
            break

    cv2.destroyAllWindows()
    cv2.waitKey(1)
    print('Copy these two lines into animation.py:')
    print('LEFT_POSITION = ({}, {})'.format(xl, yl))
    print('RIGHT_POSITION = ({}, {})'.format(xr, yr))


if __name__ == '__main__':
    main()
