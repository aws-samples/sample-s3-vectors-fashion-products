import boto3
import pandas as pd
import ast
import time
import os
from dotenv import load_dotenv

load_dotenv()
S3_VECTOR_BUCKET_NAME = os.environ.get("S3_VECTOR_BUCKET_NAME")
S3_VECTOR_INDEX_NAME = os.environ.get("S3_VECTOR_INDEX_NAME")
dataset_filename = 'dataset.csv'
NUM_VECTORS_PER_PUT = 100  # batch size for put_vectors
NUM_STATUS_PRINT = 200     # after how many vectors to print status

session = boto3.session.Session()
region = session.region_name
s3vectors = session.client("s3vectors", region_name=region)

try:
    s3vectors.create_vector_bucket(vectorBucketName=S3_VECTOR_BUCKET_NAME)
except s3vectors.exceptions.ConflictException:
    pass  

try:
    s3vectors.create_index(
        vectorBucketName=S3_VECTOR_BUCKET_NAME,
        indexName=S3_VECTOR_INDEX_NAME,
        dataType='float32',
        dimension=1024,
        distanceMetric='cosine',
    )
except s3vectors.exceptions.ConflictException:
    pass  

# read the dataset from csv
dataset = pd.read_csv(dataset_filename)

start_time = time.time()
print("Starting ingesting...")

# Counter for ingested vectors
ingested_count = 0
total_rows = len(dataset)
batch_vectors = []

def create_vector_object(row):
    """Helper function to create a vector object from a row"""
    embedding = ast.literal_eval(row['embedding_img'])

    # Skip rows where embedding is just 0 (not a valid array)
    if embedding == 0:
        return None

    return {
        "key": str(row['id']),
        "data": {"float32": embedding},
        "metadata": {
            "gender": str(row['gender']) if pd.notna(row['gender']) else "unknown",
            "master_category": str(row['masterCategory']) if pd.notna(row['masterCategory']) else "unknown",
            "sub_category": str(row['subCategory']) if pd.notna(row['subCategory']) else "unknown",
            "type": str(row['articleType']) if pd.notna(row['articleType']) else "unknown",
            "base_color": str(row['baseColour']) if pd.notna(row['baseColour']) else "unknown",
            "season": str(row['season']) if pd.notna(row['season']) else "unknown",
            "year": str(row['year']) if pd.notna(row['year']) else "unknown",
            "usage": str(row['usage']) if pd.notna(row['usage']) else "unknown",
            "item_name_in_en_us": str(row['productDisplayName']) if pd.notna(row['productDisplayName']) else "unknown",
            "img_full_path": str(row['img_full_path']) if pd.notna(row['img_full_path']) else "unknown"
        }
    }

def process_batch(batch):
    """Process a batch of vectors"""
    global ingested_count

    if not batch:  # Skip empty batches
        return

    try:
        response = s3vectors.put_vectors(
            vectorBucketName=S3_VECTOR_BUCKET_NAME,   
            indexName=S3_VECTOR_INDEX_NAME,
            vectors=batch
        )

        # Increment the counter for successful ingestion
        ingested_count += len(batch)

        # Print status every NUM_STATUS_PRINT ingested vectors
        if ingested_count % NUM_STATUS_PRINT < NUM_VECTORS_PER_PUT:
            current_time = time.time()
            elapsed_time_minutes = (current_time - start_time) / 60
            progress_percentage = ingested_count / total_rows * 100
            print(f"Progress: {ingested_count} vectors ingested ({progress_percentage:.2f}%) - Time elapsed: {elapsed_time_minutes:.2f} minutes")

    except Exception as e:
        # If batch fails, try one by one to identify problematic vectors
        print(f"Batch ingestion failed: {str(e)}. Trying one by one...")
        for vector in batch:
            try:
                s3vectors.put_vectors(
                    vectorBucketName=S3_VECTOR_BUCKET_NAME,   
                    indexName=S3_VECTOR_INDEX_NAME,
                    vectors=[vector]
                )
                ingested_count += 1
            except Exception as e:
                print(f"Error ingesting a vector: {str(e)}")

# Process the dataset in batches
for index, row in dataset.iterrows():
    vector_obj = create_vector_object(row)

    if vector_obj is None:
        print(f"Skipping row {index} - no embedding available")
        continue

    batch_vectors.append(vector_obj)

    # When we reach the batch size or the end of the dataset, process the batch
    if len(batch_vectors) >= NUM_VECTORS_PER_PUT or index == total_rows - 1:
        process_batch(batch_vectors)
        batch_vectors = []  # Reset the batch

end_time = time.time()
elapsed_time_seconds = end_time - start_time
elapsed_time_minutes = elapsed_time_seconds / 60

print(f"Total time taken: {elapsed_time_minutes:.2f} minutes")
print(f"Total vectors ingested: {ingested_count}")