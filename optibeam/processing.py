import cv2
import numpy as np


# ----------------------------- dataset preparation -----------------------------

# class HDF5DatasetWriter:
#     def __init__(self, dims, output_path, data_key="images", buf_size=1000):
#         # Check if the output path exists
#         if os.path.exists(output_path):
#             raise ValueError("The supplied 'output_path' already exists and cannot be overwritten. "
#                              "Please specify a different 'output_path'.")

#         # Open the HDF5 database for writing and create two datasets: one to store the images/features and another
#         # to store the class labels
#         self.db = h5py.File(output_path, "w")
#         self.data = self.db.create_dataset(data_key, dims, dtype="float")
#         self.labels = self.db.create_dataset("labels", (dims[0],), dtype="int")

#         # Store the buffer size and initialize the buffer itself
#         self.buf_size = buf_size
#         self.buffer = {"data": [], "labels": []}
#         self.idx = 0

#     def add(self, rows, labels):
#         # Add the rows and labels to the buffer
#         self.buffer["data"].extend(rows)
#         self.buffer["labels"].extend(labels)

#         # Check to see if the buffer needs to be flushed to disk
#         if len(self.buffer["data"]) >= self.buf_size:
#             self.flush()

#     def flush(self):
#         # Write the buffers to disk then reset the buffer
#         i = self.idx + len(self.buffer["data"])
#         self.data[self.idx:i] = self.buffer["data"]
#         self.labels[self.idx:i] = self.buffer["labels"]
#         self.idx = i
#         self.buffer = {"data": [], "labels": []}

#     def store_class_labels(self, class_labels):
#         # Create a dataset to store the actual class label names






# ----------------------------- image sample post processing -----------------------------

def crop_images_from_clicks(click_list, image):
    """
    Crop images based on a list of click positions that define the rectangle corners.
    
    Args:
    click_list (list of tuples): List containing pairs of tuples. Each pair defines
                                 the top left and bottom right corners of a rectangle.
    image (numpy.ndarray): The image from which to crop the rectangles.

    Returns:
    list of numpy.ndarray: List containing the cropped images.
    """
    cropped_images = []
    
    # Iterate through the list of tuples; each pair forms one rectangle
    for i in range(0, len(click_list)):
        top_left = click_list[i][0]
        bottom_right = click_list[i][1]
        
        # Crop the image using numpy slicing
        cropped = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
        cropped_images.append(cropped)
    
    return cropped_images



def select_crop_areas_corner(original_image, num, scale_factor=1):
    # Helper variables
    points = []
    rectangles = []
    max_x, max_y = original_image.shape[1], original_image.shape[0]

    def mouse_click(event, x, y, flags, param):
        # Access the points list
        nonlocal points, rectangles

        # Adjust click position to original image scale
        orig_x, orig_y = int(x / scale_factor), int(y / scale_factor)

        # Record the click positions
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) >= 2 * num:  # Reset if previous set is complete
                points = []
                rectangles = []
                image = cv2.resize(original_image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
                cv2.imshow('Image', image)

            points.append((orig_x, orig_y))

            # Check if we can form a rectangle
            if len(points) % 2 == 0:
                points[-2] = (max(0, min(points[-2][0], max_x)), max(0, min(points[-2][1], max_y)))
                points[-1] = (max(0, min(points[-1][0], max_x)), max(0, min(points[-1][1], max_y)))
                rectangles.append((points[-2], points[-1]))

            # Redraw the image with rectangles/points
            image = cv2.resize(original_image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
            for rect in rectangles:
                scaled_rect = [(int(pt[0] * scale_factor), int(pt[1] * scale_factor)) for pt in rect]
                cv2.rectangle(image, scaled_rect[0], scaled_rect[1], (0, 255, 0), 1)
            if len(points) % 2 == 1:
                cv2.circle(image, (int(points[-1][0] * scale_factor), int(points[-1][1] * scale_factor)), 1, (0, 0, 255), -1)
            cv2.imshow('Image', image)

    # Scale and display the image
    scaled_image = cv2.resize(original_image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
    cv2.namedWindow('Image')
    cv2.setMouseCallback('Image', mouse_click)
    cv2.imshow('Image', scaled_image)

    # Handle the window until ESC is pressed
    while True:
        k = cv2.waitKey(1) & 0xFF
        if k == 27:  # ESC key
            break

    cv2.destroyAllWindows()
    return rectangles


def select_crop_areas_center(original_image, num, scale_factor=1):
    # Helper variables
    points = []
    squares = []

    def mouse_click(event, x, y, flags, param):
        nonlocal points, squares
        max_x, max_y = original_image.shape[1], original_image.shape[0]
        # Adjust click position to original image scale
        orig_x, orig_y = int(x / scale_factor), int(y / scale_factor)

        # Record the click positions
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) >= 2 * num:  # Reset if previous set is complete
                points = []
                squares = []
                image = cv2.resize(original_image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
                cv2.imshow('Image', image)

            points.append((orig_x, orig_y))

            # Check if we can form a square
            if len(points) % 2 == 0:
                center = points[-2]
                edge_point = points[-1]
                side_length = max(abs(edge_point[0] - center[0]), abs(edge_point[1] - center[1]))
                top_left = (center[0] - side_length, center[1] - side_length)
                bottom_right = (center[0] + side_length, center[1] + side_length)
                top_left = (max(0, min(top_left[0], max_x)), max(0, min(top_left[1], max_y)))
                bottom_right = (max(0, min(bottom_right[0], max_x)), max(0, min(bottom_right[1], max_y)))
                squares.append((top_left, bottom_right))

            # Redraw the image with squares
            image = cv2.resize(original_image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
            for square in squares:
                cv2.rectangle(image, (int(square[0][0] * scale_factor), int(square[0][1] * scale_factor)),
                              (int(square[1][0] * scale_factor), int(square[1][1] * scale_factor)), (0, 255, 0), 1)
            if len(points) % 2 == 1:
                cv2.circle(image, (int(points[-1][0] * scale_factor), int(points[-1][1] * scale_factor)), 1, (0, 0, 255), -1)
            cv2.imshow('Image', image)

    # Scale and display the image
    scaled_image = cv2.resize(original_image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
    cv2.namedWindow('Image')
    cv2.setMouseCallback('Image', mouse_click)
    cv2.imshow('Image', scaled_image)

    # Handle the window until ESC is pressed
    while True:
        k = cv2.waitKey(1) & 0xFF
        if k == 27:  # ESC key
            break

    cv2.destroyAllWindows()
    return squares

# ----------------------------- image processing -----------------------------

def apply_threshold(image, threshold=5):
    """
    Apply a threshold to an image array. Pixels below the threshold are set to 0.
    If the image is normalized (0 to 1), the threshold is also normalized.

    Parameters:
    - image: numpy array, the input image.
    - threshold: float, the threshold value.

    Returns:
    - numpy array, the thresholded image.
    """
    # Check if the image is normalized
    if image.dtype == np.float32 or image.dtype == np.float64:
        if image.min() >= 0 and image.max() <= 1:
            normalized_threshold = threshold / 255.0
        else:
            normalized_threshold = threshold
    else:
        normalized_threshold = threshold
    thresholded_image = np.where(image >= normalized_threshold, image, 0)
    return thresholded_image


