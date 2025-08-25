import os
import pandas as pd
import boto3
import concurrent.futures
from tqdm import tqdm  # Optional for better progress tracking
from dotenv import load_dotenv
from utils import *

load_dotenv()
DATASET_IMAGES_LOCATION = os.environ.get("DATASET_IMAGES_LOCATION")
DATASET_CSV_PATH = os.environ.get("DATASET_CSV_PATH")
DATASET_IMAGES_PATH = os.environ.get("DATASET_IMAGES_PATH")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS"))

styles_file_name = "styles.csv"
images_file_name = "images.csv"

# Create S3 client
s3_client = boto3.client('s3')

def process_single_image(args):
    idx, path = args
    try:
        embedding = get_titan_multimodal_embedding(image_path=path, dimension=1024)["embedding"]
    except Exception as e:
        print(f"Error processing row {idx + 2} with path '{path}': {str(e)}")
        embedding = 0
    return idx, embedding

# Read the CSV file into a pandas DataFrame
dataset = pd.read_csv(f'{DATASET_CSV_PATH}/{styles_file_name}', on_bad_lines='skip')
if DATASET_IMAGES_LOCATION == "S3": # In case we want to serve the images from S3
    dataset['img_full_path'] = f"{DATASET_IMAGES_PATH}" + dataset['id'].astype(str) + ".jpg"
else: # In case we want to serve the images from their public location by Kaggle so we need to join with the images files to get the location of the image
    images_df = pd.read_csv(f'{DATASET_CSV_PATH}/{images_file_name}', on_bad_lines='skip')
    # Extract the ID from the filename by removing the .jpg suffix
    images_df['id'] = images_df['filename'].str.replace('.jpg', '')
    images_df['id'] = images_df['id'].astype(str)
    dataset['id'] = dataset['id'].astype(str)

    # Merge the link column from images_df into dataset
    dataset = pd.merge(
        dataset,
        images_df[['id', 'link']],  # Only keep the id and link columns
        on='id',
        how='left'  # Use left join to keep all rows from dataset
    )

    # Set the img_full_path to the link column
    dataset['img_full_path'] = dataset['link']
    dataset.drop('link', axis=1, inplace=True)

print(dataset)

# Print the dataframe head
print("DataFrame head:")
print(dataset.head())

# # Print basic info about the dataframe
print(f"\nDataFrame shape: {dataset.shape}")
print(f"Columns: {list(dataset.columns)}")

# Create a list of arguments for each task
tasks = list(enumerate(dataset['img_full_path']))
multimodal_embeddings_img = [None] * len(tasks)  # Pre-allocate the results list

with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    # Submit all tasks and create a dictionary to track them
    future_to_idx = {executor.submit(process_single_image, task): task[0] for task in tasks}

    # Process results as they complete
    for i, future in enumerate(tqdm(concurrent.futures.as_completed(future_to_idx), 
                                   total=len(tasks), 
                                   desc="Processing images")):
        idx, embedding = future.result()
        multimodal_embeddings_img[idx] = embedding

dataset = dataset.assign(embedding_img=multimodal_embeddings_img)
# Store dataset
dataset.to_csv('dataset.csv', index = False)