import streamlit as st
import boto3
import time
import os
from PIL import Image
import io
import base64
from dotenv import load_dotenv
from utils import *

load_dotenv()
S3_VECTOR_BUCKET_NAME = os.environ.get("S3_VECTOR_BUCKET_NAME")
S3_VECTOR_INDEX_NAME = os.environ.get("S3_VECTOR_INDEX_NAME")

GENDERS = [
    'All', 'Boys', 'Girls', 'Men', 'Unisex', 'Women'
]

CATEGORIES = [
    'All', 'Accessories', 'Apparel', 'Footwear', 'Free Items', 'Home', 'Personal Care', 'Sporting Goods'
]

# Define category to subcategory mapping
CATEGORY_SUBCATEGORY_MAPPING = {
    'All': ['All', 'Accessories', 'Apparel Set', 'Bags', 'Bath and Body', 'Beauty Accessories', 'Belts', 'Bottomwear', 'Cufflinks', 'Dress', 'Eyes', 'Eyewear', 'Flip Flops', 'Fragrance', 'Free Gifts', 'Gloves', 'Hair', 'Headwear', 'Home Furnishing', 'Innerwear', 'Jewellery', 'Lips', 'Loungewear and Nightwear', 'Makeup', 'Mufflers', 'Nails', 'Perfumes', 'Sandal', 'Saree', 'Scarves', 'Shoe Accessories', 'Shoes', 'Skin', 'Skin Care', 'Socks', 'Sports Accessories', 'Sports Equipment', 'Stoles', 'Ties', 'Topwear', 'Umbrellas', 'Vouchers', 'Wallets', 'Watches', 'Water Bottle', 'Wristbands'],
    'Accessories': ['All', 'Accessories', 'Bags', 'Belts', 'Cufflinks', 'Eyewear', 'Gloves', 'Headwear', 'Jewellery', 'Mufflers', 'Perfumes', 'Scarves', 'Shoe Accessories', 'Socks', 'Sports Accessories', 'Stoles', 'Ties', 'Umbrellas', 'Wallets', 'Watches', 'Water Bottle'],
    'Apparel': ['All', 'Apparel Set', 'Bottomwear', 'Dress', 'Innerwear', 'Loungewear and Nightwear', 'Saree', 'Socks', 'Topwear'],
    'Footwear': ['All', 'Flip Flops', 'Sandal', 'Shoes'],
    'Free Items': ['All', 'Free Gifts', 'Vouchers'],
    'Home': ['All', 'Home Furnishing'],
    'Personal Care': ['All', 'Bath and Body', 'Beauty Accessories', 'Eyes', 'Fragrance', 'Hair', 'Lips', 'Makeup', 'Nails', 'Perfumes', 'Skin', 'Skin Care'],
    'Sporting Goods': ['All', 'Sports Equipment', 'Wristbands']
}

ARTICLES = [
    'All', 'Accessory Gift Set', 'Baby Dolls', 'Backpacks', 'Bangle', 'Basketballs', 'Bath Robe', 'Beauty Accessory', 'Belts', 'Blazers', 'Body Lotion', 'Body Wash and Scrub', 'Booties', 'Boxers', 'Bra', 'Bracelet', 'Briefs', 'Camisoles', 'Capris', 'Caps', 'Casual Shoes', 'Churidar', 'Clothing Set',
    'Clutches', 'Compact', 'Concealer', 'Cufflinks', 'Cushion Covers', 'Deodorant', 'Dresses', 'Duffel Bag', 'Dupatta', 'Earrings', 'Eye Cream', 'Eyeshadow', 'Face Moisturisers', 'Face Scrub and Exfoliator', 'Face Serum and Gel', 'Face Wash and Cleanser', 'Flats', 'Flip Flops', 'Footballs', 'Formal Shoes',
    'Foundation and Primer', 'Fragrance Gift Set', 'Free Gifts', 'Gloves', 'Hair Accessory', 'Hair Colour', 'Handbags', 'Hat', 'Headband', 'Heels', 'Highlighter and Blush', 'Innerwear Vests', 'Ipad', 'Jackets', 'Jeans', 'Jeggings', 'Jewellery Set', 'Jumpsuit', 'Kajal and Eyeliner', 'Key chain', 'Kurta Sets',
    'Kurtas', 'Kurtis', 'Laptop Bag', 'Leggings', 'Lehenga Choli', 'Lip Care', 'Lip Gloss', 'Lip Liner', 'Lip Plumper', 'Lipstick', 'Lounge Pants', 'Lounge Shorts', 'Lounge Tshirts', 'Makeup Remover', 'Mascara', 'Mask and Peel', 'Mens Grooming Kit', 'Messenger Bag', 'Mobile Pouch', 'Mufflers', 'Nail Essentials',
    'Nail Polish', 'Necklace and Chains', 'Nehru Jackets', 'Night suits', 'Nightdress', 'Patiala', 'Pendant', 'Perfume and Body Mist', 'Rain Jacket', 'Rain Trousers', 'Ring', 'Robe', 'Rompers', 'Rucksacks', 'Salwar', 'Salwar and Dupatta', 'Sandals', 'Sarees', 'Scarves', 'Shapewear', 'Shirts', 'Shoe Accessories',
    'Shoe Laces', 'Shorts', 'Shrug', 'Skirts', 'Socks', 'Sports Sandals', 'Sports Shoes', 'Stockings', 'Stoles', 'Suits', 'Sunglasses', 'Sunscreen', 'Suspenders', 'Sweaters', 'Sweatshirts', 'Swimwear', 'Tablet Sleeve', 'Ties', 'Ties and Cufflinks', 'Tights', 'Toner', 'Tops', 'Track Pants', 'Tracksuits', 'Travel Accessory',
    'Trolley Bag', 'Trousers', 'Trunk', 'Tshirts', 'Tunics', 'Umbrellas', 'Waist Pouch', 'Waistcoat', 'Wallets', 'Watches', 'Water Bottle', 'Wristbands'
]

COLORES = [
    'All', 'Beige', 'Black', 'Blue', 'Bronze', 'Brown', 'Burgundy', 'Charcoal', 'Coffee Brown', 'Copper', 'Cream', 'Fluorescent Green', 'Gold', 'Green', 'Grey', 'Grey Melange', 'Khaki', 'Lavender', 'Lime Green', 'Magenta', 'Maroon', 'Mauve', 'Metallic', 'Multi', 'Mushroom Brown', 'Mustard', 'Navy Blue', 'Nude', 'Off White', 'Olive', 'Orange', 'Peach', 'Pink', 'Purple', 'Red', 'Rose', 'Rust', 'Sea Green', 'Silver', 'Skin', 'Steel', 'Tan', 'Taupe', 'Teal', 'Turquoise Blue', 'White', 'Yellow'
]

SEASONS = [
    'All', 'Fall', 'Spring', 'Summer', 'Winter'
]

YEARS = [
    'All', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019'
]

USAGES = [
    'All', 'Casual', 'Ethnic', 'Formal', 'Home', 'Party', 'Smart Casual', 'Sports', 'Travel'
]

def image_to_base64(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def main():
    st.set_page_config(
        page_title="S3 Vector Search",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 S3 Vector Search")
    st.markdown("Search for similar items in the catalog using natural language descriptions or by uploading an image...")
    
    # Initialize session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'query_time_ms' not in st.session_state:
        st.session_state.query_time_ms = 0
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")

        st.text_input(
            "Vector Bucket Name",
            key="vector_bucket_name",
            value=S3_VECTOR_BUCKET_NAME,
            help="Name of the S3 bucket containing vectors"
        )
        st.text_input(
            "Index Name",
            key="index_name",
            value=S3_VECTOR_INDEX_NAME,
            help="Name of the vector index"
        )
        st.slider(
            "Number of Results",
            min_value=1,
            max_value=30,
            key="num_results",
            value=3,
            help="Number of similar items to retrieve"
        )

        st.header("Filters")
        with st.expander("Metadata"):
            
            # Category filter
            category_filter = st.selectbox(
                "Category:",
                options=CATEGORIES,
                index=0
            )
            
            # Sub Category filter - dynamically updated based on category selection
            subcategory_options = CATEGORY_SUBCATEGORY_MAPPING.get(category_filter, ['All'])
            subcategory_filter = st.selectbox(
                "Sub Category:",
                options=subcategory_options,
                index=0
            )

            # Gender filter
            gender_filter = st.multiselect(
                "Gender:", 
                GENDERS, 
                default=["All"]
            )
            
            # Article Type filter
            articletype_filter = st.multiselect(
                "Article Type:", 
                ARTICLES, 
                default=["All"]
            )
            
            # Color filter
            color_filter = st.multiselect(
                "Color:",
                COLORES,
                default=["All"]
            )
            
            # Season filter
            season_filter = st.multiselect(
                "Season:",
                SEASONS,
                default=["All"]
            )
            
            # Year filter
            year_filter = st.multiselect(
                "Year:",
                YEARS,
                default=["All"]
            )
            
            # Usage filter
            usage_filter = st.multiselect(
                "Usage:",
                USAGES,
                default=["All"]
            )

        # Sidebar details (only shows if results exist)
        if st.session_state.search_results:
            st.header("Details")
            with st.expander("Vectors Data"):
                for idx, result in enumerate(st.session_state.search_results):
                    with st.expander(f"Vector #{idx + 1}"):
                        for key, value in result.items():
                            if key == 'metadata':
                                if isinstance(value, dict):
                                    for meta_key, meta_value in sorted(value.items()):
                                        st.markdown(f"**{meta_key}:** `{meta_value}`")
                            else:
                                st.markdown(f"**{key}:** `{value}`")
    
    # Main Search Interface
    st.header("Search Items")
    
    search_method = st.radio(
        "Choose search method:",
        ["Text Search", "Image Search"],
        horizontal=True,
        help="Select whether to search by text description or by uploading an image"
    )

    # Track previous search method
    if "prev_search_method" not in st.session_state:
        st.session_state.prev_search_method = search_method

    # If user switches between Text and Image search, clear previous results
    if search_method != st.session_state.prev_search_method:
        st.session_state.search_results = None
        st.session_state.query_time_ms = 0
        st.session_state.prev_search_method = search_method
    
    query_prompt = None
    uploaded_image = None
    search_button = False
    
    if search_method == "Text Search":
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
        
        if uploaded_image is not None:
            image = Image.open(uploaded_image)
            st.image(image, caption="Uploaded Image", width=300)
        
        search_button = st.button("🔍 Search", type="primary")
    
    # Helper function to display search results
    def display_search_results(results, query_time_ms):
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
                        item_name = element.get('metadata', {}).get('item_name_in_en_us', '')
                        # Support two options for the image path (to also support image ingestion using s3vectors-embed-cli which uses S3VECTORS-EMBED-SRC-LOCATION)
                        img_full_path = element['metadata'].get('img_full_path') or element['metadata'].get('S3VECTORS-EMBED-SRC-LOCATION', '')

                        if not item_name: 
                            item_id = img_full_path.split("/")[-1]
                            item_name = item_id
                        
                        # Create a card-like container
                        with st.container():
                            st.markdown(f"### {item_id}")
                            try:
                                if img_full_path.startswith('s3://'):
                                    image = get_image_from_s3(img_full_path)
                                    if image:
                                        st.markdown(
                                            f"<img src='data:image/png;base64,{image_to_base64(image)}' "
                                            f"style='width:300px; height:400px; border-radius:0.5rem; object-fit:cover; margin-bottom:1rem;'>",
                                            unsafe_allow_html=True
                                        )
                                    else:
                                        st.empty()
                                        st.markdown("🖼️ *Image not available*")
                                else:
                                    st.markdown(
                                        f"<img src='{img_full_path}' style='width:300px; height:400px; border-radius:0.5rem; object-fit:cover; margin-bottom:1rem;'>",
                                        unsafe_allow_html=True
                                    )
                            except Exception as e:
                                st.empty()
                                st.error(f"Error loading image: {str(e)}")
                            
                            st.markdown(f"**Item Name:** {item_name}")
                            st.markdown(f"**Score:** {distance:.4f}")
                            st.markdown("---")
        else:
            st.warning("No results found. Try a different search query/image/filter.")
    
    # Handle Search Button
    if search_button:
        if search_method == "Text Search" and not query_prompt:
            st.warning("Please enter a search query.")
            return
        elif search_method == "Image Search" and uploaded_image is None:
            st.warning("Please upload an image to search.")
            return
        
        with st.spinner("Searching for similar items..."):
            try:
                k = st.session_state.num_results
                vector_bucket_name = st.session_state.vector_bucket_name
                index_name = st.session_state.index_name

                results = None
                query_time_ms = 0

                # Build filter conditions based on provided filters
                filter_conditions = []
                
                if category_filter and category_filter != "All":
                    filter_conditions.append({"master_category": category_filter})
                
                if subcategory_filter and subcategory_filter != "All":
                    filter_conditions.append({"sub_category": subcategory_filter})
                
                if not "All" in gender_filter:
                    if len(gender_filter) == 1:
                        filter_conditions.append({"gender": gender_filter[0]})
                    elif len(gender_filter) > 1:
                        filter_conditions.append({"gender": {"$in": gender_filter}})
                
                if not "All" in articletype_filter:
                    if len(articletype_filter) == 1:
                        filter_conditions.append({"type": articletype_filter[0]})
                    elif len(articletype_filter) > 1:
                        filter_conditions.append({"type": {"$in": articletype_filter}})
                
                if not "All" in color_filter:
                    if len(color_filter) == 1:
                        filter_conditions.append({"base_color": color_filter[0]})
                    elif len(color_filter) > 1:
                        filter_conditions.append({"base_color": {"$in": color_filter}})
                
                if not "All" in season_filter:
                    if len(season_filter) == 1:
                        filter_conditions.append({"season": season_filter[0]})
                    elif len(season_filter) > 1:
                        filter_conditions.append({"season": {"$in": season_filter}})
                
                if not "All" in year_filter:
                    if len(year_filter) == 1:
                        filter_conditions.append({"year": year_filter[0]})
                    elif len(year_filter) > 1:
                        filter_conditions.append({"year": {"$in": year_filter}})
                
                if not "All" in usage_filter:
                    if len(usage_filter) == 1:
                        filter_conditions.append({"usage": usage_filter[0]})
                    elif len(usage_filter) > 1:
                        filter_conditions.append({"usage": {"$in": usage_filter}})
                
                # Build the final filter structure
                filters = None
                if len(filter_conditions) == 1:
                    # Single filter - use it directly
                    filters = filter_conditions[0]
                elif len(filter_conditions) > 1:
                    # Multiple filters - use 'and' operator
                    filters = {"$and": filter_conditions}

                print(f"Filter={filters}")
                
                if search_method == "Text Search":
                    query_dict = {"text": query_prompt}
                    results, query_time_ms = search_similar_items(query_dict, k, vector_bucket_name, index_name, filters)
                else: # Image Search
                    # Save uploaded image temporarily
                    temp_image_path = f"temp_uploaded_image.{uploaded_image.name.split('.')[-1]}"
                    with open(temp_image_path, "wb") as f:
                        f.write(uploaded_image.getbuffer())
                    
                    query_dict = {"image_path": temp_image_path}
                    results, query_time_ms = search_similar_items(query_dict, k, vector_bucket_name, index_name, filters)
                    
                    # Clean up temporary file
                    os.remove(temp_image_path)
                
                # Store in session state & rerun for sidebar refresh
                st.session_state.search_results = results
                st.session_state.query_time_ms = query_time_ms
                st.rerun()

            except Exception as e:
                st.error(f"Error during search: {str(e)}")
                st.info("Please check your AWS credentials and configuration.")
                st.session_state.search_results = None

    # After rerun, show results
    if st.session_state.search_results is not None:
        query_time_ms = st.session_state.get("query_time_ms", 0)
        display_search_results(st.session_state.search_results, query_time_ms)


if __name__ == "__main__":
    main()
