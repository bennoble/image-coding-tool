import streamlit as st
import pandas as pd
import os
from PIL import Image
import json
from datetime import datetime
import requests
import zipfile
import io

# Configure the page
st.set_page_config(
    page_title="Image Coding Tool",
    page_icon="🖼️",
    layout="wide"
)

# File paths - these will be loaded from cloud storage
PROGRESS_FILE = 'coding_progress.json'
OUTPUT_FILE = 'ra-shingle-complete.csv'

# Category definitions
CATEGORIES = {
    0: "Infographic",
    1: "Solo",
    2: "Small group",
    3: "Crowd"
}

# Context categories (mutually exclusive)
CONTEXT_CATEGORIES = {
    1: "Newscast",
    2: "Congress"
}

@st.cache_data
def load_data_from_cloud():
    """Load CSV and download ZIP file info (but not extract all images)"""
    try:
        # Get URLs from Streamlit secrets
        csv_url = st.secrets["data_files"]["csv_url"]
        images_zip_url = st.secrets["data_files"]["images_zip_url"]
        
        # Download CSV
        csv_response = requests.get(csv_url)
        csv_response.raise_for_status()
        
        # Create DataFrame from downloaded CSV
        metadata_df = pd.read_csv(io.StringIO(csv_response.text))
        
        # Download ZIP file but don't extract yet - just store the raw data
        zip_response = requests.get(images_zip_url)
        zip_response.raise_for_status()
        
        # Store ZIP data for on-demand extraction
        zip_data = zip_response.content
        
        return metadata_df, zip_data
        
    except Exception as e:
        st.error(f"Error loading data from cloud storage: {e}")
        st.info("Make sure your Streamlit secrets are configured correctly.")
        return None, None

@st.cache_data
def load_single_image(zip_data, filename):
    """Load a single image from ZIP data on-demand"""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_file:
            # Find the file in the ZIP
            for file_info in zip_file.filelist:
                if os.path.basename(file_info.filename) == filename:
                    with zip_file.open(file_info) as image_file:
                        return Image.open(io.BytesIO(image_file.read()))
        return None
    except Exception as e:
        st.error(f"Error loading image {filename}: {e}")
        return None

def save_to_cloud_csv(metadata_df):
    """Save the updated CSV back to cloud storage"""
    try:
        # For now, we'll save locally and provide download link
        # Cloud storage writing requires additional authentication
        csv_buffer = io.StringIO()
        metadata_df.to_csv(csv_buffer, index=False)
        
        return csv_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error preparing CSV for download: {e}")
        return None

def load_metadata():
    """Load the metadata from cloud storage"""
    return None  # This function is now handled by load_data_from_cloud()

def load_progress():
    """Load existing progress from JSON file"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_progress(progress_data):
    """Save progress to JSON file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress_data, f, indent=2)

def save_final_results(metadata_df, coded_labels, context_labels):
    """Save final results to CSV for download"""
    metadata_df['group_labels'] = coded_labels
    metadata_df['context_labels'] = context_labels
    metadata_df['coding_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare CSV for download
    csv_data = save_to_cloud_csv(metadata_df)
    if csv_data:
        st.download_button(
            label="💾 Download Completed Results CSV",
            data=csv_data,
            file_name=OUTPUT_FILE,
            mime="text/csv",
            type="primary"
        )
        st.success("Results prepared for download! Click the button above to save your completed coding.")
        st.info("📧 Please email this completed CSV file back to the research team.")

def main():
    st.title("📸 Image Coding Tool")
    st.markdown("### Instructions")
    st.markdown("""
    **Please categorize each image based on the number of people visible:**
    - **0 = Infographic**: No human figures visible or 50%+ text.
    - **1 = Solo**: One person is focus.
    - **2 = Small group**: Multiple people all presented as equal.  
    - **3 = Crowd**: No focal person, focal person attempting to appear as the central person in a crowd.
    
    **Additionally, if applicable, mark the context:**
    - **Newscast**: Image appears to be from a television news broadcast (not CSPAN)
    - **Congress**: Image appears to be taken in a congressional setting or CSPAN
    *(These are mutually exclusive - select only one if applicable)*
    
    If you're unsure, make a selection, but note the filename and your confusion in a separate document.
    """)
    
    # Load data from cloud storage
    with st.spinner("Loading data from cloud storage..."):
        metadata_df, zip_data = load_data_from_cloud()
    
    if metadata_df is None or zip_data is None:
        st.error("Failed to load data. Please check your configuration.")
        return
    
    progress_data = load_progress()
    
    # Initialize session state
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'coded_labels' not in st.session_state:
        st.session_state.coded_labels = [None] * len(metadata_df)
        # Load any existing progress
        for idx, data in progress_data.items():
            if idx.isdigit() and int(idx) < len(metadata_df):
                if isinstance(data, dict):
                    # New format with group_label and context
                    st.session_state.coded_labels[int(idx)] = data.get('group_label')
                else:
                    # Old format (just the label)
                    st.session_state.coded_labels[int(idx)] = data
    if 'context_labels' not in st.session_state:
        st.session_state.context_labels = [None] * len(metadata_df)
        # Load any existing context progress
        for idx, data in progress_data.items():
            if idx.isdigit() and int(idx) < len(metadata_df):
                if isinstance(data, dict) and 'context' in data:
                    st.session_state.context_labels[int(idx)] = data['context']
    
    # Auto-jump to first uncoded image on app start
    if 'has_auto_jumped' not in st.session_state:
        st.session_state.has_auto_jumped = True
        # Find first uncoded image
        for i, label in enumerate(st.session_state.coded_labels):
            if label is None:
                st.session_state.current_index = i
                break
    
    total_images = len(metadata_df)
    current_idx = st.session_state.current_index
    
    # Progress display
    coded_count = sum(1 for label in st.session_state.coded_labels if label is not None)
    progress_percent = coded_count / total_images
    
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.progress(progress_percent)
        st.write(f"Progress: {coded_count}/{total_images} images coded ({progress_percent:.1%})")
    
    with col2:
        if st.button("⬅️ Previous", disabled=(current_idx == 0)):
            st.session_state.current_index = max(0, current_idx - 1)
            st.rerun()
    
    with col3:
        if st.button("➡️ Next", disabled=(current_idx >= total_images - 1)):
            st.session_state.current_index = min(total_images - 1, current_idx + 1)
            st.rerun()
    
    # Jump to specific image
    with st.expander("Jump to specific image"):
        col1, col2 = st.columns(2)
        with col1:
            jump_to = st.number_input("Go to image number:", min_value=1, max_value=total_images, value=current_idx + 1)
            if st.button("Go"):
                st.session_state.current_index = jump_to - 1
                st.rerun()
        with col2:
            if st.button("🎯 Go to next uncoded"):
                # Find next uncoded image
                next_uncoded = None
                for i in range(current_idx + 1, total_images):
                    if st.session_state.coded_labels[i] is None:
                        next_uncoded = i
                        break
                if next_uncoded is not None:
                    st.session_state.current_index = next_uncoded
                    st.rerun()
                else:
                    st.info("No uncoded images found after current position")
    
    st.markdown("---")
    
    # Current image display
    if current_idx < total_images:
        row = metadata_df.iloc[current_idx]
        filename = row['filename']
        
        st.subheader(f"Image {current_idx + 1} of {total_images}")
        st.write(f"**Filename:** {os.path.basename(filename)}")
        
        # Display image
        filename_only = os.path.basename(filename)
        img = load_single_image(zip_data, filename_only)
        
        if img is not None:
            try:
                # Display image in a reasonable size
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.image(img, use_container_width=True)
                
                # Coding buttons
                st.markdown("### Select the appropriate category:")
                
                # Create a row of buttons
                cols = st.columns(4)
                current_label = st.session_state.coded_labels[current_idx]
                
                for i, (code, description) in enumerate(CATEGORIES.items()):
                    with cols[i]:
                        button_type = "primary" if current_label == code else "secondary"
                        if st.button(f"{code}: {description}", key=f"btn_{code}", type=button_type):
                            st.session_state.coded_labels[current_idx] = code
                            
                            # Save progress
                            progress_data[str(current_idx)] = {
                                'group_label': code,
                                'context': st.session_state.context_labels[current_idx]
                            }
                            save_progress(progress_data)
                            
                            st.rerun()
                
                # Show current selection
                if current_label is not None:
                    st.success(f"✅ Current selection: {current_label} - {CATEGORIES[current_label]}")
                else:
                    st.info("⏳ No category selected yet")
                
                # Context categories section
                st.markdown("### Context (if applicable):")
                current_context = st.session_state.context_labels[current_idx]
                
                # Context toggle buttons
                context_cols = st.columns(3)
                
                with context_cols[0]:
                    newscast_active = current_context == 1
                    if st.button("📺 Newscast", key="newscast_btn", type="primary" if newscast_active else "secondary"):
                        if newscast_active:
                            st.session_state.context_labels[current_idx] = None
                        else:
                            st.session_state.context_labels[current_idx] = 1
                        
                        # Save progress
                        progress_data[str(current_idx)] = {
                            'group_label': st.session_state.coded_labels[current_idx],
                            'context': st.session_state.context_labels[current_idx]
                        }
                        save_progress(progress_data)
                        st.rerun()
                
                with context_cols[1]:
                    congress_active = current_context == 2
                    if st.button("🏛️ Congress", key="congress_btn", type="primary" if congress_active else "secondary"):
                        if congress_active:
                            st.session_state.context_labels[current_idx] = None
                        else:
                            st.session_state.context_labels[current_idx] = 2
                        
                        # Save progress
                        progress_data[str(current_idx)] = {
                            'group_label': st.session_state.coded_labels[current_idx],
                            'context': st.session_state.context_labels[current_idx]
                        }
                        save_progress(progress_data)
                        st.rerun()
                
                with context_cols[2]:
                    if current_context is not None:
                        st.info(f"✅ Context: {CONTEXT_CATEGORIES[current_context]}")
                    else:
                        st.info("No context selected")
                
                # Auto-advance button (manual control) - moved below context
                if current_label is not None:
                    # Create columns to right-align the button
                    nav_cols = st.columns([3, 1])
                    with nav_cols[1]:  # Right column
                        if st.button("➡️ Next Image", key="advance_btn", type="primary"):
                            if current_idx < total_images - 1:
                                st.session_state.current_index = current_idx + 1
                            st.rerun()
                
                # Clear selection button
                if current_label is not None or current_context is not None:
                    if st.button("🗑️ Clear all selections", key="clear_btn"):
                        st.session_state.coded_labels[current_idx] = None
                        st.session_state.context_labels[current_idx] = None
                        if str(current_idx) in progress_data:
                            del progress_data[str(current_idx)]
                        save_progress(progress_data)
                        st.rerun()
                
            except Exception as e:
                st.error(f"Error displaying image: {e}")
        else:
            st.error(f"Image not found: {filename_only}")
    
    # Summary and export
    st.markdown("---")
    st.subheader("Summary")
    
    # Count by category
    label_counts = {}
    for label in st.session_state.coded_labels:
        if label is not None and not isinstance(label, dict):
            label_counts[label] = label_counts.get(label, 0) + 1
    
    # Count by context
    context_counts = {}
    for context in st.session_state.context_labels:
        if context is not None and not isinstance(context, dict):
            context_counts[context] = context_counts.get(context, 0) + 1
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**People Categories:**")
        if label_counts:
            for code, count in sorted(label_counts.items()):
                st.write(f"• {CATEGORIES[code]}: {count} images")
        else:
            st.write("No images coded yet")
    
    with col2:
        st.write("**Context Categories:**")
        if context_counts:
            for code, count in sorted(context_counts.items()):
                st.write(f"• {CONTEXT_CATEGORIES[code]}: {count} images")
        else:
            st.write("No context labels assigned")
    # Export button
    if coded_count == total_images:
        st.success("🎉 All images have been coded!")
        if st.button("💾 Prepare Final Results for Download", type="primary"):
            # Convert progress data to list format
            final_labels = []
            final_context = []
            for i in range(total_images):
                if str(i) in progress_data:
                    if isinstance(progress_data[str(i)], dict):
                        final_labels.append(progress_data[str(i)].get('group_label'))
                        final_context.append(progress_data[str(i)].get('context'))
                    else:
                        # Handle old format (just group label)
                        final_labels.append(progress_data[str(i)])
                        final_context.append(None)
                else:
                    final_labels.append(None)
                    final_context.append(None)
            
            save_final_results(metadata_df, final_labels, final_context)
    else:
        st.info(f"Complete coding all {total_images} images to export final results.")
    
    # Download progress backup
    st.markdown("---")
    
    # Always available download section
    st.subheader("💾 Download Progress")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Download Progress Backup (JSON)"):
            progress_json = json.dumps(progress_data, indent=2)
            st.download_button(
                label="📁 Download backup.json",
                data=progress_json,
                file_name=f"coding_progress_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("📊 Download Current Results (CSV)"):
            # Convert current progress to CSV format
            current_labels = []
            current_context = []
            for i in range(total_images):
                if str(i) in progress_data:
                    if isinstance(progress_data[str(i)], dict):
                        current_labels.append(progress_data[str(i)].get('group_label'))
                        current_context.append(progress_data[str(i)].get('context'))
                    else:
                        # Handle old format
                        current_labels.append(progress_data[str(i)])
                        current_context.append(None)
                else:
                    current_labels.append(None)
                    current_context.append(None)
            
            # Create a copy of the metadata and add coding columns
            export_df = metadata_df.copy()
            export_df['group_labels'] = current_labels
            export_df['context_labels'] = current_context
            export_df['coding_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            export_df['completion_status'] = f"{coded_count}/{total_images} images coded"
            
            # Convert to CSV
            csv_data = export_df.to_csv(index=False)
            
            st.download_button(
                label="📊 Download current-results.csv",
                data=csv_data,
                file_name=f"ra-shingle-progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
