#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p ./data/images

# Run the Streamlit app
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0