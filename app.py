import streamlit as st
import requests
import io
import pandas as pd
import zipfile

st.title("🧪 Connection Test - Phase 2")

try:
    st.write("Testing secrets access...")
    csv_url = st.secrets["data_files"]["csv_url"]
    images_zip_url = st.secrets["data_files"]["images_zip_url"]
    st.success("✅ Secrets loaded successfully!")
    
    st.write("Testing CSV download...")
    csv_response = requests.get(csv_url, timeout=10)
    csv_response.raise_for_status()
    df = pd.read_csv(io.StringIO(csv_response.text))
    st.success(f"✅ CSV download successful! {len(df)} rows")
    
    st.write("Testing ZIP download...")
    zip_response = requests.get(images_zip_url, timeout=60)
    zip_response.raise_for_status()
    zip_size_mb = len(zip_response.content) / (1024 * 1024)
    st.success(f"✅ ZIP download successful! Size: {zip_size_mb:.1f} MB")
    
    st.write("Testing ZIP file structure...")
    with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zip_file:
        file_list = zip_file.filelist
        image_files = [f.filename for f in file_list if f.filename.lower().endswith(('.jpg', '.jpeg', '.png'))]
        st.success(f"✅ ZIP contains {len(image_files)} image files")
        
        if len(image_files) > 0:
            st.write("Sample image filenames:")
            for i, filename in enumerate(image_files[:5]):
                st.write(f"- {filename}")
            
            # Test loading just ONE image
            st.write("Testing single image load...")
            with zip_file.open(image_files[0]) as image_file:
                from PIL import Image
                img = Image.open(io.BytesIO(image_file.read()))
                st.success(f"✅ Successfully loaded one image: {img.size}")
                st.image(img, caption=f"Test image: {image_files[0]}", width=300)
    
except Exception as e:
    st.error(f"❌ Error: {e}")
    import traceback
    st.code(traceback.format_exc())
