import streamlit as st
import requests
import io
import pandas as pd

st.title("🧪 Connection Test")

try:
    st.write("Testing secrets access...")
    csv_url = st.secrets["data_files"]["csv_url"]
    st.success("✅ Secrets loaded successfully!")
    
    st.write("Testing CSV download...")
    csv_response = requests.get(csv_url, timeout=10)
    csv_response.raise_for_status()
    st.success("✅ CSV download successful!")
    
    st.write("Testing CSV parsing...")
    df = pd.read_csv(io.StringIO(csv_response.text))
    st.success(f"✅ CSV parsed successfully! {len(df)} rows found")
    
    st.write("First 5 rows:")
    st.dataframe(df.head())
    
except Exception as e:
    st.error(f"❌ Error: {e}")
    import traceback
    st.code(traceback.format_exc())
