import os
import boto3
import time
from pathlib import Path
import json
import base64
from PIL import Image
from io import BytesIO
from typing import List, Union 
from sagemaker.s3 import S3Downloader as s3down
import requests

session = boto3.session.Session()
region = session.region_name

# Define bedrock client
bedrock_client = boto3.client(
    "bedrock-runtime", 
    region, 
    endpoint_url=f"https://bedrock-runtime.{region}.amazonaws.com"
)

s3vectors = boto3.client("s3vectors", region_name=region)

# Select Amazon titan-embed-image-v1 as Embedding model for multimodal indexing
multimodal_embed_model = 'amazon.titan-embed-image-v1'

"""Function to generate Embeddings from image or text"""
def get_titan_multimodal_embedding(
    image_path:str=None,  # maximum 2048 x 2048 pixels
    description:str=None, # English only and max input tokens 128
    dimension:int=1024,   # 1,024 (default), 384, 256
    model_id:str=multimodal_embed_model
):
    payload_body = {}
    embedding_config = {
        "embeddingConfig": { 
             "outputEmbeddingLength": dimension
         }
    }
    # You can specify either text or image or both
    if image_path:
        if image_path.startswith('s3'):
            s3 = boto3.client('s3')
            bucket_name, key = image_path.replace("s3://", "").split("/", 1)
            obj = s3.get_object(Bucket=bucket_name, Key=key)
            # Read the object's body
            body = obj['Body'].read()
            # Encode the body in base64
            base64_image = base64.b64encode(body).decode('utf-8')
            payload_body["inputImage"] = base64_image
        elif image_path.startswith(('http://', 'https://')):
            # Handle URLs
            try:
                response = requests.get(image_path, stream=True)
                response.raise_for_status()  # Raise an exception for 4XX/5XX responses
                # Read the content and encode in base64
                image_content = response.content
                base64_image = base64.b64encode(image_content).decode('utf-8')
                payload_body["inputImage"] = base64_image
            except requests.exceptions.RequestException as e:
                raise Exception(f"Error downloading image from URL: {e}")
        else:   
            with open(image_path, "rb") as image_file:
                input_image = base64.b64encode(image_file.read()).decode('utf8')
            payload_body["inputImage"] = input_image
    if description:
        payload_body["inputText"] = description

    assert payload_body, "please provide either an image and/or a text description"
    # print("\n".join(payload_body.keys()))

    response = bedrock_client.invoke_model(
        body=json.dumps({**payload_body, **embedding_config}), 
        modelId=model_id,
        accept="application/json", 
        contentType="application/json"
    )

    return json.loads(response.get("body").read())

def get_image_from_s3(image_full_path):
    """Download and return image from S3 path"""
    if image_full_path.startswith('s3'):
        # Download and store images locally 
        local_data_root = './data/images'
        local_file_name = image_full_path.split('/')[-1]
        s3down.download(image_full_path, local_data_root)
        local_image_path = f"{local_data_root}/{local_file_name}"
        img = Image.open(local_image_path)
        return img
    return None

def search_similar_items_from_text(query_prompt, k, vector_bucket_name, index_name):
    """Search for similar items using text query"""
    
    # Get embedding for the query
    query_emb = get_titan_multimodal_embedding(description=query_prompt, dimension=1024)["embedding"]
    
    # Measure only the s3vectors.query_vectors API call time
    start_time = time.time()
    response = s3vectors.query_vectors(
        vectorBucketName=vector_bucket_name,
        indexName=index_name,
        queryVector={"float32": query_emb}, 
        topK=k, 
        returnDistance=True,
        returnMetadata=True
    )
    end_time = time.time()
    query_time_ms = (end_time - start_time) * 1000
    
    return response["vectors"], query_time_ms

def search_similar_items_from_image(image_path, k, vector_bucket_name, index_name):
    """Search for similar items using image query"""
    
    # Get embedding for the query image
    query_emb = get_titan_multimodal_embedding(image_path=image_path, dimension=1024)["embedding"]
    
    # Measure only the s3vectors.query_vectors API call time
    start_time = time.time()
    response = s3vectors.query_vectors(
        vectorBucketName=vector_bucket_name,
        indexName=index_name,
        queryVector={"float32": query_emb}, 
        topK=k, 
        returnDistance=True,
        returnMetadata=True
    )
    end_time = time.time()
    query_time_ms = (end_time - start_time) * 1000
    
    return response["vectors"], query_time_ms
