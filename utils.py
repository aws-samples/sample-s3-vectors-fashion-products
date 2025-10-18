import os
import boto3
import time
from pathlib import Path
import json
import base64
from PIL import Image
from io import BytesIO
from typing import List, Union 
import requests
from urllib.parse import urlparse

session = boto3.session.Session()
region = session.region_name

# Define bedrock client
bedrock_client = boto3.client(
    "bedrock-runtime", 
    region, 
    endpoint_url=f"https://bedrock-runtime.{region}.amazonaws.com"
)

s3vectors = boto3.client("s3vectors", region_name=region)

# Amazon titan-embed-image-v1 modelid
multimodal_embed_model = 'amazon.titan-embed-image-v1'

# Cohere embed-english-v3 modelid
cohere_embed_model = 'cohere.embed-english-v3'

def get_titan_multimodal_embedding(
    query: dict,
    model_id: str=multimodal_embed_model,
    dimension: int=1024, # 1,024 (default), 384, 256
):
    """
    Generate embeddings using Titan Multimodal.
    
    Args:
        query (dict): Dictionary containing 'text' or 'image_path' keys
                     Example: {'text': 'red shirt'} or {'image_path': 'path/to/image.jpg'}
        model_id (str): The Titan model ID to use
        dimension (int): The embedding dimenstion to use
    
    Returns:
        list: The embedding vector
    """

    payload_body = {}
    embedding_config = {
        "embeddingConfig": { 
             "outputEmbeddingLength": dimension
         }
    }

    # Extract text and image_path from query
    text = query.get('text')
    image_path = query.get('image_path')

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
                base64_image = base64.b64encode(image_file.read()).decode('utf8')
            payload_body["inputImage"] = base64_image
    if text:
        payload_body["inputText"] = text

    assert payload_body, "please provide either an image and/or a text description"

    response = bedrock_client.invoke_model(
        body=json.dumps({**payload_body, **embedding_config}), 
        modelId=model_id,
        accept="application/json", 
        contentType="application/json"
    )

    response_body = json.loads(response.get("body").read())
    return response_body.get('embedding', [])


def get_cohere_embedding(
    query: dict,
    model_id: str = cohere_embed_model
):
    """
    Generate embeddings using Cohere embed-english model.
    
    Args:
        query (dict): Dictionary containing 'text' or 'image_path' keys
                     Example: {'text': 'red shirt'} or {'image_path': 'path/to/image.jpg'}
        model_id (str): The Cohere model ID to use
    
    Returns:
        list: The embedding vector
    """
    image_mime_type = "image/jpg"
    payload_body = {}
    
    # Extract text and image_path from query
    text = query.get('text')
    image_path = query.get('image_path')

    if image_path: # Image embeddings
        if image_path.startswith('s3'):
            s3 = boto3.client('s3')
            bucket_name, key = image_path.replace("s3://", "").split("/", 1)
            obj = s3.get_object(Bucket=bucket_name, Key=key)
            # Read the object's body
            body = obj['Body'].read()
            # Encode the body in base64
            base64_image = base64.b64encode(body).decode('utf-8')
            payload_body["images"] = [f"data:{image_mime_type};base64,{base64_image}"]
        elif image_path.startswith(('http://', 'https://')):
            # Handle URLs
            try:
                response = requests.get(image_path, stream=True)
                response.raise_for_status()  # Raise an exception for 4XX/5XX responses
                # Read the content and encode in base64
                image_content = response.content
                base64_image = base64.b64encode(image_content).decode('utf-8')
                payload_body["images"] = [f"data:{image_mime_type};base64,{base64_image}"]
            except requests.exceptions.RequestException as e:
                raise Exception(f"Error downloading image from URL: {e}")
        else:   
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf8')
                payload_body["images"] = [f"data:{image_mime_type};base64,{base64_image}"]
        
        payload_body["input_type"] = "image"
        payload_body["embedding_types"] = ["float"]
    elif text: # Text embeddings
        payload_body = {
            "texts": [text],
            "input_type": "search_document",
            "embedding_types": ["float"]
        }
    else:
        raise ValueError("Query must contain either 'text' or 'image_path' key")

    response = bedrock_client.invoke_model(
        body=json.dumps(payload_body), 
        modelId=model_id,
        accept="application/json", 
        contentType="application/json"
    )

    response_body = json.loads(response.get("body").read())

    # Cohere returns embeddings in structured format
    embeddings = response_body.get('embeddings', {})
    if 'float' in embeddings:
        return embeddings['float'][0]  # First image's float embedding
    else:
        # Fallback for other response formats
        return response_body.get('embeddings', [])[0] if response_body.get('embeddings') else []

def get_image_from_s3(image_full_path: str):
    """Download an image from S3 and return a PIL Image."""
    if image_full_path.startswith('s3'):
        s3 = boto3.client("s3")
        parsed = urlparse(image_full_path)
        bucket, key = parsed.netloc, parsed.path.lstrip('/')
        
        obj = s3.get_object(Bucket=bucket, Key=key)
        return Image.open(obj['Body'])
    return None

def search_similar_items(query, k, vector_bucket_name, index_name, query_filter=None):
    """
    Search for similar items using either a text query or an image query.
    
    Args:
        query (dict): Query dict with 'text'/'image_path' keys.
        k (int): Number of top similar items to return.
        vector_bucket_name (str): The S3 vector bucket name.
        index_name (str): The index name for vector search.
        query_filter (dict): Query filters.
    
    Returns:
        tuple: (list of similar vectors, query_time_ms)
    """

    query_emb = get_titan_multimodal_embedding(query)
    
    # Build query parameters
    query_params = {
        "vectorBucketName": vector_bucket_name,
        "indexName": index_name,
        "queryVector": {"float32": query_emb}, 
        "topK": k, 
        "returnDistance": True,
        "returnMetadata": True
    }
    
    # Add filter if any filters are specified
    if query_filter:
        query_params["filter"] = query_filter
    
    start_time = time.time()
    response = s3vectors.query_vectors(**query_params)
    end_time = time.time()
    query_time_ms = (end_time - start_time) * 1000

    return response["vectors"], query_time_ms
