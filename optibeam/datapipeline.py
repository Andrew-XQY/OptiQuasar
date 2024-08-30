import tensorflow as tf
import numpy as np
import ast

from PIL import Image
from abc import ABC, abstractmethod
from typing import *
from .utils import get_all_file_paths
from .database import Database

class DataLoader(ABC):
    @abstractmethod
    def regression(self, *args, **kwargs) -> None:
        pass
    
    @abstractmethod
    def reconstruction(self, *args, **kwargs) -> None:
        pass
    
class DataLoaderTF(DataLoader):
    def __init__(self, dirs=None) -> None:
        self.dirs = dirs
        self.batch_size = None
        
    def __len__(self):
        return len(self.dirs) // self.batch_size if self.batch_size else len(self.dirs)
    
    def get_directory(self):
        return self.dirs
        
    def dirs_from_sql(self, DB: Database, sql_query: str=None) -> None:
        self.dirs = DB.sql_select(sql_query)
    
    def dirs_from_root(self, root_dir, types=None) -> None:
        self.dirs = get_all_file_paths(root_dir, types=types)
        
    def fast_preprocess(self, image, image_size) -> tf.Tensor:
        """_summary_
        using only tf native functions to preprocess image
        
        Args:
            image (_type_): _description_
            image_size (_type_): _description_

        Returns:
            tf.Tensor
        """
        image = tf.image.resize(image, image_size)
        image = tf.cast(image, tf.float32) / 255.0
        return image
    
    @tf.function
    def preprocess_image(self, path, preprocessing_funcs):
        # Load the image file
        image = tf.io.read_file(path)
        image = tf.image.decode_jpeg(image, channels=3)  # Adjust 'decode_jpeg' based on your image file format

        # Apply each preprocessing function passed in the list
        if preprocessing_funcs:
            for func in preprocessing_funcs:
                if callable(func):
                    image = func(image)
                else:
                    tf.print("Warning: Non-callable preprocessing function skipped.")
        return image
    
    def regression(self, batch_size, preprocessing_funcs: list[Iterable]=None, buffer_size=1000) -> tf.data.Dataset:
        pass

    def reconstruction(self, batch_size, preprocessing_funcs: list[Iterable]=None, buffer_size=1000) -> tf.data.Dataset:
        """
        Create a TensorFlow tf.data.Dataset for loading and preprocessing images.
        
        Args:
            directories: List of directories containing images
            batch_size: Batch size
            image_size: Tuple of image dimensions (height, width)
            preprocessing_funcs: List of preprocessing closure functions to apply to each image
            buffer_size: Number of images to prefetch
        
        returns:
            dataset: TensorFlow Dataset object

        """
        # Create a dataset from file paths
        path_ds = tf.data.Dataset.from_tensor_slices(self.dirs)
        
        # Map the load_and_preprocess_image function to each file path
        image_ds = path_ds.map(self.load_and_preprocess_image, num_parallel_calls=tf.data.AUTOTUNE)

        # Shuffle, batch, and prefetch the dataset
        dataset = image_ds.shuffle(buffer_size=buffer_size)
        dataset = dataset.batch(batch_size)
        dataset = dataset.prefetch(buffer_size=tf.data.AUTOTUNE)

        return dataset


# ----------------- old data pipeline ----------------- #
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
