import os
import platform, warnings
import numpy as np
import multiprocessing, multiprocess
import threading

from skimage.transform import resize
from PIL import Image
from tqdm import tqdm
from functools import wraps, reduce
import time
import cv2
from typing import *


# ------------------- functional modules -------------------
def add_progress_bar(iterable_arg_index=0):
    """
    Decorator to add a progress bar to the specified iterable argument of a function.
    Parameters:
    - iterable_arg_index (int): The index of the iterable argument in the function's argument list.
    """
    def decorator(func : Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            iterable = args[iterable_arg_index]
            progress_bar = tqdm(iterable)
            new_args = list(args)  
            # Replace the iterable in the arguments with the new progress bar iterator
            new_args[iterable_arg_index] = progress_bar  
            return func(*new_args, **kwargs)
        return wrapper
    return decorator


def combine_functions(functions):
    """
    Combine a list of functions into a single function that processes
    data sequentially through each function in the list.

    Args:
        functions (list[callable]): A list of functions, where each function 
            has the same type of input and output.

    Returns:
        callable: A combined function that is the composition of all the functions 
        in the list. If the input list is empty, returns an identity function.
    """
    if not functions:  
        return lambda x: x
    return reduce(lambda f, g: lambda x: g(f(x)), functions)



def preset_kwargs(**preset_kwargs):
    """
    A decorator to preset keyword arguments of any function. The first argument
    of the function is assumed to be the input data, and the rest are considered
    keyword arguments for tuning or controlling the function's behavior.

    Parameters:
    - **preset_kwargs: Arbitrary keyword arguments that will be preset for the decorated function.
    
    Returns:
    - function: The decorated function with the preset keyword arguments. (closure)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Update the preset keyword arguments with explicitly provided ones, if any
            combined_kwargs = {**preset_kwargs, **kwargs}
            return func(*args, **combined_kwargs)
        return wrapper
    return decorator


class TimeoutError(Exception):
    pass


def timeout(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]  # Placeholder for the function's result
            def function_thread():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    result[0] = e
            
            thread = threading.Thread(target=function_thread)
            thread.start()
            thread.join(seconds)
            if thread.is_alive():
                thread.join(0.1)  # Ensure any remaining operations wrap up
                if isinstance(result[0], Exception):
                    raise result[0]
                raise TimeoutError("Function call timed out")
            return result[0]
        return wrapper
    return decorator

def print_underscore(func):
    """
    Decorator to print a line of underscores before and after the decorated function is called.
    """
    def wrapper(*args, **kwargs):
        print("-" * 80)
        result = func(*args, **kwargs)
        print("-" * 80)
        return result
    return wrapper


def deprecated(reason):
    """
    Decorator to mark a function as deprecated.
    """
    def decorator(func):
        @wraps(func)
        def new_func(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)  # turn off filter
            warnings.warn(f"{func.__name__} is deprecated: {reason}",
                          category=DeprecationWarning,
                          stacklevel=2)
            warnings.simplefilter('default', DeprecationWarning)  # reset filter
            return func(*args, **kwargs)
        return new_func
    return decorator



def deprecated_class(reason):
    """
    Decorator to mark a class as deprecated.
    """
    def class_rebuilder(cls):
        orig_init = cls.__init__
        @wraps(cls.__init__)
        def new_init(self, *args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)
            warnings.warn(f"{cls.__name__} is deprecated: {reason}",
                          category=DeprecationWarning,
                          stacklevel=2)
            warnings.simplefilter('default', DeprecationWarning)
            orig_init(self, *args, **kwargs)
        cls.__init__ = new_init
        return cls
    return class_rebuilder


# ------------------- multiprocessing -------------------

def process_list_in_parallel(function, data_list):
    with multiprocess.Pool(processes=multiprocess.cpu_count()) as pool:
        result = pool.map(function, data_list)
    return result


@deprecated("Not updating anymore, use apply_multiprocess() instead.")
def apply_multiprocessing(function):
    """
    Decorator to apply multiprocessing to a function that processes an iterable.
    No progress indicator, can be used in the terminal.
    """
    @wraps(function)
    def wrapper(iterable):
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            result = pool.map(function, iterable)
        return result
    return wrapper


def apply_multiprocess(function):
    """
    Decorator to apply multiprocess to a function that processes an iterable. 
    Use multiprocess which is compatible with Jupyter notebook.
    Could select adding a progress indicator to the operation.
    """
    @wraps(function)
    def wrapper(iterable):
        processor = multiprocess.cpu_count()
        with multiprocess.Pool(processes=processor) as pool:
            print(f"Processing {len(iterable)} items with {processor} processes...")
            result = list(tqdm(pool.imap(function, iterable), total=len(iterable)))
        return result
    return wrapper



# ------------------- file operations -------------------

def get_all_file_paths(dirs, types=['']) -> list:
    """
    Get all file paths in the specified directories with the specified file types.
    input: dirs (list of strings or string of the root of dataset folder), types (list of strings) 
    """
    if isinstance(dirs, str): # Check if dirs is a single string and convert to list if necessary
        dirs = [dirs]
    file_paths = []  
    for dir in dirs:
        for root, _, files in os.walk(dir):
            for file in files:
                if any(type in file for type in types):
                    file_path = os.path.join(root, file)
                    file_paths.append(os.path.abspath(file_path))
    print(f"Found {len(file_paths)} files.")
    return file_paths



class ImageLoader:
    def __init__(self, funcs):
        if not isinstance(funcs, list):
            funcs = [funcs]
        self.funcs = funcs
    
    @deprecated("Use ImageLoader.load instead.")
    def load_image(self, image_path):
        """
        Load an image from the specified path and apply the specified functions to the image sequentially.
        """
        with Image.open(image_path) as img:
            # Convert the image to a NumPy array
            img = np.array(img)
            for func in self.funcs:
                img = func(img)
        return img

    @deprecated("Use ImageLoader.load instead.")
    def load_images(self, image_paths):
        """
        Load multiple images and return a dataset in numpy array format.
        """
        dataset = []
        for image_path in image_paths:
            dataset.append(self.load_image(image_path))
        print(f"Loaded dataset length: {len(dataset)}")
        return dataset
    
    def load(self, input):
        """
        Automatically decide whether to load a single image or multiple images based on the input type.
        """
        if isinstance(input, str):  # Single image path
            return self.load_image(input)
        elif isinstance(input, list):  # Assuming a list of image paths
            return self.load_images(input)
        else:
            raise TypeError("Unsupported input type. Expected a string or a list of strings.")



# ------------------- image processing -------------------

def read_narray_image(image_path):
    """
    Read an image from the specified path and return it as a NumPy array.
    """
    with Image.open(image_path) as img:
        return np.array(img)


def rgb_to_grayscale(narray_img: np.array):
    """
    Convert an image in numpy array format from RGB or RGBA to grayscale by averaging all the colors, or return
    the image if it is already in grayscale.
    
    Parameters:
    - narray_img (np.array): Input image in numpy array format.

    Returns:
    - np.array: Grayscale image in numpy array format.
    """
    # Check if the image already is a 2D grayscale image
    if narray_img.ndim == 2:
        return narray_img

    # Check if the input array is a 3D image array
    elif narray_img.ndim == 3:
        if narray_img.shape[-1] == 4:  # If the image has an alpha channel.
            narray_img = narray_img[:, :, :3]
        # Calculate the mean across the color channels
        grayscale_img = np.mean(narray_img, axis=2)
        return grayscale_img
    
    else:
        raise ValueError("Input array must be either a 2D grayscale or a 3D color image array")


def crop_images(image: np.array, regions: list[tuple]) -> list:
    """
    Crop multiple regions from an image.

    Args:
    image (np.array): The input image as a NumPy array.
    regions (list of tuples): Each tuple contains two tuples, 
                              defining the top-left and bottom-right 
                              corners of the rectangle to crop (e.g., ((0,0), (66,66))).

    Returns:
    list: A list of np.array, each being a cropped region from the input image.
    """
    cropped_images = []
    for region in regions:
        top_left, bottom_right = region
        # Crop the image using array slicing
        cropped_image = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
        cropped_images.append(cropped_image)
    
    return cropped_images


def join_images(image_list, method='largest'):
    """
    Join images side by side with resizing based on the specified method.

    Args:
    image_list (list of np.array): List of images to join.
    method (str): 'largest' to resize all images to the height of the tallest image,
                  'smallest' to resize to the height of the shortest image.

    Returns:
    np.array: A new image consisting of the input images joined side by side.
    """
    if not image_list:
        raise ValueError("image_list cannot be empty")

    # Determine the target height based on the method
    if method == 'largest':
        target_height = max(img.shape[0] for img in image_list)
    elif method == 'smallest':
        target_height = min(img.shape[0] for img in image_list)
    else:
        raise ValueError("Method must be 'largest' or 'smallest'")

    # Resize images and collect them in a list
    resized_images = []
    for img in image_list:
        # Calculate the new width to maintain the aspect ratio
        scale_ratio = target_height / img.shape[0]
        new_width = int(img.shape[1] * scale_ratio)
        resized_img = cv2.resize(img, (new_width, target_height), interpolation=cv2.INTER_AREA)
        resized_images.append(resized_img)

    # Concatenate all images side by side
    final_image = np.hstack(resized_images)
    return final_image


def subtract_minimum(arr):
    """
    Subtract the minimum value from each element in a 1D NumPy array.
    Parameters:
    arr (np.ndarray): A 1D numpy array.
    Returns:
    np.ndarray: The processed array with the minimum value subtracted from each element.
    """
    if arr.ndim != 1:
        raise ValueError("Input must be a 1D numpy array.")
    min_value = np.min(arr)
    processed_arr = arr - min_value
    return processed_arr


def minmax_normalization(arr):
    """
    Min-max normalization
    """
    return (arr - np.min(arr)) / (np.max(arr) - np.min(arr))


def image_normalize(narray_img: np.array):
    """
    Normalize the input image by scaling its pixel values to the range [0, 1].
    Parameters:
    image (np.ndarray): A NumPy array representing the input image.
    Returns:
    np.ndarray: The normalized image.
    """
    return narray_img.astype('float32') / 255.


def scale_image(narray_img, scaling_factor):
    """
    Scales an image by a given scaling factor.
    
    Parameters:
    - image: ndarray, the input image to be scaled.
    - scaling_factor: float, the factor by which the image will be scaled.
    
    Returns:
    - scaled_image: ndarray, the scaled image.
    """
    # Calculate the new dimensions
    new_height = int(narray_img.shape[0] * scaling_factor)
    new_width = int(narray_img.shape[1] * scaling_factor)
    new_dimensions = (new_height, new_width)
    
    # Resize the image
    scaled_image = resize(narray_img, new_dimensions, anti_aliasing=True)
    
    return scaled_image


# ------------------- system/enviornment -------------------

def is_jupyter():
    """Check if Python is running in Jupyter (notebook or lab) or in a command line."""
    try:
        # Attempt to import a Jupyter-specific package
        from IPython import get_ipython
        # If `get_ipython` does not return None, we are in a Jupyter environment
        if get_ipython() is not None:
            return True
    except ImportError:
        # If the import fails, we are not in a Jupyter environment
        pass
    return False


def get_system_info():
    """
    Get system information including the operating system, version, machine, processor, and Python version.
    Returns:
    dict: A dictionary containing the system information.
    """
    system_info = {
        "System": platform.system(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Architecture": platform.architecture()[0],
        "Python Build": platform.python_version()
    }
    return system_info





