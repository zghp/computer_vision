"""Animation of two characters having a conversation, using OpenCV.

The speech bubble from text.png is resized (cv2.resize), mirrored for the
second character (cv2.flip) and blended into the original image with
cv2.addWeighted, as in the Batman example. The text is written with
cv2.putText. The bubble and the text fade in and out gradually by changing
the weights passed to addWeighted. The frames are saved to a video file.
"""

import cv2

IMAGE_FILE = 'Groovy.png'
BUBBLE_FILE = 'text.png'
VIDEO_FILE = 'if_sheep_could_talk.mp4'

BUBBLE_WIDTH, BUBBLE_HEIGHT = 360, 266
LEFT_POSITION = (92, 93)
RIGHT_POSITION = (461, 33)

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.8
FONT_THICKNESS = 2
LINE_HEIGHT = 32
TEXT_COLOR = (0, 0, 0)
MAX_TEXT_WIDTH = 225

FPS = 20
FADE_IN_FRAMES = 10
HOLD_FRAMES = 40
FADE_OUT_FRAMES = 10
PAUSE_FRAMES = 4

DIALOGUE = [
    (1, 'Wazzzup?'),
    (2, 'Good, good. Wazzzup with youuu?'),
    (1, 'Ehhh, surviving and all'),
    (2, 'Just surviving? When the grass tastes so good??'),
    (1, 'The grass is good but the weather is low'),
    (2, 'Too much sun makes a desert. We get to eat flowers'),
    (1, 'And they do taste good...'),
]


def load_images():
    """Read the image with the characters and the bubble, then print their sizes.

    Returns the pair (image, bubble). Stops the program if either image
    cannot be read (usually the file name is wrong or the file is not in
    the same folder as the program).
    """
    image = cv2.imread(IMAGE_FILE)
    bubble = cv2.imread(BUBBLE_FILE)
    if image is None or bubble is None:
        raise SystemExit('Cannot find {} or {} in the current folder.'
                         .format(IMAGE_FILE, BUBBLE_FILE))

    h, w, c = image.shape
    print('{}: w = {}, h = {}, c = {}'.format(IMAGE_FILE, w, h, c))
    hb, wb, cb = bubble.shape
    print('{}: w = {}, h = {}, c = {}'.format(BUBBLE_FILE, wb, hb, cb))
    return image, bubble


def prepare_bubbles(bubble):
    """Resize the bubble and create its mirrored version.

    The original bubble is used for the character on the left. The
    left-right mirrored version (cv2.flip with parameter 1) is used for
    the character on the right.
    """
    small_bubble = cv2.resize(bubble, (BUBBLE_WIDTH, BUBBLE_HEIGHT))
    mirrored_bubble = cv2.flip(small_bubble, 1)
    return small_bubble, mirrored_bubble


def check_positions(image):
    """Check that the bubble fits inside the image at both chosen positions.

    If the region of interest goes outside the image, OpenCV raises an
    error in addWeighted, so the program stops earlier with a clear message.
    """
    h, w, _ = image.shape
    for x, y in (LEFT_POSITION, RIGHT_POSITION):
        if x < 0 or y < 0 or x + BUBBLE_WIDTH > w or y + BUBBLE_HEIGHT > h:
            raise SystemExit('The bubble does not fit at position ({}, {}). '
                             'The image is {} x {}.'.format(x, y, w, h))


def split_into_lines(text):
    """Split a line of dialogue into lines that fit inside the bubble.

    Words are added to the current line as long as its width, measured
    with cv2.getTextSize, does not exceed MAX_TEXT_WIDTH.
    """
    lines = []
    current_line = ''
    for word in text.split():
        attempt = (current_line + ' ' + word).strip()
        (width, _), _ = cv2.getTextSize(attempt, FONT, FONT_SCALE,
                                        FONT_THICKNESS)
        if width <= MAX_TEXT_WIDTH or current_line == '':
            current_line = attempt
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def write_text(image, lines, x, y):
    """Write the lines centred inside the bubble whose corner is at (x, y).

    Each line is measured with cv2.getTextSize so it can be centred
    horizontally, then written with putText in TEXT_COLOR. The lines are
    placed one under the other, LINE_HEIGHT pixels apart.
    """
    center_y = y + int(BUBBLE_HEIGHT * 0.42)
    text_y = center_y - (len(lines) - 1) * LINE_HEIGHT // 2 + 10
    for line in lines:
        (width, _), _ = cv2.getTextSize(line, FONT, FONT_SCALE,
                                        FONT_THICKNESS)
        text_x = x + (BUBBLE_WIDTH - width) // 2
        cv2.putText(image, line, (text_x, text_y), FONT, FONT_SCALE,
                    TEXT_COLOR, FONT_THICKNESS)
        text_y += LINE_HEIGHT


def make_frame(image, bubbles, speaker, lines, weight):
    """Build one frame: the image + the bubble + the text, with the given weight.

    weight is between 0 (bubble invisible) and 1 (bubble fully visible).
    The bubble is blended with the region of interest using addWeighted,
    as in the Batman example. The text is written on a copy of the frame,
    and the copy is blended with the frame using addWeighted as well, so
    the text fades in and out together with the bubble.
    """
    small_bubble, mirrored_bubble = bubbles
    if speaker == 1:
        (x, y), bubble = LEFT_POSITION, small_bubble
    else:
        (x, y), bubble = RIGHT_POSITION, mirrored_bubble

    frame = image.copy()
    roi = frame[y:y + BUBBLE_HEIGHT, x:x + BUBBLE_WIDTH]
    roi = cv2.addWeighted(roi, 1, bubble, weight, 0)
    frame[y:y + BUBBLE_HEIGHT, x:x + BUBBLE_WIDTH] = roi

    with_text = frame.copy()
    write_text(with_text, lines, x, y)
    return cv2.addWeighted(frame, 1 - weight, with_text, weight, 0)


def line_weights():
    """Return the list of weights for one line of dialogue.

    The weight rises from 0 to 1 (the bubble appears), stays at 1 while
    the line is being read, drops back to 0 (the bubble disappears), and
    is followed by a short pause with no bubble.
    """
    weights = []
    for i in range(FADE_IN_FRAMES):
        weights.append((i + 1) / FADE_IN_FRAMES)
    weights += [1] * HOLD_FRAMES
    for i in range(FADE_OUT_FRAMES):
        weights.append(1 - (i + 1) / FADE_OUT_FRAMES)
    weights += [0] * PAUSE_FRAMES
    return weights


def generate_animation(image, bubbles):
    """Generate all the frames, display them and save them to the video.

    A screenshot (line_N.png) with the bubble fully visible is also saved
    for every line of dialogue. The animation can be stopped with ESC.
    """
    h, w, _ = image.shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(VIDEO_FILE, fourcc, FPS, (w, h))

    window_name = 'Animation - ESC to stop'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    stopped = False
    for k, (speaker, text) in enumerate(DIALOGUE):
        lines = split_into_lines(text)
        for weight in line_weights():
            frame = make_frame(image, bubbles, speaker, lines, weight)
            video.write(frame)
            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) == 27:
                stopped = True
                break

        cv2.imwrite('line_{}.png'.format(k + 1),
                    make_frame(image, bubbles, speaker, lines, 1))
        if stopped:
            break

    video.release()
    cv2.destroyAllWindows()
    cv2.waitKey(1)
    print('Done! Video saved to', VIDEO_FILE)


def main():
    """Run all the steps: loading, preparing the bubbles, checking, animating."""
    image, bubble = load_images()
    bubbles = prepare_bubbles(bubble)
    check_positions(image)
    generate_animation(image, bubbles)


if __name__ == '__main__':
    main()
