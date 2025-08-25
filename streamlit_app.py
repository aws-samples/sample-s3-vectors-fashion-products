import streamlit as st
import boto3
import time
import os
from utils import get_titan_multimodal_embedding
from PIL import Image
import io
import base64
from dotenv import load_dotenv
from utils import *

load_dotenv()
DATASET_IMAGES_LOCATION = os.environ.get("DATASET_IMAGES_LOCATION")
S3_VECTOR_BUCKET_NAME = os.environ.get("S3_VECTOR_BUCKET_NAME")
S3_VECTOR_INDEX_NAME = os.environ.get("S3_VECTOR_INDEX_NAME")

def main():
    st.set_page_config(
        page_title="S3 Vector Search App",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 S3 Vector Search App")
    st.markdown("Search for similar items in the catalog using natural language descriptions or by uploading an image...")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        vector_bucket_name = st.text_input(
            "Vector Bucket Name", 
            value=S3_VECTOR_BUCKET_NAME,
            help="Name of the S3 bucket containing vectors"
        )
        index_name = st.text_input(
            "Index Name", 
            value=S3_VECTOR_INDEX_NAME,
            help="Name of the vector index"
        )
        k = st.slider(
            "Number of Results", 
            min_value=1, 
            max_value=30, 
            value=3,
            help="Number of similar items to retrieve"
        )
    
    # Main search interface
    st.header("Search Items")
    
    # Search method selection
    search_method = st.radio(
        "Choose search method:",
        ["Text Search", "Image Search"],
        horizontal=True,
        help="Select whether to search by text description or by uploading an image"
    )
    
    query_prompt = None
    uploaded_image = None
    search_button = False
    
    if search_method == "Text Search":
        # Use form for text search to enable Enter key functionality
        with st.form(key="text_search_form"):
            query_prompt = st.text_input(
                "Enter your search query:",
                placeholder="e.g., red dress, blue jeans, ankle boots, floral t-shirt, leather handbag...",
                help="Describe the item you're looking for (press Enter to search)"
            )
            search_button = st.form_submit_button("🔍 Search", type="primary")
    else:
        uploaded_image = st.file_uploader(
            "Upload an image to search:",
            type=['png', 'jpg', 'jpeg'],
            help="Upload an image to find similar items"
        )
        
        # Display uploaded image preview
        if uploaded_image is not None:
            image = Image.open(uploaded_image)
            st.image(image, caption="Uploaded Image", width=300)
        
        search_button = st.button("🔍 Search", type="primary")
    
    # Helper function to display search results
    def display_search_results(results, query_time_ms):
        """Display search results in a consistent format"""
        if results:
            st.success(f"Found {len(results)} similar items! (Query time: {query_time_ms:.2f} ms)")
            
            # Sort results by distance score (lowest to highest - lower is more similar)
            sorted_results = sorted(results, key=lambda x: x['distance'], reverse=False)
            
            # Display results in rows of 3 columns
            for row_start in range(0, len(sorted_results), 3):
                cols = st.columns(3)
                
                # Get up to 3 items for this row
                row_items = sorted_results[row_start:row_start + 3]
                
                for col_idx, element in enumerate(row_items):
                    with cols[col_idx]:
                        item_id = element['key']
                        distance = element['distance']
                        item_name = element['metadata']['item_name_in_en_us']
                        img_full_path = element['metadata']['img_full_path']
                        
                        # Create a card-like container
                        with st.container():
                            st.markdown(f"### {item_id}")
                            
                            # Try to load and display image with fixed size
                            try:
                                if DATASET_IMAGES_LOCATION == "S3":
                                    image = get_image_from_s3(img_full_path)
                                    if image:
                                        st.image(image=image, width=300)
                                    else:
                                        st.empty()
                                        st.markdown("🖼️ *Image not available*")
                                else:
                                    st.image(image=img_full_path, width=300)
                            except Exception as e:
                                st.empty()
                                st.error(f"Error loading image: {str(e)}")
                            
                            # Display item details
                            st.markdown(f"**Item Name:** {item_name}")
                            st.markdown(f"**Score:** {distance:.4f}")
                            
                            # Add some spacing between rows
                            st.markdown("---")
        else:
            st.warning("No results found. Try a different search query/image.")

    # Handle search based on method
    if search_button:
        # Validate input based on search method
        if search_method == "Text Search" and not query_prompt:
            st.warning("Please enter a search query.")
            return
        elif search_method == "Image Search" and uploaded_image is None:
            st.warning("Please upload an image to search.")
            return
        
        with st.spinner("Searching for similar items..."):
            try:
                results = None
                query_time_ms = 0
                
                if search_method == "Text Search":
                    results, query_time_ms = search_similar_items_from_text(query_prompt, k, vector_bucket_name, index_name)
                else:  # Image Search
                    # Save uploaded image temporarily
                    temp_image_path = f"temp_uploaded_image.{uploaded_image.name.split('.')[-1]}"
                    with open(temp_image_path, "wb") as f:
                        f.write(uploaded_image.getbuffer())
                    
                    results, query_time_ms = search_similar_items_from_image(temp_image_path, k, vector_bucket_name, index_name)
                    
                    # Clean up temporary file
                    os.remove(temp_image_path)
                
                # Display results using the helper function
                display_search_results(results, query_time_ms)
                
            except Exception as e:
                st.error(f"Error during search: {str(e)}")
                st.info("Please check your AWS credentials and configuration.")

if __name__ == "__main__":
    main()