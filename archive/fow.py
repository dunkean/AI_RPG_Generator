import cv2
import numpy as np
import keyboard
from tkinter import filedialog
import tkinter as tk

# Initialize flags and variables
drawing = False
opacity = 0.8


def update_fog_of_war(event, x, y, flags, param):
    global drawing

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        cv2.circle(fog_of_war, (x, y), 30, (1, 1, 1), -1)
        cv2.circle(edit_fog_of_war, (x, y), 30, (1, 1, 1), -1)
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            cv2.circle(fog_of_war, (x, y), 30, (1, 1, 1), -1)
            cv2.circle(edit_fog_of_war, (x, y), 30, (1, 1, 1), -1)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False


# def ResizeWithAspectRatio(image, width=None, height=None, inter=cv2.INTER_AREA):
#     dim = None
#     (h, w) = image.shape[:2]

#     if width is None and height is None:
#         return image
#     if width is None:
#         r = height / float(h)
#         dim = (int(w * r), height)
#     else:
#         r = width / float(w)
#         dim = (width, int(h * r))

#     return cv2.resize(image, dim, interpolation=inter)


def display(image, windows_name):
    wdn_size = cv2.getWindowImageRect(windows_name)[2:4]
    ratio = min(wdn_size[0] / image.shape[1], wdn_size[1] / image.shape[0])
    # print(windows_name, image.shape, wdn_size, ratio)
    # cv2.resize(image, (int(image.shape[1] * ratio), int(image.shape[0] * ratio)), interpolation=cv2.INTER_AREA)
    # cv2.resize(image, wdn_size, interpolation=cv2.INTER_AREA)
    cv2.imshow(windows_name, image)


# Load the image (map) and create fog of war
map_image = cv2.imread("map.jpg")
image_size = map_image.shape
fog_of_war = np.zeros(image_size, dtype=np.uint8)
edit_fog_of_war = np.full(image_size, 5, dtype=np.uint8)


# Create windows for display and editing
cv2.namedWindow("Fog of War", cv2.WINDOW_NORMAL)
cv2.namedWindow("Edit Fog of War", cv2.WINDOW_NORMAL)

# Set mouse callback for editing
cv2.setMouseCallback("Edit Fog of War", update_fog_of_war)

while True:
    # Combine the fog of war with the map image
    # result_edit = cv2.addWeighted(map_image, 1-opacity, fog_of_war, opacity, 0)
    result_edit = cv2.divide(map_image, edit_fog_of_war)
    # cv2.imshow("Edit Fog of War", result_edit)
    display(result_edit, "Edit Fog of War")

    result = cv2.multiply(map_image, fog_of_war)
    # cv2.imshow("Fog of War", result)
    display(result, "Fog of War")

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q") or key == 27:
        break

    # Handle 'Ctrl+L' to load a new image
    if keyboard.is_pressed('ctrl+l'):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(title="Select a new map image")
        if file_path:
            map_image = cv2.imread(file_path)
            image_size = map_image.shape
            fog_of_war = np.zeros(image_size, dtype=np.uint8)
            edit_fog_of_war = np.full(image_size, 5, dtype=np.uint8)

cv2.destroyAllWindows()
