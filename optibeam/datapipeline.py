import tensorflow as tf
import numpy as np
import pandas as pd
import ast
import getpass

from PIL import Image
from abc import ABC, abstractmethod
from typing import *
# from webdav3.client import Client



# ----------------- Cloud Storage based data pipeline -----------------
class CloudStorage(ABC):
    def __init__(self, cloud_name:str=None):
        self.cloud_name = cloud_name
    
    @abstractmethod 
    def login(self):
        pass

    @abstractmethod
    def download_file(self, local_path:str, remote_path:str):
        pass

    @abstractmethod
    def upload_file(self, local_path:str, remote_path:str):
        pass
    

class Client: # Dummy class for testing
    pass

class CERNBox(CloudStorage):
    def __init__(self, cloud_name:str):
        super().__init__(cloud_name)
        self.client = None
    
    def login(self):
        # Credentials
        username = input("Enter your username: ")
        password = getpass.getpass("Enter your password: ")

        # Define WebDAV options
        options = {
            'webdav_hostname': "https://cernbox.cern.ch",
            'webdav_login': username,
            'webdav_password': password,
            'webdav_root':     "/cernbox/webdav/home/",
            'timeout': 600  # Timeout in seconds (e.g., 10 minutes)
        }
        
        # Initialize the client
        self.client = Client(options)

    
    def download_file(self, local_path:str, remote_path:str):
        try:
            # Download the file
            self.client.download_file(remote_path, local_path)
            print(f"File downloaded successfully: {local_path}")
        except Exception as e:
            print(f"Error downloading file: {e}")
    
    
    def upload_file(self, local_path:str, remote_path:str):
        print(f"To be developed")




# ----------------- tf pipeline with prefetch ----------------- 

def load_and_process_image(path):
    image = tf.io.read_file(path) # Read the image file
    # Decode the image to its original depth (assuming the image is grayscale)
    image = tf.image.decode_image(image, channels=1, expand_animations=False)
    image = tf.image.convert_image_dtype(image, tf.float32) # float32 type and normalization
    width = tf.shape(image)[1]  # Split the image in half horizontally
    half_width = width // 2
    label = image[:, :half_width]  # left_half
    input = image[:, half_width:]  # right_half
    return input, label

# def load_and_process_image(image_path: str, processing_steps: List[Callable[[np.ndarray], np.ndarray]]=[]) -> np.ndarray:
#     """
#     Process an image with a dynamic pipeline of functions.

#     Parameters:
#     - image_path: str
#         Path to the image file.
#     - processing_steps: List[Callable[[np.ndarray], np.ndarray]]
#         List of processing functions, each taking a NumPy array and returning a NumPy array.

#     Returns:
#     - np.ndarray
#         Processed image as a NumPy array.
#     """
#     # Step 1: Read the image file
#     binary_string = tf.io.read_file(image_path)

#     # Step 2: Decode the image
#     image_tensor = tf.image.decode_image(binary_string)

#     # Step 3: Convert TensorFlow tensor to NumPy array
#     image_array = image_tensor.numpy()

#     # Step 4: Apply each processing step in sequence
#     for step in processing_steps:
#         image_array = step(image_array)
        
#     # Step 5: Splite to repare and return the processed image
#     width = tf.shape(image_array)[1]  # Split the image in half horizontally
#     half_width = width // 2
#     label = image_array[:, :half_width]  # left_half
#     input = image_array[:, half_width:]  # right_half
#     return input, label



def tf_dataset_prep(data_dirs, func, batch_size, shuffle=True, buffer_size=1024):
    # Create a Dataset from the list of paths
    dataset = tf.data.Dataset.from_tensor_slices(data_dirs)
    if shuffle:
        dataset = dataset.shuffle(buffer_size=buffer_size)
    # Map the processing function to each file path
    dataset = dataset.map(func, num_parallel_calls=tf.data.AUTOTUNE)
    # Batch the dataset
    dataset = dataset.batch(batch_size)
    # Prefetch to improve pipeline performance
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset

def datapipeline_conclusion(dataset:tf.data.Dataset, batch_size):
    assert isinstance(dataset, tf.data.Dataset)
    print("total number of batches: ", len(dataset), "with batch size: ", batch_size)
    for left_imgs, right_imgs in dataset.take(1):  
        print(left_imgs.shape, right_imgs.shape)  






# ----------------- old data pipeline ----------------- 
class DataPipeline:
    def __init__(self, df, shape):
        self.df = df
        self.shape = shape
    
    def data_pipeline(self, dim, batch_size=1, is_batch=True):
        batch_x, batch_y = [], []
        while True:  # Loop indefinitely
            for index, row in self.df.iterrows():
                img = Image.open(row['image_path']).convert('L')  # Convert to grayscale
                crop_x = ast.literal_eval(row["speckle_crop_pos"])
                crop_y = ast.literal_eval(row["original_crop_pos"])
                crop_x = tuple(item for subtuple in crop_x for item in subtuple)
                crop_y = tuple(item for subtuple in crop_y for item in subtuple)
                img_x = img.crop(crop_x)  # crop ROI
                img_y = img.crop(crop_y)
                img_x = img_x.resize(dim)   # Resize dimensions
                img_y = img_y.resize(dim)
                res_x = np.expand_dims(np.array(img_x), axis=-1) # Change shape to (256, 256, 1)
                res_y = np.expand_dims(np.array(img_y), axis=-1)
                if is_batch:
                    batch_x.append(np.array(res_x)) 
                    batch_y.append(np.array(res_y)) 
                    if len(batch_x) >= batch_size:  # Yield a batch when batch size is reached
                        batch_x = np.stack(batch_x)
                        batch_y = np.stack(batch_y)
                        yield batch_x.astype('float32') / 255., batch_y.astype('float32') / 255.
                        batch_x, batch_y = [], []
                else:
                    yield res_x.astype('float32') / 255., res_y.astype('float32') / 255.

    def create_tf_dataset(self, batch_list, dim=(256, 256), batch_size=1, is_batch=True):
        return tf.data.Dataset.from_generator(
            generator=lambda: self.data_pipeline(df=self.df[self.df['batch'].isin(batch_list)], dim=dim, batch_size=batch_size),
            output_types=(tf.float32, tf.float32),
            output_shapes=(self.shape, self.shape)
        ).prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
